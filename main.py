'''Scan for devices via mDNS and send a reboot command to each device.

Usage:
    uv run main.py
'''

import socket
import time
import argparse

from zeroconf import (
    IPVersion,
    InterfaceChoice,
    ServiceBrowser,
    ServiceListener,
    Zeroconf,
)
import sys

SERVICE_TYPE = '_kv-command-api._tcp.local.'


def scan(timeout: int) -> list[tuple[str, str, int]]:
    '''Return a list of (name, address, port) for every device found.'''
    zc = Zeroconf(interfaces=InterfaceChoice.All, ip_version=IPVersion.All)
    names: list[str] = []

    class Listener(ServiceListener):
        def add_service(self, zc, type_, name):
            names.append(name)

    ServiceBrowser(zc, SERVICE_TYPE, Listener())

    sys.stdout.write('Scanning for devices')
    for _ in range(0, timeout):
        sys.stdout.write('.')
        sys.stdout.flush()
        time.sleep(1)

    sys.stdout.write('\n')

    devices = []
    for name in names:
        info = zc.get_service_info(SERVICE_TYPE, name)
        if info and info.port:
            for addr in info.parsed_scoped_addresses():
                devices.append((name, addr, info.port))
    zc.close()
    return devices


def recv(sock: socket.socket, n: int) -> bytes:
    '''Read exactly n bytes from the socket.'''
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError(f'expected {n} bytes, got {len(data)}')
        data += chunk
    return data


def make_packet(command: int, payload):
    return (
        command.to_bytes(2, 'little')
        + len(payload).to_bytes(2, 'little')
        + payload
    )


def reboot_device(device: tuple[str, str, int]):
    payload = make_packet(
        47,  # reboot command
        bytes([0, 0, 0, 0])
    )

    name, host, port = device

    with socket.create_connection((host, port), timeout=10) as sock:
        sock.sendall(payload)
        header = recv(sock, 4)
        in_payload_len = int.from_bytes(header[2:], 'little')
        command = int.from_bytes(header[0:2], 'little')
        in_payload = recv(sock, in_payload_len)

    status = int.from_bytes(in_payload, 'little')

    if command == 48 and status == 0:
        print(f'[{name}]: Reboot command successfully sent!')
    else:
        print(f'[{name}]: Reboot command failed with error: {status}')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--delay', type=int, default=0,
        help='Delay between devices in seconds'
    )
    parser.add_argument(
        '--mdns-timeout', type=int, default=3,
        help='mDNS scan timeout in seconds'
    )
    parser.add_argument(
        '--reboot-wait', type=int, default=2,
        help='Time to wait for devices to restart'
    )
    args = parser.parse_args()

    devices = scan(args.mdns_timeout)

    if devices:
        for device in devices:
            reboot_device(device)
            if args.delay and device != devices[-1]:
                time.sleep(args.delay)

        time.sleep(args.reboot_wait)
        devices_post_reboot = scan(args.mdns_timeout)
        if len(devices_post_reboot) != len(devices):
            print('Device list missmatch')
            print(f'prior to reboot: {devices}')
            print(f'after reboot: {devices_post_reboot}')
    else:
        print('No devices found.')


if __name__ == '__main__':
    main()
