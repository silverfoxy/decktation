"""Behavior tests for the authoritative lifecycle (no renderer clocks)."""
import importlib

import pytest

from binding_capture import read_json, write_json


@pytest.fixture
def capture(tmp_path, monkeypatch):
    import controller_listener
    from controller_debug_session import ControllerDebugSession
    now = [100.0]
    monkeypatch.setattr(controller_listener, 'CONFIG_DIR', str(tmp_path))
    listener = controller_listener.ControllerDebug(['L1'], clock=lambda: now[0])
    manager = ControllerDebugSession(str(tmp_path), clock=lambda: now[0])
    listener.refresh()
    return manager, listener, now


def test_real_listener_ack_stop_and_frozen_report(capture):
    manager, listener, now = capture
    started = manager.start({'os_id': 'steamos', 'name': 'private'})
    now[0] += 4
    listener.refresh()
    assert manager.resume()['state'] == 'recording'
    assert manager.resume()['remaining_ms'] == 30000
    listener.device('private-path', 'accepted', keys=[0x130])
    now[0] += 1
    listener.key('private-path', 0x130, 1, 'A', now[0])
    stopped = manager.stop(started['session'])
    assert stopped['state'] == 'stopping' and stopped['report'] is None
    assert manager.stop(started['session'])['revision'] == stopped['revision']
    assert manager.start({'os_id': 'different'})['session'] == started['session']
    assert manager.metadata == {'os_id': 'steamos'}
    listener.refresh()
    assert listener.finish_if_drained(now[0], pending=False)
    final = manager.resume()
    assert final['state'] == 'ready'
    assert final['report']['events'][0]['at_ms'] == 1000
    assert final['report']['metadata'] == {'os_id': 'steamos'}
    assert final['device_count'] == final['event_count'] == 1
    listener.report.events.clear()
    now[0] += 100
    assert manager.get(started['session']) == final
    assert manager.stop(started['session']) == final


def test_stop_before_ack_preserves_device_discovery_and_metadata(capture):
    manager, listener, now = capture
    started = manager.start({'os_id': 'steamos'})
    assert manager.stop(started['session'])['state'] == 'stopping'
    listener.refresh()
    listener.device('internal', 'rejected', keys=[0x2c0])
    listener.finish_if_drained(now[0], pending=False)
    result = manager.resume()
    assert result['state'] == 'ready'
    assert result['report']['metadata'] == {'os_id': 'steamos'}
    assert result['device_count'] == 1


def test_restart_never_replays_an_existing_request(capture, tmp_path):
    manager, listener, now = capture
    manager.start({})
    listener.refresh()
    assert manager.resume()['state'] == 'recording'
    import controller_listener
    restarted = controller_listener.ControllerDebug(clock=lambda: now[0])
    assert restarted.refresh() is False
    assert restarted.report is None
    assert manager.resume()['state'] == 'failed'


def test_legacy_requests_and_expired_requests_are_not_accepted(capture, tmp_path):
    manager, listener, now = capture
    write_json(tmp_path / 'controller_debug_request.json', {
        'session': 'legacy', 'started': 100, 'deadline': 130})
    assert listener.refresh() is False
    manager.start({})
    now[0] += 6
    assert listener.refresh() is False
    assert manager.resume()['state'] == 'failed'


def producer_result(manager, now, **changes):
    result = {'protocol': 2, 'session': manager.session, 'listener_id': manager.listener_id,
              'sequence': manager.sequence + 1, 'state': 'recording',
              'started_mono': manager.started if manager.started is not None else now,
              'observed_mono': now, 'report': {'phase': 'capturing', 'devices': [], 'events': []}}
    result.update(changes)
    write_json(manager.path('result'), result)
    return result


@pytest.mark.parametrize('changes', [
    {'protocol': 1}, {'protocol': 2.0}, {'session': 'old'}, {'listener_id': 'other'},
    {'state': 'stopping'}, {'started_mono': 10 ** 400},
    {'sequence': 0}, {'sequence': True}, {'sequence': -1}, {'sequence': '3'},
    {'state': 'ready', 'report': {}}, {'state': 'ready', 'report': None},
    {'state': 'ready', 'report': {'devices': [], 'events': []}},
    {'state': 'ready', 'report': {'phase': 'bogus', 'devices': [], 'events': []}},
    {'state': 'ready', 'report': {'phase': 'complete', 'devices': [], 'events': []}},
    {'state': 'ready', 'report': {'phase': 'stopped', 'devices': [], 'events': []}},
    {'state': []}, {'state': {}}, {'started_mono': float('nan')},
    {'started_mono': 99}, {'started_mono': 106}, {'observed_mono': float('inf')},
    {'observed_mono': 99}, {'observed_mono': 101},
    {'report': {'phase': 'capturing', 'devices': None, 'events': []}},
])
def test_invalid_producer_results_never_finalize_or_ack(capture, changes):
    manager, listener, now = capture
    start = manager.start({})
    producer_result(manager, now[0], **changes)
    response = manager.resume()
    assert response['state'] == 'starting' and response['report'] is None
    assert manager.sequence == 0 and response['revision'] == start['revision']


def test_stale_previous_session_result_is_ignored(capture):
    manager, listener, now = capture
    manager.start({})
    listener.refresh()
    manager.stop(manager.session)
    listener.refresh()
    listener.finish_if_drained(pending=False)
    assert manager.resume()['state'] == 'ready'
    previous = read_json(manager.path('result'))
    new = manager.start({})
    assert new['session'] != previous['session'] and new['state'] == 'starting'
    assert manager.resume()['state'] == 'starting'
    listener.refresh()
    assert manager.resume()['state'] == 'recording'
    write_json(manager.path('result'), previous)
    assert manager.resume()['state'] == 'recording'


def test_old_sequence_and_changed_ack_clock_cannot_replace_newer_snapshot(capture):
    manager, listener, now = capture
    manager.start({})
    listener.refresh()
    manager.resume()
    revision = manager.revision
    result = read_json(manager.path('result'))
    result['report']['devices'] = [{'source': 'source_1'}]
    write_json(manager.path('result'), result)
    assert manager.resume()['device_count'] == 0
    assert manager.revision == revision
    result.update(sequence=result['sequence'] + 1, started_mono=100.1, observed_mono=100.1)
    now[0] = 100.1
    write_json(manager.path('result'), result)
    assert manager.resume()['device_count'] == 0 and manager.revision == revision


@pytest.mark.parametrize('wall', [1, 9_999_999_999])
def test_wall_clock_jumps_cannot_end_capture(capture, monkeypatch, wall):
    import time
    manager, listener, now = capture
    manager.start({})
    listener.refresh()
    manager.resume()
    monkeypatch.setattr(time, 'time', lambda: wall)
    now[0] = 101
    listener.refresh()
    snapshot = manager.resume()
    assert snapshot['state'] == 'recording' and snapshot['remaining_ms'] == 29000


def test_startup_timeout_and_failure_are_terminal(capture):
    manager, listener, now = capture
    manager.start({})
    now[0] = 105.01
    result = manager.resume()
    assert result['state'] == 'failed' and 'acknowledge' in result['error']
    listener.refresh()
    assert manager.resume() == result
    assert manager.stop(manager.session) == result


def test_alive_but_stalled_reader_fails_on_heartbeat_loss(capture):
    manager, listener, now = capture
    manager.start({})
    listener.refresh()
    manager.resume()
    now[0] = 102.01
    result = manager.resume()
    assert result['state'] == 'failed' and 'heartbeat' in result['error']


def test_natural_deadline_waits_for_exact_producer_final(capture):
    manager, listener, now = capture
    manager.start({'os_id': 'steamos'})
    listener.refresh()
    manager.resume()
    listener.device('pad', 'accepted', keys=[0x130])
    now[0] = 129.99
    listener.key('pad', 0x130, 1, 'A', now[0])
    now[0] = 130
    listener.refresh()
    waiting = manager.resume()
    assert waiting['state'] == 'stopping' and waiting['report'] is None
    listener.key('pad', 0x130, 0, 'A', 130.1)
    listener.finish_if_drained(130.2, pending=False)
    now[0] = 130.2
    final = manager.resume()
    assert final['state'] == 'ready' and final['report']['phase'] == 'complete'
    assert [event['pressed'] for event in final['report']['events']] == [True, False]
    assert final['report']['events'][-1]['at_ms'] == 30000


def test_capture_finalization_timeout_never_returns_empty_ready(capture):
    manager, listener, now = capture
    manager.start({})
    listener.refresh()
    manager.resume()
    now[0] = 132.01
    listener.refresh()  # healthy process, but no final publication
    result = manager.resume()
    assert result['state'] == 'failed' and result['report'] is None
    assert 'finish' in result['error']


def test_late_final_publication_is_rejected(capture):
    manager, listener, now = capture
    manager.start({})
    listener.refresh()
    manager.resume()
    manager.stop(manager.session)
    now[0] = 103
    listener.refresh()
    listener.finish_if_drained(pending=False)
    result = manager.resume()
    assert result['state'] == 'failed' and result['report'] is None


def test_malformed_json_bytes_do_not_crash_lifecycle(capture):
    manager, listener, now = capture
    manager.start({})
    from pathlib import Path
    Path(manager.path('result')).write_bytes(b'\xff\xfe')
    assert manager.resume()['state'] == 'starting'


def test_new_listener_bootstraps_request_before_first_ack(tmp_path, monkeypatch):
    import controller_listener
    from controller_debug_session import ControllerDebugSession
    now = [100.0]
    monkeypatch.setattr(controller_listener, 'CONFIG_DIR', str(tmp_path))
    manager = ControllerDebugSession(str(tmp_path), clock=lambda: now[0])
    initial = manager.start({'os_id': 'steamos'})
    assert initial['state'] == 'starting'
    assert not (tmp_path / 'controller_debug_request.json').exists()
    listener = controller_listener.ControllerDebug(clock=lambda: now[0])
    assert not listener.refresh()
    assert manager.resume()['state'] == 'starting'
    assert listener.refresh()
    assert manager.resume()['state'] == 'recording'
    assert manager.resume()['session'] == initial['session']


def test_concurrent_start_and_background_reads_keep_one_session(capture):
    from concurrent.futures import ThreadPoolExecutor
    manager, listener, now = capture
    with ThreadPoolExecutor(max_workers=8) as pool:
        snapshots = list(pool.map(lambda _: manager.start({'os_id': 'steamos'}), range(40)))
    assert len({snapshot['session'] for snapshot in snapshots}) == 1
    assert {snapshot['state'] for snapshot in snapshots} == {'starting'}
    assert manager.requested == 100


def test_delayed_ack_starts_a_full_thirty_second_monotonic_window(tmp_path):
    module = importlib.import_module('controller_debug_session')
    now = [100.0]
    manager = module.ControllerDebugSession(str(tmp_path), clock=lambda: now[0])
    write_json(tmp_path / 'controller_debug_heartbeat.json', {
        'protocol': 2, 'listener_id': 'reader', 'observed_mono': 100.0})
    start = manager.start({'os_id': 'steamos'})
    assert start['state'] == 'starting' and start['report'] is None
    assert start['remaining_ms'] == 30000
    request = read_json(tmp_path / 'controller_debug_request.json')
    assert request['protocol'] == 2 and request['requested_mono'] == 100
    assert 'started' not in request and 'deadline' not in request
    now[0] = 104
    write_json(tmp_path / 'controller_debug_heartbeat.json', {
        'protocol': 2, 'listener_id': 'reader', 'observed_mono': 104.0})
    write_json(tmp_path / 'controller_debug_result.json', {
        'protocol': 2, 'session': start['session'], 'listener_id': 'reader',
        'sequence': 1, 'state': 'recording', 'started_mono': 104.0,
        'observed_mono': 104.0, 'report': {'phase': 'capturing', 'metadata': {'os_id': 'steamos'},
                                        'devices': [], 'events': []}})
    ack = manager.get(start['session'])
    assert ack['state'] == 'recording' and ack['remaining_ms'] == 30000
    assert ack['revision'] > start['revision'] and ack['report'] is None
    now[0] = 105
    assert manager.resume()['remaining_ms'] == 29000
    assert manager.start({})['session'] == start['session']


@pytest.mark.parametrize('publication', ['heartbeat', 'result'])
def test_concurrent_publication_is_validated_against_clock_after_read(capture, monkeypatch, publication):
    import controller_debug_session as module
    manager, listener, now = capture
    manager.start({})
    listener.refresh()
    assert manager.resume()['state'] == 'recording'
    previous_sequence = manager.sequence
    original_read = module.read_bounded
    published = []
    def read(path):
        if path == manager.path(publication) and not published:
            published.append(True)
            # Legal producer publishes after the consumer begins its poll.
            now[0] += 0.000001
            if publication == 'heartbeat':
                write_json(path, {'protocol': 2, 'listener_id': manager.listener_id,
                                 'observed_mono': now[0]})
            else:
                producer_result(manager, now[0])
        return original_read(path)
    monkeypatch.setattr(module, 'read_bounded', read)
    result = manager.resume()
    assert published
    assert result['state'] == 'recording' and 'error' not in result
    if publication == 'result':
        assert manager.sequence == previous_sequence + 1
        assert manager.observed == now[0]


def test_genuinely_future_heartbeat_still_fails_established_capture(capture):
    manager, listener, now = capture
    manager.start({})
    listener.refresh()
    manager.resume()
    write_json(manager.path('heartbeat'), {'protocol': 2, 'listener_id': manager.listener_id,
                                         'observed_mono': now[0] + 0.000001})
    result = manager.resume()
    assert result['state'] == 'failed' and 'heartbeat' in result['error']


def test_heartbeat_age_uses_clock_after_read(capture, monkeypatch):
    import controller_debug_session as module
    manager, listener, now = capture
    manager.start({})
    listener.refresh()
    manager.resume()
    original_read = module.read_bounded
    def read(path):
        value = original_read(path)
        if path == manager.path('heartbeat'):
            now[0] = 102.01
        return value
    monkeypatch.setattr(module, 'read_bounded', read)
    result = manager.resume()
    assert result['state'] == 'failed' and 'heartbeat' in result['error']


@pytest.mark.parametrize('natural', [False, True])
def test_terminal_report_explains_duration_stop_and_event_truncation(capture, natural):
    manager, listener, now = capture
    manager.start({})
    listener.refresh()
    listener.device('pad', 'accepted', keys=[0x130])
    for index in range(300):
        listener.key('pad', 0x130, (index + 1) % 2, 'A', now[0])
    now[0] = 130 if natural else 103
    listener.refresh()
    if not natural:
        manager.stop(manager.session)
    listener.refresh()
    now[0] += 0.1
    listener.finish_if_drained(pending=False)
    report = manager.resume()['report']
    assert report['duration_ms'] == (30000 if natural else 3000)
    assert report['stop_reason'] == ('capture_timeout' if natural else 'stop_requested')
    assert report['truncation']['events'] is True
    assert report['events_dropped'] == 44
    assert report['truncation']['devices'] is False


def test_live_summary_is_bounded_sanitized_and_rejects_stale_producer_evidence(capture):
    from controller_debug_report import BUTTONS
    manager, listener, now = capture
    manager.start({})
    listener.refresh()
    for index in range(20):
        path = f'/dev/input/private{index}'
        listener.device(path, 'accepted')
        for button in BUTTONS:
            listener.transition(path, 'mapped', button, True, now[0])
    listener.refresh()
    result = manager.resume()
    assert len(result['live_input']['pressed']) == 32
    raw = read_json(manager.path('result'))
    raw['sequence'] += 1
    raw['live_input'] = {'pressed': [
        {'source': 'source_1', 'button': 'A', 'serial': 'private'},
        {'source': '/dev/private', 'button': 'A'},
        {'source': 'source_1', 'button': {'name': 'private'}}],
        'last_event': {'source': 'source_1', 'kind': 'key', 'code': 30,
                       'pressed': True, 'at_ms': 0, 'path': '/dev/private'}}
    write_json(manager.path('result'), raw)
    sanitized = manager.resume()
    assert sanitized['live_input'] == {'pressed': [{'source': 'source_1', 'button': 'A'}], 'last_event': None}
    raw['live_input']['pressed'] = []
    write_json(manager.path('result'), raw)  # unchanged producer sequence
    assert manager.resume()['live_input'] == sanitized['live_input']
    now[0] += 2.01
    failed = manager.resume()
    assert failed['state'] == 'failed'
    assert failed['live_input'] == {'pressed': [], 'last_event': None}


def test_authoritative_metadata_is_bounded_together_with_frozen_report(capture):
    import json
    from controller_debug_report import BUTTONS, METADATA_FIELDS
    manager, listener, now = capture
    manager.start({key: '\U0001f3ae' * 120 for key in METADATA_FIELDS})
    listener.refresh()
    listener.report.metadata = {}  # Producer metadata is not authoritative.
    for index in range(16):
        path = f'event{index}'
        listener.device(path, 'accepted', keys=range(0x100, 0x160), axes=range(64))
        listener.report.initial(path, dict.fromkeys(BUTTONS, True), range(0x100, 0x160), now[0])
    for index in range(256):
        listener.transition('event0', 'hid', 'Left Trackpad', bool(index % 2), now[0])
    manager.stop(manager.session)
    listener.refresh()
    listener.finish_if_drained(pending=False)
    final = manager.resume()['report']
    assert len(json.dumps(final).encode()) <= 32768
    assert final['truncation']['bytes'] is True
