"""Backend-owned controller capture lifecycle; IPC is evidence, not UI state."""
import copy
from functools import wraps
import threading
import math
import os
import time
import uuid

from binding_capture import read_json, write_json
from controller_debug_report import DURATION, _safe_metadata, sanitize_report, sanitize_live_input

PROTOCOL = 2
START_TIMEOUT = 5.0
FINISH_TIMEOUT = 2.0
HEARTBEAT_TIMEOUT = 2.0
ACTIVE = frozenset(('starting', 'recording', 'stopping'))
TERMINAL = frozenset(('ready', 'failed'))


def finite_number(value):
    try:
        return type(value) in (int, float) and value >= 0 and math.isfinite(value)
    except OverflowError:
        return False


def read_bounded(path):
    try:
        if os.path.getsize(path) > 65536:
            return {}
        result = read_json(path)
        return result if isinstance(result, dict) else {}
    except OSError:
        return {}


def synchronized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)
    return call


class ControllerDebugSession:
    """Serialized transitions shared by Decky RPCs and the background input poller.

    A request is bound to a live listener incarnation. An old request therefore
    cannot replay on listener restart, even within the request's five-second TTL.
    All times are in the shared host's monotonic clock domain.
    """
    def __init__(self, directory, clock=None, listener_alive=None):
        self.lock = threading.RLock()
        self.upload_task = None
        self.directory = directory
        self.clock = clock or time.monotonic
        self.listener_alive = listener_alive or (lambda: True)
        self.session = None
        self.state = 'idle'
        self.revision = 0
        self.metadata = {}
        self.started = None
        self.requested = None
        self.stopping_at = None
        self.sequence = 0
        self.observed = None
        self.listener_id = None
        self.current = None
        self.live_input = {'pressed': [], 'last_event': None}
        self.final = None
        self.error = None
        self.uploading = False
        self.uploaded = False
        self.event_id = None

    def path(self, name):
        return os.path.join(self.directory, 'controller_debug_' + name + '.json')

    def _change(self, state):
        if self.state != state:
            self.state = state
            self.revision += 1

    def _fail(self, error):
        self.error = error
        self._change('failed')

    def _heartbeat(self):
        heartbeat = read_bounded(self.path('heartbeat'))
        # Producers can publish while IPC is read; validate against a clock
        # sampled after the evidence, never a pre-read consumer timestamp.
        now = self.clock()
        if (type(heartbeat.get('protocol')) is int and heartbeat['protocol'] == PROTOCOL and
                isinstance(heartbeat.get('listener_id'), str) and heartbeat['listener_id'] and
                finite_number(heartbeat.get('observed_mono')) and
                0 <= now - heartbeat['observed_mono'] <= HEARTBEAT_TIMEOUT):
            return heartbeat
        return None

    def _write_request(self):
        write_json(self.path('request'), {
            'protocol': PROTOCOL, 'session': self.session,
            'listener_id': self.listener_id, 'requested_mono': self.requested,
            'expires_mono': self.requested + START_TIMEOUT,
            'stopped': self.stopping_at is not None, 'metadata': self.metadata})

    @synchronized
    def start(self, metadata):
        if self.state in ACTIVE or self.uploading:
            return self.resume()
        self.session = uuid.uuid4().hex
        self.state, self.revision = 'starting', 1
        self.metadata = _safe_metadata(metadata)
        self.requested = self.clock()  # metadata collection must finish first
        self.started = self.stopping_at = self.observed = self.listener_id = None
        self.sequence = 0
        self.current = self.final = self.error = self.event_id = None
        self.live_input = {'pressed': [], 'last_event': None}
        self.uploading = self.uploaded = False
        return self.resume()

    def _consume(self):
        result = read_bounded(self.path('result'))
        now = self.clock()
        report = result.get('report')
        state = result.get('state')
        phase = report.get('phase') if isinstance(report, dict) else None
        valid_phase = {'recording': ('capturing',), 'stopping': ('capturing',),
                       'ready': ('complete', 'stopped')}
        started, observed, sequence = (result.get('started_mono'),
                                       result.get('observed_mono'), result.get('sequence'))
        if not (type(result.get('protocol')) is int and result['protocol'] == PROTOCOL and
                result.get('session') == self.session and self.listener_id is not None and
                result.get('listener_id') == self.listener_id and
                type(sequence) is int and sequence > self.sequence and
                isinstance(state, str) and state in valid_phase and phase in valid_phase[state] and
                finite_number(started) and self.requested <= started < self.requested + START_TIMEOUT and
                finite_number(observed) and started <= observed <= now and
                (self.started is None or started == self.started) and
                (self.observed is None or observed >= self.observed) and
                isinstance(report.get('devices'), list) and isinstance(report.get('events'), list)):
            return
        if state == 'stopping' and self.stopping_at is None and observed < started + DURATION:
            return
        if state == 'ready':
            finish_by = started + DURATION + FINISH_TIMEOUT
            if self.stopping_at is not None:
                finish_by = min(finish_by, self.stopping_at + FINISH_TIMEOUT)
            if observed >= finish_by:
                return
            if phase == 'stopped' and (self.stopping_at is None or observed < self.stopping_at):
                return
            if phase == 'complete' and observed < started + DURATION:
                return
        self.sequence, self.started, self.observed = sequence, started, observed
        self.current = sanitize_report({**report, 'metadata': self.metadata})
        self.live_input = sanitize_live_input(result.get('live_input'),
            {device['source'] for device in self.current['devices'] if 'source' in device})
        self.revision += 1
        if state == 'ready':
            self.final = copy.deepcopy(self.current)
            self._change('ready')
        elif self.state != 'stopping':
            self._change('recording')

    def _advance(self):
        if self.state not in ACTIVE:
            return
        heartbeat = self._heartbeat()
        if self.listener_id is None and heartbeat:
            self.listener_id = heartbeat['listener_id']
            self._write_request()
        self._consume()
        now = self.clock()
        if self.state in TERMINAL:
            return
        if not self.listener_alive():
            self._fail('Controller listener stopped. Restart the controller listener and try again.')
        elif self.stopping_at is not None and now >= self.stopping_at + FINISH_TIMEOUT:
            self._fail('Controller listener did not finish the report. Restart the listener and try again.')
        elif self.started is None and now >= self.requested + START_TIMEOUT:
            self._fail('Controller listener did not acknowledge capture. Restart the listener and try again.')
        elif self.started is not None:
            if not heartbeat or heartbeat['listener_id'] != self.listener_id:
                self._fail('Controller listener heartbeat lost or restarted. Restart capture and try again.')
            elif now >= self.started + DURATION + FINISH_TIMEOUT:
                self._fail('Controller listener did not finish the report. Restart the listener and try again.')
            elif now >= self.started + DURATION:
                self._change('stopping')

    @synchronized
    def snapshot(self, success=True, error=None):
        remaining = DURATION * 1000 if self.state == 'starting' else 0
        if self.state == 'recording':
            remaining = max(0, min(30000, int((self.started + DURATION - self.clock()) * 1000)))
        result = {'success': success, 'session': self.session, 'revision': self.revision,
                  'state': self.state, 'remaining_ms': remaining,
                  'event_count': len((self.current or {}).get('events', [])),
                  'device_count': len((self.current or {}).get('devices', [])),
                  'live_input': copy.deepcopy(self.live_input) if self.state == 'recording'
                                else {'pressed': [], 'last_event': None},
                  'metadata': copy.deepcopy(self.metadata),
                  'report': copy.deepcopy(self.final) if self.state == 'ready' else None,
                  'event_id': self.event_id}
        if error or self.error:
            result['error'] = error or self.error
        return result

    @synchronized
    def resume(self):
        try:
            self._advance()
        except OSError:
            self._fail('Controller debug IPC unavailable. Restart the listener and try again.')
        return self.snapshot()

    @synchronized
    def get(self, session):
        result = self.resume()
        if not session or session != self.session:
            return self.snapshot(False, 'Controller debug session ended.')
        return result

    @synchronized
    def stop(self, session):
        result = self.get(session)
        if not result['success'] or self.state in TERMINAL:
            return result
        if self.stopping_at is None:
            self.stopping_at = self.clock()
            self._change('stopping')
            try:
                if self.listener_id:
                    self._write_request()
            except OSError:
                self._fail('Controller debug IPC unavailable. Restart the listener and try again.')
        return self.snapshot()

    @synchronized
    def begin_upload(self, session, consent):
        if (consent is not True or session != self.session or self.state != 'ready' or
                self.uploading or self.uploaded):
            return None
        self.uploading = True
        return copy.deepcopy(self.final)

    @synchronized
    def finish_upload(self, event_id=None, error=None):
        self.uploading = False
        if error:
            return self.snapshot(False, error)
        self.uploaded, self.event_id = True, event_id
        self.revision += 1
        return self.snapshot()
