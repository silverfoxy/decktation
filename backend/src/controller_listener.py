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
import tempfile
from deck_hid import STEAM_DECK_BUTTON_BITS, raw_button_states, triton_button_states
from legion_go_s import BUTTON_BITS as LEGION_GO_S_BUTTON_BITS, button_states as legion_go_s_button_states
from gamepad_evdev import EvdevGamepad
from binding_capture import BindingCapture, read_json, write_json
from controller_debug_report import InputReport, DURATION
from controller_debug_session import PROTOCOL, START_TIMEOUT, finite_number, read_bounded
import uuid

STATE_FILE = "/tmp/decktation_l5"
PREVIEW_FILE = "/tmp/decktation_button_preview"
PID_FILE = "/tmp/decktation_listener.pid"
CONTROLLER_TYPE_FILE = "/tmp/decktation_controller_type"
HAPTIC_SOURCE_FILE = "/tmp/decktation_haptic_source.json"
RECENT_SOURCE_FILE = "/tmp/decktation_recent_controller.json"
STATUS_FILE = "/tmp/decktation_controller_status"
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
for product, kind, suffixes, bus in (
    (0x1304, 'steam_controller_2026_puck', tuple(f'/input{i}' for i in range(2, 6)), 3),
    (0x1305, 'steam_controller_2026_receiver', tuple(f'/input{i}' for i in range(2, 6)), 3),
    (0x1302, 'steam_controller_2026_wired', ('/input0', '/input1', '/input2'), 3),
    (0x1303, 'steam_controller_2026_bluetooth', None, 5),
):
    hid_id = f'{bus:04X}:000028DE:{product:08X}'
    STEAM_HID_INTERFACES[hid_id] = suffixes
    STEAM_CONTROLLER_TYPES[hid_id] = kind

DIAGNOSTIC_PREFIX = 'DECKTATION_CONTROLLER '

def inspect_rejected_device(device):
    """Sample controller-only codes on rejected hybrid interfaces, never typing."""
    keys = device.capability_keys
    return any(type(key) is int and
               (key in (0x116, 0x117) or 0x120 <= key <= 0x15f or
                0x220 <= key <= 0x223 or 0x2c0 <= key <= 0x2ff)
               for key in keys)


def controller_details(device, controller_type):
    if controller_type == 'legion_go_s':
        return {**device.identity, 'controller_type': controller_type,
                'input_backend': 'hidraw', 'connection': 'usb',
                'supported_buttons': sorted(device.supported_buttons)}
    if controller_type != 'evdev_gamepad':
        buttons = set(RAW_BUTTON_BITS)
        if controller_type not in ('steam_deck',) and not controller_type.startswith('steam_controller_2026'):
            buttons -= {'L4', 'R4'}
        product = {'steam_deck': 0x1205, 'steam_controller_wired': 0x1102,
                   'steam_controller_wireless': 0x1142,
                   'steam_controller_2026_puck': 0x1304,
                   'steam_controller_2026_receiver': 0x1305,
                   'steam_controller_2026_wired': 0x1302,
                   'steam_controller_2026_bluetooth': 0x1303}.get(controller_type, 0)
        bluetooth = controller_type.endswith('_bluetooth')
        return {'controller_type': controller_type, 'input_backend': 'hidraw',
                'vendor_id': 0x28de, 'product_id': product,
                'connection': 'bluetooth' if bluetooth else 'usb', 'bus': 5 if bluetooth else 3,
                'supported_buttons': sorted(buttons)}
    identity = getattr(device, 'identity', {})
    family = {0x045e: 'xbox', 0x054c: 'playstation', 0x057e: 'nintendo',
              0x28de: 'valve'}.get(identity.get('vendor_id'), 'generic_gamepad')
    return {**identity, 'controller_type': family, 'input_backend': 'evdev',
            'connection': {3: 'usb', 5: 'bluetooth', 6: 'virtual'}.get(identity.get('bus'), 'other'),
            'supported_buttons': sorted(getattr(device, 'supported_buttons', []))}

def write_button_preview(states):
    """Publish one controller's held buttons atomically, including releases."""
    value = '+'.join(name for name, pressed in states.items() if pressed) or 'None'
    with tempfile.NamedTemporaryFile(mode='w', dir=os.path.dirname(PREVIEW_FILE),
                                     prefix='.decktation-preview-', delete=False) as f:
        temporary = f.name
        f.write(value)
    try:
        os.replace(temporary, PREVIEW_FILE)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_source(path, value):
    """Publish a source before the recording state becomes visible."""
    with tempfile.NamedTemporaryFile(mode='w', dir=os.path.dirname(path),
                                     prefix='.decktation-source-', delete=False) as f:
        temporary = f.name
        json.dump(value, f)
    try:
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

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
            if hid_id in STEAM_CONTROLLER_TYPES and (interface_suffixes is None or
                    properties.get("HID_PHYS", "").endswith(interface_suffixes)):
                yield path, STEAM_CONTROLLER_TYPES[hid_id]
        except (OSError, ValueError):
            continue


def find_legion_go_s_hidraw(sysfs_root='/sys/class/hidraw'):
    """Find only the physical USB gamepad interface, not touchpad/IMU/keyboard."""
    for path in glob.glob('/dev/hidraw*'):
        device = os.path.join(sysfs_root, os.path.basename(path), 'device')
        try:
            with open(os.path.join(device, 'uevent')) as source:
                hid_id = next((line.partition('=')[2].strip() for line in source
                               if line.startswith('HID_ID=')), '')
            if hid_id.upper() not in ('0003:00001A86:0000E310', '0003:00001A86:0000E311'):
                continue
            with open(os.path.join(device, '..', 'bInterfaceNumber')) as source:
                if source.read().strip() != '06':
                    continue
            yield path, 'legion_go_s'
        except OSError:
            continue


class LegionGoSGamepad:
    """Observe the Lenovo gamepad HID input without grabbing or writing to it."""
    def __init__(self, path, product_id=None):
        if product_id is None:
            uevent = os.path.join('/sys/class/hidraw', os.path.basename(path), 'device', 'uevent')
            with open(uevent) as source:
                hid_id = next((line.partition('=')[2].strip().upper() for line in source
                               if line.startswith('HID_ID=')), '')
            if hid_id not in ('0003:00001A86:0000E310', '0003:00001A86:0000E311'):
                raise ValueError('not a Legion Go S gamepad')
            product_id = int(hid_id[-4:], 16)
        self.fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        self.identity = {'bus': 3, 'vendor_id': 0x1a86, 'product_id': product_id}
        self.supported_buttons = set(LEGION_GO_S_BUTTON_BITS)

    def close(self):
        os.close(self.fd)

    def read_states(self):
        report = os.read(self.fd, 32)
        if not report:
            raise OSError('Legion Go S HID disconnected')
        states = legion_go_s_button_states(report)
        if states is not None:
            yield states


class RawGamepad:
    def __init__(self, path):
        # Some hid-steam versions require read/write for input delivery.
        self.fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        self.identity = {}
        try:
            with open(f'/sys/class/hidraw/{os.path.basename(path)}/device/uevent') as source:
                hid_id = next((line.strip().partition('=')[2] for line in source
                               if line.startswith('HID_ID=')), '')
            parts = hid_id.split(':')
            if len(parts) == 3 and all(parts):
                values = [int(part, 16) for part in parts]
                if all(0 <= value <= 65535 for value in values):
                    self.identity = dict(zip(('bus', 'vendor_id', 'product_id'), values))
        except (OSError, ValueError):
            pass  # Missing identity must not prevent observing input.

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


class TritonGamepad(RawGamepad):
    def read_states(self):
        report = os.read(self.fd, 64)
        if not report:
            raise OSError('empty HID report')
        states = triton_button_states(report)
        if states is not None:
            yield states


class ControllerDebug:
    """Monotonic protocol-v2 producer, bound to one listener incarnation."""
    def __init__(self, buttons=None, clock=None):
        self.buttons = buttons or []
        self.clock = clock or time.monotonic
        self.listener_id = uuid.uuid4().hex
        self.report = None
        self.finished_written = False
        self.terminal_phase = None
        self.sequence = 0
        self.resync_baselines = {}
        self.release_required = False
        self.request_file = os.path.join(CONFIG_DIR, 'controller_debug_request.json')
        self.result_file = os.path.join(CONFIG_DIR, 'controller_debug_result.json')
        self.heartbeat_file = os.path.join(CONFIG_DIR, 'controller_debug_heartbeat.json')

    @property
    def terminal_pending(self):
        return self.terminal_phase is not None and not self.finished_written

    def _publish(self, now, state, phase):
        self.sequence += 1
        snapshot = self.report.snapshot(now)
        snapshot.update(phase=phase, ready=True)
        write_json(self.result_file, {
            'protocol': PROTOCOL, 'session': self.report.session,
            'listener_id': self.listener_id, 'sequence': self.sequence,
            'started_mono': self.report.started, 'observed_mono': now,
            'state': state, 'report': snapshot, 'live_input': self.report.live_input()})

    def refresh(self, now=None):
        now = self.clock() if now is None else now
        write_json(self.heartbeat_file, {
            'protocol': PROTOCOL, 'listener_id': self.listener_id, 'observed_mono': now})
        request = read_bounded(self.request_file)
        session = request.get('session')
        requested, expires = request.get('requested_mono'), request.get('expires_mono')
        try:
            valid_session = isinstance(session, str) and uuid.UUID(hex=session).hex == session
        except (ValueError, AttributeError):
            valid_session = False
        valid_request = (type(request.get('protocol')) is int and request['protocol'] == PROTOCOL and valid_session and
                         request.get('listener_id') == self.listener_id and
                         finite_number(requested) and finite_number(expires) and
                         expires == requested + START_TIMEOUT)
        if (valid_request and session != getattr(self.report, 'session', None) and
                requested <= now < expires and
                (self.report is None or self.finished_written)):
            # ACK, not the backend request, starts the full capture window.
            self.report = InputReport(session, now, self.buttons, request.get('metadata'))
            self.resync_baselines = {}
            self.sequence = 0
            self.release_required = True
            self.finished_written = False
            self.terminal_phase = None
        if not self.report or self.finished_written:
            return False
        if valid_request and session == self.report.session and request.get('stopped') is True:
            self.terminal_phase = 'stopped'
        elif now >= self.report.started + DURATION and self.terminal_phase is None:
            self.terminal_phase = 'complete'
        if self.terminal_phase:
            self.report.begin_drain(now)
        self._publish(now, 'stopping' if self.terminal_pending else 'recording', 'capturing')
        return True

    def finish_if_drained(self, now=None, pending=False):
        now = self.clock() if now is None else now
        if (self.report is None or not self.terminal_pending or
                (pending and now < self.report.drain_until)):
            return False
        self.report.stopped = self.terminal_phase == 'stopped'
        self._publish(now, 'ready', self.terminal_phase)
        self.finished_written = True
        return True

    def blocks_actions(self, sources):
        if self.report is not None and not self.finished_written:
            return True
        if self.release_required and not any(any(states.values()) for states in sources.values()):
            self.release_required = False
        return self.release_required

    def device(self, path, status, identity=None, keys=(), axes=(), errno=None):
        if self.report and not self.finished_written:
            self.report.device(path, status, identity, keys, axes, errno)

    def observe_device(self, path, device, kind, states=None):
        rejected = getattr(device, 'rejected', False)
        keys = getattr(device, 'capability_keys', ())
        axes = getattr(device, 'capability_axes', ())
        identity = {**getattr(device, 'identity', {}),
                    'input_backend': 'evdev' if kind == 'evdev_gamepad' else 'hidraw',
                    'controller_type': kind, 'bindings_accepted': not rejected,
                    'diagnostic_observed': True}
        if rejected:
            buttons_missing = not {0x130, 0x131}.issubset(keys)
            axes_missing = not {0, 1}.issubset(axes)
            identity['rejection_reason'] = ('missing_gamepad_buttons_and_stick_axes'
                if buttons_missing and axes_missing else 'missing_gamepad_buttons'
                if buttons_missing else 'missing_stick_axes')
        self.device(path, 'rejected' if rejected else
                    'accepted' if kind == 'evdev_gamepad' else 'hidraw', identity, keys, axes)
        if self.report and not self.finished_written:
            if kind == 'evdev_gamepad':
                if rejected:
                    states = {}  # Raw controller-only keys are observed, never mapped for bindings.
                elif hasattr(device, 'states'):
                    states = device.states()
            self.report.initial(path, states, getattr(device, 'keys', ()), self.clock())
            if path in self.report.sources:
                self.resync_baselines[path] = getattr(device, 'resync_count', 0)
                self.observe_loss(path, device)

    def observe_loss(self, path, device):
        if self.report and not self.finished_written:
            source = self.report.sources.get(path)
            count = max(0, getattr(device, 'resync_count', 0) - self.resync_baselines.get(path, 0))
            for entry in self.report.devices:
                if entry['source'] == source:
                    entry['resync_count'] = min(65535, count)
                    entry['input_dropped'] = (entry.get('input_dropped', False) or
                                              bool(getattr(device, 'dropped', False)) or count > 0)

    def disconnected(self, path, errno=None):
        if self.report and not self.finished_written:
            self.report.disconnected(path, errno)

    def key(self, path, code, value, button, now):
        if self.report and not self.finished_written:
            self.report.key(path, code, value, button, now)

    def transition(self, path, kind, name, pressed, now):
        if self.report and not self.finished_written:
            self.report.event(path, kind, now, button=name, pressed=pressed)


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
    write_button_preview({})

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

    capture = None
    capture_blocked = False
    debug = ControllerDebug(button_names)
    rejected = {}
    request_file = os.path.join(CONFIG_DIR, "binding_capture_request.json")
    result_file = os.path.join(CONFIG_DIR, "binding_capture_result.json")

    def update_capture():
        nonlocal capture, capture_blocked
        request = read_json(request_file)
        if request.get("session") and not request.get("cancelled") and request.get("deadline", 0) > time.time() and (capture is None or capture.session != request["session"]):
            capture = BindingCapture(request["session"], request["deadline"])
            capture_blocked = True
        if capture and capture.active:
            if request.get("cancelled"):
                capture.phase = "cancelled"
            else:
                capture.update(tracker.sources, time.time())
            write_json(result_file, capture.status())
        if capture_blocked and capture and not capture.active:
            if not any(any(states.values()) for states in tracker.sources.values()):
                capture_blocked = False


    def diagnostic(event, **extra):
        snapshot = {
            'event': event, 'configured_buttons': button_names,
            'source_count': len(devices),
            'sources': list(details.values()),
            'current_controller': details.get(active_source, {}),
            **extra,
        }
        # Publish discovery and receipt independently of process liveness.
        with tempfile.NamedTemporaryFile(mode='w', dir=os.path.dirname(STATUS_FILE),
                                         prefix='.decktation-status-', delete=False) as f:
            json.dump(snapshot, f)
            temporary = f.name
        os.replace(temporary, STATUS_FILE)
        print(DIAGNOSTIC_PREFIX + json.dumps(snapshot), flush=True)

    def update_combo():
        nonlocal combo_active
        debug_blocked = debug.blocks_actions(tracker.sources)
        active = tracker.active and not capture_blocked and not debug_blocked
        if active != combo_active:
            combo_active = active
            if combo_active:
                # The source completing the combo is selected in publish(),
                # before the backend can observe STATE_FILE=1.
                write_source(HAPTIC_SOURCE_FILE, source_snapshot(active_source))
            print(f"{combo_str} COMBO: {'pressed' if combo_active else 'released'}", flush=True)
            with open(STATE_FILE, 'w') as f:
                f.write("1" if combo_active else "0")

    def source_snapshot(path):
        if path not in details:
            return None
        return {'path': path, 'kind': devices[path][1],
                'identity': {key: details[path].get(key) for key in
                             ('bus', 'vendor_id', 'product_id')},
                'time': time.time()}

    def publish(path, states, controller_type):
        nonlocal active_source
        if debug.report and not debug.finished_written:
            debug.report.initial(path, states, getattr(devices[path][0], 'keys', ()), time.monotonic())
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
            for name, pressed in changed.items():
                debug.transition(path, 'mapped' if isinstance(device, EvdevGamepad) else 'hid',
                                 name, pressed, time.monotonic())
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
                if debug.report and not debug.finished_written: debug.report.event(path, 'source', time.monotonic())
        if changed and any(states.values()):
            write_source(RECENT_SOURCE_FILE, source_snapshot(path))
        tracker.update(path, states)
        if capture and capture.active:
            for name, pressed in changed.items():
                debug.transition(path, 'binding', name, pressed, time.monotonic())
        if changed:
            write_button_preview(tracker.sources.get(active_source, {}))
        update_capture()
        update_combo()

    def remove(path, error=None):
        nonlocal active_source
        debug.disconnected(path, getattr(error, 'errno', None))
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
        write_button_preview(tracker.sources.get(active_source, {}))
        update_capture()
        update_combo()

    try:
        next_scan = 0
        waiting = False
        with open(CONTROLLER_TYPE_FILE, 'w') as f:
            f.write('unknown')
        diagnostic('started', process_identity=identity)
        while True:
            previous_debug_session = getattr(debug.report, 'session', None)
            debug_active = debug.refresh(time.monotonic())
            if debug_active and debug.report.session != previous_debug_session:
                # Populate every source before an early Stop can finalize.
                next_scan = 0
            for path in list(rejected):
                if not debug_active:
                    device = rejected.pop(path)
                    selector.unregister(device.fd)
                    device.close()
                elif path not in debug.report.sources:
                    debug.observe_device(path, rejected[path], 'evdev_gamepad')
            for path, (device, kind) in devices.items():
                if debug_active:
                    if path not in debug.report.sources:
                        debug.observe_device(path, device, kind, tracker.sources.get(path))
                    if isinstance(device, EvdevGamepad):
                        device.on_key = lambda code, value, p=path, d=device: debug.key(
                            p, code, value, d.key_buttons.get(code), time.monotonic())
                elif isinstance(device, EvdevGamepad):
                    device.on_key = None
            update_capture()
            update_combo()
            if time.monotonic() >= next_scan:
                candidates = dict(find_steam_hidraw())
                candidates.update(find_legion_go_s_hidraw())
                candidates.update({path: 'evdev_gamepad' for path in glob.glob('/dev/input/event*')})
                for path in list(devices):
                    if path not in candidates:
                        remove(path)
                for path, controller_type in candidates.items():
                    if path in devices or path in rejected:
                        continue
                    device = None
                    try:
                        reader = (EvdevGamepad if controller_type == 'evdev_gamepad' else
                                  LegionGoSGamepad if controller_type == 'legion_go_s' else
                                  TritonGamepad if controller_type.startswith('steam_controller_2026') else
                                  RawGamepad)
                        device = (reader(path, diagnostic_only=True)
                                  if reader is EvdevGamepad and debug_active else reader(path))
                        # Discard private keyboard interfaces before registration:
                        # closing an fd does not remove DefaultSelector's map entry.
                        if getattr(device, 'rejected', False) and not inspect_rejected_device(device):
                            device.close()
                            continue
                        selector.register(device.fd, selectors.EVENT_READ, path)
                    except ValueError:
                        if device is not None:
                            device.close()
                        continue  # Constructors close their own fd when rejecting.
                    except OSError as e:
                        if device is not None:
                            device.close()
                        error_key = (path, e.errno)
                        if error_key not in open_errors:
                            open_errors.add(error_key)
                            print(f"Cannot open controller {path}: {e}", flush=True)
                            diagnostic('open_failed', errno=e.errno,
                                       input_backend='evdev' if controller_type == 'evdev_gamepad' else 'hidraw')
                        if debug_active: debug.device(path, 'open_failed', errno=e.errno)
                        continue
                    if getattr(device, 'rejected', False):
                        rejected[path] = device
                        debug.observe_device(path, device, controller_type)
                        device.on_key = lambda code, value, p=path: debug.key(
                            p, code, value, None, time.monotonic())
                        continue
                    devices[path] = (device, controller_type)
                    if debug_active:
                        debug.observe_device(path, device, controller_type)
                        if isinstance(device, EvdevGamepad):
                            device.on_key = lambda code, value, p=path, d=device: debug.key(
                                p, code, value, d.key_buttons.get(code), time.monotonic())
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
            ready_events = selector.select(timeout=0 if debug.terminal_pending else 0.25)
            for key, _ in ready_events:
                path = key.data
                if path in rejected:
                    device = rejected[path]
                    try:
                        for _ in device.read_states(): pass
                        debug.observe_loss(path, device)
                    except (OSError, ValueError):
                        debug.disconnected(path)
                        selector.unregister(device.fd)
                        device.close()
                        rejected.pop(path, None)
                    continue
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
                    debug.observe_loss(path, device)
                except BlockingIOError:
                    pass
                except OSError as e:
                    print(f"Controller disconnected {path}: {e}", flush=True)
                    remove(path, e)
            debug.finish_if_drained(time.monotonic(), pending=bool(ready_events))
    except KeyboardInterrupt:
        pass
    finally:
        for device in rejected.values():
            device.close()
        for device, _ in devices.values():
            device.close()
        selector.close()
        for path in (STATE_FILE, PID_FILE, PREVIEW_FILE, CONTROLLER_TYPE_FILE, STATUS_FILE,
                     HAPTIC_SOURCE_FILE, RECENT_SOURCE_FILE):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

if __name__ == "__main__":
    main()
