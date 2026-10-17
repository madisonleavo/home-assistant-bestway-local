"""V01 codec and bounded transport behavior."""

import asyncio
import contextlib
from pathlib import Path

import pytest

from custom_components.bestway_spa_local import protocol as p

SAMPLE = bytes.fromhex((Path(__file__).parent / "fixtures/v01_status.hex").read_text())


def test_confirmed_status():
    s = p.decode_status(SAMPLE)
    assert (s.current_temperature, s.target_temperature, s.unit) == (104, 104, "F")
    assert (s.heat_code, s.filter_code, s.target_reached, s.errors) == (4, 2, True, ())
    assert s.power and s.locked


def test_control_mask_and_preservation():
    s = p.decode_status(SAMPLE)
    result = p.encode_control(s, {"locked": False, "target_temperature": 100, "heat": True})
    assert result[:5] == b"\x01" + ((1 << 2) | (1 << 8) | (1 << 9)).to_bytes(4, "big")
    expected = bytearray(s.raw[:38])
    expected[0] &= ~4
    expected[1] = 100
    expected[2] = 1
    assert result[5:] == expected


@pytest.mark.parametrize(
    "updates",
    [
        {"target_temperature": 105},
        {"target_temperature": True},
        {"power": 1},
        {"heat": 2},
        {"bubbles": 101},
        {"unit": "C"},
        {"target_temperature": 100.5},
    ],
)
def test_invalid_controls(updates):
    with pytest.raises(ValueError):
        p.encode_control(p.decode_status(SAMPLE), updates)


def test_celsius_bounds_and_faults():
    data = bytearray(SAMPLE)
    data[1] |= 2
    data[-1] = 1
    s = p.decode_status(data)
    assert s.errors == ("E01",)
    for v in (20, 40):
        p.encode_control(s, {"target_temperature": v})
    with pytest.raises(ValueError):
        p.encode_control(s, {"target_temperature": 41})


@pytest.mark.parametrize("data", [b"", SAMPLE[:-1], b"\x02" + SAMPLE[1:], SAMPLE + b"\x00"])
def test_invalid_status(data):
    with pytest.raises(p.ProtocolError):
        p.decode_status(data)


def identity_payload(key=p.PRODUCT_KEY, mac=b"\x02\x00\x00\x00\x00\x01"):
    values = (b"synthetic-device", mac, b"1.0", key.encode())
    return (
        b"".join(len(v).to_bytes(2, "big") + v for v in values)
        + bytes(8)
        + b"api.invalid\x004.0\x00"
    )


@pytest.mark.parametrize(
    "data", [b"", b"\0\0\0\3\x80\x80\x80\x80", b"\0\0\0\3\x03\0\0", b"\0\0\0\3\x80\x40"]
)
def test_malformed_frames(data):
    with pytest.raises(p.ProtocolError):
        p.parse_frame(data)


def test_identity_fields():
    identity = p.parse_identity(identity_payload())
    assert identity.mac == "020000000001"
    assert identity.device_id == "synthetic-device"
    assert identity.wifi_firmware == "1.0"
    with pytest.raises(p.UnsupportedDeviceError):
        p.parse_identity(identity_payload("x" * 32))
    with pytest.raises(p.ProtocolError):
        p.parse_identity(identity_payload()[:12])


class FakeSpa(asyncio.DatagramProtocol):
    def __init__(
        self,
        *,
        bind=True,
        ignore_control=False,
        ignore_read=False,
        key=p.PRODUCT_KEY,
        apply_control=True,
    ):
        self.apply_control = apply_control
        self.bind = bind
        self.ignore_control = ignore_control
        self.ignore_read = ignore_read
        self.key = key
        self.mac = bytes.fromhex("020000000001")
        self.raw = bytearray(SAMPLE)
        self.commands = []
        self.tasks = set()
        self.writers = set()
        self.read_started = asyncio.Event()
        self.control_started = asyncio.Event()
        self.heartbeats = 0

    def connection_made(self, transport):
        self.udp = transport

    def datagram_received(self, data, addr):
        assert p.parse_frame(data) == (3, b"")
        self.udp.sendto(p.frame(4, identity_payload(self.key, self.mac)), addr)

    async def start(self):
        loop = asyncio.get_running_loop()
        self.udp, _ = await loop.create_datagram_endpoint(lambda: self, local_addr=("127.0.0.1", 0))
        self.tcp = await asyncio.start_server(self.connected, "127.0.0.1", 0)
        return p.Client(
            "127.0.0.1",
            timeout=0.15,
            port=self.tcp.sockets[0].getsockname()[1],
            discovery_port=self.udp.get_extra_info("sockname")[1],
            heartbeat_interval=0.04,
        )

    async def stop(self):
        self.udp.close()
        self.tcp.close()
        await self.tcp.wait_closed()
        for writer in self.writers:
            writer.close()
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def connected(self, reader, writer):
        task = asyncio.current_task()
        self.tasks.add(task)
        self.writers.add(writer)
        helper = p.Client("unused")
        helper._reader = reader
        try:
            while True:
                command, payload = await helper._receive()
                self.commands.append((command, payload))
                if command == 6:
                    response = p.frame(7, b"\x00\x0a0123456789" if self.bind else b"\x00\x00")
                elif command == 8:
                    assert payload == b"\x00\x0a0123456789"
                    response = p.frame(9, b"\0")
                elif command == 0x90:
                    self.read_started.set()
                    if self.ignore_read:
                        continue
                    response = p.frame(0x91, bytes(self.raw))
                elif command == 0x93:
                    self.control_started.set()
                    if self.ignore_control:
                        continue
                    seq, control = payload[:4], payload[4:]
                    old_raw = self.raw[:]
                    mask = int.from_bytes(control[1:5], "big")
                    for attr, offset in ((8, 1), (9, 2), (10, 3), (11, 4)):
                        if mask & (1 << attr):
                            self.raw[1 + offset] = control[5 + offset]
                    for attr, bit in ((0, 1), (2, 4)):
                        if mask & (1 << attr):
                            self.raw[1] = (self.raw[1] & ~bit) | (control[5] & bit)
                    if not self.apply_control:
                        self.raw = old_raw
                    # Unsolicited update and wrong sequence are coalesced before matching ack.
                    response = (
                        p.frame(0x91, bytes(self.raw)) + p.frame(0x94, b"xxxx") + p.frame(0x94, seq)
                    )
                elif command == 0x15:
                    self.heartbeats += 1
                    response = p.frame(0x91, bytes(self.raw)) + p.frame(0x16)
                else:
                    raise AssertionError(command)
                for offset in range(0, len(response), 3):
                    writer.write(response[offset : offset + 3])
                    await writer.drain()
                    await asyncio.sleep(0)
        except asyncio.IncompleteReadError, ConnectionResetError:
            pass
        finally:
            writer.close()
            with contextlib.suppress(ConnectionResetError):
                await writer.wait_closed()
            self.writers.discard(writer)
            self.tasks.discard(task)


@pytest.mark.enable_socket
async def test_loopback_control_fragmentation_heartbeat_and_cached_passcode():
    spa = FakeSpa(bind=False)
    client = await spa.start()
    client.passcode = "0123456789"
    try:
        await client.async_open()
        await client.async_open()
        assert "0123456789" not in repr(client)
        assert (await client.async_read_state()).heat_code == 4
        state = await client.async_set_values({"target_temperature": 100, "locked": False})
        assert state.target_temperature == 100 and not state.locked
        assert [c for c, _ in spa.commands][:6] == [6, 8, 0x90, 0x90, 0x93, 0x90]
        await asyncio.sleep(0.07)
        assert spa.heartbeats >= 1
    finally:
        await client.async_close()
        await spa.stop()
    assert not client.connected and client._heartbeat is None


@pytest.mark.enable_socket
async def test_ambiguous_write_is_never_retried():
    spa = FakeSpa(ignore_control=True)
    client = await spa.start()
    try:
        await client.async_open()
        with pytest.raises(p.CommandAmbiguousError):
            await client.async_set_values({"power": False})
        assert len([c for c, _ in spa.commands if c == 0x93]) == 1
        assert not client.connected
    finally:
        await client.async_close()
        await spa.stop()


@pytest.mark.enable_socket
async def test_close_interrupts_pending_read():
    spa = FakeSpa(ignore_read=True)
    client = await spa.start()
    try:
        await client.async_open()
        pending = asyncio.create_task(client.async_read_state())
        await spa.read_started.wait()
        await asyncio.wait_for(client.async_close(), 0.1)
        with pytest.raises((p.ProtocolError, asyncio.IncompleteReadError, OSError)):
            await asyncio.wait_for(pending, 0.1)
    finally:
        await client.async_close()
        await spa.stop()


@pytest.mark.enable_socket
async def test_binding_required_and_unknown_product():
    for bind, key, exception in (
        (False, p.PRODUCT_KEY, p.AuthenticationError),
        (True, "x" * 32, p.UnsupportedDeviceError),
    ):
        spa = FakeSpa(bind=bind, key=key)
        client = await spa.start()
        try:
            with pytest.raises(exception):
                await client.async_open()
            assert not client.connected and client._heartbeat is None
        finally:
            await client.async_close()
            await spa.stop()


@pytest.mark.enable_socket
async def test_cancellation_closes_connection():
    spa = FakeSpa(ignore_read=True)
    client = await spa.start()
    try:
        await client.async_open()
        pending = asyncio.create_task(client.async_read_state())
        await spa.read_started.wait()
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert not client.connected and client._heartbeat is None
    finally:
        await client.async_close()
        await spa.stop()


@pytest.mark.enable_socket
async def test_disconnect_is_protocol_error():
    spa = FakeSpa(ignore_read=True)
    client = await spa.start()
    try:
        await client.async_open()
        pending = asyncio.create_task(client.async_read_state())
        await spa.read_started.wait()
        for writer in list(spa.writers):
            writer.close()
        with pytest.raises(p.ProtocolError):
            await pending
        assert not client.connected
    finally:
        await client.async_close()
        await spa.stop()


@pytest.mark.enable_socket
async def test_readback_mismatch_is_reported_without_replay():
    spa = FakeSpa(apply_control=False)
    client = await spa.start()
    try:
        await client.async_open()
        with pytest.raises(p.CommandAmbiguousError):
            await client.async_set_values({"target_temperature": 100})
        assert len([c for c, _ in spa.commands if c == 0x93]) == 1
    finally:
        await client.async_close()
        await spa.stop()


@pytest.mark.enable_socket
async def test_identity_change_rejected_on_reconnect():
    spa = FakeSpa()
    client = await spa.start()
    try:
        await client.async_open()
        await client.async_close()
        spa.mac = bytes.fromhex("020000000002")
        with pytest.raises(p.ProtocolError, match="identity changed"):
            await client.async_open()
        assert not client.connected
    finally:
        await client.async_close()
        await spa.stop()


@pytest.mark.enable_socket
async def test_passcode_encoding_error_is_redacted():
    spa = FakeSpa(bind=False)
    client = await spa.start()
    client.passcode = "secret-☃"
    try:
        with pytest.raises(p.AuthenticationError) as error:
            await client.async_open()
        assert "secret" not in str(error.value)
        assert error.value.__suppress_context__
        assert not client.connected
    finally:
        await client.async_close()
        await spa.stop()


@pytest.mark.enable_socket
async def test_discovery_accepts_same_host_reply_from_different_port():
    spa = FakeSpa()
    client = await spa.start()
    loop = asyncio.get_running_loop()
    alternate, _ = await loop.create_datagram_endpoint(
        asyncio.DatagramProtocol, local_addr=("127.0.0.1", 0)
    )
    primary = spa.udp
    spa.udp = alternate
    try:
        await client.async_open()
        assert client.identity.mac == "020000000001"
    finally:
        await client.async_close()
        await spa.stop()
        primary.close()


@pytest.mark.enable_socket
async def test_queued_push_is_not_mistaken_for_fresh_read():
    spa = FakeSpa()
    client = await spa.start()
    try:
        await client.async_open()
        await client.async_read_state()
        stale_push = b"\x04" + SAMPLE[1:]
        for writer in spa.writers:
            writer.write(p.frame(0x91, stale_push))
            await writer.drain()
        spa.raw[2] = 99
        assert (await client.async_read_state()).target_temperature == 99
    finally:
        await client.async_close()
        await spa.stop()


@pytest.mark.enable_socket
async def test_foreign_udp_reply_is_ignored():
    spa = FakeSpa()
    client = await spa.start()
    loop = asyncio.get_running_loop()
    foreign, _ = await loop.create_datagram_endpoint(
        asyncio.DatagramProtocol, local_addr=("127.0.0.2", 0)
    )
    primary = spa.udp

    class InjectForeign:
        def sendto(self, data, addr):
            foreign.sendto(p.frame(4, identity_payload("x" * 32)), addr)
            loop.call_later(0.01, primary.sendto, data, addr)

    spa.udp = InjectForeign()
    try:
        await client.async_open()
        assert client.identity.product_key == p.PRODUCT_KEY
    finally:
        spa.udp = primary
        await client.async_close()
        await spa.stop()
        foreign.close()


@pytest.mark.enable_socket
async def test_read_timeout_cleans_up_and_can_reconnect():
    spa = FakeSpa(ignore_read=True)
    client = await spa.start()
    try:
        await client.async_open()
        with pytest.raises(TimeoutError):
            await client.async_read_state()
        assert not client.connected and client._heartbeat is None
        spa.ignore_read = False
        await client.async_open()
        assert (await client.async_read_state()).current_temperature == 104
    finally:
        await client.async_close()
        await spa.stop()


@pytest.mark.enable_socket
async def test_control_uses_fresh_reserved_bytes():
    spa = FakeSpa()
    client = await spa.start()
    try:
        await client.async_open()
        await client.async_read_state()
        spa.raw[31] = 123
        await client.async_set_values({"bubbles": 50, "heat": True})
        payload = next(payload for command, payload in spa.commands if command == 0x93)
        assert payload[4 + 5 + 30] == 123
        assert client.last_state.bubbles == 50
    finally:
        await client.async_close()
        await spa.stop()


@pytest.mark.enable_socket
async def test_oversized_stream_frame_closes_connection():
    spa = FakeSpa(ignore_read=True)
    client = await spa.start()
    try:
        await client.async_open()
        pending = asyncio.create_task(client.async_read_state())
        await spa.read_started.wait()
        for writer in spa.writers:
            writer.write(b"\x00\x00\x00\x03\x80\x40")
            await writer.drain()
        with pytest.raises(p.ProtocolError):
            await pending
        assert not client.connected
    finally:
        await client.async_close()
        await spa.stop()


def test_empty_device_id_is_valid_with_mac_and_product_key():
    payload = identity_payload()
    length = int.from_bytes(payload[:2], "big")
    identity = p.parse_identity(b"\x00\x00" + payload[2 + length :])
    assert identity.device_id == ""
    assert identity.mac == "020000000001"


@pytest.mark.enable_socket
@pytest.mark.parametrize("stage", ["discovery", "tcp"])
async def test_close_cancels_pending_open(stage, monkeypatch):
    spa = FakeSpa()
    client = await spa.start()
    entered = asyncio.Event()
    release = asyncio.Event()
    original = client._discover if stage == "discovery" else asyncio.open_connection

    async def blocked(*args, **kwargs):
        entered.set()
        await release.wait()
        return await original(*args, **kwargs)

    if stage == "discovery":
        monkeypatch.setattr(client, "_discover", blocked)
    else:
        monkeypatch.setattr(asyncio, "open_connection", blocked)
    opening = asyncio.create_task(client.async_open())
    try:
        await entered.wait()
        await asyncio.wait_for(client.async_close(), 0.1)
        assert opening.done(), "close must finish pending connection setup"
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await opening
        assert not client.connected and client._heartbeat is None
    finally:
        release.set()
        await asyncio.gather(opening, return_exceptions=True)
        await client.async_close()
        await spa.stop()


def test_profile_registry_is_immutable_and_contains_only_confirmed_model():
    from dataclasses import FrozenInstanceError

    assert set(p.PROFILES) == {p.PRODUCT_KEY}
    profile = p.PROFILES[p.PRODUCT_KEY]
    assert profile.model == "AirJet V01"
    assert profile.decode is p.decode_status and profile.encode is p.encode_control
    with pytest.raises(TypeError):
        p.PROFILES["unverified"] = profile
    with pytest.raises(FrozenInstanceError):
        profile.model = "changed"


@pytest.mark.enable_socket
async def test_client_routes_status_and_controls_through_verified_profile(monkeypatch):
    from types import MappingProxyType

    decodes = []
    encodes = []

    def decode(payload):
        decodes.append(bytes(payload))
        return p.decode_status(payload)

    def encode(state, updates):
        encodes.append(dict(updates))
        return p.encode_control(state, updates)

    profile = p.ProductProfile(p.PRODUCT_KEY, "Synthetic test delegate", decode, encode)
    monkeypatch.setattr(p, "PROFILES", MappingProxyType({p.PRODUCT_KEY: profile}))
    spa = FakeSpa()
    client = await spa.start()
    try:
        await client.async_open()
        assert client.profile is profile
        assert (await client.async_read_state()).current_temperature == 104
        await client.async_set_values({"target_temperature": 100})
        assert encodes == [{"target_temperature": 100}]
        assert decodes and any(data[2] == 100 for data in decodes)
        assert client.last_state.target_temperature == 100
        with pytest.raises(p.UnsupportedDeviceError):
            p.parse_identity(identity_payload("x" * 32))
    finally:
        await client.async_close()
        await spa.stop()


async def test_read_before_open_raises_protocol_error():
    client = p.Client("127.0.0.1")
    with pytest.raises(p.ConnectionError):
        await client.async_read_state()
