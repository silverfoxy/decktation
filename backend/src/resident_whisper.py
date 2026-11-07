"""One local whisper.cpp worker per loaded model, with bounded lifecycle."""
import ctypes
import json
import logging
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import urllib.request
import uuid

logger = logging.getLogger(__name__)


def server_command(binary, model, port, use_gpu):
    command = ['/usr/bin/python3', str(Path(__file__).resolve()), str(binary)]
    if not use_gpu:
        command.append('--no-gpu')
    command.extend([
        '--model', str(model), '--host', '127.0.0.1', '--port', str(port),
        '--language', 'auto', '--beam-size', '5'])
    return command


class ResidentWhisper:
    def __init__(self, binary, model, environment, use_gpu=True, timeout=60):
        self.process = None
        self.device = 'gpu' if use_gpu else 'cpu'
        self.directory = tempfile.TemporaryDirectory(prefix='decktation-resident-')
        self.log_path = Path(self.directory.name) / 'worker.log'
        self.log_file = self.log_path.open('wb')
        start = time.monotonic()
        try:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            self.url = f'http://127.0.0.1:{port}'
            self.http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            self.process = subprocess.Popen(
                server_command(binary, model, port, use_gpu),
                env={**environment, "DECKTATION_WHISPER_PARENT": str(os.getpid())}, stdin=subprocess.DEVNULL,
                stdout=self.log_file, stderr=subprocess.STDOUT, start_new_session=True)
            while time.monotonic() - start < timeout:
                if self.process.poll() is not None:
                    raise RuntimeError('Worker exited: ' + self._tail())
                try:
                    with self.http.open(self.url + '/health', timeout=.5) as response:
                        ready = json.loads(response.read()).get('status') == 'ok'
                    if ready:
                        evidence = self.log_path.read_text(errors='replace')
                        if use_gpu and 'using Vulkan0 backend' not in evidence:
                            raise RuntimeError('Worker did not confirm Vulkan0: ' + self._tail())
                        logger.info('Resident Whisper ready: device=%s pid=%s startup=%.3fs model=%s',
                                    self.device, self.process.pid, time.monotonic()-start, model)
                        if use_gpu:
                            logger.info('Resident Vulkan worker: %s', '\n'.join(
                                line for line in evidence.splitlines()
                                if 'ggml_vulkan:' in line or 'using Vulkan0 backend' in line))
                        return
                except (OSError, ValueError):
                    pass
                time.sleep(.1)
            raise TimeoutError(f'Resident {self.device} startup timed out: ' + self._tail())
        except Exception:
            self.close()
            raise

    def _tail(self):
        return self.log_path.read_text(errors='replace')[-2000:]

    def transcribe(self, wav_path, language, prompt):
        if self.process.poll() is not None:
            raise RuntimeError(f'Resident {self.device} worker died: ' + self._tail())
        # Send every mutable decoding option on every request, including empty
        # prompt, so a previous recording's language/context cannot leak.
        # The pinned server creates fresh request parameters with no_context
        # enabled by default. It does not parse a no_context form field, so send
        # the mutable values it does support, including an explicitly empty
        # prompt to prevent one recording's context from leaking into another.
        fields = {'language': language or 'auto', 'prompt': prompt or '',
                  'response_format': 'json', 'beam_size': '5',
                  # Dictation consumes text only, so skip word timing work.
                  'token_timestamps': 'false',
                  'translate': 'false'}
        boundary = 'decktation-' + uuid.uuid4().hex
        body = bytearray()
        for key, value in fields.items():
            body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode())
        body.extend(Path(wav_path).read_bytes())
        body.extend(f'\r\n--{boundary}--\r\n'.encode())
        request = urllib.request.Request(self.url + '/inference', data=bytes(body),
                    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
        with self.http.open(request, timeout=90) as response:
            result = json.loads(response.read())
        if not isinstance(result.get('text'), str):
            raise RuntimeError('Invalid resident transcript response')
        return result['text']

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=1)
            self.process = None
        self.log_file.close()
        self.directory.cleanup()


if __name__ == '__main__':
    # This separate launcher avoids preexec_fn in Decky's threaded process.
    # Kernel kills the resident worker if its owning plugin exits or crashes.
    import sys
    parent = int(os.environ.pop("DECKTATION_WHISPER_PARENT"))
    if os.getppid() != parent:
        raise SystemExit(1)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'Could not set worker parent-death signal')
    if os.getppid() != parent:
        raise SystemExit(1)
    os.execvpe(sys.argv[1], sys.argv[1:], os.environ)
