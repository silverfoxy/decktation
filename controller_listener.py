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
CONFIG_FILE = "/tmp/decktation_button_config.json"

# Button name to evdev code mapping (digital buttons - EV_KEY)
BUTTON_CODES = {
    "L1": 310,   # BTN_TL (left bumper)
    "R1": 311,   # BTN_TR (right bumper)
    "L5": 314,   # BTN_SELECT (left back grip - may not work on all devices)
    "R5": 315,   # BTN_START (right back grip - may not work on all devices)
    "A": 304,    # BTN_SOUTH
    "B": 305,    # BTN_EAST
    "X": 307,    # BTN_NORTH
    "Y": 308,    # BTN_WEST
}

# Analog trigger axes (EV_ABS) - L2/R2 are analog triggers on Steam Deck
TRIGGER_AXES = {
    "L2": 2,     # ABS_Z (left trigger)
    "R2": 5,     # ABS_RZ (right trigger)
}

# Digital button codes for triggers (some devices send these too)
TRIGGER_BUTTONS = {
    "L2": 312,   # BTN_TL2 (left trigger digital)
    "R2": 313,   # BTN_TR2 (right trigger digital)
}

# Threshold for analog triggers (0-255 range)
TRIGGER_THRESHOLD = 128  # Consider trigger pressed if value > 128

def load_button_config():
    """Load button configuration from JSON file"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                buttons = config.get("buttons", ["L1", "R1"])
                if isinstance(buttons, list) and len(buttons) > 0:
                    return buttons
    except Exception as e:
        print(f"Error loading config: {e}, using defaults", flush=True)

    # Default to L1+R1
    return ["L1", "R1"]

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
    button_names = load_button_config()

    # Build button info list
    button_info = []
    for btn_name in button_names:
        is_trigger = btn_name in TRIGGER_AXES

        # Get codes for this button (analog, digital, or regular)
        code = TRIGGER_AXES.get(btn_name) if is_trigger else BUTTON_CODES.get(btn_name)
        digital_code = TRIGGER_BUTTONS.get(btn_name) if is_trigger else None

        if code is None:
            print(f"ERROR: Invalid button: {btn_name}", flush=True)
            sys.exit(1)

        button_info.append({
            "name": btn_name,
            "code": code,
            "digital_code": digital_code,
            "is_trigger": is_trigger,
            "pressed": False
        })

    combo_str = "+".join([btn["name"] for btn in button_info])
    print(f"Button combo: {combo_str}", flush=True)
    for btn in button_info:
        btn_type = "trigger" if btn["is_trigger"] else "button"
        print(f"  {btn['name']}: {btn_type}/{btn['code']}", flush=True)

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
    print(f"Waiting for {combo_str} combo...", flush=True)

    combo_active = False

    try:
        for event in device.read_loop():
            state_changed = False

            # Handle digital buttons (EV_KEY)
            if event.type == ecodes.EV_KEY:
                for btn in button_info:
                    # Check regular digital buttons
                    if not btn["is_trigger"] and event.code == btn["code"]:
                        btn["pressed"] = event.value == 1
                        state_changed = True
                        break
                    # Check digital trigger buttons (L2/R2 may send these)
                    elif btn["is_trigger"] and btn["digital_code"] and event.code == btn["digital_code"]:
                        btn["pressed"] = event.value == 1
                        state_changed = True
                        break

            # Handle analog triggers (EV_ABS)
            elif event.type == ecodes.EV_ABS:
                for btn in button_info:
                    if btn["is_trigger"] and event.code == btn["code"]:
                        btn["pressed"] = event.value > TRIGGER_THRESHOLD
                        state_changed = True
                        break

            # Check combo state only if something changed
            if state_changed:
                # All buttons must be pressed for combo to be active
                all_pressed = all(btn["pressed"] for btn in button_info)

                if all_pressed and not combo_active:
                    # Combo just activated
                    combo_active = True
                    print(f"{combo_str} COMBO: pressed", flush=True)
                    with open(STATE_FILE, 'w') as f:
                        f.write("1")
                elif not all_pressed and combo_active:
                    # Combo released (any button released)
                    combo_active = False
                    print(f"{combo_str} COMBO: released", flush=True)
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
