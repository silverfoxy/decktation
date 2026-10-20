import importlib
import json
from pathlib import Path
import uuid

import pytest
from binding_capture import read_json, write_json


@pytest.mark.parametrize('module', ['controller_debug_report', 'controller_debug_session', 'legion_go_s'])
def test_debug_modules_are_bundled_with_listener(module):
    root = Path(__file__).parents[1]
    assert 'src/' + module + '.py' in (root / 'backend/entrypoint.sh').read_text()
    for script in ('install_to_decky.sh', 'update_decktation_plugin.sh'):
        assert f'cp "$SOURCE_DIR/backend/src/{module}.py" "$PLUGIN_DIR/bin/"' in (root / script).read_text()


@pytest.fixture
def producer(monkeypatch, tmp_path):
    listener = importlib.import_module('controller_listener')
    monkeypatch.setattr(listener, 'CONFIG_DIR', str(tmp_path))
    now = [100.0]
    debug = listener.ControllerDebug(['L1'], clock=lambda: now[0])
    request = {'protocol': 2, 'session': uuid.uuid4().hex, 'listener_id': debug.listener_id,
               'requested_mono': 100.0, 'expires_mono': 105.0,
               'metadata': {'os_id': 'steamos', 'kernel_release': 'test-kernel'}}
    write_json(tmp_path / 'controller_debug_request.json', request)
    return debug, request, now


def stop(producer, tmp_path):
    debug, request, now = producer
    request['stopped'] = True
    write_json(tmp_path / 'controller_debug_request.json', request)
    assert debug.refresh()
    return debug


def test_listener_debug_session_writes_bounded_report_on_stop(producer, tmp_path):
    debug, request, now = producer
    assert debug.refresh()
    debug.device('event7', 'rejected', {'vendor_id': 0x17ef, 'name': 'private'}, keys={0x2c0}, axes={0})
    now[0] = 102
    debug.key('event7', 0x2c0, 1, None, now[0])
    now[0] = 103
    stop(producer, tmp_path)
    assert debug.finish_if_drained(pending=False)
    result = read_json(tmp_path / 'controller_debug_result.json')
    assert result['protocol'] == 2 and result['state'] == 'ready'
    assert result['started_mono'] == 100 and result['sequence'] > 1
    assert result['report']['phase'] == 'stopped'
    assert result['report']['events'][0]['code'] == 0x2c0
    assert 'private' not in json.dumps(result)
    now[0] = 104
    assert not debug.refresh()
    assert read_json(tmp_path / 'controller_debug_result.json') == result


def test_finished_debug_capture_does_not_rewrite_result(producer, tmp_path):
    debug, request, now = producer
    debug.refresh()
    now[0] = 130
    debug.refresh()
    assert debug.terminal_pending
    assert debug.finish_if_drained(pending=False)
    final = read_json(tmp_path / 'controller_debug_result.json')
    now[0] = 140
    debug.refresh()
    assert read_json(tmp_path / 'controller_debug_result.json') == final
    assert read_json(tmp_path / 'controller_debug_heartbeat.json')['observed_mono'] == 140


def test_rejected_keyboard_is_not_sampled_but_auxiliary_paddle_is():
    from controller_listener import inspect_rejected_device, InputReport
    from types import SimpleNamespace
    ordinary_keyboard = SimpleNamespace(rejected=True, capability_keys={0x1e, 0x30, 0x39})
    keyboard_helper = SimpleNamespace(rejected=True, capability_keys={0x1e, 0x130, 0x131, 0x2c0})
    auxiliary_paddle = SimpleNamespace(rejected=True, capability_keys={0x2c0})
    assert not inspect_rejected_device(ordinary_keyboard)
    assert inspect_rejected_device(keyboard_helper)
    assert inspect_rejected_device(auxiliary_paddle)

    report = InputReport('s', 0, [])
    report.device('hybrid', 'rejected', keys=keyboard_helper.capability_keys)
    report.key('hybrid', 0x1e, 1, None, 1)
    report.key('hybrid', 0x2c0, 1, None, 2)
    events = report.snapshot(3)['events']
    assert [event['code'] for event in events] == [0x2c0]


@pytest.mark.parametrize('natural', [True, False])
def test_terminal_capture_drains_bounded_pending_input(producer, tmp_path, natural):
    debug, request, now = producer
    assert debug.refresh()
    now[0] = 130 if natural else 103
    if natural:
        debug.refresh()
    else:
        stop(producer, tmp_path)
    assert debug.terminal_pending
    prior = read_json(tmp_path / 'controller_debug_result.json')
    assert prior['state'] == 'stopping' and prior['report']['phase'] == 'capturing'
    debug.device('event7', 'rejected', keys=[0x2c0])
    now[0] += 0.1
    debug.key('event7', 0x2c0, 1, None, now[0])
    assert not debug.finish_if_drained(pending=True)
    assert debug.finish_if_drained(pending=False)
    report = read_json(tmp_path / 'controller_debug_result.json')['report']
    assert report['phase'] == ('complete' if natural else 'stopped')
    assert report['events'][0]['at_ms'] == (30000 if natural else 3099)


def test_drain_never_exceeds_250ms_even_with_continuous_input(producer, tmp_path):
    debug, request, now = producer
    debug.refresh()
    stop(producer, tmp_path)
    now[0] += 0.251
    assert debug.finish_if_drained(pending=True)


def test_stop_before_first_refresh_writes_stopped_report(producer, tmp_path):
    debug, request, now = producer
    stop(producer, tmp_path)
    assert debug.terminal_pending
    debug.device('aux', 'rejected', keys=[0x2c0])
    assert debug.finish_if_drained(pending=False)
    result = read_json(tmp_path / 'controller_debug_result.json')
    assert result['session'] == request['session']
    assert result['report']['phase'] == 'stopped'
    assert result['report']['metadata']['os_id'] == 'steamos'
    assert len(result['report']['devices']) == 1


def test_debug_suppresses_ptt_until_every_held_button_is_released(producer, tmp_path):
    debug, request, now = producer
    from controller_listener import ComboTracker
    tracker = ComboTracker(['L1'])
    tracker.update('pad', {'L1': True})
    assert not debug.blocks_actions(tracker.sources)
    debug.refresh()
    assert debug.blocks_actions(tracker.sources)
    debug.device('pad', 'accepted', keys=[0x136])
    debug.key('pad', 0x136, 1, 'L1', now[0])
    assert len(debug.report.events) == 1  # observation is not suppressed
    stop(producer, tmp_path)
    debug.finish_if_drained(pending=False)
    assert debug.blocks_actions(tracker.sources)
    tracker.update('pad', {'L1': False, 'A': True})
    assert debug.blocks_actions(tracker.sources)
    tracker.update('pad', {'L1': False, 'A': False})
    assert not debug.blocks_actions(tracker.sources)
    tracker.update('pad', {'L1': True})
    assert tracker.active and not debug.blocks_actions(tracker.sources)


def test_first_ack_never_uses_old_request_clock(producer, tmp_path):
    debug, request, now = producer
    now[0] = 104.9
    assert debug.refresh()
    assert debug.report.started == 104.9
    now[0] = 130.1
    assert debug.refresh() and not debug.terminal_pending
    now[0] = 135
    assert debug.refresh() and debug.terminal_pending


def test_observed_interfaces_explain_backend_identity_and_binding_rejection(producer):
    from types import SimpleNamespace
    debug, _, now = producer
    debug.refresh()
    hid = SimpleNamespace(identity={'bus': 3, 'vendor_id': 0x28de, 'product_id': 0x1205,
                                    'serial': 'private'})
    debug.observe_device('/dev/hidraw0', hid, 'steam_deck')
    hybrid = SimpleNamespace(identity={'vendor_id': 0x2808}, rejected=True,
                             capability_keys={330}, capability_axes={0, 1})
    debug.observe_device('/dev/input/event6', hybrid, 'evdev_gamepad')
    debug.observe_device('unknown-hid', SimpleNamespace(), 'unknown')
    devices = debug.report.snapshot(now[0])['devices']
    assert devices[0]['input_backend'] == 'hidraw'
    assert devices[0]['controller_type'] == 'steam_deck'
    assert devices[0]['vendor_id'] == 0x28de and devices[0]['product_id'] == 0x1205
    assert devices[1]['rejection_reason'] == 'missing_gamepad_buttons'
    assert devices[1]['bindings_accepted'] is False
    assert devices[1]['diagnostic_observed'] is True
    assert 'vendor_id' not in devices[2] and 'product_id' not in devices[2]
    assert 'private' not in json.dumps(devices) and '/dev/' not in json.dumps(devices)


@pytest.mark.parametrize('uevent, expected', [
    ('HID_ID=0003:000028DE:00001205\nHID_UNIQ=private\n',
     {'bus': 3, 'vendor_id': 0x28de, 'product_id': 0x1205}),
    ('HID_ID=malformed\n', {}), ('', {})])
def test_hid_identity_is_read_from_kernel_not_invented(monkeypatch, uevent, expected):
    import builtins
    import io
    from controller_listener import RawGamepad
    monkeypatch.setattr(builtins, 'open', lambda *a, **kw: io.StringIO(uevent))
    monkeypatch.setattr('controller_listener.os.open', lambda *a: 123)
    assert RawGamepad('/dev/hidraw0').identity == expected


def test_initial_held_state_preserves_first_release_without_typing(producer, tmp_path):
    from types import SimpleNamespace
    debug, _, now = producer
    debug.refresh()
    device = SimpleNamespace(identity={}, rejected=False,
        capability_keys={0x136, 30}, capability_axes={0, 1}, keys={0x136, 30},
        states=lambda: {'L1': True, 'private': True})
    debug.observe_device('private-path', device, 'evdev_gamepad')
    now[0] = 101
    debug.key('private-path', 0x136, 0, 'L1', now[0])
    stop(producer, tmp_path)
    debug.finish_if_drained(pending=False)
    report = read_json(tmp_path / 'controller_debug_result.json')['report']
    assert report['initial_state'] == [{'source': 'source_1', 'at_ms': 0,
        'known': True, 'buttons': ['L1'], 'keys': [0x136]}]
    assert report['events'] == [{'source': 'source_1', 'at_ms': 1000,
        'kind': 'key', 'code': 0x136, 'button': 'L1', 'pressed': False}]
    assert 'private' not in json.dumps(report)


def test_input_loss_and_disconnect_preserve_interface_evidence_and_clear_live(producer, tmp_path):
    from types import SimpleNamespace
    debug, _, now = producer
    debug.refresh()
    device = SimpleNamespace(identity={'vendor_id': 123}, rejected=False,
        capability_keys={0x130}, capability_axes={0, 1}, keys=set(),
        states=lambda: {'A': False}, resync_count=5, dropped=False)
    debug.observe_device('pad', device, 'evdev_gamepad')
    debug.transition('pad', 'mapped', 'A', True, now[0])
    device.resync_count = 6
    debug.observe_loss('pad', device)
    debug.disconnected('pad', 19)
    assert debug.report.live_input() == {'pressed': [], 'last_event': None}
    stop(producer, tmp_path)
    debug.finish_if_drained(pending=False)
    item = read_json(tmp_path / 'controller_debug_result.json')['report']['devices'][0]
    assert item['status'] == 'disconnected' and item['errno'] == 19
    assert item['keys'] == [0x130] and item['vendor_id'] == 123
    assert item['input_dropped'] is True and item['resync_count'] == 1
    assert item['bindings_accepted'] is True and item['diagnostic_observed'] is True
