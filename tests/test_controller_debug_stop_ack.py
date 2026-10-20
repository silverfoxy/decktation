import asyncio
from types import SimpleNamespace

import pytest
from binding_capture import read_json
from test_controller_debug_rpc import backend, live_backend, assert_snapshot


def test_stop_is_nonblocking_and_missing_ack_fails_after_two_seconds(backend, monkeypatch):
    plugin = backend.Plugin
    now = [100.0]
    debug = plugin._controller_debug()
    debug.clock = lambda: now[0]
    start = asyncio.run(plugin.start_controller_debug(None))
    async def forbidden_sleep(*args):
        pytest.fail('Stop must not wait for a listener')
    monkeypatch.setattr(backend.asyncio, 'sleep', forbidden_sleep)
    stopped = assert_snapshot(asyncio.run(plugin.stop_controller_debug(None, start['session'])))
    assert stopped['state'] == 'stopping'
    now[0] = 102.01
    result = assert_snapshot(asyncio.run(plugin.resume_controller_debug(None)))
    assert result['state'] == 'failed' and 'finish' in result['error']
    assert asyncio.run(plugin.stop_controller_debug(None, start['session'])) == result


def test_real_main_loop_stop_before_ack_discovers_devices_and_suppresses_actions(tmp_path, monkeypatch):
    """Replay actual poll loop: IPC, raw keys, discovery, finalization, rearming."""
    import controller_listener as listener
    from controller_debug_session import ControllerDebugSession
    now = [100.0]
    manager = ControllerDebugSession(str(tmp_path), clock=lambda: now[0])
    monkeypatch.setattr(listener, 'CONFIG_DIR', str(tmp_path))
    for name in ('STATE_FILE', 'PID_FILE', 'PREVIEW_FILE', 'CONTROLLER_TYPE_FILE', 'STATUS_FILE',
                 'HAPTIC_SOURCE_FILE', 'RECENT_SOURCE_FILE'):
        monkeypatch.setattr(listener, name, str(tmp_path / name))
    monkeypatch.setattr(listener.time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(listener.time, 'time', lambda: 9_999_999_999.0)
    monkeypatch.setattr(listener, 'load_button_config', lambda: ['L1'])
    monkeypatch.setattr(listener, 'find_steam_hidraw', lambda: iter(()))
    monkeypatch.setattr(listener, 'find_legion_go_s_hidraw', lambda: iter(()))
    scans = []
    def discover(pattern):
        scans.append(pattern)
        return ['/dev/input/pad'] + (['/dev/input/aux'] if len(scans) > 1 else [])
    monkeypatch.setattr(listener.glob, 'glob', discover)

    class Pad:
        identity = {'vendor_id': 0x045e, 'product_id': 0x0b13, 'bus': 5}
        supported_buttons = {'L1'}
        capability_keys = {0x136}
        capability_axes = set()
        key_buttons = {0x136: 'L1'}
        rejected = False
        reads = 0
        on_key = None
        def __init__(self, path, diagnostic_only=False):
            self.fd = 10 if path.endswith('pad') else 11
            self.rejected = self.fd == 11
            if self.rejected:
                self.capability_keys = {0x2c0}
        def states(self):
            return {'L1': False}
        def read_states(self):
            self.reads += 1
            pressed = self.reads != 2
            if self.on_key:
                self.on_key(0x136, int(pressed))
            yield {'L1': pressed}
        def close(self):
            pass
    monkeypatch.setattr(listener, 'EvdevGamepad', Pad)

    class Selector:
        calls = 0
        registered = {}
        def register(self, fd, events, path):
            self.registered[fd] = path
        def unregister(self, fd):
            del self.registered[fd]
        def select(self, timeout):
            self.calls += 1
            state = (tmp_path / 'STATE_FILE').read_text()
            if self.calls == 1:
                manager.start({'os_id': 'steamos'})
                assert manager.stop(manager.session)['state'] == 'stopping'
                now[0] += 0.1
                return []
            if self.calls == 2:
                assert 11 in self.registered, 'ACK must force discovery before early Stop finalizes'
                return [(SimpleNamespace(data='/dev/input/pad'), 1)]
            if self.calls == 3:
                assert state == '0'
                return []  # finish the grace drain
            if self.calls == 4:
                final = manager.resume()
                assert final['state'] == 'ready'
                assert final['device_count'] == 2 and final['event_count'] >= 1
                assert final['report']['metadata'] == {'os_id': 'steamos'}
                assert final['report']['devices'][0]['input_backend'] == 'evdev'
                assert final['report']['devices'][1]['bindings_accepted'] is False
                assert final['report']['devices'][1]['diagnostic_observed'] is True
                assert final['report']['events'][0]['at_ms'] < 1000
                assert state == '0', 'Held combo must not trigger after capture'
                return [(SimpleNamespace(data='/dev/input/pad'), 1)]  # release
            if self.calls == 5:
                assert state == '0'
                return [(SimpleNamespace(data='/dev/input/pad'), 1)]  # fresh press
            assert state == '1', 'Fresh press after full release must rearm normal PTT'
            raise KeyboardInterrupt
        def close(self):
            pass
    monkeypatch.setattr(listener.selectors, 'DefaultSelector', Selector)
    listener.main()
    assert read_json(tmp_path / 'controller_debug_result.json')['state'] == 'ready'


def test_real_selector_reuses_rejected_keyboard_fd_during_capture(tmp_path, monkeypatch):
    import os
    import selectors
    import controller_listener as listener
    from controller_debug_session import ControllerDebugSession

    manager = ControllerDebugSession(str(tmp_path))
    monkeypatch.setattr(listener, 'CONFIG_DIR', str(tmp_path))
    for name in ('STATE_FILE', 'PID_FILE', 'PREVIEW_FILE', 'CONTROLLER_TYPE_FILE', 'STATUS_FILE',
                 'HAPTIC_SOURCE_FILE', 'RECENT_SOURCE_FILE'):
        monkeypatch.setattr(listener, name, str(tmp_path / name))
    monkeypatch.setattr(listener, 'load_button_config', lambda: ['L1'])
    monkeypatch.setattr(listener, 'find_steam_hidraw', lambda: iter(()))
    monkeypatch.setattr(listener, 'find_legion_go_s_hidraw', lambda: iter(()))
    monkeypatch.setattr(listener.glob, 'glob', lambda _: [] if manager.session is None else
                        ['/dev/input/keyboard', '/dev/input/pad', '/dev/input/aux'])
    opened = {}

    class Pad:
        identity = {}
        capability_axes = set()
        supported_buttons = {'L1'}
        key_buttons = {0x136: 'L1'}
        on_key = None
        def __init__(self, path, diagnostic_only=False):
            assert diagnostic_only
            self.fd, self.writer = os.pipe()
            self.rejected = not path.endswith('pad')
            self.capability_keys = {30} if path.endswith('keyboard') else {0x136}
            opened[path] = self
        def states(self):
            return {'L1': False}
        def close(self):
            os.close(self.fd)
            os.close(self.writer)
    monkeypatch.setattr(listener, 'EvdevGamepad', Pad)
    real_selector = selectors.DefaultSelector

    class ReplaySelector(real_selector):
        calls = 0
        def select(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                assert manager.start({})['state'] == 'starting'
                return []
            if self.calls == 3:
                return []
            if self.calls == 4:
                assert manager.resume()['device_count'] == 2, 'controller-only rejects remain sampled'
                raise KeyboardInterrupt
            assert manager.resume()['state'] == 'recording', 'capture must be acknowledged'
            assert opened['/dev/input/keyboard'].fd == opened['/dev/input/pad'].fd
            assert {key.data for key in self.get_map().values()} == {
                '/dev/input/pad', '/dev/input/aux'}
            if self.calls == 2:
                manager.stop(manager.session)
                return []
    monkeypatch.setattr(listener.selectors, 'DefaultSelector', ReplaySelector)
    listener.main()


def test_back_to_back_capture_retains_rejected_diagnostic_interfaces(tmp_path, monkeypatch):
    import controller_listener as listener
    from controller_debug_session import ControllerDebugSession
    now = [100.0]
    manager = ControllerDebugSession(str(tmp_path), clock=lambda: now[0])
    monkeypatch.setattr(listener, 'CONFIG_DIR', str(tmp_path))
    for name in ('STATE_FILE', 'PID_FILE', 'PREVIEW_FILE', 'CONTROLLER_TYPE_FILE', 'STATUS_FILE',
                 'HAPTIC_SOURCE_FILE', 'RECENT_SOURCE_FILE'):
        monkeypatch.setattr(listener, name, str(tmp_path / name))
    monkeypatch.setattr(listener.time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(listener, 'load_button_config', lambda: ['L1'])
    monkeypatch.setattr(listener, 'find_steam_hidraw', lambda: iter(()))
    monkeypatch.setattr(listener, 'find_legion_go_s_hidraw', lambda: iter(()))
    monkeypatch.setattr(listener.glob, 'glob', lambda _: ['/dev/input/aux'] if manager.session else [])
    class Aux:
        identity = {}
        capability_keys = {0x2c0}
        capability_axes = set()
        rejected = True
        fd = 10
        keys = {0x2c0}
        def __init__(self, path, diagnostic_only=False):
            assert diagnostic_only
        def close(self):
            pass
    monkeypatch.setattr(listener, 'EvdevGamepad', Aux)
    finish = listener.ControllerDebug.finish_if_drained
    restarted = []
    def finish_and_restart(debug, *args, **kwargs):
        result = finish(debug, *args, **kwargs)
        if result and not restarted:
            assert manager.resume()['state'] == 'ready'
            restarted.append(manager.start({})['session'])
        return result
    monkeypatch.setattr(listener.ControllerDebug, 'finish_if_drained', finish_and_restart)
    class Selector:
        calls = 0
        def register(self, *args):
            pass
        def unregister(self, *args):
            pass
        def close(self):
            pass
        def select(self, timeout):
            self.calls += 1
            if self.calls == 1:
                manager.start({})
            elif self.calls == 2:
                manager.stop(manager.session)
            elif self.calls == 6:
                result = manager.resume()
                assert result['state'] == 'recording'
                assert result['device_count'] == 1
                raise KeyboardInterrupt
            return []
    monkeypatch.setattr(listener.selectors, 'DefaultSelector', Selector)
    listener.main()
