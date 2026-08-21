#!/usr/bin/env python3
"""
Standalone controller listener using the Steam Deck's raw HID reports.
Runs as a separate process so controller polling cannot block Decky.
Writes button state to /tmp/decktation_l5 file.
Listens for configurable button combo (default: L1+R1).
"""
import os
import sys
import time
import json
import glob
from deck_hid import STEAM_DECK_BUTTON_BITS, raw_button_states

STATE_FILE = "/tmp/decktation_l5"
PREVIEW_FILE = "/tmp/decktation_button_preview"
PID_FILE = "/tmp/decktation_listener.pid"
CONTROLLER_TYPE_FILE = "/tmp/decktation_controller_type"
# The Decky backend passes its user-owned settings directory. The fallback is
# retained for standalone development runs.
CONFIG_DIR = os.environ.get(
    "DECKTATION_CONFIG_DIR",
    os.path.expanduser("~/.config/decktation"),
)
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, "button_config.json")

# All selectable built-in controls are read from the physical Steam Deck HID
# report, independent of the active Steam Input layout.
RAW_BUTTON_BITS = STEAM_DECK_BUTTON_BITS

STEAM_HID_INTERFACES = {
    # Steam Deck vendor controller interface.
    "0003:000028DE:00001205": ("/input2",),
    # Original Steam Controller, wired and wireless receiver. The receiver has
    # appeared as input1 and input2 across hid-steam/kernel versions.
    "0003:000028DE:00001102": ("/input2",),
    "0003:000028DE:00001142": ("/input1", "/input2"),
}
STEAM_CONTROLLER_TYPES = {
    "0003:000028DE:00001205": "steam_deck",
    "0003:000028DE:00001102": "steam_controller_wired",
    "0003:000028DE:00001142": "steam_controller_wireless",
}

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

def find_steam_deck_hidraw():
    """Find a Valve vendor HID interface containing raw controller reports."""
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
            hid_id = properties.get("HID_ID")
            interface_suffixes = STEAM_HID_INTERFACES.get(hid_id, ())
            if properties.get("HID_PHYS", "").endswith(interface_suffixes):
                with open(CONTROLLER_TYPE_FILE, "w") as controller_file:
                    controller_file.write(STEAM_CONTROLLER_TYPES[hid_id])
                return path
        except (OSError, ValueError):
            continue
    return None

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
        if btn_name not in RAW_BUTTON_BITS:
            print(f"ERROR: Invalid button: {btn_name}", flush=True)
            sys.exit(1)

        button_info.append({
            "name": btn_name,
            "pressed": False
        })

    combo_str = "+".join([btn["name"] for btn in button_info])
    print(f"Button combo: {combo_str}", flush=True)
    for btn in button_info:
        btn_type = "raw HID trigger" if btn["name"] in ("L2", "R2") else "raw HID button"
        code = RAW_BUTTON_BITS[btn["name"]]
        print(f"  {btn['name']}: {btn_type}/{code}", flush=True)

    print(f"Waiting for {combo_str} combo...", flush=True)

    combo_active = False

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

    def listen_hidraw():
        previous_states = {name: False for name in RAW_BUTTON_BITS}
        while True:
            path = find_steam_deck_hidraw()
            if not path:
                print("Supported Valve raw HID interface not found; retrying...", flush=True)
                time.sleep(2)
                continue
            print(f"Listening for raw Valve controller controls on: {path}", flush=True)
            try:
                # The DeckShock reference implementation opens this vendor HID
                # interface read/write. Some hid-steam versions do not deliver
                # input reports to an O_RDONLY descriptor.
                with open(path, "r+b", buffering=0) as device:
                    received_report = False
                    while True:
                        report = device.read(64)
                        if not report:
                            raise OSError("empty HID report")
                        if not received_report:
                            print(
                                f"Received first raw HID report ({len(report)} bytes)",
                                flush=True,
                            )
                            received_report = True
                        states = raw_button_states(report)
                        if states is None:
                            # The interface can also emit battery/status packets.
                            continue
                        for name in RAW_BUTTON_BITS:
                            pressed = states.get(name, False)
                            if pressed != previous_states[name]:
                                previous_states[name] = pressed
                                write_button_preview(name, pressed)
                        changed = False
                        for btn in button_info:
                            # The original Steam Controller has only two grips,
                            # exposed as L5/R5. Deck-only L4/R4 remain released.
                            pressed = states.get(btn["name"], False)
                            if pressed != btn["pressed"]:
                                btn["pressed"] = pressed
                                changed = True
                        if changed:
                            update_combo()
            except (OSError, IOError) as e:
                print(f"Raw HID disconnected: {e}; retrying...", flush=True)
                for btn in button_info:
                    btn["pressed"] = False
                update_combo()
                time.sleep(1)

    try:
        listen_hidraw()

    except KeyboardInterrupt:
        pass
    finally:
        # Cleanup
        try:
            os.remove(STATE_FILE)
            os.remove(PID_FILE)
            os.remove(PREVIEW_FILE)
            os.remove(CONTROLLER_TYPE_FILE)
        except:
            pass

if __name__ == "__main__":
    main()
