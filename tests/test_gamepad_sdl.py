"""Exercise the public SDL ABI with virtual gamepads, without input hardware."""
import ctypes as c
import os

import pytest

from gamepad_sdl import SdlInput, Event, DOWN, UP, load_sdl


class VirtualDesc(c.Structure):
    _fields_ = [('version', c.c_uint32), ('type', c.c_uint16), ('padding', c.c_uint16),
                ('vendor', c.c_uint16), ('product', c.c_uint16),
                ('axes', c.c_uint16), ('buttons', c.c_uint16), ('balls', c.c_uint16),
                ('hats', c.c_uint16), ('touchpads_count', c.c_uint16), ('sensors_count', c.c_uint16),
                ('padding2', c.c_uint16 * 2), ('button_mask', c.c_uint32), ('axis_mask', c.c_uint32),
                ('name', c.c_char_p), ('touchpads', c.c_void_p), ('sensors', c.c_void_p),
                ('callbacks', c.c_void_p * 9)]


@pytest.fixture
def sdl():
    library = os.environ.get('DECKTATION_TEST_SDL_LIBRARY')
    try:
        lib = load_sdl(library)
    except OSError:
        if library:
            raise
        pytest.skip('SDL3 not installed; CI explicitly builds the pinned library')
    reader = SdlInput(lib)
    for name, result, args in (
        ('SDL_AttachVirtualJoystick', c.c_uint32, [c.POINTER(VirtualDesc)]),
        ('SDL_DetachVirtualJoystick', c.c_bool, [c.c_uint32]),
        ('SDL_GetGamepadJoystick', c.c_void_p, [c.c_void_p]),
        ('SDL_SetJoystickVirtualButton', c.c_bool, [c.c_void_p, c.c_int, c.c_bool]),
        ('SDL_SetJoystickVirtualAxis', c.c_bool, [c.c_void_p, c.c_int, c.c_int16]),
        ('SDL_PushEvent', c.c_bool, [c.POINTER(Event)]),
    ):
        fn = getattr(lib, name)
        fn.restype, fn.argtypes = result, args
    yield reader
    reader.close()


def attach(reader, rumble=None):
    desc = VirtualDesc(version=c.sizeof(VirtualDesc), type=1, vendor=0x1234,
                       product=0x5678, axes=6, buttons=21,
                       button_mask=(1 << 21) - 1, axis_mask=63, name=b'Decktation test gamepad')
    if rumble is not None:
        desc.callbacks[3] = c.cast(rumble, c.c_void_p)
    instance = reader.lib.SDL_AttachVirtualJoystick(c.byref(desc))
    assert instance
    reader.poll()
    path = f'sdl:{instance}'
    return path, reader.devices[path]


def test_haptic_requests_route_to_owner_and_reject_stale_sessions(sdl, tmp_path):
    import time
    from binding_capture import write_json
    pulses = []
    callback_type = c.CFUNCTYPE(c.c_bool, c.c_void_p, c.c_uint16, c.c_uint16)
    callback = callback_type(lambda _, low, high: pulses.append((low, high)) or True)
    path, pad = attach(sdl, callback)
    other, _ = attach(sdl)
    request_file = tmp_path / 'haptics.json'
    request = {'id': 'start', 'session': sdl.session, 'path': path,
               'time': time.time(), 'speed': 45000, 'duration_ms': 150}
    write_json(request_file, request)
    sdl.update_haptics(request_file)
    assert pulses[-1] == (45000, 45000)
    count = len(pulses)
    sdl.update_haptics(request_file)
    assert len(pulses) == count  # The same request is not replayed every pump.
    for invalid in ({'session': 'old-listener'}, {'time': time.time() - 2},
                    {'time': time.time() + 2}, {'duration_ms': 1000},
                    {'path': 'sdl:missing'}, {'speed': -1}):
        write_json(request_file, {**request, 'id': str(invalid), **invalid})
        sdl.update_haptics(request_file)
        assert len(pulses) == count
    write_json(request_file, {**request, 'id': 'stop', 'speed': 0, 'duration_ms': 0})
    sdl.update_haptics(request_file)
    assert pulses[-1] == (0, 0)
    assert sdl.lib.SDL_DetachVirtualJoystick(pad.instance)
    count = len(pulses)
    write_json(request_file, {**request, 'id': 'disconnected'})
    sdl.update_haptics(request_file)
    assert len(pulses) == count
    assert other in sdl.devices  # Never redirect to another connected pad.


def test_virtual_buttons_triggers_capabilities_and_disconnect(sdl):
    path, pad = attach(sdl)
    assert {'A', 'L1', 'R1', 'L2', 'R2', 'L4', 'R4', 'L5', 'R5'} <= pad.supported_buttons
    assert pad.identity['vendor_id'] == 0x1234
    joystick = sdl.lib.SDL_GetGamepadJoystick(pad.handle)
    assert sdl.lib.SDL_SetJoystickVirtualButton(joystick, 17, True)
    assert sdl.lib.SDL_SetJoystickVirtualAxis(joystick, 4, 20000)
    frames = sdl.poll()
    assert any(p == path and state['L4'] for p, state in frames)
    assert frames[-1][1]['L2']
    assert sdl.lib.SDL_SetJoystickVirtualButton(joystick, 17, False)
    assert sdl.lib.SDL_SetJoystickVirtualAxis(joystick, 4, 0)
    assert not sdl.poll()[-1][1]['L2']
    assert not pad.states()['L4']
    assert sdl.lib.SDL_DetachVirtualJoystick(pad.instance)
    assert (path, None) in sdl.poll()
    sdl.remove(path)
    assert path not in sdl.devices
    replacement, other = attach(sdl)
    assert replacement != path
    assert not any(other.states().values())


def test_down_and_up_in_one_pump_are_not_collapsed(sdl):
    path, pad = attach(sdl)
    for kind in (DOWN, UP):
        event = Event()
        event.button.type = kind
        event.button.which = pad.instance
        event.button.button = 0
        event.button.down = kind == DOWN
        assert sdl.lib.SDL_PushEvent(c.byref(event))
    assert [state['A'] for p, state in sdl.poll() if p == path] == [True, False]


def test_sources_are_independent_and_report_is_scrubbed(sdl):
    from controller_listener import ComboTracker, ControllerDebug, controller_details
    from controller_debug_report import InputReport
    path, pad = attach(sdl)
    other, _ = attach(sdl)
    tracker = ComboTracker(['L1', 'R1'])
    assert not tracker.update(path, {'L1': True})
    assert not tracker.update(other, {'R1': True})
    assert tracker.update(path, {'L1': True, 'R1': True})
    debug = ControllerDebug(clock=lambda: 0)
    debug.report = InputReport('test', 0, ['L1', 'R1'])
    debug.observe_device(path, pad, 'sdl_gamepad')
    debug.transition(path, 'mapped', 'L4', True, 1)
    report = debug.report.snapshot(2)
    device = report['devices'][0]
    assert device['input_backend'] == 'sdl'
    assert device['sdl_version'] >= 3002000
    assert 'L4' in device['supported_buttons']
    assert report['events'][0]['button'] == 'L4'
    assert report['initial_state'][0]['known']
    assert 'name' not in device and 'path' not in device
    assert controller_details(pad, 'sdl_gamepad')['input_backend'] == 'sdl'


def test_listener_sdl_combo_release_and_disconnect(sdl, monkeypatch, tmp_path):
    import json
    import controller_listener as listener
    path, pad = attach(sdl)
    sdl.remove(path)  # Let the listener discover this attached virtual device.
    monkeypatch.setenv('DECKTATION_CONTROLLER_BACKEND', 'sdl')
    monkeypatch.setattr(listener, 'SdlInput', lambda: sdl)
    monkeypatch.setattr(listener, 'CONFIG_DIR', str(tmp_path))
    monkeypatch.setattr(listener, 'load_button_config', lambda: ['L1', 'R1'])
    for name in ('STATE_FILE', 'PID_FILE', 'PREVIEW_FILE', 'CONTROLLER_TYPE_FILE',
                 'STATUS_FILE', 'HAPTIC_SOURCE_FILE', 'RECENT_SOURCE_FILE'):
        monkeypatch.setattr(listener, name, str(tmp_path / name))

    class Selector:
        calls = 0
        def select(self, timeout):
            self.calls += 1
            assert timeout == 0.008
            state = (tmp_path / 'STATE_FILE').read_text()
            if self.calls == 1:
                assert state == '0'
                self.joystick = sdl.lib.SDL_GetGamepadJoystick(sdl.devices[path].handle)
                sdl.lib.SDL_SetJoystickVirtualButton(self.joystick, 9, True)
                sdl.lib.SDL_SetJoystickVirtualButton(self.joystick, 10, True)
            elif self.calls == 2:
                assert state == '1'
                source = json.loads((tmp_path / 'HAPTIC_SOURCE_FILE').read_text())
                assert source['kind'] == 'sdl_gamepad'
                sdl.lib.SDL_SetJoystickVirtualButton(self.joystick, 9, False)
            elif self.calls == 3:
                assert state == '1'  # Existing release-all behavior is retained.
                sdl.lib.SDL_SetJoystickVirtualButton(self.joystick, 10, False)
            elif self.calls == 4:
                assert state == '0'
                sdl.lib.SDL_SetJoystickVirtualButton(self.joystick, 9, True)
                sdl.lib.SDL_SetJoystickVirtualButton(self.joystick, 10, True)
            elif self.calls == 5:
                assert state == '1'
                sdl.lib.SDL_DetachVirtualJoystick(pad.instance)
            else:
                assert state == '0'
                assert (tmp_path / 'PREVIEW_FILE').read_text() == 'None'
                raise KeyboardInterrupt
            return []
        def close(self):
            pass
    monkeypatch.setattr(listener.selectors, 'DefaultSelector', Selector)
    listener.main()


def test_debug_capture_reports_unmapped_joystick_without_enabling_bindings(sdl):
    from controller_listener import ControllerDebug
    from controller_debug_report import InputReport
    desc = VirtualDesc(version=c.sizeof(VirtualDesc), type=0, vendor=0x1234,
                       product=0x9876, axes=2, buttons=3, name=b'PRIVATE controller name')
    instance = sdl.lib.SDL_AttachVirtualJoystick(c.byref(desc))
    assert instance
    sdl.poll()
    assert f'sdl:{instance}' not in sdl.devices
    debug = ControllerDebug(clock=lambda: 0)
    debug.report = InputReport('capture', 0, ['L1', 'R1'])
    debug.observe_sdl(sdl)
    report = debug.report.snapshot(1)
    device = next(d for d in report['devices'] if d['product_id'] == 0x9876)
    assert device['status'] == 'rejected'
    assert device['rejection_reason'] == 'not_sdl_gamepad'
    assert device['sdl_is_gamepad'] is False
    assert device['bindings_accepted'] is False
    assert report['input_backend'] == 'sdl'
    assert report['sdl']['joystick_count'] >= 1
    assert report['sdl']['hints']['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS']['state'] == '1'
    import json
    assert 'PRIVATE' not in json.dumps(report) and 'sdl:' not in json.dumps(report)
    assert sdl.lib.SDL_DetachVirtualJoystick(instance)
    sdl.poll()
    debug.observe_sdl(sdl)
    assert debug.report.snapshot(2)['devices'][0]['status'] == 'disconnected'


def test_debug_capture_reports_open_failure_and_logs_actual_sdl_error(sdl, monkeypatch, capsys):
    from controller_listener import ControllerDebug
    from controller_debug_report import InputReport
    path, pad = attach(sdl)
    sdl.remove(path)
    with monkeypatch.context() as patch:
        patch.setattr(sdl.lib, 'SDL_OpenGamepad', lambda instance: None)
        patch.setattr(sdl.lib, 'SDL_GetError', lambda: b'Permission denied: /dev/hidraw99 PRIVATE')
        assert sdl.poll() == []
        debug = ControllerDebug(clock=lambda: 0)
        debug.report = InputReport('capture', 0, ['L1', 'R1'])
        debug.observe_sdl(sdl)
        report = debug.report.snapshot(1)
        assert report['devices'][0]['status'] == 'open_failed'
        assert report['devices'][0]['sdl_is_gamepad'] is True
        assert report['devices'][0]['sdl_error'] == 'permission_denied'
        assert '/dev/hidraw99' in capsys.readouterr().out
        import json
        assert 'PRIVATE' not in json.dumps(report) and '/dev/' not in json.dumps(report)
    sdl.poll()
    debug.observe_sdl(sdl)
    assert debug.report.snapshot(2)['devices'][0]['status'] == 'accepted'
    assert 'sdl_error' not in debug.report.snapshot(2)['devices'][0]


def test_diagnostics_includes_hints_with_zero_controllers(sdl):
    diagnostic = sdl.diagnostics()
    assert diagnostic['enumeration_failed'] is False
    assert diagnostic['joystick_count'] >= 0
    assert diagnostic['version'] == sdl.lib.SDL_GetVersion()
    assert diagnostic['hints']['SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS']['state'] == '1'
