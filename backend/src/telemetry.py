"""Privacy-safe structured diagnostics for Decktation."""

import json
import re
import socket

import sentry_sdk


SENTRY_DSN = (
    "https://730a8f28c0769d1a03b3be546f6abe4b"
    "@o4511848568193024.ingest.us.sentry.io/4511848572911616"
)
_HOME_PATH = re.compile(r"/(?:home/[^/\s]+|root)(?=/|\s|$)")
_DEVICE_NAME = socket.gethostname()
_enabled = False
_captured_errors = set()
_controller_context = {}
_CONTROLLER_EVENTS = {
    'started', 'connected', 'disconnected', 'active_changed', 'first_input',
    'resynced', 'open_failed', 'waiting',
}
_BUTTONS = {'A', 'B', 'X', 'Y', 'L1', 'R1', 'L2', 'R2', 'L4', 'R4', 'L5', 'R5'}


def _controller_details(data):
    """Allow model IDs and capabilities, never names, serials or addresses."""
    if not isinstance(data, dict):
        return {}
    result = {}
    for key, allowed in {
        'controller_type': {'steam_deck', 'steam_controller_wired', 'steam_controller_wireless',
                            'xbox', 'playstation', 'nintendo', 'valve', 'generic_gamepad'},
        'input_backend': {'evdev', 'hidraw'},
        'connection': {'usb', 'bluetooth', 'virtual', 'other'},
    }.items():
        value = data.get(key)
        if isinstance(value, str) and value in allowed:
            result[key] = value
    for key in ('bus', 'vendor_id', 'product_id', 'hardware_version', 'resync_count'):
        value = data.get(key)
        if type(value) is int and 0 <= value <= 2**31 - 1:
            result[key] = value
    for key in ('combo_supported', 'input_received'):
        if type(data.get(key)) is bool:
            result[key] = data[key]
    buttons = data.get('supported_buttons', [])
    if isinstance(buttons, list):
        result['supported_buttons'] = [b for b in buttons if isinstance(b, str) and b in _BUTTONS][:12]
    return result


def controller_event(message):
    """Consume structured child diagnostics even while sharing is disabled.

    Keeping a local snapshot lets enabling diagnostics include already-connected
    controllers. Only opted-in sessions emit Sentry breadcrumbs or events.
    """
    global _controller_context
    prefix = 'DECKTATION_CONTROLLER '
    if not message.startswith(prefix) or len(message) > 65536:
        return
    try:
        data = json.loads(message[len(prefix):])
    except (ValueError, TypeError):
        return
    if (not isinstance(data, dict) or not isinstance(data.get('event'), str)
            or data['event'] not in _CONTROLLER_EVENTS):
        return
    buttons = data.get('configured_buttons', [])
    sources = data.get('sources', [])
    if not isinstance(buttons, list) or not isinstance(sources, list):
        return
    snapshot = {
        'listener_event': data['event'],
        'configured_buttons': [b for b in buttons if isinstance(b, str) and b in _BUTTONS][:5],
        'source_count': len(sources),
        'sources': [_controller_details(source) for source in sources[:16]],
        'current_controller': _controller_details(data.get('current_controller')),
        'affected_controller': _controller_details(data.get('affected_controller')),
    }
    if type(data.get('errno')) is int:
        snapshot['errno'] = data['errno']
    if data.get('input_backend') in ('evdev', 'hidraw'):
        snapshot['input_backend'] = data['input_backend']
    _controller_context = snapshot
    breadcrumb('controller.' + data['event'], **snapshot)
    if data['event'] == 'open_failed':
        capture_error('controller.open_failed')


def clear_controller_context():
    global _controller_context
    _controller_context = {}


def _attach_controller(target):
    snapshot = _controller_context
    if snapshot:
        target.set_context('controller', snapshot)
        for key in ('controller_type', 'input_backend', 'connection', 'vendor_id', 'product_id'):
            value = snapshot.get('current_controller', {}).get(key)
            if value is not None:
                target.set_tag(key, value)


def _scrub(value):
    if isinstance(value, dict):
        return {
            key: _scrub(item)
            for key, item in value.items()
            if key.lower() not in {
                "audio",
                "authorization",
                "context",
                "cookie",
                "device",
                "email",
                "hostname",
                "ip",
                "ip_address",
                "machine",
                "password",
                "serial",
                "server_name",
                "text",
                "transcription",
                "user",
                "username",
            }
        }
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    if isinstance(value, str):
        value = value.replace(_DEVICE_NAME, "<device>")
        return _HOME_PATH.sub("<home>", value)[:1000]
    return value


def _before_send(event, hint):
    for field in (
        "debug_meta",
        "modules",
        "request",
        "server_name",
        "user",
    ):
        event.pop(field, None)

    # Runtime, OS, device and arbitrary integration contexts are unnecessary
    # for Decktation diagnostics. Keep only our allowlisted structured data and
    # Sentry's non-personal trace identifiers.
    contexts = event.get("contexts", {})
    event["contexts"] = {
        name: value
        for name, value in contexts.items()
        if name in {"decktation", "failure", "trace", "controller"}
    }
    return _scrub(event)


def initialize(version):
    """Initialize Sentry without automatic PII or raw-log collection."""
    global _enabled
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        release=f"decktation@{version}",
        environment="production",
        server_name="decktation-client",
        send_default_pii=False,
        enable_logs=False,
        traces_sample_rate=0.1,
        default_integrations=False,
        before_send=_before_send,
        before_send_transaction=_before_send,
        include_local_variables=False,
        attach_stacktrace=False,
        auto_session_tracking=False,
        send_client_reports=False,
    )
    sentry_sdk.set_tag("component", "decky-backend")
    _enabled = True


def set_enabled(enabled, version):
    """Apply the user's diagnostics preference immediately."""
    global _enabled
    if enabled and not _enabled:
        initialize(version)
        breadcrumb("diagnostics.enabled")
    elif not enabled and _enabled:
        flush()
        _enabled = False
        sentry_sdk.get_client().close(timeout=2)


def is_enabled():
    return _enabled


def breadcrumb(name, **data):
    """Record a successful lifecycle step without consuming an error event."""
    if not _enabled:
        return
    sentry_sdk.add_breadcrumb(
        category="decktation",
        message=name,
        level="info",
        data=_scrub(data),
    )


def capture_error(name, error=None, **data):
    """Submit one searchable failure event with recent breadcrumbs."""
    if not _enabled or name in _captured_errors:
        return None
    _captured_errors.add(name)
    with sentry_sdk.new_scope() as scope:
        _attach_controller(scope)
        scope.set_tag("diagnostic_event", name)
        scope.set_context("decktation", _scrub(data))
        if error is not None:
            scope.set_context(
                "failure",
                {
                    "type": type(error).__name__,
                },
            )
        return sentry_sdk.capture_message(name, level="error")


def start_dictation_trace(preset, controller_type):
    if not _enabled:
        return None
    transaction = sentry_sdk.start_transaction(
        name="dictation",
        op="decktation.dictation",
    )
    controller_type = _controller_context.get('current_controller', {}).get('controller_type', controller_type)
    transaction.set_tag("preset", preset)
    transaction.set_tag("controller_type", controller_type)
    transaction.set_data("preset", preset)
    transaction.set_data("controller_type", controller_type)
    _attach_controller(transaction)
    return transaction


def finish_dictation_trace(transaction, success):
    if transaction is None:
        return
    transaction.set_tag("success", success)
    transaction.set_data("success", success)
    transaction.set_status("ok" if success else "internal_error")
    transaction.finish()


def flush(timeout=2):
    if _enabled:
        sentry_sdk.flush(timeout=timeout)
