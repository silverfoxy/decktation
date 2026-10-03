#!/usr/bin/env python3
"""Manual, bounded Steam Deck rumble probe; never used by automated tests."""

import fcntl
import glob
import os
import struct
import sys
import time


def vendor_interface():
    for path in glob.glob("/dev/hidraw*"):
        name = os.path.basename(path)
        with open(f"/sys/class/hidraw/{name}/device/uevent", encoding="ascii") as source:
            properties = dict(line.rstrip().split("=", 1) for line in source if "=" in line)
        if (properties.get("HID_ID") == "0003:000028DE:00001205"
                and properties.get("HID_PHYS", "").endswith("/input2")):
            return path
    raise RuntimeError("Steam Deck vendor HID interface not found")


def send_rumble(fd, speed):
    # Linux hid-steam's legacy ID_TRIGGER_RUMBLE_CMD (0xeb), report ID 0.
    report = bytearray(65)
    report[:12] = b"\x00" + struct.pack("<BBBHHHBB", 0xEB, 9, 0, 0, speed, speed, 2, 0)
    request = 0xC0000000 | (65 << 16) | (ord("H") << 8) | 6
    fcntl.ioctl(fd, request, report)


def main():
    pattern = sys.argv[1] if len(sys.argv) > 1 else "start"
    if pattern not in ("start", "stop"):
        raise SystemExit("usage: test_deck_rumble.py [start|stop]")
    path = vendor_interface()
    fd = os.open(path, os.O_RDWR)
    try:
        try:
            bursts = 1 if pattern == "start" else 2
            for index in range(bursts):
                for _ in range(3 if pattern == "start" else 2):
                    send_rumble(fd, 45000)
                    time.sleep(0.05)
                send_rumble(fd, 0)
                if index + 1 < bursts:
                    time.sleep(0.075)
        finally:
            send_rumble(fd, 0)
    finally:
        os.close(fd)
    print(f"Sent bounded {pattern} rumble pattern on {path}; stop command sent")


if __name__ == "__main__":
    main()
