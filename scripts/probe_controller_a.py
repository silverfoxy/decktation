#!/usr/bin/env python3
"""Create a persistent Linux gamepad and pulse A; run only for manual testing."""
import argparse
import fcntl
import os
import struct
import time


EVENT = struct.Struct('@llHHi')


def ioctl_write(number, size):
    return (1 << 30) | (size << 16) | (ord('U') << 8) | number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interval', type=float, default=5,
                        help='Seconds between A presses (default: 5)')
    parser.add_argument('--hold-ms', type=int, default=100)
    parser.add_argument('--startup-delay', type=float, default=15)
    args = parser.parse_args()
    if args.interval < 1 or not 20 <= args.hold_ms <= 1000 or args.startup_delay < 0:
        parser.error('Require interval >= 1, hold-ms 20..1000, startup-delay >= 0')

    fd = os.open('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK)

    def emit(kind, code, value):
        os.write(fd, EVENT.pack(0, 0, kind, code, value))

    created = False
    try:
        for kind in (1, 3):  # EV_KEY, EV_ABS
            fcntl.ioctl(fd, ioctl_write(100, 4), kind)
        for button in (304, 305, 307, 308, 310, 311, 314, 315, 316, 317, 318):
            fcntl.ioctl(fd, ioctl_write(101, 4), button)
        for axis in (0, 1, 2, 3, 4, 5, 16, 17):
            fcntl.ioctl(fd, ioctl_write(103, 4), axis)
            minimum, maximum = ((0, 255) if axis in (2, 5) else
                                (-1, 1) if axis in (16, 17) else (-32768, 32767))
            # uinput_abs_setup: axis, padding, input_absinfo.
            setup = struct.pack('@H2xiiiiii', axis, 0, minimum, maximum, 0, 0, 0)
            fcntl.ioctl(fd, ioctl_write(4, 28), setup)
        # Xbox-compatible identity/layout for SDL/Steam mapping discovery.
        setup = struct.pack('@HHHH80sI', 3, 0x045e, 0x028e, 1,
                            b'Decktation A probe', 0)
        fcntl.ioctl(fd, ioctl_write(3, 92), setup)
        fcntl.ioctl(fd, (ord('U') << 8) | 1)  # UI_DEV_CREATE
        created = True
        print('Created Decktation A probe. Stop with Ctrl+C.', flush=True)
        print('A will pulse repeatedly; focus a controller tester before the delay ends.',
              flush=True)
        time.sleep(args.startup_delay)
        while True:
            try:
                emit(1, 304, 1)
                emit(0, 0, 0)
                time.sleep(args.hold_ms / 1000)
            finally:
                emit(1, 304, 0)
                emit(0, 0, 0)
            print('A down/up emitted (delivery to game not confirmed)', flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        if created:
            fcntl.ioctl(fd, (ord('U') << 8) | 2)  # UI_DEV_DESTROY
        os.close(fd)


if __name__ == '__main__':
    main()
