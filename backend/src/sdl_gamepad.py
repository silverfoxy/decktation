"""Optional SDL 3 observer for the standalone comparison tool, never PTT input.

Only the SDL gamepad subsystem is initialized: no window, keyboard, text input,
rumble, grabs, or Steam API. HIDAPI drivers can themselves configure devices.
The owner must call poll() on the main thread and close() before exiting.
"""
import ctypes as C
import ctypes.util
import os

INIT_GAMEPAD = 0x2000
AXIS, DOWN, UP, ADDED, REMOVED, REMAPPED = range(0x650, 0x656)
JOY_DOWN, JOY_UP = 0x603, 0x604
# SDL3's positional face buttons; keep Decktation's positional naming.
BUTTONS = {
    0: 'A', 1: 'B', 2: 'X', 3: 'Y', 4: 'View', 5: 'SDL Guide',
    6: 'Menu', 7: 'L3', 8: 'R3', 9: 'L1', 10: 'R1',
    11: 'D-pad Up', 12: 'D-pad Down', 13: 'D-pad Left', 14: 'D-pad Right',
    15: 'SDL Misc1', 16: 'R4', 17: 'L4', 18: 'R5', 19: 'L5',
    # One generic click is not evidence of separate left/right trackpad clicks.
    20: 'SDL Touchpad', **{i: f'SDL Misc{i - 19}' for i in range(21, 26)},
}
TRIGGERS = {4: 'L2', 5: 'R2'}


class DeviceEvent(C.Structure):
    _fields_ = [('type', C.c_uint32), ('reserved', C.c_uint32),
                ('timestamp', C.c_uint64), ('which', C.c_uint32)]


class ButtonEvent(C.Structure):
    _fields_ = DeviceEvent._fields_ + [('button', C.c_uint8), ('down', C.c_bool),
                                    ('padding1', C.c_uint8), ('padding2', C.c_uint8)]


class AxisEvent(C.Structure):
    _fields_ = DeviceEvent._fields_ + [('axis', C.c_uint8), ('padding', C.c_uint8 * 3),
                                    ('value', C.c_int16), ('padding4', C.c_uint16)]


class Event(C.Union):
    # SDL3 guarantees 128 bytes, with 8-byte alignment on Linux x86_64.
    _fields_ = [('type', C.c_uint32), ('device', DeviceEvent),
                ('button', ButtonEvent), ('axis', AxisEvent), ('padding', C.c_uint8 * 128)]


def load_sdl(path=None):
    path = path or ctypes.util.find_library('SDL3')
    if not path:
        raise RuntimeError('SDL 3 library not found; supply --sdl-library /path/to/libSDL3.so.0')
    try:
        lib = C.CDLL(path)
        signatures = {
            'SDL_GetVersion': (C.c_int, []),
            'SDL_GetError': (C.c_char_p, []),
            'SDL_SetHintWithPriority': (C.c_bool, [C.c_char_p, C.c_char_p, C.c_int]),
            'SDL_Init': (C.c_bool, [C.c_uint32]),
            'SDL_QuitSubSystem': (None, [C.c_uint32]),
            'SDL_PollEvent': (C.c_bool, [C.POINTER(Event)]),
            'SDL_GetGamepads': (C.POINTER(C.c_uint32), [C.POINTER(C.c_int)]),
            'SDL_free': (None, [C.c_void_p]),
            'SDL_OpenGamepad': (C.c_void_p, [C.c_uint32]),
            'SDL_CloseGamepad': (None, [C.c_void_p]),
            'SDL_GamepadHasButton': (C.c_bool, [C.c_void_p, C.c_int]),
            'SDL_GamepadHasAxis': (C.c_bool, [C.c_void_p, C.c_int]),
            'SDL_GetGamepadButton': (C.c_bool, [C.c_void_p, C.c_int]),
            'SDL_GetGamepadAxis': (C.c_int16, [C.c_void_p, C.c_int]),
            'SDL_GetGamepadVendor': (C.c_uint16, [C.c_void_p]),
            'SDL_GetGamepadProduct': (C.c_uint16, [C.c_void_p]),
            'SDL_GetGamepadPath': (C.c_char_p, [C.c_void_p]),
            'SDL_GetNumGamepadTouchpads': (C.c_int, [C.c_void_p]),
            'SDL_GetGamepadJoystick': (C.c_void_p, [C.c_void_p]),
            'SDL_GetNumJoystickButtons': (C.c_int, [C.c_void_p]),
        }
        for name, (result, args) in signatures.items():
            function = getattr(lib, name)
            function.restype, function.argtypes = result, args
        if not 3002000 <= lib.SDL_GetVersion() < 4000000:
            raise RuntimeError('SDL 3.2 or newer within SDL 3 is required')
        return lib
    except (OSError, AttributeError) as error:
        raise RuntimeError(f'Cannot load SDL 3: {error}') from error


class SdlGamepads:
    def __init__(self, library=None, hidapi=False):
        self.lib = load_sdl(library)
        self.devices = {}
        self.hints = {
            'SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS': '1',
            'SDL_JOYSTICK_HIDAPI': '1' if hidapi else '0',
            # Explicit overrides prevent inherited per-driver hints defeating the mode.
            'SDL_JOYSTICK_HIDAPI_STEAM': '1' if hidapi else '0',
            'SDL_JOYSTICK_HIDAPI_STEAMDECK': '1' if hidapi else '0',
            'SDL_JOYSTICK_HIDAPI_STEAM_TRITON': '1' if hidapi else '0',
        }
        if not hidapi:
            # Per-driver environment hints otherwise override the global switch.
            self.hints.update({name: '0' for name in os.environ
                               if name.startswith('SDL_JOYSTICK_HIDAPI_')})
        for name, value in self.hints.items():
            if not self.lib.SDL_SetHintWithPriority(name.encode(), value.encode(), 2):
                raise RuntimeError(f'Cannot set SDL hint {name}')
        if not self.lib.SDL_Init(INIT_GAMEPAD):
            error = self.lib.SDL_GetError().decode(errors='replace')
            self.lib.SDL_QuitSubSystem(INIT_GAMEPAD)
            raise RuntimeError(f'SDL gamepad initialization failed: {error}')

    def _open(self, instance):
        if instance in self.devices:
            return None
        handle = self.lib.SDL_OpenGamepad(instance)
        if not handle:
            return {'event': 'open_failed', 'source': f'sdl:{instance}',
                    'error': self.lib.SDL_GetError().decode(errors='replace')}
        buttons = {index: name for index, name in BUTTONS.items()
                   if self.lib.SDL_GamepadHasButton(handle, index)}
        axes = {index: name for index, name in TRIGGERS.items()
                if self.lib.SDL_GamepadHasAxis(handle, index)}
        states = {name: bool(self.lib.SDL_GetGamepadButton(handle, index))
                  for index, name in buttons.items()}
        states.update({name: self.lib.SDL_GetGamepadAxis(handle, index) >= 16384
                       for index, name in axes.items()})
        path = self.lib.SDL_GetGamepadPath(handle)
        self.devices[instance] = {'handle': handle, 'states': states, 'buttons': buttons, 'axes': axes}
        return {'event': 'connected', 'source': f'sdl:{instance}', 'backend': 'sdl',
                'identity': {'vendor_id': self.lib.SDL_GetGamepadVendor(handle),
                             'product_id': self.lib.SDL_GetGamepadProduct(handle)},
                'path': path.decode(errors='replace') if path else None,
                'supported_buttons': sorted(states), 'initial': states.copy(),
                'touchpad_count': self.lib.SDL_GetNumGamepadTouchpads(handle),
                'joystick_button_count': self.lib.SDL_GetNumJoystickButtons(
                    self.lib.SDL_GetGamepadJoystick(handle))}

    def poll(self):
        """Drain ordered events, retaining fast press/release pairs between polls."""
        records = []
        count = C.c_int()
        instances = self.lib.SDL_GetGamepads(C.byref(count))
        if not instances:
            raise RuntimeError('SDL gamepad enumeration failed: ' +
                               self.lib.SDL_GetError().decode(errors='replace'))
        try:
            for index in range(count.value):
                record = self._open(instances[index])
                if record:
                    records.append(record)
        finally:
            self.lib.SDL_free(instances)
        event = Event()
        # Bound each drain so a noisy device cannot starve legacy readers.
        for _ in range(4096):
            if not self.lib.SDL_PollEvent(C.byref(event)):
                break
            instance = event.device.which
            if event.type == ADDED:
                record = self._open(instance)
                if record:
                    records.append(record)
            elif event.type in (REMOVED, REMAPPED) and instance in self.devices:
                device = self.devices.pop(instance)
                records.append({'event': 'disconnected', 'source': f'sdl:{instance}',
                                'reason': 'removed' if event.type == REMOVED else 'remapped'})
                self.lib.SDL_CloseGamepad(device['handle'])
            elif instance in self.devices:
                device = self.devices[instance]
                if event.type in (JOY_DOWN, JOY_UP):
                    # Diagnostic evidence only: do not guess a trackpad's handedness.
                    records.append({'event': 'raw_button', 'source': f'sdl:{instance}',
                                    'button_index': event.button.button, 'pressed': event.button.down})
                    continue
                if event.type in (DOWN, UP):
                    name = device['buttons'].get(event.button.button)
                    pressed = bool(event.button.down)
                elif event.type == AXIS:
                    name = device['axes'].get(event.axis.axis)
                    pressed = event.axis.value >= 16384
                else:
                    continue
                if name is not None and device['states'].get(name) != pressed:
                    device['states'][name] = pressed
                    records.append({'event': 'transition', 'source': f'sdl:{instance}',
                                    'button': name, 'pressed': pressed})
        return records

    def close(self):
        for device in self.devices.values():
            self.lib.SDL_CloseGamepad(device['handle'])
        self.devices.clear()
        self.lib.SDL_QuitSubSystem(INIT_GAMEPAD)
