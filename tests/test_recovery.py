"""Standalone recovery helper, with no real network traffic."""

import ast
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "recover_wifi", Path(__file__).parents[1] / "tools/recover_wifi.py"
)
r = importlib.util.module_from_spec(spec)


def test_helper_supports_python_311_syntax():
    ast.parse(Path(spec.origin).read_text(), feature_version=(3, 11))


def load():
    assert spec.loader is not None
    spec.loader.exec_module(r)
    return r


def test_packet():
    m = load()
    assert m.provision_packet("é", "12345678") == bytes.fromhex(
        "00000003110000010002c3a900083132333435363738"
    )
    assert m.provision_packet("x", "") == bytes.fromhex("00000003080000010001780000")


@pytest.mark.parametrize(
    "ssid,password",
    [
        ("", "12345678"),
        ("é" * 17, "12345678"),
        ("x", "short"),
        ("x", "é" * 8),
        ("x", "g" * 64),
        ("x", "x" * 65),
    ],
)
def test_reject_credentials_before_network(ssid, password):
    m = load()
    with pytest.raises(ValueError):
        m.recover(ssid, password, socket_factory=lambda *a: pytest.fail("network opened"))


def test_psk_and_limits():
    m = load()
    assert m.provision_packet("é" * 16, "a" * 64)
    assert m.provision_packet("x", " " * 8)


class FakeSocket:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.sent = []
        self.closed = False

    def settimeout(self, timeout):
        assert 0 < timeout <= 10

    def sendto(self, packet, endpoint):
        self.sent.append((packet, endpoint))

    def recvfrom(self, size):
        reply = next(self.replies, TimeoutError())
        if isinstance(reply, Exception):
            raise reply
        return reply

    def close(self):
        self.closed = True


ACK = bytes.fromhex("0000000303000002")
ENDPOINT = ("10.10.100.254", 12414)


def test_ack():
    m = load()
    sock = FakeSocket([(ACK, ENDPOINT)])
    assert m.recover("myssid", "secret123", socket_factory=lambda *a: sock)
    assert len(sock.sent) == 1
    assert sock.closed


@pytest.mark.parametrize(
    "reply,endpoint",
    [
        (ACK, ("10.10.100.1", 12414)),
        (ACK, (ENDPOINT[0], 1)),
        (b"bad", ENDPOINT),
        (ACK + b"x", ENDPOINT),
        (bytes.fromhex("0000000303010002"), ENDPOINT),
        (bytes.fromhex("0000000303000001"), ENDPOINT),
        (bytes.fromhex("0000000380808080000002"), ENDPOINT),
        (bytes.fromhex("0000000304000002"), ENDPOINT),
        (bytes.fromhex("000000030400000200"), ENDPOINT),
    ],
)
def test_foreign_or_malformed_ack(reply, endpoint):
    m = load()
    sock = FakeSocket([(reply, endpoint)] * 3)
    assert not m.recover("myssid", "secret123", socket_factory=lambda *a: sock)
    assert len(sock.sent) == 3
    assert sock.closed


def test_timeout_and_retry():
    m = load()
    sock = FakeSocket([TimeoutError(), (ACK, ENDPOINT)])
    assert m.recover("myssid", "secret123", socket_factory=lambda *a: sock)
    assert len(sock.sent) == 2
    sock = FakeSocket([])
    assert not m.recover("myssid", "secret123", socket_factory=lambda *a: sock)
    assert len(sock.sent) == 3


def test_cli_hidden_password_and_no_secret_output(monkeypatch, capsys):
    m = load()
    monkeypatch.setattr("builtins.input", lambda prompt: "privateSSID")
    monkeypatch.setattr(m.getpass, "getpass", lambda prompt: "privatePASSWORD")
    monkeypatch.setattr(m, "recover", lambda *a, **kw: True)
    assert m.main([]) == 0
    output = capsys.readouterr()
    assert "privateSSID" not in output.out + output.err
    assert "privatePASSWORD" not in output.out + output.err
    assert "DHCP" in output.out


@pytest.mark.parametrize("timeout", [0, -1, 11, float("nan"), float("inf")])
def test_timeout_validation(timeout):
    m = load()
    with pytest.raises(ValueError):
        m.recover(
            "x",
            "12345678",
            timeout=timeout,
            socket_factory=lambda *a: pytest.fail("network opened"),
        )
