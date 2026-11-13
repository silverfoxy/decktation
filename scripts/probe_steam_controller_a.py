#!/usr/bin/env python3
"""Send bounded A pulses through an existing Steam virtual Xbox evdev device."""
import argparse
import fcntl
import os
from pathlib import Path
import struct
import time

EVENT = struct.Struct('@llHHi')


def identity(fd):
    data = bytearray(8)
    fcntl.ioctl(fd, (2 << 30) | (8 << 16) | (ord('E') << 8) | 2, data)
    return struct.unpack('@HHHH', data)


def candidates():
    for entry in sorted(Path('/sys/class/input').glob('event*')):
        try:
            vendor = (entry / 'device/id/vendor').read_text().strip()
            product = (entry / 'device/id/product').read_text().strip()
            if (vendor, product) == ('28de', '11ff'):
                yield '/dev/input/' + entry.name
        except OSError:
            continue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', help='Exact Steam virtual controller event path')
    parser.add_argument('--send', action='store_true', help='Send five A pulses')
    parser.add_argument('--startup-delay', type=float, default=15)
    args = parser.parse_args()
    if not 0 <= args.startup_delay <= 300:
        parser.error('startup-delay must be 0..300 seconds')
    paths = list(candidates())
    if not args.send:
        print('Steam virtual gamepads:', ', '.join(paths) or 'none')
        print('Use --path /dev/input/eventN --send to send five pulses.')
        return
    if args.path not in paths:
        parser.error('--path must identify a discovered Steam virtual gamepad')
    fd = os.open(args.path, os.O_RDWR | os.O_NONBLOCK)
    try:
        if identity(fd)[1:3] != (0x28de, 0x11ff):
            parser.error('Opened device is not a Steam virtual gamepad')
        def emit(value):
            packet = EVENT.pack(0, 0, 1, 304, value) + EVENT.pack(0, 0, 0, 0, 0)
            if os.write(fd, packet) != len(packet):
                raise OSError('Short input event write')
        print(f'Target {args.path}; focus tester; do not hold physical A.', flush=True)
        time.sleep(args.startup_delay)
        for index in range(5):
            # Refuse to release a physical A press that was already held.
            keys = bytearray(96)
            fcntl.ioctl(fd, (2 << 30) | (96 << 16) | (ord('E') << 8) | 0x18, keys)
            if keys[304 // 8] & (1 << (304 % 8)):
                raise RuntimeError('A is already held; release it before testing')
            try:
                emit(1)
                time.sleep(0.1)
            finally:
                emit(0)
            print(f'A pulse {index + 1}/5 emitted; game delivery unconfirmed', flush=True)
            if index < 4:
                time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        os.close(fd)


if __name__ == '__main__':
    main()
