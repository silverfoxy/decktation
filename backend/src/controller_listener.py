#!/usr/bin/env python3
"""
Standalone controller listener using evdev plus Valve raw HID reports.
Runs as a separate process so controller polling cannot block Decky.
Writes button state to /tmp/decktation_l5 file.
Listens for configurable button combo (default: L1+R1).
"""
import os
import sys
import time
import json
import glob
import selectors
from deck_hid import STEAM_DECK_BUTTON_BITS, raw_button_states
from gamepad_evdev import EvdevGamepad

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

DIAGNOSTIC_PREFIX = 'DECKTATION_CONTROLLER '


def controller_details(device, controller_type):
    if controller_type != 'evdev_gamepad':
        buttons = set(RAW_BUTTON_BITS)
        if controller_type != 'steam_deck':
            buttons -= {'L4', 'R4'}
        product = {'steam_deck': 0x1205, 'steam_controller_wired': 0x1102,
                   'steam_controller_wireless': 0x1142}.get(controller_type, 0)
        return {'controller_type': controller_type, 'input_backend': 'hidraw',
                'vendor_id': 0x28de, 'product_id': product, 'connection': 'usb', 'bus': 3,
                'supported_buttons': sorted(buttons)}
    identity = getattr(device, 'identity', {})
    family = {0x045e: 'xbox', 0x054c: 'playstation', 0x057e: 'nintendo',
              0x28de: 'valve'}.get(identity.get('vendor_id'), 'generic_gamepad')
    return {**identity, 'controller_type': family, 'input_backend': 'evdev',
            'connection': {3: 'usb', 5: 'bluetooth', 6: 'virtual'}.get(identity.get('bus'), 'other'),
            'supported_buttons': sorted(getattr(device, 'supported_buttons', []))}

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

def find_steam_hidraw():
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
                yield path, STEAM_CONTROLLER_TYPES[hid_id]
        except (OSError, ValueError):
            continue


class RawGamepad:
    def __init__(self, path):
        # Some hid-steam versions require read/write for input delivery.
        self.fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)

    def close(self):
        os.close(self.fd)

    def read_states(self):
        report = os.read(self.fd, 64)
        if not report:
            raise OSError('empty HID report')
        # A wireless controller can disconnect while its USB receiver stays.
        if len(report) >= 5 and report[:3] == b'\x01\x00\x03' and report[4] == 1:
            yield {name: False for name in RAW_BUTTON_BITS}
            return
        states = raw_button_states(report)
        if states is not None:
            yield states


class ComboTracker:
    """Evaluate each source independently; never combine separate gamepads."""
    def __init__(self, buttons):
        self.buttons = buttons
        self.sources = {}

    def update(self, source, states):
        self.sources[source] = states
        return self.active

    def remove(self, source):
        self.sources.pop(source, None)
        return self.active

    @property
    def active(self):
        return any(all(states.get(button, False) for button in self.buttons)
                   for states in self.sources.values())

def main():
    # Write PID file
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    # Initial state - not pressed
    with open(STATE_FILE, 'w') as f:
        f.write("0")
    write_button_preview("None", False)

    identity = {
        'uid': os.geteuid(),
        'gid': os.getegid(),
        'groups': os.getgroups(),
    }
    print(
        f"Controller listener starting (PID {os.getpid()}, "
        f"uid={identity['uid']}, gid={identity['gid']}, "
        f"groups={identity['groups']})...",
        flush=True,
    )

    # Load button configuration
    button_names = load_button_config()

    for btn_name in button_names:
        if btn_name not in RAW_BUTTON_BITS:
            print(f"ERROR: Invalid button: {btn_name}", flush=True)
            sys.exit(1)
    combo_str = "+".join(button_names)
    print(f"Button combo: {combo_str}", flush=True)
    tracker = ComboTracker(button_names)
    selector = selectors.DefaultSelector()
    devices = {}
    details = {}
    active_source = None
    open_errors = set()
    combo_active = False

    def diagnostic(event, **extra):
        snapshot = {
            'event': event, 'configured_buttons': button_names,
            'source_count': len(devices),
            'sources': list(details.values()),
            'current_controller': details.get(active_source, {}),
            **extra,
        }
        print(DIAGNOSTIC_PREFIX + json.dumps(snapshot), flush=True)

    def update_combo():
        nonlocal combo_active
        if tracker.active != combo_active:
            combo_active = tracker.active
            print(f"{combo_str} COMBO: {'pressed' if combo_active else 'released'}", flush=True)
            with open(STATE_FILE, 'w') as f:
                f.write("1" if combo_active else "0")

    def publish(path, states, controller_type):
        nonlocal active_source
        previous = tracker.sources.get(path, {})
        changed = {name: pressed for name, pressed in states.items()
                   if pressed != previous.get(name, False)}
        if changed:
            device = devices[path][0]
            raw_keys = [hex(code) for code in sorted(getattr(device, 'keys', set()))
                        if code in getattr(device, 'key_buttons', {})]
            print(f"Controller input: path={path} type={details[path]['controller_type']} "
                  f"changed={changed} held={[name for name, down in states.items() if down]} "
                  f"evdev_keys={raw_keys}", flush=True)
        for name, pressed in states.items():
            if pressed != previous.get(name, False):
                write_button_preview(name, pressed)
        # Keep the controller responsible for a held combo selected even when
        # another controller sends unrelated input or a virtual duplicate.
        owns_combo = active_source and all(tracker.sources.get(active_source, {}).get(b, False)
                                          for b in button_names)
        if states != previous and any(states.values()) and (not owns_combo or active_source == path):
            changed_source = active_source != path
            active_source = path
            with open(CONTROLLER_TYPE_FILE, 'w') as f:
                f.write(details[path]['controller_type'])
            if changed_source:
                diagnostic('active_changed')
        tracker.update(path, states)
        update_combo()

    def remove(path, error=None):
        nonlocal active_source
        disconnected = details.pop(path)
        device, _ = devices.pop(path)
        selector.unregister(device.fd)
        device.close()
        tracker.remove(path)
        if active_source == path:
            active_source = next((source for source, states in tracker.sources.items()
                                  if all(states.get(b, False) for b in button_names)), None)
            with open(CONTROLLER_TYPE_FILE, 'w') as f:
                f.write(details.get(active_source, {}).get('controller_type', 'unknown'))
        diagnostic('disconnected', affected_controller=disconnected, errno=getattr(error, 'errno', None))
        update_combo()

    try:
        next_scan = 0
        waiting = False
        with open(CONTROLLER_TYPE_FILE, 'w') as f:
            f.write('unknown')
        diagnostic('started', process_identity=identity)
        while True:
            if time.monotonic() >= next_scan:
                candidates = dict(find_steam_hidraw())
                candidates.update({path: 'evdev_gamepad' for path in glob.glob('/dev/input/event*')})
                for path in list(devices):
                    if path not in candidates:
                        remove(path)
                for path, controller_type in candidates.items():
                    if path in devices:
                        continue
                    device = None
                    try:
                        device = (EvdevGamepad(path) if controller_type == 'evdev_gamepad'
                                  else RawGamepad(path))
                        selector.register(device.fd, selectors.EVENT_READ, path)
                    except ValueError:
                        continue  # Not a gamepad; constructor closes its fd.
                    except OSError as e:
                        if device is not None:
                            device.close()
                        print(f"Cannot open controller {path}: {e}", flush=True)
                        error_key = (path, e.errno)
                        if error_key not in open_errors:
                            open_errors.add(error_key)
                            diagnostic('open_failed', errno=e.errno,
                                       input_backend='evdev' if controller_type == 'evdev_gamepad' else 'hidraw')
                        continue
                    devices[path] = (device, controller_type)
                    open_errors = {item for item in open_errors if item[0] != path}
                    details[path] = controller_details(device, controller_type)
                    details[path]['combo_supported'] = set(button_names).issubset(details[path]['supported_buttons'])
                    details[path]['input_received'] = False
                    details[path]['resync_count'] = 0
                    diagnostic('connected', affected_controller=details[path])
                    print(f"Listening on {path} ({controller_type})", flush=True)
                    if isinstance(device, EvdevGamepad):
                        publish(path, device.states(), controller_type)
                if not devices and not waiting:
                    diagnostic('waiting')
                waiting = not devices
                next_scan = time.monotonic() + 2
            for key, _ in selector.select(timeout=0.25):
                path = key.data
                device, controller_type = devices[path]
                try:
                    for states in device.read_states():
                        if not details[path]['input_received']:
                            details[path]['input_received'] = True
                            diagnostic('first_input', affected_controller=details[path])
                        resync_count = getattr(device, 'resync_count', 0)
                        if resync_count != details[path]['resync_count']:
                            details[path]['resync_count'] = resync_count
                            diagnostic('resynced', affected_controller=details[path])
                        publish(path, states, controller_type)
                except BlockingIOError:
                    pass
                except OSError as e:
                    print(f"Controller disconnected {path}: {e}", flush=True)
                    remove(path, e)
    except KeyboardInterrupt:
        pass
    finally:
        for device, _ in devices.values():
            device.close()
        selector.close()
        for path in (STATE_FILE, PID_FILE, PREVIEW_FILE, CONTROLLER_TYPE_FILE):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

if __name__ == "__main__":
    main()
