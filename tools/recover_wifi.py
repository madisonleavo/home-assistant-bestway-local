#!/usr/bin/env python3
"""Explicit, local Bestway V01 Wi-Fi provisioning; Python 3.11+, stdlib only."""

import argparse
import getpass
import ipaddress
import math
import socket
import warnings

MAGIC = b"\x00\x00\x00\x03"
PORT = 12414


def provision_packet(ssid, password):
    """Validate credentials before creating the command 1 packet."""
    name = ssid.encode("utf-8")
    if not 1 <= len(name) <= 32:
        raise ValueError("SSID must contain 1–32 UTF-8 bytes.")
    if password:
        valid_passphrase = 8 <= len(password) <= 63 and all(32 <= ord(c) <= 126 for c in password)
        valid_psk = len(password) == 64 and all(c in "0123456789abcdefABCDEF" for c in password)
        if not (valid_passphrase or valid_psk):
            raise ValueError(
                "Use an empty password, 8–63 ASCII characters, or 64 hexadecimal PSK digits."
            )
    secret = password.encode("ascii")
    body = (
        b"\x00\x00\x01"
        + len(name).to_bytes(2, "big")
        + name
        + len(secret).to_bytes(2, "big")
        + secret
    )
    # Minimal duplicated framing keeps this file usable without Home Assistant.
    remaining = len(body)
    encoded = bytearray()
    while True:
        part = remaining & 127
        remaining >>= 7
        encoded.append(part | (128 if remaining else 0))
        if not remaining:
            return MAGIC + encoded + body


def valid_ack(data):
    """Require exactly the empty command 2 ACK, zero flags and valid framing."""
    # Its three-byte body always uses a single MQTT remaining-length byte.
    return data == MAGIC + b"\x03\x00\x00\x02"


def recover(ssid, password, host="10.10.100.254", timeout=2.0, *, socket_factory=socket.socket):
    """Send at most three requests; each receives at most one bounded reply."""
    packet = provision_packet(ssid, password)
    if not math.isfinite(timeout) or not 0 < timeout <= 10:
        raise ValueError("Timeout must be greater than 0 and at most 10 seconds.")
    endpoint = (str(ipaddress.IPv4Address(host)), PORT)
    sock = socket_factory(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(timeout)
        for _ in range(3):
            sock.sendto(packet, endpoint)
            try:
                data, source = sock.recvfrom(4096)
            except TimeoutError:
                continue
            if source == endpoint and valid_ack(data):
                return True
        return False
    finally:
        sock.close()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Provision a Bestway V01 spa after manually joining its Wi-Fi AP. Credentials are prompted, never stored."
    )
    parser.add_argument(
        "--host", default="10.10.100.254", help="Spa AP IPv4 address (default: 10.10.100.254)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Seconds per attempt, greater than 0 and at most 10 (three attempts)",
    )
    args = parser.parse_args(argv)
    print("Manually join BW-Airjet-V01-xxxx first (AP password: 123456789).")
    print("This sends your entered Wi-Fi credentials locally to the selected spa AP.")
    try:
        ssid = input("Home 2.4 GHz Wi-Fi SSID: ")
        # Refuse getpass's echoing fallback in terminals without hidden input.
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("Home Wi-Fi password (hidden; empty for open Wi-Fi): ")
        acknowledged = recover(ssid, password, args.host, args.timeout)
    except (ValueError, UnicodeError):
        print(
            "Invalid input. Check SSID/password format, IPv4 host, and timeout; nothing was sent."
        )
        return 2
    except getpass.GetPassWarning:
        print("A terminal with hidden password input is required; nothing was sent.")
        return 2
    except (OSError, EOFError, KeyboardInterrupt):
        print(
            "Recovery interrupted or network unavailable. Check local network access and AP connection."
        )
        return 1
    if acknowledged:
        print(
            "Valid provisioning ACK received. This does not prove DHCP or home Wi-Fi connectivity."
        )
        print(
            "Reconnect your phone to home Wi-Fi and verify the spa in your router and Home Assistant."
        )
        return 0
    print(
        "No valid ACK after three attempts. Check the AP connection; do not reset the spa automatically."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
