import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from binding_capture import read_json, write_json


@pytest.fixture
def backend(monkeypatch, tmp_path):
    import audio_runtime
    repo = Path(__file__).parents[1]
    monkeypatch.setitem(sys.modules, 'decky', SimpleNamespace(
        logger=MagicMock(), DECKY_USER_HOME=str(tmp_path), DECKY_SETTINGS_DIR=str(tmp_path)))
    monkeypatch.setenv('DECKY_PLUGIN_DIR', str(repo))
    monkeypatch.setattr(audio_runtime, 'setup_audio_environment', lambda *args: None)
    spec = importlib.util.spec_from_file_location('debug_backend_test', repo / 'backend/src/decktation_backend.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'CONFIG_DIR', str(tmp_path))
    module.Plugin.listener_process = MagicMock()
    module.Plugin.listener_process.poll.return_value = None
    return module


@pytest.fixture
def live_backend(backend, tmp_path, monkeypatch):
    import controller_listener
    monkeypatch.setattr(controller_listener, 'CONFIG_DIR', str(tmp_path))
    listener = controller_listener.ControllerDebug(['L2', 'R2', 'X'])
    listener.refresh()
    return backend.Plugin, listener


def assert_snapshot(value):
    assert {'success', 'session', 'revision', 'state', 'remaining_ms', 'event_count',
            'device_count', 'metadata', 'report'} <= value.keys()
    assert type(value['revision']) is int and value['revision'] >= 0
    assert 0 <= value['remaining_ms'] <= 30000
    if value['state'] != 'ready':
        assert value['report'] is None
    return value


def ready_report(plugin, listener):
    start = asyncio.run(plugin.start_controller_debug(None))
    listener.refresh()
    asyncio.run(plugin.get_controller_debug(None, start['session']))
    listener.device('private-path', 'accepted', keys=[0x130])
    listener.key('private-path', 0x130, 1, 'A', listener.clock())
    assert asyncio.run(plugin.stop_controller_debug(None, start['session']))['state'] == 'stopping'
    listener.refresh()
    listener.finish_if_drained(pending=False)
    return assert_snapshot(asyncio.run(plugin.get_controller_debug(None, start['session'])))


def test_start_poll_stop_and_stale_session(live_backend, tmp_path):
    plugin, listener = live_backend
    assert assert_snapshot(asyncio.run(plugin.resume_controller_debug(None)))['state'] == 'idle'
    started = assert_snapshot(asyncio.run(plugin.start_controller_debug(None)))
    assert started['state'] == 'starting'
    session = started['session']
    request = read_json(tmp_path / 'controller_debug_request.json')
    assert request['session'] == session and request['protocol'] == 2
    assert request['metadata']['decktation_version']
    assert request['metadata']['kernel_release']
    assert asyncio.run(plugin.start_controller_debug(None))['session'] == session
    listener.refresh()
    current = assert_snapshot(asyncio.run(plugin.get_controller_debug(None, session)))
    assert current['state'] == 'recording' and current['remaining_ms'] > 29000
    assert not asyncio.run(plugin.get_controller_debug(None, 'other'))['success']
    stopped = assert_snapshot(asyncio.run(plugin.stop_controller_debug(None, session)))
    assert stopped['state'] == 'stopping'
    listener.refresh()
    listener.finish_if_drained(pending=False)
    final = assert_snapshot(asyncio.run(plugin.resume_controller_debug(None)))
    assert final['state'] == 'ready' and final['report']['phase'] == 'stopped'
    assert asyncio.run(plugin.stop_controller_debug(None, session)) == final


def test_resume_returns_actual_frozen_final_report(live_backend):
    plugin, listener = live_backend
    final = ready_report(plugin, listener)
    assert final['state'] == 'ready'
    assert final['event_count'] == final['device_count'] == 1
    assert final == asyncio.run(plugin.resume_controller_debug(None))
    assert 'private-path' not in json.dumps(final)


def test_upload_cancellation_does_not_release_inflight_claim(live_backend, backend, monkeypatch):
    import threading
    plugin, listener = live_backend
    final = ready_report(plugin, listener)
    entered, release = threading.Event(), threading.Event()
    def upload(*args):
        entered.set()
        release.wait(3)
        return 'queued-event'
    sender = MagicMock(side_effect=upload)
    monkeypatch.setattr(backend, 'telemetry_upload_controller_report', sender)
    async def run():
        task = asyncio.create_task(plugin.upload_controller_debug(None, final['session'], True))
        try:
            assert await asyncio.to_thread(entered.wait, 3)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert plugin.controller_debug.uploading
            assert not (await plugin.upload_controller_debug(None, final['session'], True))['success']
            assert (await plugin.start_controller_debug(None))['session'] == final['session']
        finally:
            release.set()
        for _ in range(100):
            if not plugin.controller_debug.uploading:
                break
            await asyncio.sleep(0.001)
        assert plugin.controller_debug.event_id == 'queued-event'
    asyncio.run(run())
    assert sender.call_count == 1


def test_upload_needs_explicit_per_report_consent_and_exact_review(live_backend, backend, monkeypatch, tmp_path):
    plugin, listener = live_backend
    session = asyncio.run(plugin.start_controller_debug(None))['session']
    upload = MagicMock(return_value='event-42')
    monkeypatch.setattr(backend, 'telemetry_upload_controller_report', upload)
    assert not asyncio.run(plugin.upload_controller_debug(None, session, True))['success']
    final = ready_report(plugin, listener)
    assert not asyncio.run(plugin.upload_controller_debug(None, session, False))['success']
    write_json(tmp_path / 'controller_debug_result.json', {'session': session, 'phase': 'complete', 'name': 'private'})
    result = assert_snapshot(asyncio.run(plugin.upload_controller_debug(None, session, True)))
    assert result['state'] == 'ready' and result['session'] == session and result['event_id'] == 'event-42'
    assert upload.call_args.args[0] == final['report']
    assert not asyncio.run(plugin.upload_controller_debug(None, session, True))['success']
    new = asyncio.run(plugin.start_controller_debug(None))
    assert new['session'] != session
    assert not asyncio.run(plugin.upload_controller_debug(None, new['session'], True))['success']


def test_concurrent_upload_and_start_preserve_reviewed_session(live_backend, backend, monkeypatch):
    import threading
    plugin, listener = live_backend
    final = ready_report(plugin, listener)
    entered, release = threading.Event(), threading.Event()
    def upload(*args):
        entered.set()
        assert release.wait(3)
        return 'queued-event'
    sender = MagicMock(side_effect=upload)
    monkeypatch.setattr(backend, 'telemetry_upload_controller_report', sender)
    async def run():
        first = asyncio.create_task(plugin.upload_controller_debug(None, final['session'], True))
        try:
            assert await asyncio.to_thread(entered.wait, 3)
            second = await plugin.upload_controller_debug(None, final['session'], True)
            started = await plugin.start_controller_debug(None)
            assert not second['success']
            assert started['session'] == final['session'] and started['report'] == final['report']
        finally:
            release.set()
        return await first
    assert assert_snapshot(asyncio.run(run()))['event_id'] == 'queued-event'
    assert sender.call_count == 1


def test_dead_listener_returns_failed_snapshot(backend):
    plugin = backend.Plugin
    session = asyncio.run(plugin.start_controller_debug(None))['session']
    plugin.listener_process.poll.return_value = 1
    result = assert_snapshot(asyncio.run(plugin.get_controller_debug(None, session)))
    assert result['state'] == 'failed' and result['error']


def test_backend_ptt_is_suppressed_even_before_listener_ack(backend, tmp_path, monkeypatch):
    plugin = backend.Plugin
    start = asyncio.run(plugin.start_controller_debug(None))
    assert start['state'] == 'starting'
    state = tmp_path / 'ptt_state'
    state.write_text('1')
    monkeypatch.setattr(backend, 'STATE_FILE', str(state))
    plugin.controller_enabled = True
    plugin.poll_running = True
    plugin.voice_service = MagicMock()
    plugin.voice_service.is_recording = False
    plugin.voice_service.pending_snapshot.return_value = None
    def tick(_delay):
        plugin.poll_running = False
    monkeypatch.setattr(backend.time, 'sleep', tick)
    plugin.poll_button_state()
    plugin.voice_service.start_recording.assert_not_called()
    plugin.voice_service.cancel_pending.assert_not_called()


def test_backend_poll_advances_completed_capture_without_frontend_polling(live_backend, backend, tmp_path, monkeypatch):
    plugin, listener = live_backend
    session = asyncio.run(plugin.start_controller_debug(None))['session']
    listener.refresh()
    asyncio.run(plugin.stop_controller_debug(None, session))
    listener.refresh()
    listener.finish_if_drained(pending=False)
    assert plugin.controller_debug.state == 'stopping'
    state = tmp_path / 'ptt_state'
    state.write_text('0')
    monkeypatch.setattr(backend, 'STATE_FILE', str(state))
    plugin.controller_enabled = True
    plugin.poll_running = True
    plugin.voice_service = None
    monkeypatch.setattr(backend.time, 'sleep', lambda _: setattr(plugin, 'poll_running', False))
    plugin.poll_button_state()
    assert plugin.controller_debug.state == 'ready'


def test_metadata_collection_finishes_before_requested_monotonic_timestamp(backend, monkeypatch):
    completed = []
    def metadata(_version):
        completed.append(backend.time.monotonic())
        return {'os_id': 'steamos'}
    monkeypatch.setattr(backend, 'collect_runtime_metadata', metadata)
    start = asyncio.run(backend.Plugin.start_controller_debug(None))
    assert completed
    assert backend.Plugin.controller_debug.requested >= completed[0]
    assert start['metadata'] == {'os_id': 'steamos'}


def configure_ptt_replay(backend, tmp_path, monkeypatch):
    plugin = backend.Plugin
    state = tmp_path / 'ptt_state'
    state.write_text('1')
    monkeypatch.setattr(backend, 'STATE_FILE', str(state))
    plugin.controller_enabled = plugin.poll_running = True
    voice = plugin.voice_service = MagicMock()
    voice.is_recording = voice.is_transcribing = False
    voice.pending_text = None
    voice.pending_snapshot.return_value = None
    voice.start_recording.side_effect = lambda: setattr(voice, 'is_recording', True)
    voice.stop_recording.side_effect = lambda: setattr(voice, 'is_recording', False)
    return plugin, voice, state


def test_binding_capture_cannot_swallow_release_of_existing_recording(backend, tmp_path, monkeypatch):
    plugin, voice, state = configure_ptt_replay(backend, tmp_path, monkeypatch)
    ticks = 0
    def tick(_delay):
        nonlocal ticks
        ticks += 1
        if ticks == 1:
            assert voice.is_recording
            plugin.binding_session = 'interleaved-capture'
            plugin.binding_deadline = backend.time.time() + 10
            state.write_text('0')
        else:
            plugin.poll_running = False
    monkeypatch.setattr(backend.time, 'sleep', tick)
    plugin.poll_button_state()
    voice.stop_recording.assert_called_once_with()
    assert not voice.is_recording


def test_debug_start_rejected_during_ptt_preserves_release(backend, tmp_path, monkeypatch):
    plugin, voice, state = configure_ptt_replay(backend, tmp_path, monkeypatch)
    replies = []
    def tick(_delay):
        if not replies:
            assert voice.is_recording
            replies.append(assert_snapshot(asyncio.run(plugin.start_controller_debug(None))))
            state.write_text('0')
        else:
            plugin.poll_running = False
    monkeypatch.setattr(backend.time, 'sleep', tick)
    plugin.poll_button_state()
    assert replies[0]['success'] is False
    assert replies[0]['session'] is None and replies[0]['state'] == 'idle'
    assert 'Finish' in replies[0]['error']
    assert not (tmp_path / 'controller_debug_request.json').exists()
    voice.stop_recording.assert_called_once_with()
    assert not voice.is_recording


@pytest.mark.parametrize('busy', ['is_transcribing', 'pending_snapshot'])
def test_debug_start_rejects_other_busy_voice_states(backend, tmp_path, monkeypatch, busy):
    plugin, voice, _ = configure_ptt_replay(backend, tmp_path, monkeypatch)
    if busy == 'pending_snapshot':
        voice.pending_snapshot.return_value = {'id': 'draft'}
    else:
        voice.is_transcribing = True
    before = plugin._controller_debug().snapshot()
    result = assert_snapshot(asyncio.run(plugin.start_controller_debug(None)))
    assert result['success'] is False and 'Finish' in result['error']
    assert plugin.controller_debug.snapshot() == before
    voice.start_recording.assert_not_called()
    voice.stop_recording.assert_not_called()
    voice.cancel_pending.assert_not_called()


def test_debug_entry_serializes_with_inflight_ptt_start(backend, tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    plugin, voice, _ = configure_ptt_replay(backend, tmp_path, monkeypatch)
    entered, release, attempted = threading.Event(), threading.Event(), threading.Event()
    capture_thread = []
    dispatch_lock = plugin.controller_lock
    class ObservedLock:
        def __enter__(self):
            if capture_thread and threading.get_ident() == capture_thread[0]:
                attempted.set()
            dispatch_lock.acquire()
        def __exit__(self, *args):
            dispatch_lock.release()
    monkeypatch.setattr(plugin, 'controller_lock', ObservedLock())
    def start_recording():
        entered.set()
        assert release.wait(3)
        voice.is_recording = True
    voice.start_recording.side_effect = start_recording
    monkeypatch.setattr(backend.time, 'sleep', lambda _: setattr(plugin, 'poll_running', False))
    def capture():
        capture_thread.append(threading.get_ident())
        return asyncio.run(plugin.start_controller_debug(None))
    with ThreadPoolExecutor(max_workers=2) as pool:
        poll = pool.submit(plugin.poll_button_state)
        assert entered.wait(3)
        entry = pool.submit(capture)
        try:
            assert attempted.wait(3)
            # The recording transition owns the dispatch lock until it publishes busy.
            assert not entry.done()
        finally:
            release.set()
        poll.result(3)
        result = entry.result(3)
    assert result['success'] is False and result['session'] is None


def test_ptt_rechecks_capture_entered_after_initial_poll_check(backend, tmp_path, monkeypatch):
    plugin, voice, _ = configure_ptt_replay(backend, tmp_path, monkeypatch)
    def pending():
        assert asyncio.run(plugin.start_controller_debug(None))['state'] == 'starting'
        return None
    # Capture enters after poll's initial suppression check, before dispatch lock.
    original_gesture = backend.ReviewGesture
    class Gesture(original_gesture):
        def update(self, *args):
            pending()
            return super().update(*args)
    monkeypatch.setattr(backend, 'ReviewGesture', Gesture)

    monkeypatch.setattr(backend.time, 'sleep', lambda _: setattr(plugin, 'poll_running', False))
    plugin.poll_button_state()
    voice.start_recording.assert_not_called()


def test_live_status_uses_real_ipc_tracks_release_after_event_limit_and_clears(live_backend):
    plugin, listener = live_backend
    empty = {'pressed': [], 'last_event': None}
    start = asyncio.run(plugin.start_controller_debug(None))
    assert start['live_input'] == empty
    listener.refresh()
    listener.device('/dev/private', 'accepted', keys=[0x130])
    for index in range(300):
        listener.key('/dev/private', 0x130, (index + 1) % 2, 'A', listener.clock())
    listener.key('/dev/private', 0x130, 1, 'A', listener.clock())
    listener.refresh()
    current = asyncio.run(plugin.get_controller_debug(None, start['session']))
    assert current['report'] is None and current['event_count'] == 256
    assert current['live_input']['pressed'] == [{'source': 'source_1', 'button': 'A'}]
    assert current['live_input']['last_event']['pressed'] is True
    listener.key('/dev/private', 0x130, 0, 'A', listener.clock())
    listener.refresh()
    released = asyncio.run(plugin.resume_controller_debug(None))
    assert released['live_input']['pressed'] == []
    assert released['live_input']['last_event']['pressed'] is False
    assert released['revision'] > current['revision']
    assert '/dev/' not in json.dumps(released)
    assert asyncio.run(plugin.stop_controller_debug(None, start['session']))['live_input'] == empty
    listener.refresh()
    listener.finish_if_drained(pending=False)
    assert asyncio.run(plugin.resume_controller_debug(None))['live_input'] == empty
    assert asyncio.run(plugin.start_controller_debug(None))['live_input'] == empty
