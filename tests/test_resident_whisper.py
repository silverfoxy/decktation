import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call
import pytest
import resident_whisper


def test_cpu_worker_disables_gpu():
    command = resident_whisper.server_command('/bin/whisper-server', '/model', 1234, False)
    assert '--no-gpu' in command
    assert command[command.index('--model') + 1] == '/model'


def test_gpu_worker_keeps_gpu_enabled():
    command = resident_whisper.server_command('/bin/whisper-server', '/model', 1234, True)
    assert '--no-gpu' not in command


def test_requests_reuse_worker_and_clear_previous_context(tmp_path):
    worker = resident_whisper.ResidentWhisper.__new__(resident_whisper.ResidentWhisper)
    worker.process = MagicMock(); worker.process.poll.return_value = None
    worker.url = 'http://127.0.0.1:1234'
    bodies = []
    class HTTP:
        def open(self, request, timeout):
            assert timeout == 90
            bodies.append(request.data)
            return io.BytesIO(json.dumps({'text':'hola'}).encode())
    worker.http = HTTP()
    wav = tmp_path/'audio.wav'; wav.write_bytes(b'RIFF-audio')
    assert worker.transcribe(wav, 'es', 'Azeroth') == 'hola'
    assert worker.transcribe(wav, None, None) == 'hola'
    assert b'\r\nes\r\n' in bodies[0] and b'Azeroth' in bodies[0]
    assert b'\r\nauto\r\n' in bodies[1] and b'Azeroth' not in bodies[1]
    assert b'name="prompt"\r\n\r\n\r\n' in bodies[1]
    assert b'name="no_context"' not in bodies[1]
    for body in bodies:
        assert b'name="token_timestamps"\r\n\r\nfalse\r\n' in body


def test_startup_failure_reaps_worker(monkeypatch):
    socket = MagicMock(); socket.__enter__.return_value.getsockname.return_value = ('127.0.0.1',1234)
    monkeypatch.setattr(resident_whisper.socket, 'socket', lambda: socket)
    process = MagicMock(); process.poll.return_value = 1
    monkeypatch.setattr(resident_whisper.subprocess, 'Popen', lambda *a, **k: process)
    with pytest.raises(RuntimeError, match='Worker exited'):
        resident_whisper.ResidentWhisper('/missing', '/model', {})
    assert process.poll.called


def test_timeout_kills_worker(tmp_path):
    worker = resident_whisper.ResidentWhisper.__new__(resident_whisper.ResidentWhisper)
    worker.process = process = MagicMock(); process.poll.return_value = None
    process.wait.side_effect = [resident_whisper.subprocess.TimeoutExpired('worker',5),None]
    worker.log_file = MagicMock(); worker.directory = MagicMock()
    worker.close()
    process.terminate.assert_called_once(); process.kill.assert_called_once()
    assert worker.process is None
    assert process.wait.call_args_list == [call(timeout=1)] * 2
