import json
import time
from unittest.mock import MagicMock

import pytest

from controller_debug_report import InputReport, sanitize_report
from gamepad_evdev import EvdevGamepad, EVENT
import telemetry


def test_report_includes_allowlisted_runtime_and_os_build_metadata():
    from controller_debug_report import collect_runtime_metadata
    metadata = collect_runtime_metadata('0.3.20-dev.abc123', reader=lambda path: {
        '/etc/os-release': 'ID=steamos\nVERSION_ID=3.7.8\nBUILD_ID=20260501.1\nPRETTY_NAME="SteamOS 3.7.8"',
        '/sys/devices/virtual/dmi/id/sys_vendor': 'LENOVO',
        '/sys/devices/virtual/dmi/id/product_name': 'Legion Go',
        '/sys/devices/virtual/dmi/id/product_version': '8APU1',
        '/sys/devices/virtual/dmi/id/product_sku': '83E1',
        '/sys/devices/virtual/dmi/id/bios_version': 'N3CN40WW',
        '/proc/cpuinfo': 'model name : AMD Ryzen Z1 Extreme',
        '/sys/devices/virtual/dmi/id/product_serial': 'DO-NOT-COLLECT',
    }.get(path, ''))
    report = InputReport('s', 0, ['L4'], metadata=metadata).snapshot(1)
    assert report['metadata']['decktation_version'] == '0.3.20-dev.abc123'
    assert report['metadata']['os_id'] == 'steamos'
    assert report['metadata']['os_version'] == '3.7.8'
    assert report['metadata']['os_build'] == '20260501.1'
    assert report['metadata']['kernel_release']
    assert report['metadata']['device_vendor'] == 'LENOVO'
    assert report['metadata']['device_model'] == 'Legion Go'
    assert report['metadata']['device_product_version'] == '8APU1'
    assert report['metadata']['device_sku'] == '83E1'
    assert report['metadata']['cpu_model'] == 'AMD Ryzen Z1 Extreme'
    assert report['metadata']['bios_version'] == 'N3CN40WW'
    assert 'DO-NOT-COLLECT' not in json.dumps(report)


def test_capture_records_unknown_key_and_mapping_without_names():
    report = InputReport('session', 100, ['L4', 'R4'])
    report.device('event7', 'rejected', {'vendor_id': 0x17ef, 'product_id': 0x6182,
                  'name': 'Personal Legion', 'path': '/dev/input/event7'}, keys=[0x130, 0x2c0], axes=[0, 1])
    report.key('event7', 0x2c0, 1, None, 101)
    report.key('event7', 0x2c0, 2, None, 102)
    report.key('event7', 0x2c0, 0, None, 103)
    result = report.snapshot(104)
    assert result['devices'][0]['status'] == 'rejected'
    assert result['events'] == [
        {'at_ms': 1000, 'source': 'source_1', 'kind': 'key', 'code': 0x2c0, 'pressed': True},
        {'at_ms': 3000, 'source': 'source_1', 'kind': 'key', 'code': 0x2c0, 'pressed': False}]
    assert 'Personal' not in json.dumps(result) and '/dev/' not in json.dumps(result)


@pytest.mark.parametrize('held_on_reconnect', [False, True], ids=['released', 'held'])
def test_reconnect_reseeds_current_state_without_rewriting_initial_evidence(held_on_reconnect):
    report = InputReport('session', 100, ['L4', 'R4'])
    path = '/dev/input/event7'
    report.device(path, 'accepted', keys=[0x2c0, 0x2c1])
    report.initial(path, {'L4': True}, [0x2c0], 101)
    original_initial = [{'source': 'source_1', 'at_ms': 1000, 'known': True,
                         'keys': [0x2c0], 'buttons': ['L4']}]
    assert report.snapshot(101)['initial_state'] == original_initial

    report.disconnected(path)
    assert report.live_input() == {'pressed': [], 'last_event': None}
    report.device(path, 'accepted', keys=[0x2c0, 0x2c1])
    states = {'R4': held_on_reconnect}
    keys = [0x2c1] if held_on_reconnect else []
    report.initial(path, states, keys, 103)
    assert report.live_input()['pressed'] == (
        [{'source': 'source_1', 'button': 'R4'}] if held_on_reconnect else [])

    code, button = (0x2c1, 'R4') if held_on_reconnect else (0x2c0, 'L4')
    expected_events = []
    if not held_on_reconnect:
        report.key(path, code, 1, button, 104)
        expected_events.append({'at_ms': 4000, 'source': 'source_1', 'kind': 'key',
                                'code': code, 'pressed': True, 'button': button})
        assert report.live_input()['pressed'] == [{'source': 'source_1', 'button': button}]
    # Publishing the same connection's initial snapshot must not reset tracking.
    report.initial(path, states, keys, 105)
    report.key(path, code, 0, button, 106)
    expected_events.append({'at_ms': 6000, 'source': 'source_1', 'kind': 'key',
                            'code': code, 'pressed': False, 'button': button})
    report.initial(path, states, keys, 107)
    report.key(path, code, 0, button, 108)
    assert report.live_input()['pressed'] == []
    result = report.snapshot(109)
    assert result['events'] == expected_events
    assert result['initial_state'] == original_initial
    assert [device['source'] for device in result['devices']] == ['source_1']
    assert path not in json.dumps(result)


def test_drain_grace_is_bounded_and_clamps_timestamps():
    report = InputReport('session', 100, [])
    report.device('event7', 'rejected', keys=[0x2c0])
    report.begin_drain(130)
    report.key('event7', 0x2c0, 1, None, 130.1)
    report.key('event7', 0x2c0, 0, None, 130.251)

    events = report.snapshot(130.3)['events']
    assert len(events) == 1
    assert events[0]['at_ms'] == 30000


def test_report_limits_duration_devices_events_and_size():
    report = InputReport('session', 0, ['L1'])
    for i in range(50):
        report.device(f'event{i}', 'accepted', {}, keys=range(700), axes=range(200))
    for i in range(1000):
        report.key('event0', 0x2c0, i % 2, None, i / 100)
    report.key('event0', 0x2c0, 1, None, 31)
    result = report.snapshot(100)
    assert result['phase'] == 'complete'
    assert len(result['devices']) <= 16
    assert len(result['events']) <= 256
    assert len(json.dumps(result).encode()) <= 32768
    assert all(event['at_ms'] <= 30000 for event in result['events'])


def test_rejected_evdev_reader_captures_raw_keys_without_mapping(monkeypatch):
    from gamepad_evdev import ioctl_read
    import gamepad_evdev
    def ioctl(fd, number, size):
        if number == 0x21: return bytes(size)
        if number == 0x23: return bytes(size)
        if number == 0x18: return bytes(size)
        if number == 0x02: return bytes(8)
        raise AssertionError(number)
    monkeypatch.setattr(gamepad_evdev.os, 'open', lambda *a: 123)
    monkeypatch.setattr(gamepad_evdev.os, 'close', lambda *a: None)
    monkeypatch.setattr(gamepad_evdev, 'ioctl_read', ioctl)
    device = EvdevGamepad('/dev/input/event9', diagnostic_only=True)
    assert device.rejected
    seen = []
    device.on_key = lambda code, value: seen.append((code, value))
    monkeypatch.setattr(gamepad_evdev.os, 'read', lambda fd, size: EVENT.pack(0, 0, 1, 0x2c0, 1))
    list(device.read_states())
    assert seen == [(0x2c0, 1)]


def test_sanitizer_rejects_user_supplied_metadata_and_bounds_events():
    unsafe = {'session': 'secret', 'path': '/dev/input/event7', 'devices': [
        {'source': 'source_1', 'status': 'rejected', 'vendor_id': 0x17ef,
         'name': 'My Private Controller', 'keys': [0x2c0, 0x9999], 'axes': [0, 1],
         'error': '/home/alice/private'}],
         'events': [{'source': 'source_1', 'kind': 'key', 'code': 0x2c0,
                     'pressed': True, 'serial': 'private'}] * 1000}
    result = sanitize_report(unsafe)
    serialized = json.dumps(result)
    assert len(serialized.encode()) <= 32768
    assert len(result['events']) <= 256
    for private in ('secret', '/dev/', 'Private', '/home/', 'private'):
        assert private not in serialized


def test_sanitizer_tolerates_malformed_nested_fields():
    result = sanitize_report({'configured_buttons': [{'name': 'private'}],
        'devices': [{'source': 'source_1', 'status': 'accepted', 'keys': [[1], 0x2c0]}],
        'events': [{'source': {'path': '/dev/private'}, 'kind': 'key', 'code': 1,
                    'at_ms': 0, 'pressed': True}]})
    assert result['configured_buttons'] == []
    assert result['events'] == []
    assert result['devices'][0]['keys'] == [0x2c0]


def test_selected_hid_trackpad_transition_is_allowlisted():
    result = sanitize_report({'devices': [{'source': 'source_1', 'status': 'hidraw'}],
        'events': [{'source': 'source_1', 'kind': 'hid', 'at_ms': 1,
                    'button': 'Left Trackpad', 'pressed': True}]})
    assert result['events'][0]['button'] == 'Left Trackpad'


def test_capabilities_prioritize_gamepad_and_trigger_happy_codes():
    report = InputReport('s', 0, [])
    report.device('event1', 'rejected', {}, keys=set(range(100)) | {0x116, 0x130, 0x2c0, 0x2c1})
    keys = report.snapshot(1)['devices'][0]['keys']
    assert {0x116, 0x130, 0x2c0, 0x2c1}.issubset(keys)
    report.key('event1', 0x116, 1, None, 1)
    assert report.snapshot(2)['events'][0]['code'] == 0x116

def test_controller_button_ranges_keep_dpad_and_reject_keyboard_extension_codes():
    report = InputReport('s', 0, [])
    report.device('event1', 'accepted', {}, keys={0x130, 0x200, 0x220, 0x2c0})
    report.key('event1', 0x200, 1, None, 1)
    report.key('event1', 0x220, 1, 'D-pad Up', 2)
    result = report.snapshot(3)
    assert 0x200 not in result['devices'][0]['keys']
    assert {0x220, 0x2c0}.issubset(result['devices'][0]['keys'])
    assert [event['code'] for event in result['events']] == [0x220]


def test_keyboard_codes_never_enter_local_report_or_upload_sanitizer():
    report = InputReport('s', 0, [])
    report.device('event1', 'rejected', {}, keys={0x1e, 0x30, 0x130, 0x200, 0x2c0})
    report.key('event1', 0x1e, 1, None, 1)
    report.key('event1', 0x200, 1, None, 1)
    report.key('event1', 0x130, 1, 'A', 1)
    local = report.snapshot(2)
    assert set(local['devices'][0]['keys']) == {0x130, 0x2c0}
    assert [e['code'] for e in local['events']] == [0x130]
    malicious = {'devices': [{'source': 'source_1', 'keys': [0x1e, 0x130, 0x200]}],
                 'events': [{'source': 'source_1', 'kind': 'key', 'at_ms': 0,
                             'code': 0x1e, 'pressed': True},
                            {'source': 'source_1', 'kind': 'key', 'at_ms': 0,
                             'code': 0x200, 'pressed': True}]}
    safe = sanitize_report(malicious)
    assert safe['devices'][0]['keys'] == [0x130]
    assert safe['events'] == []


def test_explicit_upload_is_isolated_and_does_not_enable_telemetry(monkeypatch):
    monkeypatch.setattr(telemetry, '_enabled', False)
    events = []
    class FakeScope:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def add_attachment(self, **kw): events.append(kw)
    class FakeClient:
        def __init__(self, **options): self.options = options
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def capture_event(self, event, scope):
            events.append(event)
            return 'abc123'
        def flush(self, timeout): return True
    monkeypatch.setattr(telemetry.sentry_sdk, 'Client', FakeClient)
    monkeypatch.setattr(telemetry.sentry_sdk, 'Scope', FakeScope)
    event_id = telemetry.upload_controller_report({'events': [], 'devices': []}, 'test')
    assert event_id == 'abc123'
    assert not telemetry.is_enabled()
    assert events[0]['filename'] == 'controller-input-report.json'
    assert events[1]['message'] == 'User-submitted controller input report'
    assert events[0]['bytes'] == json.dumps(sanitize_report({'events': [], 'devices': []}), separators=(',', ':')).encode()


def test_real_sdk_attachment_is_delivered_to_isolated_transport(monkeypatch):
    from sentry_sdk.transport import Transport
    envelopes = []
    class MemoryTransport(Transport):
        def capture_envelope(self, envelope): envelopes.append(envelope)
    actual_client = telemetry.sentry_sdk.Client
    monkeypatch.setattr(telemetry.sentry_sdk, 'Client', lambda **kw: actual_client(
        **{**kw, 'transport': MemoryTransport()}))
    monkeypatch.setattr(telemetry, '_enabled', False)
    event_id = telemetry.upload_controller_report({'devices': [], 'events': []}, 'test')
    assert event_id
    assert not telemetry.is_enabled()
    assert len(envelopes) == 1
    assert {item.headers['type'] for item in envelopes[0].items} == {'event', 'attachment'}


def test_maximum_report_indicates_every_bound_and_is_idempotently_sanitized():
    from controller_debug_report import BUTTONS
    report = InputReport('s', 0, list(BUTTONS)[:5])
    for index in range(20):
        path = f'event{index}'
        report.device(path, 'accepted', keys=range(0x100, 0x300), axes=range(64))
        report.initial(path, {button: True for button in BUTTONS}, range(0x100, 0x160), 0)
    for index in range(256):
        report.event('event0', 'mapped', index / 100, button='Left Trackpad', pressed=bool(index % 2))
    result = report.snapshot(4)
    assert result['truncation']['devices'] is True
    assert result['truncation']['bytes'] is True
    assert all(device['capabilities_truncated'] for device in result['devices'])
    assert len(json.dumps(result).encode()) <= 32768
    assert len(result['devices']) == len(result['initial_state']) == 16
    assert all(len(item['keys']) <= 48 and len(item['buttons']) <= 32 for item in result['initial_state'])
    assert sanitize_report(result) == result


def test_byte_limit_holds_even_when_metadata_and_initial_state_fill_payload():
    from controller_debug_report import BUTTONS, METADATA_FIELDS
    report = InputReport('s', 0, ['L1'], {key: '\U0001f3ae' * 120 for key in METADATA_FIELDS})
    for index in range(16):
        path = f'event{index}'
        report.device(path, 'accepted', keys=range(0x100, 0x160), axes=range(64))
        report.initial(path, dict.fromkeys(BUTTONS, True), range(0x100, 0x160), 0)
    result = report.snapshot(1)
    assert len(json.dumps(result).encode()) <= 32768
    assert result['truncation']['bytes'] is True
    assert sanitize_report(result) == result
