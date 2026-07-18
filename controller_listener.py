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
import glob
import threading

# Controller listener uses system evdev (not bundled lib/)
# The bundled lib/ is compiled for Decky's Python 3.11, but this script
# runs with system Python which may be a different version.
# System evdev is installed via python-evdev package.

import evdev
from evdev import ecodes

STATE_FILE = "/tmp/decktation_l5"
PREVIEW_FILE = "/tmp/decktation_button_preview"
PID_FILE = "/tmp/decktation_listener.pid"
# Config in user home directory for persistence and write access
CONFIG_DIR = os.path.expanduser("~/.config/decktation")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, "button_config.json")

# Button name to evdev code mapping (digital buttons - EV_KEY)
BUTTON_CODES = {
    "L1": 310,   # BTN_TL (left bumper)
    "R1": 311,   # BTN_TR (right bumper)
    "A": 304,    # BTN_SOUTH
    "B": 305,    # BTN_EAST
    "X": 307,    # BTN_NORTH
    "Y": 308,    # BTN_WEST
}

# Steam Deck vendor HID report locations. These buttons are not exposed by the
# virtual Xbox evdev device, so they are read from the physical Valve device.
RAW_BUTTON_BITS = {
    "L4": (13, 1),
    "R4": (13, 2),
    "L5": (9, 7),
    "R5": (10, 0),
}

STEAM_DECK_HID_ID = "0003:000028DE:00001205"

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

def write_button_preview(name, pressed):
    """Publish the latest pressed button for the plugin test display.

    Keep the last press latched so a quick tap cannot begin and end between two
    frontend status polls. ``None`` is used only to initialize the display.
    """
    if pressed or name == "None":
        with open(PREVIEW_FILE, "w") as f:
            f.write(name if pressed else "None")
    print(
        f"Button preview: {name} {'pressed' if pressed else 'released'}",
        flush=True,
    )

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
    """Find gamepad device with actual gamepad buttons (not keyboard interface)"""
    for path in evdev.list_devices():
        try:
            device = evdev.InputDevice(path)
            name_lower = device.name.lower()

            # Check if device has gamepad capabilities (BTN_SOUTH, BTN_NORTH, etc.)
            caps = device.capabilities()
            has_gamepad_buttons = False
            if 1 in caps:  # EV_KEY
                key_codes = caps[1]
                # Check for gamepad buttons (304-307 are SOUTH/EAST/NORTH/WEST - A/B/X/Y)
                has_gamepad_buttons = any(code in key_codes for code in [304, 305, 307, 308, 310, 311])

            # Only match devices that have actual gamepad buttons
            if has_gamepad_buttons and any(keyword in name_lower for keyword in ["x-box 360", "xbox 360", "gamepad", "steam deck controller", "valve"]):
                return device
        except:
            pass
    return None

def find_steam_deck_hidraw():
    """Find the Steam Deck vendor-defined HID interface containing raw reports."""
    for path in glob.glob("/dev/hidraw*"):
        name = os.path.basename(path)
        uevent_path = f"/sys/class/hidraw/{name}/device/uevent"
        try:
            with open(uevent_path, "r") as f:
                properties = dict(
                    line.rstrip().split("=", 1)
                    for line in f
                    if "=" in line
                )
            if (
                properties.get("HID_ID") == STEAM_DECK_HID_ID
                and properties.get("HID_PHYS", "").endswith("/input2")
            ):
                return path
        except (OSError, ValueError):
            continue
    return None

def raw_button_states(report):
    """Decode the four rear grip buttons from a Steam Deck HID report."""
    if len(report) < 14:
        return None
    return {
        name: bool(report[byte] & (1 << bit))
        for name, (byte, bit) in RAW_BUTTON_BITS.items()
    }

def main():
    # Write PID file
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    # Initial state - not pressed
    with open(STATE_FILE, 'w') as f:
        f.write("0")
    write_button_preview("None", False)

    print(f"Controller listener starting (PID {os.getpid()})...", flush=True)

    # Load button configuration
    button_names = load_button_config()

    # Build button info list
    button_info = []
    for btn_name in button_names:
        is_trigger = btn_name in TRIGGER_AXES
        is_raw = btn_name in RAW_BUTTON_BITS

        # Get codes for this button (analog, digital, or regular)
        code = TRIGGER_AXES.get(btn_name) if is_trigger else BUTTON_CODES.get(btn_name)
        digital_code = TRIGGER_BUTTONS.get(btn_name) if is_trigger else None

        if code is None and not is_raw:
            print(f"ERROR: Invalid button: {btn_name}", flush=True)
            sys.exit(1)

        button_info.append({
            "name": btn_name,
            "code": code,
            "digital_code": digital_code,
            "is_trigger": is_trigger,
            "is_raw": is_raw,
            "pressed": False
        })

    combo_str = "+".join([btn["name"] for btn in button_info])
    print(f"Button combo: {combo_str}", flush=True)
    for btn in button_info:
        btn_type = "rear grip (raw HID)" if btn["is_raw"] else ("trigger" if btn["is_trigger"] else "button")
        code = RAW_BUTTON_BITS.get(btn["name"], btn["code"])
        print(f"  {btn['name']}: {btn_type}/{code}", flush=True)

    print(f"Waiting for {combo_str} combo...", flush=True)

    combo_active = False
    state_lock = threading.Lock()

    def update_combo():
        nonlocal combo_active
        all_pressed = all(btn["pressed"] for btn in button_info)

        if all_pressed and not combo_active:
            combo_active = True
            print(f"{combo_str} COMBO: pressed", flush=True)
            with open(STATE_FILE, 'w') as f:
                f.write("1")
        elif not all_pressed and combo_active:
            combo_active = False
            print(f"{combo_str} COMBO: released", flush=True)
            with open(STATE_FILE, 'w') as f:
                f.write("0")

    def listen_evdev():
        evdev_buttons = [btn for btn in button_info if not btn["is_raw"]]
        preview_key_codes = {code: name for name, code in BUTTON_CODES.items()}
        preview_trigger_codes = {code: name for name, code in TRIGGER_BUTTONS.items()}
        preview_trigger_axes = {code: name for name, code in TRIGGER_AXES.items()}
        while True:
            device = find_gamepad()
            if not device:
                print("No evdev gamepad found; retrying...", flush=True)
                time.sleep(2)
                continue
            print(f"Listening for standard buttons on: {device.name}", flush=True)
            try:
                for event in device.read_loop():
                    changed = False
                    if event.type == ecodes.EV_KEY:
                        preview_name = preview_key_codes.get(event.code) or preview_trigger_codes.get(event.code)
                        if preview_name:
                            write_button_preview(preview_name, event.value != 0)
                        for btn in evdev_buttons:
                            if not btn["is_trigger"] and event.code == btn["code"]:
                                with state_lock:
                                    btn["pressed"] = event.value != 0
                                    update_combo()
                                changed = True
                                break
                            if btn["is_trigger"] and btn["digital_code"] and event.code == btn["digital_code"]:
                                with state_lock:
                                    btn["pressed"] = event.value != 0
                                    update_combo()
                                changed = True
                                break
                    elif event.type == ecodes.EV_ABS:
                        preview_name = preview_trigger_axes.get(event.code)
                        if preview_name:
                            write_button_preview(preview_name, event.value > TRIGGER_THRESHOLD)
                        for btn in evdev_buttons:
                            if btn["is_trigger"] and event.code == btn["code"]:
                                with state_lock:
                                    btn["pressed"] = event.value > TRIGGER_THRESHOLD
                                    update_combo()
                                changed = True
                                break
            except (OSError, IOError) as e:
                print(f"evdev disconnected: {e}; retrying...", flush=True)
                with state_lock:
                    for btn in evdev_buttons:
                        btn["pressed"] = False
                    update_combo()
                time.sleep(1)

    def listen_hidraw():
        raw_buttons = [btn for btn in button_info if btn["is_raw"]]
        previous_states = {name: False for name in RAW_BUTTON_BITS}
        while True:
            path = find_steam_deck_hidraw()
            if not path:
                print("Steam Deck raw HID interface not found; retrying...", flush=True)
                time.sleep(2)
                continue
            print(f"Listening for rear grips on: {path}", flush=True)
            try:
                # The DeckShock reference implementation opens this vendor HID
                # interface read/write. Some hid-steam versions do not deliver
                # input reports to an O_RDONLY descriptor.
                with open(path, "r+b", buffering=0) as device:
                    received_report = False
                    while True:
                        report = device.read(64)
                        if not received_report:
                            print(
                                f"Received first raw HID report ({len(report)} bytes)",
                                flush=True,
                            )
                            received_report = True
                        states = raw_button_states(report)
                        if states is None:
                            raise OSError("short or empty HID report")
                        with state_lock:
                            for name, pressed in states.items():
                                if pressed != previous_states[name]:
                                    previous_states[name] = pressed
                                    write_button_preview(name, pressed)
                            changed = False
                            for btn in raw_buttons:
                                pressed = states[btn["name"]]
                                if pressed != btn["pressed"]:
                                    btn["pressed"] = pressed
                                    changed = True
                            if changed:
                                update_combo()
            except (OSError, IOError) as e:
                print(f"Raw HID disconnected: {e}; retrying...", flush=True)
                with state_lock:
                    for btn in raw_buttons:
                        btn["pressed"] = False
                    update_combo()
                time.sleep(1)

    try:
        threads = []
        # Both streams stay active so the test display can preview every button,
        # even when that button is not part of the configured PTT combination.
        threads.append(threading.Thread(target=listen_evdev, daemon=True))
        threads.append(threading.Thread(target=listen_hidraw, daemon=True))
        for thread in threads:
            thread.start()
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        try:
            os.remove(STATE_FILE)
            os.remove(PID_FILE)
            os.remove(PREVIEW_FILE)
        except:
            pass

if __name__ == "__main__":
    main()
