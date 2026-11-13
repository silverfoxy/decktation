#!/usr/bin/env python3
"""
Standalone controller listener using evdev plus Valve raw HID reports.
Runs as a separate process so controller polling cannot block Decky.
Writes button state to /tmp/decktation_l5 file.
Listens for configurable button combo (default: L1+R1).
"""
import os
from runtime_paths import ipc_path
import sys
import time
import json
import glob
import selectors
import tempfile
from deck_hid import STEAM_DECK_BUTTON_BITS
from gamepad_evdev import EvdevGamepad
from controller_output import discover_outputs, resolve_output, without_injected_a
from controller_profiles import PROFILES_BY_KIND, HidGamepad, find_hidraw
from gamepad_sdl import SdlInput, SdlGamepad
from binding_capture import BindingCapture, read_json, write_json
from controller_debug_report import InputReport, DURATION
from controller_debug_session import PROTOCOL, START_TIMEOUT, finite_number, read_bounded
import uuid

STATE_FILE = ipc_path('decktation_l5')
PREVIEW_FILE = ipc_path('decktation_button_preview')
PID_FILE = ipc_path('decktation_listener.pid')
CONTROLLER_TYPE_FILE = ipc_path('decktation_controller_type')
HAPTIC_SOURCE_FILE = ipc_path('decktation_haptic_source.json')
RECENT_SOURCE_FILE = ipc_path('decktation_recent_controller.json')
STATUS_FILE = ipc_path('decktation_controller_status')
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

DIAGNOSTIC_PREFIX = 'DECKTATION_CONTROLLER '

def inspect_rejected_device(device):
    """Sample controller-only codes on rejected hybrid interfaces, never typing."""
    keys = device.capability_keys
    return any(type(key) is int and
               (key in (0x116, 0x117) or 0x120 <= key <= 0x15f or
                0x220 <= key <= 0x223 or 0x2c0 <= key <= 0x2ff)
               for key in keys)


def controller_details(device, controller_type):
    if controller_type == 'sdl_gamepad':
        return {**device.identity, 'controller_type': controller_type,
                'input_backend': 'sdl', 'connection': 'other',
                'supported_buttons': sorted(device.supported_buttons)}
    if controller_type in PROFILES_BY_KIND:
        profile = PROFILES_BY_KIND[controller_type]
        return {**getattr(device, 'identity', {}), 'controller_type': profile.kind,
                'input_backend': 'hidraw',
                'connection': {3: 'usb', 5: 'bluetooth'}.get(profile.bus, 'other'),
                'supported_buttons': sorted(getattr(device, 'supported_buttons', profile.buttons))}
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

def load_exact_binding_ms():
    """The "Exact binding only" window in milliseconds, 0 when it's off."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            value = json.load(f).get("exactBindingMs", 0)
        return max(0, min(500, int(value)))
    except Exception:
        return 0

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
                    'input_backend': 'sdl' if kind == 'sdl_gamepad' else 'evdev' if kind == 'evdev_gamepad' else 'hidraw',
                    'controller_type': kind, 'bindings_accepted': not rejected,
                    'diagnostic_observed': True}
        if kind == 'sdl_gamepad':
            identity['supported_buttons'] = sorted(device.supported_buttons)
        if rejected:
            buttons_missing = not {0x130, 0x131}.issubset(keys)
            axes_missing = not {0, 1}.issubset(axes)
            identity['rejection_reason'] = ('missing_gamepad_buttons_and_stick_axes'
                if buttons_missing and axes_missing else 'missing_gamepad_buttons'
                if buttons_missing else 'missing_stick_axes')
        self.device(path, 'rejected' if rejected else
                    'accepted' if kind in ('evdev_gamepad', 'sdl_gamepad') else 'hidraw', identity, keys, axes)
        if self.report and not self.finished_written:
            if kind in ('evdev_gamepad', 'sdl_gamepad'):
                if rejected:
                    states = {}  # Raw controller-only keys are observed, never mapped for bindings.
                elif hasattr(device, 'states'):
                    states = device.states()
            self.report.initial(path, states, getattr(device, 'keys', ()), self.clock())
            if path in self.report.sources:
                self.resync_baselines[path] = getattr(device, 'resync_count', 0)
                self.observe_loss(path, device)

    def observe_sdl(self, reader):
        if not self.report or self.finished_written:
            return
        self.report.input_backend = 'sdl'
        self.report.sdl = reader.diagnostics()
        if self.report.sdl.get('enumeration_failed'):
            return
        observations = reader.diagnostic_devices
        previous = getattr(self, '_sdl_observed', set()) if getattr(self, '_sdl_session', None) == self.report.session else set()
        if self.report.sdl.get('joystick_count', 0) <= 16:
            for path in previous - observations.keys():
                self.report.disconnected(path)
        for path, (status, identity) in observations.items():
            if path in reader.devices:
                self.observe_device(path, reader.devices[path], 'sdl_gamepad')
            else:
                self.device(path, status, identity)
        self._sdl_observed, self._sdl_session = set(observations), self.report.session
        if self.report.sdl.get('joystick_count', 0) > 16:
            self.report.devices_truncated = True

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
    """Evaluate each source independently; never combine separate gamepads.

    With a window (seconds, from "Exact binding only"), the binding only counts
    when no other button went down from the window before its first button to
    the window after it was complete, and it becomes active once that window
    has passed. Another button in that span makes it a different binding: the
    press doesn't count until every binding button is up. Buttons held from
    earlier, or pressed after the window, don't matter.
    """
    def __init__(self, buttons, window=0.0, clock=time.monotonic):
        self.buttons = buttons
        self.window = window
        self.clock = clock
        self.sources = {}
        self._pressed_at = {}  # source -> {button: most recent button-down time}
        self._press = {}       # source -> the binding press being formed or held

    def update(self, source, states):
        if self.window:
            self._observe(source, states)
        self.sources[source] = states
        return self.active

    def remove(self, source):
        self.sources.pop(source, None)
        self._pressed_at.pop(source, None)
        self._press.pop(source, None)
        return self.active

    def _observe(self, source, states):
        now = self.clock()
        previous = self.sources.get(source, {})
        # Keep the last press even after release, so a tap just before the
        # binding still counts. One timestamp per button bounds this history.
        pressed_at = self._pressed_at.setdefault(source, {})
        for name, down in states.items():
            if down and not previous.get(name, False):
                pressed_at[name] = now
        held = [button for button in self.buttons if states.get(button, False)]
        if not held:
            self._press.pop(source, None)
            return
        press = self._press.get(source)
        if press is None:
            first = min(pressed_at.get(button, now) for button in held)
            press = self._press[source] = {"first": first, "complete": None, "spoiled": False}
        # Letting go of one binding button and pressing it again restarts the wait.
        if len(held) < len(self.buttons):
            press["complete"] = None
        elif press["complete"] is None:
            press["complete"] = now
        # Another button from the window before the binding until the window
        # after it's complete (or any time while it's still being pressed)
        # makes this a bigger chord. That sticks until the binding is let go,
        # so releasing the extra button doesn't turn the chord into dictation.
        end = now if press["complete"] is None else press["complete"] + self.window
        if any(name not in self.buttons and press["first"] - self.window <= when <= end
               for name, when in pressed_at.items()):
            press["spoiled"] = True

    def _qualifies(self, source, states):
        if not all(states.get(button, False) for button in self.buttons):
            return False
        if not self.window:
            return True
        press = self._press.get(source)
        # A microsecond of slack, so a wake-up timed to the window isn't lost to rounding.
        return bool(press and not press["spoiled"] and press["complete"] is not None
                    and self.clock() - press["complete"] >= self.window - 1e-6)

    @property
    def active(self):
        return any(self._qualifies(source, states) for source, states in self.sources.items())

    def activation_source(self, preferred=None):
        """Return a source whose own binding qualifies, never merged inputs."""
        if preferred in self.sources and self._qualifies(preferred, self.sources[preferred]):
            return preferred
        return next((source for source, states in self.sources.items()
                     if self._qualifies(source, states)), None)

    def time_to_active(self):
        """Seconds until a press waiting out its window becomes active, or None."""
        if not self.window:
            return None
        now, left = self.clock(), None
        for press in self._press.values():
            if press["complete"] is not None and not press["spoiled"]:
                remaining = press["complete"] + self.window - now
                if remaining > 0:
                    left = remaining if left is None else min(left, remaining)
        return left

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
    exact_binding_ms = load_exact_binding_ms()
    if exact_binding_ms:
        print(f"Exact binding only: {exact_binding_ms} ms", flush=True)
    tracker = ComboTracker(button_names, exact_binding_ms / 1000)
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
    # Legacy is the default; SDL requires an explicit plugin selection.
    # Never silently mix readers: only one backend owns each binding.
    backend = os.environ.get('DECKTATION_CONTROLLER_BACKEND', 'legacy')
    if backend not in ('legacy', 'sdl'):
        raise ValueError('Unknown controller backend')
    sdl = None
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
        nonlocal combo_active, active_source
        debug_blocked = debug.blocks_actions(tracker.sources)
        if combo_active:
            # Once armed, keep the recording active until every configured
            # button is up on every observed source. A partial duplicate can
            # still be holding a configured button after its peer stops.
            active = any(states.get(button, False)
                         for states in tracker.sources.values()
                         for button in button_names)
        else:
            active = tracker.active and not capture_blocked and not debug_blocked
        if active != combo_active:
            combo_active = active
            if combo_active:
                # Exact-binding waits can expire after another controller moves.
                # Freeze a qualifying source before exposing STATE_FILE=1.
                active_source = tracker.activation_source(active_source)
                snapshot = source_snapshot(active_source)
                if snapshot is not None:
                    snapshot['output_controller'] = resolve_output(snapshot, discover_outputs())
                write_source(HAPTIC_SOURCE_FILE, snapshot)
                diagnostic('ptt_activated', activation_source=snapshot)
            print(f"{combo_str} COMBO: {'pressed' if combo_active else 'released'}", flush=True)
            with open(STATE_FILE, 'w') as f:
                f.write("1" if combo_active else "0")

    def source_snapshot(path):
        if path not in details:
            return None
        return {'path': path, 'kind': devices[path][1],
                'evdev_path': getattr(devices[path][0], 'evdev_path', None),
                'sdl_session': sdl.session if sdl is not None else None,
                'identity': {key: details[path].get(key) for key in
                             ('bus', 'vendor_id', 'product_id')},
                'time': time.time()}

    def publish(path, states, controller_type):
        nonlocal active_source
        states = without_injected_a(getattr(devices[path][0], 'evdev_path', None) or path, states)
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
                debug.transition(path, 'mapped' if isinstance(device, (EvdevGamepad, SdlGamepad)) else 'hid',
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
        if isinstance(device, SdlGamepad):
            sdl.remove(path)
        else:
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
        if backend == 'sdl':
            sdl = SdlInput()
        next_scan = 0
        next_debug_refresh = 0
        next_sdl_diagnostics = 0
        debug_active = False
        waiting = False
        with open(CONTROLLER_TYPE_FILE, 'w') as f:
            f.write('unknown')
        diagnostic('started', process_identity=identity)
        while True:
            previous_debug_session = getattr(debug.report, 'session', None)
            now = time.monotonic()
            # Poll SDL quickly without writing heartbeat/report files at the
            # controller sampling rate. Capture commands still refresh at 10Hz.
            if sdl is None or now >= next_debug_refresh:
                debug_active = debug.refresh(now)
                next_debug_refresh = now + 0.1
            if debug_active and debug.report.session != previous_debug_session:
                # Populate every source before an early Stop can finalize.
                next_scan = 0
                next_sdl_diagnostics = 0
                debug.report.input_backend = backend
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
            if sdl is not None:
                for path, states in sdl.poll():
                    if states is None:
                        if path in devices:
                            remove(path)
                        continue
                    if path not in devices:
                        device = sdl.devices[path]
                        devices[path] = (device, 'sdl_gamepad')
                        details[path] = controller_details(device, 'sdl_gamepad')
                        details[path].update(combo_supported=set(button_names).issubset(device.supported_buttons),
                                             input_received=False, resync_count=0)
                        if debug_active:
                            debug.observe_device(path, device, 'sdl_gamepad')
                        diagnostic('connected', affected_controller=details[path])
                    if states != tracker.sources.get(path, {}) and any(states.values()) and not details[path]['input_received']:
                        details[path]['input_received'] = True
                        diagnostic('first_input', affected_controller=details[path])
                    publish(path, states, 'sdl_gamepad')
                if debug_active and now >= next_sdl_diagnostics:
                    debug.observe_sdl(sdl)
                    next_sdl_diagnostics = now + 0.5
                sdl.update_haptics()
            if time.monotonic() >= next_scan:
                candidates = ({path: 'sdl_gamepad' for path in devices} if sdl is not None
                              else dict(find_hidraw()))
                if sdl is None:
                    candidates.update({path: 'evdev_gamepad' for path in glob.glob('/dev/input/event*')})
                for path in list(devices):
                    if path not in candidates:
                        remove(path)
                for path, controller_type in candidates.items():
                    if path in devices or path in rejected:
                        continue
                    device = None
                    try:
                        if controller_type == 'evdev_gamepad':
                            device = (EvdevGamepad(path, diagnostic_only=True) if debug_active
                                      else EvdevGamepad(path))
                        else:
                            device = HidGamepad(path, PROFILES_BY_KIND[controller_type])
                        # Reject typing interfaces before selector registration.
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
            timeout = 0 if debug.terminal_pending else 0.008 if sdl is not None else 0.25
            # A held binding sends no new input, so nothing would check it again
            # when its "Exact binding only" window ends. Wake up then instead.
            waiting_binding = tracker.time_to_active()
            if waiting_binding is not None:
                timeout = min(timeout, waiting_binding)
            ready_events = selector.select(timeout=timeout)
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
            if waiting_binding is not None:
                update_combo()  # even if the wake-up brought no input
            debug.finish_if_drained(time.monotonic(), pending=bool(ready_events))
    except KeyboardInterrupt:
        pass
    finally:
        for device in rejected.values():
            device.close()
        for device, _ in devices.values():
            device.close()
        if sdl is not None:
            sdl.close()
        selector.close()
        for path in (STATE_FILE, PID_FILE, PREVIEW_FILE, CONTROLLER_TYPE_FILE, STATUS_FILE,
                     HAPTIC_SOURCE_FILE, RECENT_SOURCE_FILE):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

if __name__ == "__main__":
    main()
