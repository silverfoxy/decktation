"""SDL 3 gamepad input for the experimental controller listener.

Only joystick/gamepad subsystems are initialized: no window, keyboard capture,
exclusive grab, or sensor enablement. Keep SDL calls on the listener's
main thread. ctypes uses SDL's public SDL3 ABI; no Python wheel is required.
"""
import ctypes as c
import os
import time
import uuid

from binding_capture import read_json
from controller_sdl_diagnostics import HINTS, error_category, hint_evidence

HAPTIC_REQUEST_FILE = '/tmp/decktation_sdl_haptic.json'

BUTTONS = dict(enumerate((
    'A', 'B', 'X', 'Y', 'View', None, 'Menu', 'L3', 'R3', 'L1', 'R1',
    'D-pad Up', 'D-pad Down', 'D-pad Left', 'D-pad Right', None,
    'R4', 'L4', 'R5', 'L5', 'Right Trackpad',
)))
TRIGGERS = {4: 'L2', 5: 'R2'}
AXIS, DOWN, UP, ADDED, REMOVED, REMAPPED = range(0x650, 0x656)


class ButtonEvent(c.Structure):
    _fields_ = [('type', c.c_uint32), ('reserved', c.c_uint32),
                ('timestamp', c.c_uint64), ('which', c.c_uint32),
                ('button', c.c_uint8), ('down', c.c_bool), ('padding', c.c_uint16)]


class AxisEvent(c.Structure):
    _fields_ = [('type', c.c_uint32), ('reserved', c.c_uint32),
                ('timestamp', c.c_uint64), ('which', c.c_uint32),
                ('axis', c.c_uint8), ('padding', c.c_uint8 * 3),
                ('value', c.c_int16), ('padding2', c.c_uint16)]


class Event(c.Union):
    _fields_ = [('type', c.c_uint32), ('button', ButtonEvent),
                ('axis', AxisEvent), ('padding', c.c_uint8 * 128)]


def load_sdl(path=None):
    # Installed builds always load their private library. A system SDL is only
    # used by source-tree development, so missing packaged files fail clearly.
    bundled = os.path.join(os.path.dirname(__file__), 'lib', 'libSDL3.so.0')
    if path is None:
        path = bundled if os.path.isdir(os.path.dirname(bundled)) else 'libSDL3.so.0'
    lib = c.CDLL(path)
    signatures = {
        'SDL_GetHint': (c.c_char_p, [c.c_char_p]),
        'SDL_GetJoysticks': (c.POINTER(c.c_uint32), [c.POINTER(c.c_int)]),
        'SDL_IsGamepad': (c.c_bool, [c.c_uint32]),
        'SDL_GetJoystickVendorForID': (c.c_uint16, [c.c_uint32]),
        'SDL_GetJoystickProductForID': (c.c_uint16, [c.c_uint32]),
        'SDL_GetJoystickProductVersionForID': (c.c_uint16, [c.c_uint32]),
        'SDL_SetHint': (c.c_bool, [c.c_char_p, c.c_char_p]),
        'SDL_Init': (c.c_bool, [c.c_uint32]),
        'SDL_Quit': (None, []), 'SDL_GetVersion': (c.c_int, []),
        'SDL_GetError': (c.c_char_p, []), 'SDL_free': (None, [c.c_void_p]),
        'SDL_PumpEvents': (None, []),
        'SDL_PollEvent': (c.c_bool, [c.POINTER(Event)]),
        'SDL_GetGamepads': (c.POINTER(c.c_uint32), [c.POINTER(c.c_int)]),
        'SDL_OpenGamepad': (c.c_void_p, [c.c_uint32]),
        'SDL_GetGamepadPath': (c.c_char_p, [c.c_void_p]),
        'SDL_CloseGamepad': (None, [c.c_void_p]),
        'SDL_GamepadConnected': (c.c_bool, [c.c_void_p]),
        'SDL_RumbleGamepad': (c.c_bool, [c.c_void_p, c.c_uint16, c.c_uint16, c.c_uint32]),
        'SDL_GamepadHasButton': (c.c_bool, [c.c_void_p, c.c_int]),
        'SDL_GamepadHasAxis': (c.c_bool, [c.c_void_p, c.c_int]),
        'SDL_GetGamepadButton': (c.c_bool, [c.c_void_p, c.c_int]),
        'SDL_GetGamepadAxis': (c.c_int16, [c.c_void_p, c.c_int]),
        'SDL_GetGamepadVendor': (c.c_uint16, [c.c_void_p]),
        'SDL_GetGamepadProduct': (c.c_uint16, [c.c_void_p]),
        'SDL_GetGamepadProductVersion': (c.c_uint16, [c.c_void_p]),
        'SDL_GetGamepadType': (c.c_int, [c.c_void_p]),
        'SDL_GetGamepadConnectionState': (c.c_int, [c.c_void_p]),
    }
    for name, (result, args) in signatures.items():
        function = getattr(lib, name)
        function.restype, function.argtypes = result, args
    return lib


class SdlGamepad:
    def __init__(self, lib, instance):
        self.lib, self.instance = lib, instance
        self.handle = lib.SDL_OpenGamepad(instance)
        if not self.handle:
            error = lib.SDL_GetError()
            raise RuntimeError(error.decode('utf-8', 'replace') if error else 'SDL could not open gamepad')
        raw_path = lib.SDL_GetGamepadPath(self.handle) if hasattr(lib, 'SDL_GetGamepadPath') else None
        self.evdev_path = raw_path.decode('utf-8', 'replace') if isinstance(raw_path, bytes) else None
        self.supported_buttons = {name for button, name in BUTTONS.items()
                                  if name and lib.SDL_GamepadHasButton(self.handle, button)}
        self.supported_buttons.update(name for axis, name in TRIGGERS.items()
                                      if lib.SDL_GamepadHasAxis(self.handle, axis))
        self.identity = {
            'vendor_id': lib.SDL_GetGamepadVendor(self.handle),
            'product_id': lib.SDL_GetGamepadProduct(self.handle),
            'hardware_version': lib.SDL_GetGamepadProductVersion(self.handle),
            'sdl_is_gamepad': True,
            'sdl_version': lib.SDL_GetVersion(),
            'sdl_gamepad_type': lib.SDL_GetGamepadType(self.handle),
        }
        # SDL reports wired/wireless, not a Linux bus ID or exact transport.
        self.identity['sdl_connection_state'] = lib.SDL_GetGamepadConnectionState(self.handle)
        self._states = {name: bool(lib.SDL_GetGamepadButton(self.handle, button))
                        for button, name in BUTTONS.items() if name in self.supported_buttons}
        self._states.update({name: lib.SDL_GetGamepadAxis(self.handle, axis) >= 16384
                             for axis, name in TRIGGERS.items() if name in self.supported_buttons})

    def states(self):
        return dict(self._states)

    def close(self):
        if self.handle:
            self.lib.SDL_RumbleGamepad(self.handle, 0, 0, 0)
            self.lib.SDL_CloseGamepad(self.handle)
            self.handle = None


class SdlInput:
    """Return ordered snapshots, preserving down/up pairs within one pump."""
    def __init__(self, lib=None):
        self.lib = lib if lib is not None else load_sdl()
        self.devices = {}
        self.open_failed = set()
        self.open_errors = {}
        self.diagnostic_devices = {}
        # Instance IDs can be reused after a listener restart. Never replay a
        # request from an earlier listener against a different controller.
        self.session = uuid.uuid4().hex
        self._haptic_request = None
        self.lib.SDL_SetHint(b'SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS', b'1')
        # No window or video initialization. Joystick is implied by GAMEPAD.
        if not self.lib.SDL_Init(0x00002000):
            error = self.lib.SDL_GetError()
            self.lib.SDL_Quit()
            raise RuntimeError(f'SDL gamepad initialization failed: {error!r}')
        print(f'SDL controller backend ready: version={self.lib.SDL_GetVersion()} background_events=1', flush=True)

    def poll(self):
        self.lib.SDL_PumpEvents()
        count = c.c_int()
        ids = self.lib.SDL_GetGamepads(c.byref(count))
        if not ids:
            raise RuntimeError(f'SDL gamepad enumeration failed: {self.lib.SDL_GetError()!r}')
        try:
            connected = {ids[i] for i in range(count.value)}
        finally:
            self.lib.SDL_free(ids)
        frames = []
        # Disconnect frames are consumed before closing so callers can safely
        # clear combo ownership and release held buttons.
        for path, pad in list(self.devices.items()):
            if pad.instance not in connected or not self.lib.SDL_GamepadConnected(pad.handle):
                frames.append((path, None))
        new = set()
        removed = {path for path, state in frames if state is None}
        for instance in sorted(connected):
            path = f'sdl:{instance}'
            if path not in self.devices:
                try:
                    self.devices[path] = SdlGamepad(self.lib, instance)
                    self.open_failed.discard(instance)
                    self.open_errors.pop(instance, None)
                except RuntimeError as error:
                    self.open_errors[instance] = error_category(error)
                    if instance not in self.open_failed:
                        print(f'SDL gamepad open failed: instance={instance} error={str(error)!r}', flush=True)
                        self.open_failed.add(instance)
                    continue
                new.add(path)
                frames.append((path, self.devices[path].states()))
        self.open_failed.intersection_update(connected)
        self.open_errors = {i: error for i, error in self.open_errors.items() if i in connected}
        event = Event()
        while self.lib.SDL_PollEvent(c.byref(event)):
            path = f'sdl:{event.button.which}'
            pad = self.devices.get(path)
            if not pad or path in new or path in removed or pad.instance not in connected:
                continue
            name = None
            if event.type in (DOWN, UP):
                name, down = BUTTONS.get(event.button.button), event.type == DOWN
            elif event.type == AXIS:
                name, down = TRIGGERS.get(event.axis.axis), event.axis.value >= 16384
            elif event.type == REMAPPED:
                # Reopen next pump to refresh capabilities and initial state.
                frames.append((path, None))
                removed.add(path)
            if name in pad.supported_buttons and pad._states.get(name) != down:
                pad._states[name] = down
                frames.append((path, pad.states()))
        return frames

    def diagnostics(self):
        """Inspect unrecognized joysticks only during an explicit debug capture."""
        hints = {}
        for name in HINTS:
            raw = self.lib.SDL_GetHint(name.encode())
            hints[name] = hint_evidence(name, raw.decode('utf-8', 'replace') if raw else None)
        count = c.c_int()
        ids = self.lib.SDL_GetJoysticks(c.byref(count))
        context = {'version': self.lib.SDL_GetVersion(), 'hints': hints,
                   'enumeration_failed': not bool(ids)}
        if not ids:
            print(f'SDL joystick enumeration failed: {self.lib.SDL_GetError()!r}', flush=True)
            return context
        try:
            instances = [ids[i] for i in range(count.value)]
        finally:
            self.lib.SDL_free(ids)
        gamepads = {i for i in instances if self.lib.SDL_IsGamepad(i)}
        context.update(joystick_count=len(instances), gamepad_count=len(gamepads))
        observations = {}
        # Give usable and failed gamepads priority over unrelated joysticks.
        for instance in sorted(instances, key=lambda i: (i not in gamepads, i))[:16]:
            path = f'sdl:{instance}'
            identity = {
                'input_backend': 'sdl', 'controller_type': 'sdl_gamepad',
                'sdl_is_gamepad': instance in gamepads, 'diagnostic_observed': True,
                'bindings_accepted': path in self.devices,
                'vendor_id': self.lib.SDL_GetJoystickVendorForID(instance),
                'product_id': self.lib.SDL_GetJoystickProductForID(instance),
                'hardware_version': self.lib.SDL_GetJoystickProductVersionForID(instance),
            }
            status = 'accepted' if path in self.devices else 'open_failed' if instance in gamepads else 'rejected'
            if instance not in gamepads:
                identity['rejection_reason'] = 'not_sdl_gamepad'
            if instance in self.open_errors:
                identity['sdl_error'] = self.open_errors[instance]
            observations[path] = (status, identity)
        self.diagnostic_devices = observations
        return context

    def update_haptics(self, request_file=HAPTIC_REQUEST_FILE):
        request = read_json(request_file)
        if not isinstance(request, dict):
            return
        request_id = request.get('id')
        if not request_id or request_id == self._haptic_request:
            return
        self._haptic_request = request_id
        if request.get('session') != self.session:
            return
        sent = request.get('time')
        if not isinstance(sent, (int, float)) or not 0 <= time.time() - sent <= 0.5:
            return
        path = request.get('path')
        if not isinstance(path, str):
            return
        pad = self.devices.get(path)
        speed, duration = request.get('speed'), request.get('duration_ms')
        if (pad is None or not pad.handle or not self.lib.SDL_GamepadConnected(pad.handle)
                or type(speed) is not int or not 0 <= speed <= 65535
                or type(duration) is not int or not 0 <= duration <= 150
                or (speed > 0 and duration == 0)):
            return
        if not self.lib.SDL_RumbleGamepad(pad.handle, speed, speed, duration):
            print(f'SDL haptic feedback unavailable: {self.lib.SDL_GetError()!r}', flush=True)

    def remove(self, path):
        self.devices.pop(path).close()

    def close(self):
        for pad in self.devices.values():
            pad.close()
        self.devices.clear()
        self.lib.SDL_Quit()
