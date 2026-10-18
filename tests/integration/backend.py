"""Loopback-only test adapter: real Plugin RPCs + ControllerDebug file IPC.

Hardware enumeration, microphone, text injection, Decky and telemetry are fixture
boundaries. This is NOT a native listener/Steam test. Never import from production.
"""
import asyncio
import importlib.util
import json
import logging
import os
from pathlib import Path
import secrets
import signal
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend/src'))
TOKEN = os.environ['DECKTATION_TEST_TOKEN']
ORIGIN = 'http://127.0.0.1:5179'
MAX_BODY = 8192
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('integration-backend')


class VoiceFixture:
    """Fail closed at every irreversible voice boundary; count attempted calls."""
    def __init__(self, counts):
        self.counts = counts
        self.is_recording = self.is_transcribing = self.model_loading = False
        self.manual_send = False
        self.type_as_keys = False
        self.inference_device = 'fixture'
        self.pending_text = ''
        self.confirm_delay = 0

    def pending_snapshot(self):
        return None

    def cancel_pending(self):
        pass

    def is_model_ready(self):
        return False

    def start_recording(self, *args, **kwargs):
        self.counts['microphone'] += 1
        raise RuntimeError('Microphone prohibited in browser fixture')

    def type_text(self, *args, **kwargs):
        self.counts['typing'] += 1
        raise RuntimeError('Text injection prohibited in browser fixture')


class Runtime:
    RPC = {
        'start_controller_debug': 0, 'resume_controller_debug': 0,
        'get_controller_debug': 1, 'stop_controller_debug': 1,
        'upload_controller_debug': 2, 'get_status': 0,
        'get_button_config': 0, 'get_presets': 0,
        'set_review_context': 2,
    }
    # UI-only unrelated native/network services; never masquerade as capture RPCs.
    UI_RPC = {'get_plugin_update': 1, 'set_overlay_transcribing_label': 1,
              'set_type_as_keys': 1}

    def __init__(self):
        self.lock = threading.RLock()
        self.closed = threading.Event()
        self.temp = None
        self.reset()
        self.worker = threading.Thread(target=self.run, name='replay-producer', daemon=True)
        self.worker.start()

    def reset(self):
        with self.lock:
            if self.temp:
                self.temp.cleanup()
            self.temp = tempfile.TemporaryDirectory(prefix='decktation-browser-')
            self.directory = Path(self.temp.name)
            self.counts = {'microphone': 0, 'typing': 0, 'upload': 0}
            self.uploads, self.history = [], []
            self.offset = 0.0
            self.alive = True
            self.paused = False
            self.ack_delay = 0.7
            self.ack_after = 0.0
            self.finish_after = None
            self.rpc_delay = self.start_response_delay = 0.0
            self.injected_session = None
            self.actor_error = None
            self.generation = secrets.token_hex(8)
            decky = ModuleType('decky')
            decky.logger = log
            decky.DECKY_USER_HOME = decky.DECKY_SETTINGS_DIR = str(self.directory)
            sys.modules['decky'] = decky
            # Native and network imports are replaced BEFORE loading the real backend.
            telemetry = ModuleType('telemetry')
            for name in ('breadcrumb', 'capture_error', 'controller_event',
                         'clear_controller_context', 'count_metric', 'distribution_metric',
                         'flush', 'finish_dictation_trace', 'set_enabled', 'start_dictation_trace'):
                setattr(telemetry, name, lambda *a, **kw: None)
            telemetry.is_enabled = lambda: False
            telemetry.upload_controller_report = self.upload
            sys.modules['telemetry'] = telemetry
            voice = ModuleType('wow_voice_chat')
            voice.__file__ = __file__ + ':VoiceFixture'
            voice.WoWVoiceChat = VoiceFixture
            sys.modules['wow_voice_chat'] = voice
            import audio_runtime
            audio_runtime.setup_audio_environment = lambda *a: None
            os.environ['DECKY_PLUGIN_DIR'] = str(ROOT)
            spec = importlib.util.spec_from_file_location('browser_backend_' + self.generation,
                                                        ROOT / 'backend/src/decktation_backend.py')
            self.backend = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.backend)
            self.plugin = self.backend.Plugin
            self.plugin.voice_service = VoiceFixture(self.counts)
            self.plugin.listener_process = SimpleNamespace(poll=lambda: None if self.alive else 1)
            # No real listener startup is allowed, even when a fault declares it dead.
            self.plugin.start_controller_listener = lambda: None
            for name in ('STATE_FILE', 'PREVIEW_FILE', 'PID_FILE', 'CONTROLLER_TYPE_FILE',
                         'HAPTIC_SOURCE_FILE', 'RECENT_SOURCE_FILE', 'CONTROLLER_STATUS_FILE'):
                setattr(self.backend, name, str(self.directory / name))
            import controller_listener
            controller_listener.CONFIG_DIR = str(self.directory)
            self.listener = controller_listener.ControllerDebug(['L1', 'R1'], clock=self.clock)
            self.listener.refresh()
            # Instantiate through the real factory; change only the monotonic source.
            self.plugin._controller_debug().clock = self.clock
            log.info('RESET generation=%s tempdir=%s', self.generation, self.directory)

    def clock(self):
        return time.monotonic() + self.offset

    def upload(self, report, version):
        self.counts['upload'] += 1
        self.uploads.append({'report': report, 'version': version})
        return 'local-fixture-event-' + str(self.counts['upload'])

    def tick(self):
        if self.alive and not self.paused and time.monotonic() >= self.ack_after:
            active = self.listener.refresh()
            if active and self.listener.report.session != self.injected_session:
                self.injected_session = self.listener.report.session
                self.listener.device('fixture-controller-private-path', 'accepted',
                                     {'bus': 3, 'vendor_id': 10462, 'product_id': 4613},
                                     keys=[0x130, 0x2c0], axes=[0, 1])
                self.listener.device('fixture-rejected-private-path', 'rejected', keys=[0x131])
                for code, button in ((0x130, 'A'), (0x2c0, 'L4')):
                    self.listener.key('fixture-controller-private-path', code, 1, button, self.clock())
                    self.listener.key('fixture-controller-private-path', code, 0, button, self.clock())
            if self.listener.terminal_pending:
                if self.finish_after is None:
                    self.finish_after = time.monotonic() + 0.4
                if time.monotonic() >= self.finish_after:
                    self.listener.finish_if_drained(pending=False)
        # Background backend ownership advances even with no renderer or RPC polling.
        asyncio.run(self.plugin.resume_controller_debug(None))

    def run(self):
        while not self.closed.wait(0.05):
            try:
                with self.lock:
                    self.tick()
            except Exception as exc:
                self.actor_error = repr(exc)
                log.exception('Producer failed')
                return

    def rpc(self, method, args):
        allowed = {**self.RPC, **self.UI_RPC}
        if method not in allowed or not isinstance(args, list) or len(args) != allowed[method]:
            raise ValueError('RPC is not allowlisted or wrong arity')
        if method in ('get_controller_debug', 'stop_controller_debug', 'upload_controller_debug'):
            if not isinstance(args[0], str) or len(args[0]) > 64:
                raise ValueError('Invalid session')
        if method == 'upload_controller_debug' and type(args[1]) is not bool:
            raise ValueError('Consent must be boolean')
        generation = self.generation
        if method == 'get_controller_debug' and self.rpc_delay:
            time.sleep(self.rpc_delay)
        with self.lock:
            if generation != self.generation:
                raise ValueError('Fixture reset during RPC')
            if method == 'get_plugin_update':
                return {'success': True, 'update_available': False, 'current': self.backend.plugin_version}
            if method == 'set_overlay_transcribing_label':
                return {'success': True}
            if method == 'start_controller_debug' and self.plugin.controller_debug.state not in ('starting', 'recording', 'stopping'):
                self.ack_after = time.monotonic() + self.ack_delay
                self.finish_after = None
            result = asyncio.run(getattr(self.plugin, method)(None, *args))
            self.history.append({'method': method, 'state': result.get('state'), 'session': result.get('session')})
            log.info('RPC %s state=%s session=%s', method, result.get('state'), result.get('session'))
            return result

    def control(self, payload):
        command = payload.get('command')
        with self.lock:
            if command == 'reset':
                self.reset()
            elif command == 'ack_delay':
                value = payload.get('seconds')
                if type(value) not in (int, float) or not 0 <= value <= 4.5:
                    raise ValueError('ACK delay outside bound')
                self.ack_delay = value
            elif command == 'input':
                # Replay observations through the actual producer; never mutate an
                # RPC result/current/final report or choose arbitrary input paths.
                source, button, pressed = (payload.get(key) for key in ('source', 'button', 'pressed'))
                if source not in ('controller', 'hidraw') or button not in ('A', 'L4', 'Left Trackpad', 'Right Trackpad', 'D-pad Right', 'D-pad Left') or (source == 'controller' and button not in ('A', 'L4')) or type(pressed) is not bool:
                    raise ValueError('Invalid fixture input transition')
                if not self.listener.report:
                    raise ValueError('Capture must acknowledge before input replay')
                now = self.clock()
                if source == 'controller':
                    self.listener.key('fixture-controller-private-path',
                                      {'A': 0x130, 'L4': 0x2c0}[button], int(pressed), button, now)
                else:
                    self.listener.device('fixture-hidraw-private-path', 'hidraw',
                                         {'vendor_id': 10462, 'product_id': 4613})
                    self.listener.transition('fixture-hidraw-private-path', 'hid', button, pressed, now)
                self.tick()
            elif command == 'advance':
                value = payload.get('seconds')
                if type(value) not in (int, float) or not 0 <= value <= 35:
                    raise ValueError('Advance outside bound')
                self.offset += value
                self.tick()
            elif command == 'dead_listener':
                self.alive = False
            elif command == 'pause':
                if type(payload.get('value')) is not bool:
                    raise ValueError('Pause must be boolean')
                self.paused = payload['value']
            elif command == 'busy':
                value = payload.get('kind')
                if value not in ('recording', 'transcribing', 'idle'):
                    raise ValueError('Unknown busy kind')
                self.plugin.voice_service.is_recording = value == 'recording'
                self.plugin.voice_service.is_transcribing = value == 'transcribing'
            elif command == 'start_response_delay':
                value = payload.get('seconds')
                if type(value) not in (int, float) or not 0 <= value <= 7:
                    raise ValueError('Start response delay outside bound')
                self.start_response_delay = value
            elif command == 'rpc_delay':
                value = payload.get('seconds')
                if type(value) not in (int, float) or not 0 <= value <= 7:
                    raise ValueError('RPC delay outside bound')
                self.rpc_delay = value
            elif command == 'corrupt_snapshot':
                from binding_capture import read_json, write_json
                result_file = self.directory / 'controller_debug_result.json'
                value = payload.get('kind')
                if value not in ('stale', 'malformed'):
                    raise ValueError('Unknown corruption')
                self.paused = True
                old = read_json(result_file)
                if value == 'stale':
                    old['session'] = '0' * 32
                    old['sequence'] = 999999
                else:
                    old['started_mono'] = 'not-a-clock'
                    old['report'] = {'devices': 'not-a-list', 'events': []}
                write_json(result_file, old)
            elif command != 'inspect':
                raise ValueError('Control is not allowlisted')
            return {'snapshot': self.plugin.controller_debug.snapshot(), 'counts': self.counts.copy(),
                    'uploads': list(self.uploads), 'history': list(self.history),
                    'actor_error': self.actor_error, 'generation': self.generation}

    def close(self):
        self.closed.set()
        self.worker.join(timeout=3)
        self.temp.cleanup()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.info(fmt, *args)

    def send(self, status, value):
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        # Defense in depth: random process token + exact Origin if supplied.
        if (self.client_address[0] != '127.0.0.1' or
                not secrets.compare_digest(self.headers.get('X-Decktation-Test-Token', ''), TOKEN) or
                self.headers.get('Origin', ORIGIN) != ORIGIN):
            return self.send(403, {'error': 'Forbidden'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.send(415, {'error': 'JSON required'})
        try:
            size = int(self.headers.get('Content-Length', '-1'))
            if not 0 < size <= MAX_BODY:
                return self.send(413, {'error': 'Body too large or missing'})
            self.connection.settimeout(3)
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError('Object required')
            if self.path == '/api/rpc':
                result = runtime.rpc(payload.get('method'), payload.get('args', []))
                if payload.get('method') == 'start_controller_debug':
                    # Delay delivery, not producer execution or the backend lock.
                    time.sleep(runtime.start_response_delay)
            elif self.path == '/api/control':
                result = runtime.control(payload)
            else:
                return self.send(404, {'error': 'Unknown endpoint'})
            self.send(200, result)
        except (ValueError, TypeError, KeyError) as exc:
            self.send(400, {'error': str(exc)})
        except Exception:
            log.exception('Bridge request failed')
            self.send(500, {'error': 'Bridge request failed; see backend log'})


if __name__ == '__main__':
    runtime = Runtime()
    server = ThreadingHTTPServer(('127.0.0.1', int(os.environ.get('DECKTATION_TEST_BACKEND_PORT', '5180'))), Handler)
    server.daemon_threads = True
    def stop(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print('BACKEND_READY', flush=True)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()
        runtime.close()
