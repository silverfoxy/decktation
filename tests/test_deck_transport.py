"""Real localhost HTTP + WebSocket fixture; never a Steam target."""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
import struct
import threading
import time
from contextlib import contextmanager
import pytest
from test_deck_artifact import runner


@contextmanager
def fixture_server(hang=False, ui=False):
    events = []
    closed = threading.Event()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            if self.path == '/json/list':
                body = json.dumps([{'type': 'page', 'title': 'Steam',
                    'webSocketDebuggerUrl': f'ws://127.0.0.1:{self.server.server_port}/devtools/page/1'}]).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            key = self.headers['Sec-WebSocket-Key']
            accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
            self.send_response(101)
            self.send_header('Upgrade', 'websocket')
            self.send_header('Connection', 'Upgrade')
            self.send_header('Sec-WebSocket-Accept', accept)
            self.end_headers()
            phase = 'idle'
            try:
                while True:
                    h = self.rfile.read(2)
                    if not h or h[0] & 15 == 8:
                        return
                    n = h[1] & 127
                    if n == 126:
                        n = struct.unpack('!H', self.rfile.read(2))[0]
                    elif n == 127:
                        n = struct.unpack('!Q', self.rfile.read(8))[0]
                    mask = self.rfile.read(4)
                    data = self.rfile.read(n)
                    request = json.loads(bytes(b ^ mask[i % 4] for i, b in enumerate(data)))
                    events.append(request)
                    if hang:
                        continue
                    result = {'result': {'value': {'ok': True}}}
                    if ui:
                        from test_deck_smoke import snapshot
                        if request['method'] == 'Runtime.evaluate':
                            result = {'result': {'value': snapshot(phase)}}
                        elif request['method'] == 'Page.captureScreenshot':
                            result = {'data': 'iVBORw0KGgo='}
                        elif request['method'] == 'Input.dispatchMouseEvent' and request['params']['type'] == 'mouseReleased':
                            phase = 'recording' if phase == 'idle' else 'ready'
                    body = json.dumps({'id': request['id'], 'result': result}).encode()
                    header = bytes([129, len(body)]) if len(body) < 126 else bytes([129, 126]) + struct.pack('!H', len(body))
                    self.wfile.write(header + body)
                    self.wfile.flush()
            finally:
                closed.set()
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port, events, closed
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_real_transport_and_synthetic_key_order():
    r = runner()
    with fixture_server() as (port, events, closed):
        target = r.discover(port, 'Steam', 'page', 1)
        with r.CDP(target['webSocketDebuggerUrl'], 1) as cdp:
            assert cdp.evaluate('1')['ok']
            r.send_key(cdp, 'Escape', allow_input=True)
        assert closed.wait(1)
        assert [x['params']['type'] for x in events if x['method'] == 'Input.dispatchKeyEvent'] == ['keyDown', 'keyUp']
        assert r.INPUT_LABEL == 'synthetic CDP keyboard; not physical controller evidence'


def test_missing_or_unsupported_target_and_timeout_cleanup():
    r = runner()
    with fixture_server(hang=True) as (port, events, closed):
        with pytest.raises(ValueError, match='exactly one'):
            r.discover(port, 'not Steam', 'page', 1)
        with pytest.raises(ValueError, match='target type'):
            r.discover(port, 'Steam', 'browser', 1)
        target = r.discover(port, 'Steam', 'page', 1)
        start = time.monotonic()
        with pytest.raises((TimeoutError, socket.timeout)):
            with r.CDP(target['webSocketDebuggerUrl'], .1) as cdp:
                cdp.evaluate('1')
        assert time.monotonic() - start < 2
        assert closed.wait(1)


def test_mutation_gate_and_safe_ssh():
    r = runner()
    class Forbidden:
        def call(self, *args, **kwargs):
            pytest.fail('input sent without consent')
    with pytest.raises(ValueError, match='allow-input'):
        r.send_key(Forbidden(), 'Enter')
    args = r.parser().parse_args(['preflight', '--host', 'deck@example', '--artifact', 'ci.zip', '--target-title', 'Steam'])
    assert not args.allow_input
    command = r.ssh_command('deck@example', ['/usr/bin/sha256sum', '/path with spaces/main.py'])
    assert 'StrictHostKeyChecking=yes' in command
    assert "'/path with spaces/main.py'" in command[-1]
    with pytest.raises(ValueError):
        r.ssh_command('-oProxyCommand=bad', ['true'])
    with pytest.raises(ValueError):
        r.CDP('ws://example.com:9222/devtools/page/1', 1)


def test_key_release_attempted_after_dispatch_failure():
    r = runner()
    calls = []
    class Broken:
        def call(self, method, params):
            calls.append(params['type'])
            if params['type'] == 'keyDown':
                raise TimeoutError('fixture failure')
    with pytest.raises(TimeoutError):
        r.send_key(Broken(), 'Enter', allow_input=True)
    assert calls == ['keyDown', 'keyUp']


def test_main_input_gate_never_starts_ssh(tmp_path, monkeypatch):
    r = runner()
    def forbidden(*args, **kwargs):
        pytest.fail('SSH must not run before input consent')
    monkeypatch.setattr(r, 'installed_hashes', forbidden)
    status = r.main(['smoke', '--host', 'fixture', '--artifact', str(tmp_path/'missing.zip'),
                     '--target-title', 'Steam', '--output', str(tmp_path/'evidence')])
    assert status == 1
    result = json.loads((tmp_path/'evidence/result.json').read_text())
    assert 'allow-input' in result['reason']
    # There is deliberately no deploy/install/reload CLI operation.
    with pytest.raises(SystemExit):
        r.parser().parse_args(['deploy'])


def test_tunnel_port_check_allows_timewait_but_rejects_live_listener(monkeypatch):
    r = runner()
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
    listener.listen()
    def boundary(*args, **kwargs):
        raise RuntimeError('fixture spawn boundary; no SSH started')
    monkeypatch.setattr(r.subprocess, 'Popen', boundary)
    with pytest.raises(OSError):
        with r.tunnel('fixture', port, 8080, .1):
            pass
    client = socket.create_connection(('127.0.0.1', port))
    accepted, _ = listener.accept()
    accepted.close()  # server-side active close puts this local port in TIME_WAIT
    client.close()
    listener.close()
    with pytest.raises(RuntimeError, match='fixture spawn boundary'):
        with r.tunnel('fixture', port, 8080, .1):
            pass


def test_cli_real_subprocess_tunnel_and_failure_cleanup(tmp_path):
    import os
    import subprocess
    import sys
    from test_deck_artifact import artifact, ROOT
    r = runner()
    zip_path, _ = artifact(tmp_path)
    manifest = r.inspect_artifact(zip_path)
    shim = tmp_path / 'ssh'
    shim.write_text('''#!/usr/bin/python3
import os,sys,socket,threading,select
from pathlib import Path
if '-N' not in sys.argv:
    print(os.environ['HASH_OUTPUT'], end='')
    raise SystemExit(0)
Path(os.environ['PID_PATH']).write_text(str(os.getpid()))
spec=sys.argv[sys.argv.index('-L')+1].split(':')
server=socket.socket(); server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
server.bind((spec[0],int(spec[1]))); server.listen()
def forward(client):
    remote=socket.create_connection((spec[2],int(spec[3])))
    try:
        while True:
            ready,_,_=select.select([client,remote],[],[],2)
            for source in ready:
                data=source.recv(65536)
                if not data: return
                (remote if source is client else client).sendall(data)
    finally: client.close(); remote.close()
while True:
    client,_=server.accept()
    threading.Thread(target=forward,args=(client,),daemon=True).start()
''')
    shim.chmod(0o755)
    environment = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ['PATH'],
        HASH_OUTPUT=''.join(f'{manifest["files"][name]}  /fixture/{name}\n' for name in r.REQUIRED),
        PID_PATH=str(tmp_path / 'ssh.pid'))
    def free_port():
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]
    with fixture_server(ui=True) as (port, events, closed):
        command = [sys.executable, str(ROOT / 'scripts/deck/runner.py'), 'smoke',
            '--host', 'fixture', '--artifact', str(zip_path), '--installed-root', '/fixture',
            '--target-title', 'Steam', '--local-port', str(free_port()), '--remote-port', str(port),
            '--output', str(tmp_path / 'evidence'), '--allow-input', '--allow-unverified-runtime']
        result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=10)
        assert result.returncode == 2, result.stderr + result.stdout
        report = json.loads((tmp_path / 'evidence/result.json').read_text())
        assert report['flow'] == 'passed'
        assert report['verdict'] == 'inconclusive-runtime-identity'
        assert closed.wait(1)
        pid = int((tmp_path / 'ssh.pid').read_text())
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
        # Same real subprocess path, wrong exact title: fails closed, still kills only owned tunnel.
        command[command.index('--target-title') + 1] = 'Wrong target'
        result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=10)
        assert result.returncode == 1
        report = json.loads((tmp_path / 'evidence/result.json').read_text())
        assert 'exactly one' in report['reason']
        with pytest.raises(ProcessLookupError):
            os.kill(int((tmp_path / 'ssh.pid').read_text()), 0)
