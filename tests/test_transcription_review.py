import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import decktation_backend as backend
from wow_voice_chat import WoWVoiceChat
from review_gesture import ReviewGesture
from recording_overlay_manager import RecordingOverlay


def service(**kwargs):
    return WoWVoiceChat(lazy_load=True, review_mode=True, preset={
        'default_channel': 'say', 'channels': {'say': '/s ', 'party': '/p ', 'type': ''},
    }, **kwargs)


def test_review_freezes_message_without_timer_and_sends_only_once():
    voice = service()
    voice.send_to_wow_chat = MagicMock(return_value=True)
    voice.queue_transcription('party hello everyone')
    draft = voice.pending_snapshot()
    assert draft['text'] == 'hello everyone'
    assert draft['channel'] == 'party'
    assert draft['deadline'] is None
    assert voice._pending_timer is None
    voice.send_to_wow_chat.assert_not_called()
    assert voice.confirm_pending(draft['id'])
    assert not voice.confirm_pending(draft['id'])
    voice.send_to_wow_chat.assert_called_once_with('hello everyone', channel='party')
    assert voice.pending_snapshot() is None


def test_cancelled_and_stale_drafts_cannot_send_new_text():
    voice = service()
    voice.send_to_wow_chat = MagicMock(return_value=True)
    voice.queue_transcription('first')
    old = voice.pending_snapshot()['id']
    assert voice.cancel_pending(old)
    voice.queue_transcription('second')
    assert not voice.cancel_pending(old)
    assert not voice.confirm_pending(old)
    voice._send_pending(old)
    voice.send_to_wow_chat.assert_not_called()
    assert voice.pending_snapshot()['text'] == 'second'


def test_failed_injection_retains_text_but_invalidates_old_confirmation():
    voice = service()
    voice.send_to_wow_chat = MagicMock(return_value=False)
    voice.queue_transcription('hello')
    old = voice.pending_snapshot()['id']
    assert not voice.confirm_pending(old)
    draft = voice.pending_snapshot()
    assert draft['text'] == 'hello' and draft['error']
    assert draft['id'] != old and draft['deadline'] is None
    assert not voice.confirm_pending(old)
    voice.send_to_wow_chat.assert_called_once()


def test_concurrent_confirmations_inject_once():
    voice = service()
    entered, release = threading.Event(), threading.Event()

    def inject(*args, **kwargs):
        entered.set()
        assert release.wait(2)
        return True

    voice.send_to_wow_chat = MagicMock(side_effect=inject)
    voice.queue_transcription('hello')
    draft_id = voice.pending_snapshot()['id']
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(voice.confirm_pending, draft_id)
        assert entered.wait(2)
        second = pool.submit(voice.confirm_pending, draft_id)
        release.set()
        assert first.result() is True
        assert second.result() is False
    voice.send_to_wow_chat.assert_called_once()


def test_cancel_invalidates_transcription_in_flight():
    voice = service()
    generation = voice._draft_generation
    voice.cancel_pending()
    voice.queue_transcription('too late', generation)
    assert voice.pending_snapshot() is None


def test_countdown_uses_fixed_deadline_and_id_checked_timer(monkeypatch):
    timer = MagicMock()
    monkeypatch.setattr('wow_voice_chat.threading.Timer', timer)
    voice = service()
    voice.review_mode = False
    voice.confirm_delay = 2
    voice.queue_transcription('hello')
    draft = voice.pending_snapshot()
    assert draft['mode'] == 'countdown'
    assert 0 < draft['deadline'] - time.time() <= 6
    assert timer.call_args.kwargs['args'] == (draft['id'],)
    voice.cancel_pending(draft['id'])
    timer.return_value.cancel.assert_called_once()


def test_manual_draft_uses_type_action_and_cancel_does_not_remember_channel():
    voice = service(manual_send=True, remember_last_channel=True)
    voice.queue_transcription('party hello')
    draft = voice.pending_snapshot()
    assert draft['action'] == 'Type into chat'
    voice.cancel_pending(draft['id'])
    assert voice.last_channel is None


@pytest.mark.parametrize('ready', [True, False])
def test_tap_sends_only_when_preview_is_readable(ready):
    gesture = ReviewGesture()
    draft = {'id': 'draft', 'mode': 'review'}
    assert gesture.update(True, draft, ready, 1)[1] is None
    handled, action, _ = gesture.update(False, draft, ready, 1.2)
    assert handled
    assert action == ('send' if ready else None)


def test_preview_becoming_ready_during_press_does_not_confirm():
    gesture = ReviewGesture()
    draft = {'id': 'draft', 'mode': 'review'}
    gesture.update(True, draft, False, 1)
    assert gesture.update(False, draft, True, 1.2)[1] is None


def test_hold_cancels_even_without_overlay_and_consumes_release():
    gesture = ReviewGesture()
    draft = {'id': 'draft', 'mode': 'review'}
    gesture.update(True, draft, False, 1)
    assert gesture.update(True, draft, False, 1.7)[1] == 'cancel'
    assert gesture.update(False, None, False, 1.8)[:2] == (True, None)
    assert gesture.update(True, None, False, 2)[:2] == (False, None)


def test_release_past_threshold_is_cancel_not_send():
    gesture = ReviewGesture()
    draft = {'id': 'draft', 'mode': 'review'}
    gesture.update(True, draft, True, 1)
    assert gesture.update(False, draft, True, 1.7)[1] == 'cancel'


def test_binding_held_during_transcription_cannot_approve_new_draft():
    gesture = ReviewGesture()
    gesture.suppress_until_release(True)
    draft = {'id': 'new', 'mode': 'review'}
    assert gesture.update(False, draft, True, 1)[1] is None
    gesture.update(True, draft, True, 2)
    assert gesture.update(False, draft, True, 2.2)[1] == 'send'


def test_old_gesture_cannot_send_replacement_draft():
    gesture = ReviewGesture()
    gesture.update(True, {'id': 'old', 'mode': 'review'}, True, 1)
    assert gesture.update(False, {'id': 'new', 'mode': 'review'}, True, 1.2)[1] is None


def test_legacy_countdown_press_still_cancels_immediately():
    gesture = ReviewGesture()
    assert gesture.update(True, {'id': 'old', 'mode': 'countdown'}, True, 1)[1] == 'cancel'


def test_legacy_confirm_config_migrates_without_changing_gestures(tmp_path, monkeypatch):
    config = tmp_path / 'config.json'
    config.write_text('{"confirmMode": true}')
    monkeypatch.setattr(backend, 'BUTTON_CONFIG_FILE', str(config))
    assert backend._read_button_config()['sendingMode'] == 'countdown'


def test_panel_confirmation_requires_approval_and_observed_qam_close(monkeypatch):
    async def run_inline(function, *args):
        return function(*args)

    monkeypatch.setattr(backend.asyncio, "to_thread", run_inline)
    voice = service()
    voice.send_to_wow_chat = MagicMock(return_value=True)
    monkeypatch.setattr(backend.Plugin, 'voice_service', voice)
    monkeypatch.setattr(backend.Plugin, 'review_qam_visible', True)
    monkeypatch.setattr(backend.Plugin, 'review_context_time', time.monotonic())
    monkeypatch.setattr(backend.Plugin, 'review_armed_id', None)
    voice.queue_transcription('hello')
    draft_id = voice.pending_snapshot()['id']
    plugin = backend.Plugin()
    assert asyncio.run(plugin.arm_draft(draft_id))['success']
    assert not asyncio.run(plugin.send_armed_draft(draft_id))['success']
    voice.send_to_wow_chat.assert_not_called()
    asyncio.run(plugin.set_review_context(False))
    assert not asyncio.run(plugin.send_armed_draft(draft_id))['success']
    monkeypatch.setattr(backend.Plugin, 'review_closed_at', time.monotonic() - 1)
    assert asyncio.run(plugin.send_armed_draft(draft_id))['success']
    assert not asyncio.run(plugin.send_armed_draft(draft_id))['success']
    voice.send_to_wow_chat.assert_called_once()


def test_overlay_health_rejects_stale_or_other_draft_ack(tmp_path):
    import json
    overlay = RecordingOverlay('/plugin', MagicMock(), enabled=False)
    overlay.directory = tmp_path
    overlay.process = SimpleNamespace(poll=lambda: None)
    ack = tmp_path / 'status'
    ack.write_text(json.dumps({'id': 'draft', 'time': time.time(), 'ready': True}))
    assert overlay.preview_ready('draft')
    assert not overlay.preview_ready('other')
    ack.write_text(json.dumps({'id': 'draft', 'time': time.time() - 5, 'ready': True}))
    assert not overlay.preview_ready('draft')
    ack.write_text('partially-written')
    assert not overlay.preview_ready('draft')


def test_paused_countdown_cannot_send_from_late_timer_callback(monkeypatch):
    monkeypatch.setattr('wow_voice_chat.threading.Timer', MagicMock())
    voice = service()
    voice.review_mode = False
    voice.confirm_delay = 2
    voice.send_to_wow_chat = MagicMock(return_value=True)
    voice.queue_transcription('hello')
    draft_id = voice.pending_snapshot()['id']
    voice.pause_countdown()
    voice._send_pending(draft_id)
    assert not voice.confirm_pending(draft_id, countdown=True)
    voice.send_to_wow_chat.assert_not_called()
    assert voice.pending_snapshot()['mode'] == 'review'
    assert voice.confirm_pending(draft_id)


def test_unexpected_injection_exception_still_allows_retry():
    voice = service()
    voice.send_to_wow_chat = MagicMock(side_effect=RuntimeError('keyboard unavailable'))
    voice.queue_transcription('hello')
    assert not voice.confirm_pending(voice.pending_snapshot()['id'])
    assert not voice.pending_snapshot()['sending']
    assert voice.pending_snapshot()['error']


def test_channel_persistence_failure_does_not_retry_a_successful_send():
    voice = service(remember_last_channel=True, channel_rememberer=MagicMock(side_effect=OSError('disk full')))
    voice.send_to_wow_chat = MagicMock(return_value=True)
    voice.queue_transcription('party hello')
    draft_id = voice.pending_snapshot()['id']
    assert voice.confirm_pending(draft_id)
    assert voice.pending_snapshot() is None
    assert not voice.confirm_pending(draft_id)
    voice.send_to_wow_chat.assert_called_once()


def test_shutdown_discards_review_and_rejects_late_transcription():
    voice = service()
    voice.send_to_wow_chat = MagicMock(return_value=True)
    voice.queue_transcription('pending')
    draft_id = voice.pending_snapshot()['id']
    voice.begin_shutdown()
    voice.queue_transcription('late result')
    assert voice.pending_snapshot() is None
    assert not voice.confirm_pending(draft_id)
    voice.send_to_wow_chat.assert_not_called()
