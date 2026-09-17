from unittest.mock import MagicMock
import json

import pytest

import telemetry


@pytest.fixture(autouse=True)
def clean_controller_context(monkeypatch):
    monkeypatch.setattr(telemetry, '_controller_context', {})


def controller_message(event='active_changed', **changes):
    controller = {
        'controller_type': 'xbox', 'input_backend': 'evdev', 'connection': 'bluetooth',
        'vendor_id': 0x045e, 'product_id': 0x0b13, 'hardware_version': 1, 'bus': 5,
        'supported_buttons': ['A', 'L1', 'R1'], 'combo_supported': True,
        'input_received': True, 'resync_count': 0,
        'name': 'Private controller name', 'serial': 'secret-serial',
        'address': '01:02:03:04:05:06',
    }
    return 'DECKTATION_CONTROLLER ' + json.dumps({
        'event': event, 'current_controller': controller, 'sources': [controller],
        'configured_buttons': ['L1', 'R1'], **changes,
    })


def test_controller_snapshot_is_allowlisted_even_with_sharing_disabled(monkeypatch):
    monkeypatch.setattr(telemetry, '_enabled', False)
    add = MagicMock()
    capture = MagicMock()
    monkeypatch.setattr(telemetry.sentry_sdk, 'add_breadcrumb', add)
    monkeypatch.setattr(telemetry.sentry_sdk, 'capture_message', capture)
    telemetry.controller_event(controller_message('open_failed', errno=13))
    assert telemetry._controller_context['current_controller']['product_id'] == 0x0b13
    assert telemetry._controller_context['errno'] == 13
    serialized = json.dumps(telemetry._controller_context)
    assert 'Private' not in serialized
    assert 'secret-serial' not in serialized
    assert '01:02' not in serialized
    add.assert_not_called()
    capture.assert_not_called()


@pytest.mark.parametrize('message', [
    'ordinary child output', 'DECKTATION_CONTROLLER invalid',
    'DECKTATION_CONTROLLER []', 'DECKTATION_CONTROLLER {"event": []}',
    'DECKTATION_CONTROLLER {"event": "connected", "sources": null}',
])
def test_malformed_controller_messages_are_ignored(message):
    telemetry.controller_event(message)
    assert telemetry._controller_context == {}


def test_controller_disconnect_clears_current_controller(monkeypatch):
    monkeypatch.setattr(telemetry, '_enabled', False)
    telemetry.controller_event(controller_message())
    telemetry.controller_event(controller_message('disconnected', current_controller={}, sources=[]))
    assert 'controller_type' not in telemetry._controller_context['current_controller']
    assert telemetry._controller_context['source_count'] == 0
    telemetry.clear_controller_context()
    assert telemetry._controller_context == {}


def test_real_sdk_captures_controller_errors_traces_and_consent(monkeypatch):
    """Exercise the pinned SDK and scrub hooks with an in-memory transport."""
    from sentry_sdk.transport import Transport

    envelopes = []
    class MemoryTransport(Transport):
        def capture_envelope(self, envelope):
            envelopes.append(envelope)

    sdk = telemetry.sentry_sdk
    original_init = sdk.init
    previous_client = sdk.get_client()
    options = {}
    def initialize(**kwargs):
        options.update(kwargs)
        kwargs.update(transport=MemoryTransport(), traces_sample_rate=1.0)
        return original_init(**kwargs)
    monkeypatch.setattr(sdk, 'init', initialize)
    monkeypatch.setattr(telemetry, '_enabled', False)
    monkeypatch.setattr(telemetry, '_captured_errors', set())
    try:
        with sdk.isolation_scope():
            telemetry.set_enabled(True, 'test-version')
            telemetry.controller_event(controller_message())
            telemetry.controller_event(controller_message('open_failed', errno=13, input_backend='evdev'))
            telemetry.capture_error('recording.start_failed', RuntimeError('private speech'),
                                    transcription='private speech')
            transaction = telemetry.start_dictation_trace('wow', 'unknown')
            # A subsequent disconnect must not rewrite the trace's starting controller.
            telemetry.controller_event(controller_message('disconnected', current_controller={}, sources=[]))
            telemetry.finish_dictation_trace(transaction, True)
            telemetry.set_enabled(False, 'test-version')
            count = len(envelopes)
            telemetry.controller_event(controller_message('open_failed', errno=13))
            telemetry.capture_error('after.optout')
            assert telemetry.start_dictation_trace('wow', 'xbox') is None
            assert len(envelopes) == count

        events = [item.payload.json for envelope in envelopes for item in envelope.items
                  if item.headers.get('type') in ('event', 'transaction')]
        assert len(events) == 3
        errors = [event for event in events if event.get('type') != 'transaction']
        for event in errors:
            assert event['tags']['controller_type'] == 'xbox'
            assert event['tags']['input_backend'] == 'evdev'
            assert event['contexts']['controller']['configured_buttons'] == ['L1', 'R1']
        assert errors[0]['contexts']['controller']['errno'] == 13
        trace = next(event for event in events if event.get('type') == 'transaction')
        assert trace['tags']['controller_type'] == 'xbox'
        assert trace['contexts']['controller']['current_controller']['product_id'] == 0x0b13
        assert trace['tags']['success'] is True
        assert trace['release'] == 'decktation@test-version'
        assert options['default_integrations'] is False
        assert options['send_default_pii'] is False
        serialized = json.dumps(events)
        for private in ('private speech', 'Private controller name', 'secret-serial', '01:02:03:04:05:06'):
            assert private not in serialized
    finally:
        sdk.get_client().close(timeout=0)
        sdk.get_global_scope().set_client(previous_client)


def test_dictation_trace_contains_only_requested_diagnostics(monkeypatch):
    monkeypatch.setattr(telemetry, "_enabled", True)
    transaction = MagicMock()
    monkeypatch.setattr(
        telemetry.sentry_sdk,
        "start_transaction",
        MagicMock(return_value=transaction),
    )

    result = telemetry.start_dictation_trace("guild_wars_2", "steam_deck")
    telemetry.finish_dictation_trace(result, True)

    transaction.set_tag.assert_any_call("preset", "guild_wars_2")
    transaction.set_tag.assert_any_call("controller_type", "steam_deck")
    transaction.set_tag.assert_any_call("success", True)
    transaction.set_status.assert_called_once_with("ok")
    transaction.finish.assert_called_once_with()


def test_scrubber_removes_user_content_and_home_path():
    scrubbed = telemetry._scrub(
        {
            "transcription": "private speech",
            "username": "deck",
            "path": "/home/deck/plugin/file",
        }
    )

    assert scrubbed == {"path": "<home>/plugin/file"}


def test_event_scrubber_removes_automatic_device_metadata():
    event = {
        "server_name": "personal-device",
        "user": {"ip_address": "192.0.2.1"},
        "request": {"headers": {"authorization": "secret"}},
        "modules": {"private-package": "1.0"},
        "contexts": {
            "device": {"name": "Personal Deck"},
            "os": {"name": "Linux"},
            "runtime": {"name": "CPython"},
            "trace": {"trace_id": "abc", "span_id": "def"},
            "decktation": {"preset": "wow"},
        },
    }

    assert telemetry._before_send(event, {}) == {
        "contexts": {
            "trace": {"trace_id": "abc", "span_id": "def"},
            "decktation": {"preset": "wow"},
        }
    }


def test_disabled_diagnostics_do_not_create_events_or_traces(monkeypatch):
    monkeypatch.setattr(telemetry, "_enabled", False)
    capture_message = MagicMock()
    start_transaction = MagicMock()
    monkeypatch.setattr(telemetry.sentry_sdk, "capture_message", capture_message)
    monkeypatch.setattr(
        telemetry.sentry_sdk, "start_transaction", start_transaction
    )

    assert telemetry.capture_error("test.failure") is None
    assert telemetry.start_dictation_trace("wow", "steam_deck") is None
    capture_message.assert_not_called()
    start_transaction.assert_not_called()


def test_each_failure_category_is_sent_once_per_session(monkeypatch):
    monkeypatch.setattr(telemetry, "_enabled", True)
    monkeypatch.setattr(telemetry, "_captured_errors", set())
    capture_message = MagicMock(return_value="event-id")
    monkeypatch.setattr(telemetry.sentry_sdk, "capture_message", capture_message)

    telemetry.capture_error("controller.device_not_found")
    telemetry.capture_error("controller.device_not_found")
    telemetry.capture_error("controller.hid_disconnected")

    assert capture_message.call_count == 2
