"""Scan for devices via mDNS, pick one, send a raw command and read the reply.

Usage:
    uv run main.py
"""

import socket
import time

from zeroconf import (
    IPVersion,
    InterfaceChoice,
    ServiceBrowser,
    ServiceListener,
    Zeroconf,
)

SERVICE_TYPE = "_kv-command-api._tcp.local."
SCAN_SECONDS = 3


def scan() -> list[tuple[str, str, int]]:
    """Return a list of (name, address, port) for every device found."""
    zc = Zeroconf(interfaces=InterfaceChoice.All, ip_version=IPVersion.All)
    names: list[str] = []

    class Listener(ServiceListener):
        def add_service(self, zc, type_, name):
            names.append(name)

    ServiceBrowser(zc, SERVICE_TYPE, Listener())
    print(f"Scanning for {SERVICE_TYPE} ({SCAN_SECONDS}s) ...")
    time.sleep(SCAN_SECONDS)

    devices = []
    for name in names:
        info = zc.get_service_info(SERVICE_TYPE, name)
        if info and info.port:
            for addr in info.parsed_scoped_addresses():
                devices.append((name, addr, info.port))
    zc.close()
    return devices


def select(devices: list[tuple[str, str, int]]) -> tuple[str, int]:
    for i, (name, addr, port) in enumerate(devices):
        print(f"  [{i}] {name}  {addr}:{port}")
    i = int(input("Select device: ")) if len(devices) > 1 else 0
    _, addr, port = devices[i]
    return addr, port


def recv(sock: socket.socket, n: int) -> bytes:
    """Read exactly n bytes from the socket."""
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError(f"expected {n} bytes, got {len(data)}")
        data += chunk
    return data


def u16(b: bytes) -> int:
    return int.from_bytes(b, "little")


def make_packet(command: int, payload):
    return (
        command.to_bytes(2, 'little')
        + len(payload).to_bytes(2, 'little')
        + payload
    )


def main() -> None:
    devices = scan()
    if not devices:
        print("No devices found.")
        return
    host, port = select(devices)

    payload = make_packet(
        47,  # reboot command
        bytes([0, 0, 0, 0])
    )

    print(f'host: {host}, port: {port}')

# -    print(f"Connecting to {host}:{port} ...")
# -    sock = socket.create_connection((host, port), timeout=10)
# -    sock.settimeout(None)
# -    print("Connected. Type /help for input formats.\n")

    with socket.create_connection((host, port), timeout=10) as sock:
        sock.sendall(payload)
        print(f"Sent:     {list(payload)}")

        header = recv(sock, 4)
        command = int.from_bytes(header[0:2], 'little')
        payload_len = int.from_bytes(header[2:], 'little')
        payload = recv(sock, payload_len)
        print("Received:")
        print(f"  command: {command}")
        print(f"  payload_length: {payload_len}")
        print(f"  payload: {payload}")

    status = int.from_bytes(payload, 'little')
    if status == 0:
        print("Reboot ok")
    else:
        print(f"Reboot failed with error: {status}")


if __name__ == "__main__":
    main()
