#!/usr/bin/env python3
"""Quick test to see what events L2/R2 triggers generate"""
import sys
sys.path.insert(0, "/home/deck/homebrew/plugins/decktation/lib")

import evdev
from evdev import ecodes
import select

# Find all input devices
devices = []
print("Available input devices:")
print("-" * 60)
for path in evdev.list_devices():
    try:
        d = evdev.InputDevice(path)
        print(f"{path}: {d.name}")
        # Check if device has ABS axes (analog inputs)
        caps = d.capabilities()
        if ecodes.EV_ABS in caps:
            abs_axes = [code for (code, info) in caps[ecodes.EV_ABS]]
            if 2 in abs_axes or 5 in abs_axes:  # Has ABS_Z or ABS_RZ
                print(f"  -> HAS TRIGGERS (ABS_Z={2 in abs_axes}, ABS_RZ={5 in abs_axes})")
                devices.append(d)
    except:
        pass

if not devices:
    print("\nNo devices with trigger axes found!")
    sys.exit(1)

print(f"\nListening to {len(devices)} device(s) for L2/R2 triggers...")
print("Press L2 and R2 triggers (Ctrl+C to exit):")
print("-" * 60)

device_map = {dev.fd: dev for dev in devices}

try:
    while True:
        r, w, x = select.select(device_map, [], [])
        for fd in r:
            device = device_map[fd]
            for event in device.read():
                if event.type == 3:  # EV_ABS
                    if event.code in [2, 5]:
                        name = "L2 (ABS_Z)" if event.code == 2 else "R2 (ABS_RZ)"
                        print(f"[{device.name}] {name}: {event.value}", flush=True)
except KeyboardInterrupt:
    print("\nDone")
