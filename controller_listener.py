#!/usr/bin/env python3
"""
Standalone controller listener using evdev.
Runs as a separate process to avoid import issues in Decky.
Writes button state to /tmp/decktation_l5 file.
Listens for configurable button combo (default: L1+R1).
"""
import os
import sys
import time
import json

# Add lib path for evdev
lib_path = "/home/deck/homebrew/plugins/decktation/lib"
if os.path.exists(lib_path):
    sys.path.insert(0, lib_path)

import evdev
from evdev import ecodes

STATE_FILE = "/tmp/decktation_l5"
PID_FILE = "/tmp/decktation_listener.pid"
CONFIG_FILE = "/home/deck/homebrew/plugins/decktation/button_config.json"

# Button name to evdev code mapping
BUTTON_CODES = {
    "L1": 310,   # BTN_TL (left bumper)
    "R1": 311,   # BTN_TR (right bumper)
    "L2": 312,   # BTN_TL2 (left trigger)
    "R2": 313,   # BTN_TR2 (right trigger)
    "L5": 314,   # BTN_SELECT (left back grip - may not work on all devices)
    "R5": 315,   # BTN_START (right back grip - may not work on all devices)
    "A": 304,    # BTN_SOUTH
    "B": 305,    # BTN_EAST
    "X": 307,    # BTN_NORTH
    "Y": 308,    # BTN_WEST
}

def load_button_config():
    """Load button configuration from JSON file"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                button1 = config.get("button1", "L1")
                button2 = config.get("button2", "R1")
                return button1, button2
    except Exception as e:
        print(f"Error loading config: {e}, using defaults", flush=True)

    # Default to L1+R1
    return "L1", "R1"

def find_gamepad():
    """Find Xbox 360 pad device (Steam Deck gamepad)"""
    for path in evdev.list_devices():
        try:
            device = evdev.InputDevice(path)
            if "X-Box 360" in device.name or "Xbox 360" in device.name:
                return device
        except:
            pass
    return None

def main():
    # Write PID file
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    # Initial state - not pressed
    with open(STATE_FILE, 'w') as f:
        f.write("0")

    print(f"Controller listener starting (PID {os.getpid()})...", flush=True)

    # Load button configuration
    button1_name, button2_name = load_button_config()
    button1_code = BUTTON_CODES.get(button1_name)
    button2_code = BUTTON_CODES.get(button2_name)

    if not button1_code or not button2_code:
        print(f"ERROR: Invalid button configuration: {button1_name}+{button2_name}", flush=True)
        sys.exit(1)

    print(f"Button combo: {button1_name}+{button2_name} (codes {button1_code}+{button2_code})", flush=True)

    device = find_gamepad()
    if not device:
        print("ERROR: No gamepad device found", flush=True)
        print("Available devices:", flush=True)
        for path in evdev.list_devices():
            try:
                d = evdev.InputDevice(path)
                print(f"  {path}: {d.name}", flush=True)
            except:
                pass
        sys.exit(1)

    print(f"Listening on: {device.name}", flush=True)
    print(f"Waiting for {button1_name}+{button2_name} combo...", flush=True)

    # Track button states
    button1_pressed = False
    button2_pressed = False
    combo_active = False

    try:
        for event in device.read_loop():
            if event.type == ecodes.EV_KEY:
                if event.code == button1_code:
                    button1_pressed = event.value == 1
                elif event.code == button2_code:
                    button2_pressed = event.value == 1

                # Check combo state
                both_pressed = button1_pressed and button2_pressed

                if both_pressed and not combo_active:
                    # Combo just activated
                    combo_active = True
                    print(f"{button1_name}+{button2_name} COMBO: pressed", flush=True)
                    with open(STATE_FILE, 'w') as f:
                        f.write("1")
                elif not both_pressed and combo_active:
                    # Combo released (either button released)
                    combo_active = False
                    print(f"{button1_name}+{button2_name} COMBO: released", flush=True)
                    with open(STATE_FILE, 'w') as f:
                        f.write("0")

    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        try:
            os.remove(STATE_FILE)
            os.remove(PID_FILE)
        except:
            pass

if __name__ == "__main__":
    main()
