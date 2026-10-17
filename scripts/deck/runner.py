#!/usr/bin/env python3
"""Opt-in installed Steam/Decky evidence runner. No deploy or reload support."""
import argparse
import base64
import contextlib
import os
import shlex
import socket
import struct
import subprocess
import time
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

REQUIRED = ('package.json', 'dist/index.js', 'main.py', 'bin/decktation_backend.py',
            'bin/controller_listener.py', 'bin/controller_debug_report.py',
            'bin/controller_debug_session.py')
MAX_SOURCE = 16 * 1024 * 1024


def inspect_artifact(path):
    """Inspect bounded critical sources, never unpack bundled dependencies."""
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    with zipfile.ZipFile(path) as archive:
        sources = {}
        seen = set()
        for info in archive.infolist():
            name = info.filename
            parts = PurePosixPath(name).parts
            if (name.startswith('/') or '\\' in name or '..' in parts
                    or not parts or parts[0] != 'decktation' or '\x00' in name):
                raise ValueError('unsafe ZIP path')
            if name.rstrip('/') != str(PurePosixPath(name)):
                raise ValueError('noncanonical ZIP path')
            if name in seen:
                raise ValueError('duplicate ZIP entry')
            seen.add(name)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError('ZIP symlink forbidden')
            relative = '/'.join(parts[1:])
            if relative in REQUIRED:
                if info.file_size > MAX_SOURCE:
                    raise ValueError('oversized source')
                sources[relative] = archive.read(info)
        if set(sources) != set(REQUIRED):
            raise ValueError('missing required ZIP entries')
    tree = ast.parse(sources['bin/controller_debug_session.py'])
    protocols = [ast.literal_eval(node.value) for node in tree.body
                 if isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'PROTOCOL' for t in node.targets)]
    if protocols != [2]:
        raise ValueError('expected controller protocol 2')
    version = json.loads(sources['package.json'])['version']
    hint = re.search(r'(?:dev[.-])?g([0-9a-f]{7,40})(?:$|[.+-])', version)
    return {'zip_sha256': digest.hexdigest(), 'version': version, 'protocol': 2,
            'source_sha_hint': hint.group(1) if hint else None,
            'files': {k: hashlib.sha256(v).hexdigest() for k, v in sources.items()}}


def compare_installed(manifest, hashes):
    if hashes != manifest['files']:
        raise ValueError('installed artifact hash mismatch')
    return {'installed_bytes_match': True,
            'active_frontend_identity': 'inconclusive: installed bytes are not renderer identity',
            'active_backend_identity': 'inconclusive: installed bytes are not process identity'}

INPUT_LABEL = 'synthetic CDP keyboard; not physical controller evidence'


def ssh_command(host, argv):
    if not re.fullmatch(r'(?:[A-Za-z0-9_][A-Za-z0-9_.-]*@)?[A-Za-z0-9][A-Za-z0-9_.-]*', host):
        raise ValueError('invalid SSH host')
    return ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'ConnectTimeout=5', '--', host, shlex.join(argv)]


def installed_hashes(host, root, timeout):
    if not root.startswith('/') or '\x00' in root or '..' in PurePosixPath(root).parts:
        raise ValueError('installed root must be absolute')
    paths = [str(PurePosixPath(root) / f) for f in REQUIRED]
    result = subprocess.run(ssh_command(host, ['sha256sum', '--', *paths]),
                            check=True, capture_output=True, text=True, timeout=timeout)
    hashes = {}
    for line, relative in zip(result.stdout.splitlines(), REQUIRED):
        match = re.fullmatch(r'([a-f0-9]{64})  (.*)', line)
        if not match or match[2] != str(PurePosixPath(root) / relative):
            raise ValueError('invalid remote hash output')
        hashes[relative] = match[1]
    return hashes


def discover(port, title, target_type, timeout):
    if target_type not in ('page', 'webview'):
        raise ValueError('unsupported target type')
    opener = build_opener(ProxyHandler({}))
    with opener.open(f'http://127.0.0.1:{port}/json/list', timeout=timeout) as response:
        data = response.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError('oversized target listing')
    matches = [t for t in json.loads(data) if t.get('type') == target_type and t.get('title') == title]
    if len(matches) != 1:
        raise ValueError('need exactly one target matching exact type/title')
    url = urlsplit(matches[0]['webSocketDebuggerUrl'])
    if url.scheme != 'ws' or url.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('debugger must advertise loopback websocket')
    matches[0]['webSocketDebuggerUrl'] = f'ws://127.0.0.1:{port}{url.path}'
    return matches[0]


class CDP:
    """Bounded RFC6455 synchronous client. Only loopback, no dependencies."""
    def __init__(self, url, timeout):
        parsed = urlsplit(url)
        if parsed.scheme != 'ws' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
            raise ValueError('CDP requires loopback websocket')
        self.sock = None
        self.timeout = timeout
        self.deadline = time.monotonic() + timeout
        self.sequence = 0
        self.events = []
        try:
            self.sock = socket.create_connection((parsed.hostname, parsed.port), timeout)
            key = base64.b64encode(os.urandom(16)).decode()
            self.sock.sendall((f'GET {parsed.path} HTTP/1.1\r\nHost: {parsed.netloc}\r\n'
                f'Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n'
                'Sec-WebSocket-Version: 13\r\n\r\n').encode())
            headers = bytearray()
            while not headers.endswith(b'\r\n\r\n'):
                headers.extend(self._read(1))
                if len(headers) > 16384:
                    raise ValueError('oversized handshake')
            accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
            if b' 101 ' not in headers.split(b'\r\n')[0] or b'sec-websocket-accept: ' + accept.lower() not in bytes(headers).lower():
                raise ValueError('invalid websocket handshake')
        except BaseException:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def _read(self, size):
        data = bytearray()
        while len(data) < size:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('CDP deadline exceeded')
            self.sock.settimeout(remaining)
            chunk = self.sock.recv(size - len(data))
            if not chunk:
                raise ConnectionError('CDP socket closed')
            data.extend(chunk)
        return bytes(data)

    def _send(self, opcode, data):
        mask = os.urandom(4)
        size = len(data)
        if size < 126:
            header = bytes([128 | opcode, 128 | size])
        elif size < 65536:
            header = bytes([128 | opcode, 254]) + struct.pack('!H', size)
        else:
            header = bytes([128 | opcode, 255]) + struct.pack('!Q', size)
        self.sock.sendall(header + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _message(self):
        chunks = bytearray()
        while True:
            head = self._read(2)
            opcode, final = head[0] & 15, head[0] & 128
            size = head[1] & 127
            if size == 126:
                size = struct.unpack('!H', self._read(2))[0]
            elif size == 127:
                size = struct.unpack('!Q', self._read(8))[0]
            if head[1] & 128 or size + len(chunks) > 12 * 1024 * 1024:
                raise ValueError('invalid or oversized websocket frame')
            payload = self._read(size)
            if opcode == 8:
                raise ConnectionError('CDP peer closed')
            if opcode == 9:
                self._send(10, payload)
                continue
            if opcode == 10:
                continue
            if opcode not in (0, 1):
                raise ValueError('unsupported websocket opcode')
            chunks.extend(payload)
            if final:
                return json.loads(chunks)

    def call(self, method, params=None):
        self.sequence += 1
        self.deadline = min(time.monotonic() + self.timeout, getattr(self, 'overall_deadline', float('inf')))
        self._send(1, json.dumps({'id': self.sequence, 'method': method, 'params': params or {}}).encode())
        while True:
            message = self._message()
            if message.get('id') == self.sequence:
                if 'error' in message:
                    raise ValueError('CDP command failed: ' + method)
                return message['result']
            if 'method' in message:
                self.events.append({'method': message['method']})
                self.events = self.events[-100:]

    def evaluate(self, expression):
        result = self.call('Runtime.evaluate', {'expression': expression, 'returnByValue': True})
        if 'exceptionDetails' in result:
            raise ValueError('UI probe failed')
        return result['result'].get('value')


def send_key(cdp, key, allow_input=False):
    if not allow_input:
        raise ValueError('requires --allow-input')
    codes = {'Enter': 13, 'Escape': 27, 'ArrowDown': 40}
    params = {'key': key, 'code': key, 'windowsVirtualKeyCode': codes[key],
              'nativeVirtualKeyCode': codes[key]}
    try:
        cdp.call('Input.dispatchKeyEvent', dict(params, type='keyDown'))
    finally:
        cdp.call('Input.dispatchKeyEvent', dict(params, type='keyUp'))


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('command', choices=['verify-artifact', 'preflight', 'capture', 'smoke'])
    cli.add_argument('--host', required=True)
    cli.add_argument('--artifact', required=True, type=Path)
    cli.add_argument('--installed-root', default='/home/deck/homebrew/plugins/decktation')
    cli.add_argument('--local-port', type=int, default=19222)
    cli.add_argument('--remote-port', type=int, default=8080)
    cli.add_argument('--target-title', required=True)
    cli.add_argument('--target-type', choices=['page', 'webview'], default='page')
    cli.add_argument('--allow-input', action='store_true')
    cli.add_argument('--allow-unverified-runtime', action='store_true', help='run behavior evidence but never emit a verified runtime verdict')
    cli.add_argument('--output', type=Path, default=Path('device-evidence'))
    cli.add_argument('--phase-timeout', type=float, default=8)
    cli.add_argument('--overall-timeout', type=float, default=60)
    return cli



def probe(cdp):
    return cdp.evaluate(Path(__file__).with_name('js').joinpath('diagnostics.js').read_text())


def screenshot(cdp, output, name):
    result = cdp.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
    output.joinpath(name + '.png').write_bytes(base64.b64decode(result['data'], validate=True))


def smoke(cdp, output, allow_input=False, allow_unverified_runtime=False,
          phase_timeout=8, overall_timeout=45):
    if not allow_input:
        raise ValueError('smoke requires --allow-input')
    if not allow_unverified_runtime:
        raise ValueError('active runtime identity unavailable; explicit --allow-unverified-runtime required for inconclusive evidence')
    deadline = time.monotonic() + overall_timeout
    timeline = []

    def observe():
        if time.monotonic() >= deadline:
            raise TimeoutError('overall smoke deadline exceeded')
        state = probe(cdp)
        timeline.append(state)
        return state

    def wait_for(phase):
        end = min(deadline, time.monotonic() + phase_timeout)
        while time.monotonic() < end:
            state = observe()
            if not state.get('visible'):
                raise ValueError('capture debugger disappeared')
            if state.get('phase') == phase:
                return state
            time.sleep(min(.1, max(0, end - time.monotonic())))
        raise TimeoutError('capture phase deadline: ' + phase)

    def click(state, name):
        if not state.get('visible') or name not in state.get('controls', {}):
            raise ValueError('capture control unavailable: ' + name)
        x, y = state['controls'][name]
        for kind in ('mousePressed', 'mouseReleased'):
            cdp.call('Input.dispatchMouseEvent', {'type': kind, 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})

    output.mkdir(parents=True, exist_ok=True)
    try:
        baseline = observe()
        if not baseline.get('visible') or baseline.get('phase') not in ('idle', 'ready'):
            raise ValueError('open idle Decktation Diagnostics first')
        if not baseline.get('native_focus') or any(f['label'] == 'outside-debugger' for f in baseline['native_focus']):
            raise ValueError('native .gpfocus evidence unavailable or outside debugger')
        screenshot(cdp, output, 'baseline')
        click(baseline, 'start')  # declared synthetic mouse; never DOM focus as native evidence
        recording = wait_for('recording')
        if not isinstance(recording.get('seconds'), int) or not 0 < recording['seconds'] <= 30:
            raise ValueError('capture countdown unavailable')
        for key in ('Escape', 'ArrowDown', 'Enter'):
            send_key(cdp, key, allow_input=True)
            state = observe()
            if not state.get('visible') or state.get('phase') != 'recording':
                raise ValueError('capture exited after synthetic ' + key)
            if not state.get('native_focus') or any(f['label'] == 'outside-debugger' for f in state['native_focus']):
                raise ValueError('capture lost native focus evidence')
        screenshot(cdp, output, 'recording')
        click(observe(), 'stop')
        wait_for('ready')
        screenshot(cdp, output, 'ready')
        return {'flow': 'passed', 'verdict': 'inconclusive-runtime-identity',
                'input': INPUT_LABEL, 'activation': 'synthetic CDP mouse Start and Stop',
                'physical_controller': 'UNRUN'}
    except Exception:
        with contextlib.suppress(Exception):
            screenshot(cdp, output, 'failure')
        raise
    finally:
        output.joinpath('timeline.json').write_text(json.dumps(timeline, indent=2))


@contextlib.contextmanager
def tunnel(host, local_port, remote_port, timeout):
    base = ssh_command(host, [])
    if not all(1 <= p <= 65535 for p in (local_port, remote_port)):
        raise ValueError('invalid port')
    # Reject an occupied port instead of attaching to an unrelated debugger.
    with socket.socket() as check:
        # TIME_WAIT from our previous tunnel is not a live listener. This still
        # rejects an active listener (we never enable SO_REUSEPORT).
        check.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        check.bind(('127.0.0.1', local_port))
    command = base[:-3] + ['-o', 'ExitOnForwardFailure=yes', '-N', '-L',
                f'127.0.0.1:{local_port}:127.0.0.1:{remote_port}', '--', host]
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise ValueError('SSH tunnel failed; verify known_hosts, authorization and debugger configuration manually')
            try:
                connection = socket.create_connection(('127.0.0.1', local_port), timeout=.1)
            except (ConnectionRefusedError, socket.timeout):
                time.sleep(.05)
                continue
            connection.close()
            yield
            return
        raise TimeoutError('SSH tunnel readiness deadline')
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)


def main(argv=None):
    args = parser().parse_args(argv)
    report = {'device_physical_checks': 'UNRUN', 'input': INPUT_LABEL}
    args.output.mkdir(parents=True, exist_ok=True)
    cdp = None
    try:
        if not 0 < args.phase_timeout <= 15 or not 0 < args.overall_timeout <= 120:
            raise ValueError('phase timeout must be 0..15s; overall timeout 0..120s')
        if args.command == 'smoke' and not args.allow_input:
            raise ValueError('smoke requires --allow-input (no SSH actions attempted)')
        if args.command == 'smoke' and not args.allow_unverified_runtime:
            raise ValueError('active runtime identity unavailable; --allow-unverified-runtime required for inconclusive evidence')
        manifest = inspect_artifact(args.artifact)
        report['artifact'] = manifest
        report.update(compare_installed(manifest, installed_hashes(args.host, args.installed_root, args.phase_timeout)))
        if args.command == 'verify-artifact':
            report['verdict'] = 'installed-bytes-match; active-runtime-inconclusive'
            return 0
        with tunnel(args.host, args.local_port, args.remote_port, args.phase_timeout):
            target = discover(args.local_port, args.target_title, args.target_type, args.phase_timeout)
            with CDP(target['webSocketDebuggerUrl'], args.phase_timeout) as cdp:
                cdp.overall_deadline = time.monotonic() + args.overall_timeout
                cdp.call('Runtime.enable')
                cdp.call('Log.enable')
                state = probe(cdp)
                report['baseline'] = state
                if not state.get('visible'):
                    raise ValueError('open Decktation Diagnostics first (English UI required)')
                if args.command == 'smoke':
                    report.update(smoke(cdp, args.output, args.allow_input, args.allow_unverified_runtime,
                                        args.phase_timeout, args.overall_timeout))
                elif args.command == 'capture':
                    screenshot(cdp, args.output, 'capture')
                report['verdict'] = 'inconclusive-runtime-identity'
                # Current production UI exposes neither active frontend byte hash nor backend identity.
                return 2
    except Exception as error:
        report['verdict'] = 'failed'
        # Do not persist remote error text: it may contain home paths, usernames or secrets.
        report['error'] = type(error).__name__
        if isinstance(error, (ValueError, TimeoutError)):
            report['reason'] = str(error)[:240]
        if cdp and cdp.sock:
            with contextlib.suppress(Exception):
                screenshot(cdp, args.output, 'failure')
        return 1
    finally:
        if cdp:
            report['cdp_events'] = cdp.events
        args.output.joinpath('result.json').write_text(json.dumps(report, indent=2))
        print(json.dumps({'verdict': report.get('verdict'), 'evidence': str(args.output)}))


if __name__ == '__main__':
    raise SystemExit(main())
