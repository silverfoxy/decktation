"""SDL 3 gamepad input for the experimental controller listener.

Only joystick/gamepad subsystems are initialized: no window, keyboard capture,
exclusive grab, sensor enablement, or rumble. Keep SDL calls on the listener's
main thread. ctypes uses SDL's public SDL3 ABI; no Python wheel is required.
"""
import ctypes as c
import os

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
        'SDL_SetHint': (c.c_bool, [c.c_char_p, c.c_char_p]),
        'SDL_Init': (c.c_bool, [c.c_uint32]),
        'SDL_Quit': (None, []), 'SDL_GetVersion': (c.c_int, []),
        'SDL_GetError': (c.c_char_p, []), 'SDL_free': (None, [c.c_void_p]),
        'SDL_PumpEvents': (None, []),
        'SDL_PollEvent': (c.c_bool, [c.POINTER(Event)]),
        'SDL_GetGamepads': (c.POINTER(c.c_uint32), [c.POINTER(c.c_int)]),
        'SDL_OpenGamepad': (c.c_void_p, [c.c_uint32]),
        'SDL_CloseGamepad': (None, [c.c_void_p]),
        'SDL_GamepadConnected': (c.c_bool, [c.c_void_p]),
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
            raise RuntimeError('SDL could not open gamepad')
        self.supported_buttons = {name for button, name in BUTTONS.items()
                                  if name and lib.SDL_GamepadHasButton(self.handle, button)}
        self.supported_buttons.update(name for axis, name in TRIGGERS.items()
                                      if lib.SDL_GamepadHasAxis(self.handle, axis))
        self.identity = {
            'vendor_id': lib.SDL_GetGamepadVendor(self.handle),
            'product_id': lib.SDL_GetGamepadProduct(self.handle),
            'hardware_version': lib.SDL_GetGamepadProductVersion(self.handle),
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
            self.lib.SDL_CloseGamepad(self.handle)
            self.handle = None


class SdlInput:
    """Return ordered snapshots, preserving down/up pairs within one pump."""
    def __init__(self, lib=None):
        self.lib = lib if lib is not None else load_sdl()
        self.devices = {}
        self.open_failed = set()
        self.lib.SDL_SetHint(b'SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS', b'1')
        # No window or video initialization. Joystick is implied by GAMEPAD.
        if not self.lib.SDL_Init(0x00002000):
            self.lib.SDL_Quit()
            raise RuntimeError('SDL gamepad initialization failed')
        print(f'SDL controller backend ready: version={self.lib.SDL_GetVersion()} background_events=1', flush=True)

    def poll(self):
        self.lib.SDL_PumpEvents()
        count = c.c_int()
        ids = self.lib.SDL_GetGamepads(c.byref(count))
        if not ids:
            raise RuntimeError('SDL gamepad enumeration failed')
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
                except RuntimeError:
                    if instance not in self.open_failed:
                        print(f'SDL gamepad open failed: instance={instance}', flush=True)
                        self.open_failed.add(instance)
                    continue
                new.add(path)
                frames.append((path, self.devices[path].states()))
        self.open_failed.intersection_update(connected)
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

    def remove(self, path):
        self.devices.pop(path).close()

    def close(self):
        for pad in self.devices.values():
            pad.close()
        self.devices.clear()
        self.lib.SDL_Quit()
