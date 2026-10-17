"""Dependency-free Gizwits LAN transport and AirJet V01 codec."""

from __future__ import annotations

import asyncio
import contextlib
import socket
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

PRODUCT_KEY = "d3ac9226d983470284b5d133cf4fd6b4"
MAX_FRAME = 4096


class ProtocolError(Exception):
    """Invalid or failed protocol exchange."""


class AuthenticationError(ProtocolError):
    """Physical binding or valid cached credentials required."""


class UnsupportedDeviceError(ProtocolError):
    """Unsupported product profile."""


class ConnectionError(ProtocolError):
    """Client is disconnected."""


class CommandAmbiguousError(ProtocolError):
    """Sent control outcome is unknown; do not replay."""


class ValidationError(ValueError):
    """Invalid control input."""


@dataclass(frozen=True)
class DeviceIdentity:
    mac: str
    product_key: str
    device_id: str
    wifi_firmware: str


@dataclass(frozen=True)
class SpaState:
    raw: bytes
    current_temperature: int
    target_temperature: int
    unit: str
    power: bool
    locked: bool
    heat_code: int
    filter_code: int
    bubbles: int
    target_reached: bool
    errors: tuple[str, ...]

    @property
    def version(self):
        return int.from_bytes(self.raw[39:41], "big")


def decode_status(payload):
    if len(payload) != 46 or payload[0] not in (3, 4):
        raise ProtocolError("Invalid V01 status")
    raw = bytes(payload[1:])
    faults = int.from_bytes(raw[41:45], "big")
    return SpaState(
        raw,
        raw[38],
        raw[1],
        "C" if raw[0] & 2 else "F",
        bool(raw[0] & 1),
        bool(raw[0] & 4),
        raw[2],
        raw[3],
        raw[4],
        bool(faults & (1 << 31)),
        tuple(f"E{i + 1:02}" for i in range(31) if faults & (1 << i)),
    )


def encode_control(state, updates):
    raw = bytearray(state.raw[:38])
    mask = 0
    attrs = {
        "power": (0, 0),
        "locked": (2, 0),
        "target_temperature": (8, 1),
        "heat": (9, 2),
        "filter": (10, 3),
        "bubbles": (11, 4),
    }
    if not updates:
        raise ValidationError("No controls supplied")
    for key, value in updates.items():
        if key not in attrs:
            raise ValidationError("Unsupported control")
        attr, offset = attrs[key]
        if key in ("power", "locked", "heat", "filter"):
            if type(value) is not bool:
                raise ValidationError("Control requires a boolean")
            number = int(value)
        else:
            if type(value) is not int:
                raise ValidationError("Control requires an integer")
            bounds = (20, 40) if state.unit == "C" else (68, 104)
            low, high = bounds if key == "target_temperature" else (0, 100)
            if not low <= value <= high:
                raise ValidationError("Control outside native range")
            number = value
        if key in ("power", "locked"):
            bit = 1 if key == "power" else 4
            raw[0] = (raw[0] & ~bit) | (bit if number else 0)
        else:
            raw[offset] = number
        mask |= 1 << attr
    return b"\x01" + mask.to_bytes(4, "big") + raw


@dataclass(frozen=True)
class ProductProfile:
    """An explicitly verified product's state and control codecs."""

    product_key: str
    model: str
    decode: Callable[[bytes], SpaState]
    encode: Callable[[SpaState, Mapping[str, object]], bytes]


PROFILES: Mapping[str, ProductProfile] = MappingProxyType(
    {
        PRODUCT_KEY: ProductProfile(PRODUCT_KEY, "AirJet V01", decode_status, encode_control),
    }
)


def frame(command, payload=b""):
    body = b"\x00" + command.to_bytes(2, "big") + payload
    length = len(body)
    encoded = bytearray()
    while True:
        part = length & 127
        length >>= 7
        encoded.append(part | (128 if length else 0))
        if not length:
            break
    return b"\x00\x00\x00\x03" + encoded + body


def parse_frame(data):
    if data[:4] != b"\x00\x00\x00\x03":
        raise ProtocolError("Invalid frame header")
    length = 0
    for i in range(4):
        pos = 4 + i
        if pos >= len(data):
            raise ProtocolError("Truncated length")
        value = data[pos]
        length |= (value & 127) << (7 * i)
        if not value & 128:
            break
    else:
        raise ProtocolError("Invalid frame length")
    body = data[pos + 1 :]
    if length < 3 or length > MAX_FRAME or len(body) != length or body[0] != 0:
        raise ProtocolError("Invalid frame size or flags")
    return int.from_bytes(body[1:3], "big"), body[3:]


def parse_identity(payload):
    offset = 0

    def field():
        nonlocal offset
        if offset + 2 > len(payload):
            raise ProtocolError("Truncated identity")
        length = int.from_bytes(payload[offset : offset + 2], "big")
        offset += 2
        if offset + length > len(payload):
            raise ProtocolError("Truncated identity")
        result = payload[offset : offset + length]
        offset += length
        return result

    try:
        device_id, mac, firmware, key = field(), field(), field(), field()
        if len(mac) != 6:
            raise ProtocolError("Invalid identity")
        product_key = key.decode("ascii")
        if product_key not in PROFILES:
            raise UnsupportedDeviceError("Unsupported product key")
        return DeviceIdentity(
            mac.hex(), product_key, device_id.decode("ascii"), firmware.decode("ascii")
        )
    except UnicodeError as err:
        raise ProtocolError("Invalid identity encoding") from err


class Client:
    """One serialized stream and heartbeat. Credentials never appear in repr."""

    def __init__(
        self,
        host,
        passcode=None,
        timeout=5,
        port=12416,
        discovery_port=12414,
        *,
        heartbeat_interval=4,
    ):
        self.host = host
        self.passcode = passcode
        self.timeout = timeout
        self.port = port
        self.discovery_port = discovery_port
        self.identity = None
        self.profile: ProductProfile | None = None
        self.last_state = None
        self._reader = self._writer = self._heartbeat = None
        self._lock = asyncio.Lock()
        self._sequence = 0
        self._heartbeat_interval = heartbeat_interval
        self._opener = None
        self._generation = 0

    @property
    def connected(self):
        return self._writer is not None and not self._writer.is_closing()

    async def _discover(self):
        loop = asyncio.get_running_loop()
        addresses = await loop.getaddrinfo(
            self.host, self.discovery_port, family=socket.AF_INET, type=socket.SOCK_DGRAM
        )
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        try:
            peer = addresses[0][4]
            await loop.sock_sendto(sock, frame(3), peer)
            while True:
                data, source = await loop.sock_recvfrom(sock, MAX_FRAME + 16)
                if source[0] == peer[0]:
                    break
            command, payload = parse_frame(data)
            if command != 4:
                raise ProtocolError("Unexpected discovery reply")
            return parse_identity(payload)
        finally:
            sock.close()

    async def _receive(self):
        reader = self._reader
        if reader is None:
            raise ConnectionError("Client is closed")
        prefix = await reader.readexactly(4)
        encoded = bytearray()
        size = 0
        for i in range(4):
            value = (await reader.readexactly(1))[0]
            encoded.append(value)
            size |= (value & 127) << (7 * i)
            if not value & 128:
                break
        else:
            raise ProtocolError("Invalid frame length")
        if size < 3 or size > MAX_FRAME:
            raise ProtocolError("Invalid frame size")
        return parse_frame(prefix + encoded + await reader.readexactly(size))

    async def _exchange(self, command, payload, reply, sequence=None):
        if not self.connected:
            raise ConnectionError("Client is closed")
        async with asyncio.timeout(self.timeout):
            self._writer.write(frame(command, payload))
            await self._writer.drain()
            while True:
                try:
                    received, data = await self._receive()
                except asyncio.IncompleteReadError:
                    raise ConnectionError("Device disconnected during exchange") from None
                if received == 0x91:
                    self.last_state = self.profile.decode(data)
                if received == reply and (sequence is None or data[:4] == sequence):
                    if reply == 0x91 and data[0] != 3:
                        continue
                    return data
                if received == 0x94 and len(data) >= 5 and data[4] in (3, 4):
                    self.last_state = self.profile.decode(data[4:])

    async def async_open(self):
        generation = self._generation
        async with self._lock:
            if generation != self._generation:
                raise ConnectionError("Client closed while waiting to connect")
            if self.connected:
                return
            self._opener = asyncio.current_task()
            try:
                async with asyncio.timeout(self.timeout):
                    identity = await self._discover()
                    if self.identity and identity.mac != self.identity.mac:
                        raise ProtocolError("Device identity changed")
                    self.identity = identity
                    self.profile = PROFILES[identity.product_key]
                    self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
                result = await self._exchange(6, b"", 7)
                if len(result) < 2 or len(result[2:]) != int.from_bytes(result[:2], "big"):
                    raise ProtocolError("Invalid passcode reply")
                try:
                    credential = result[2:].decode("ascii") or self.passcode
                    if not credential:
                        raise AuthenticationError("Physical binding is required")
                    encoded = credential.encode("ascii")
                except UnicodeError, AttributeError:
                    raise AuthenticationError("Invalid credential encoding") from None
                if len(encoded) != 10 or not encoded.isalnum():
                    raise AuthenticationError("Invalid credential format")
                if await self._exchange(8, len(encoded).to_bytes(2, "big") + encoded, 9) != b"\x00":
                    raise AuthenticationError("Device login rejected")
                self.passcode = credential
                self._heartbeat = asyncio.create_task(self._heartbeat_loop())
            except BaseException:
                await self.async_close()
                raise
            finally:
                if self._opener is asyncio.current_task():
                    self._opener = None

    async def _read(self):
        if self.profile is None:
            raise ConnectionError("Client has no verified product profile")
        return self.profile.decode(await self._exchange(0x90, b"\x02", 0x91))

    async def async_read_state(self):
        async with self._lock:
            try:
                self.last_state = await self._read()
                return self.last_state
            except BaseException:
                await self.async_close()
                raise

    async def async_set_values(self, updates):
        async with self._lock:
            sent = False
            try:
                state = await self._read()
                control = self.profile.encode(state, updates)
                self._sequence = (self._sequence + 1) & 0xFFFFFFFF
                sequence = self._sequence.to_bytes(4, "big")
                sent = True
                await self._exchange(0x93, sequence + control, 0x94, sequence)
                self.last_state = await self._read()
                for key, requested in updates.items():
                    observed = getattr(
                        self.last_state,
                        {"heat": "heat_code", "filter": "filter_code"}.get(key, key),
                    )
                    if key in ("heat", "filter"):
                        observed = bool(observed)
                    if observed != requested:
                        raise ProtocolError("Control readback differs from request")
                return self.last_state
            except ValueError:
                raise
            except BaseException as err:
                await self.async_close()
                if sent and isinstance(err, Exception):
                    raise CommandAmbiguousError("Control outcome is unconfirmed") from err
                raise

    async def _heartbeat_loop(self):
        try:
            while True:
                await asyncio.sleep(self._heartbeat_interval)
                async with self._lock:
                    await self._exchange(0x15, b"", 0x16)
        except asyncio.CancelledError:
            raise
        except Exception:
            await self.async_close()

    async def async_close(self):
        self._generation += 1
        opener, self._opener = self._opener, None
        if opener and opener is not asyncio.current_task():
            opener.cancel()
        heartbeat, self._heartbeat = self._heartbeat, None
        writer, self._writer = self._writer, None
        self._reader = None
        if writer:
            writer.close()
        if heartbeat and heartbeat is not asyncio.current_task():
            heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat
        if opener and opener is not asyncio.current_task():
            with contextlib.suppress(asyncio.CancelledError):
                await opener
        if writer:
            with contextlib.suppress(Exception):
                async with asyncio.timeout(self.timeout):
                    await writer.wait_closed()
