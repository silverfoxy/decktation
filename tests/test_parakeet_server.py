import io
import json
import threading
import urllib.error
import urllib.request
import wave

import sys

import pytest

# conftest.py mocks numpy for the whole suite. This worker does real audio math,
# so load it against real numpy and restore the mock for the other tests.
_numpy_mock = sys.modules.pop("numpy", None)
try:
    import numpy as np
    sys.modules.pop("parakeet_server", None)
    import parakeet_server as ps
finally:
    if _numpy_mock is not None:
        sys.modules["numpy"] = _numpy_mock


def wav_bytes(samples, rate=16000, channels=1, width=2):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(width)
        handle.setframerate(rate)
        handle.writeframes(samples)
    return buffer.getvalue()


def tone(seconds, rate=16000, channels=1):
    t = np.arange(int(seconds * rate)) / rate
    mono = (np.sin(2 * np.pi * 440 * t) * 8000).astype("<i2")
    return np.repeat(mono, channels).tobytes() if channels > 1 else mono.tobytes()


def multipart(fields, file_bytes, boundary="b0undary"):
    body = bytearray()
    for key, value in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
    if file_bytes is not None:
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
                 'Content-Type: audio/wav\r\n\r\n').encode()
        body += file_bytes + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def test_parse_multipart_returns_file_and_fields():
    body, ctype = multipart({"language": "auto", "prompt": ""}, b"RIFFdata")
    parts = ps.parse_multipart(body, ctype)
    assert parts["file"] == b"RIFFdata"
    assert parts["language"] == b"auto"
    assert parts["prompt"] == b""


def test_parse_multipart_rejects_missing_boundary():
    with pytest.raises(ps.BadRequest):
        ps.parse_multipart(b"x", "multipart/form-data")


def test_wav_16k_mono_passes_through():
    pcm = ps.wav_to_pcm16k(wav_bytes(tone(1.0)))
    assert pcm.dtype == np.float32 and pcm.ndim == 1
    assert len(pcm) == 16000
    assert np.abs(pcm).max() <= 1.0


def test_wav_44k_stereo_is_downmixed_and_resampled():
    pcm = ps.wav_to_pcm16k(wav_bytes(tone(1.0, rate=44100, channels=2), rate=44100, channels=2))
    assert pcm.ndim == 1
    assert abs(len(pcm) - 16000) <= 1


def test_wav_8bit_is_rejected():
    with pytest.raises(ps.BadRequest):
        ps.wav_to_pcm16k(wav_bytes(bytes(16000), width=1))


def test_garbage_is_rejected():
    with pytest.raises(ps.BadRequest):
        ps.wav_to_pcm16k(b"not a wav")


def test_too_long_audio_is_rejected():
    with pytest.raises(ps.TooLarge):
        ps.wav_to_pcm16k(wav_bytes(tone(301.0)))


def test_two_minute_dictation_is_accepted():
    assert len(ps.wav_to_pcm16k(wav_bytes(tone(120.0)))) == 120 * 16000


def test_truncated_wav_with_odd_byte_count_is_trimmed_not_crashing():
    data = wav_bytes(tone(1.0))[:-1]  # header promises one more byte than the file holds
    pcm = ps.wav_to_pcm16k(data)
    assert len(pcm) == 15999


class FakeEngine:
    def __init__(self):
        self.calls = []

    def transcribe(self, pcm):
        self.calls.append(len(pcm))
        return " olá mundo " if len(pcm) >= 1600 else ""


@pytest.fixture
def server():
    engine = FakeEngine()
    httpd = ps.make_server(engine, "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield engine, f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def post(url, body, ctype):
    request = urllib.request.Request(url + "/inference", data=body, headers={"Content-Type": ctype})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return opener.open(request, timeout=5)


def test_health_reports_ok(server):
    _, url = server
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url + "/health", timeout=5) as response:
        assert json.loads(response.read()) == {"status": "ok"}


def test_inference_returns_stripped_text(server):
    engine, url = server
    body, ctype = multipart({"language": "auto", "prompt": "Azeroth"}, wav_bytes(tone(1.0)))
    with post(url, body, ctype) as response:
        assert json.loads(response.read()) == {"text": "olá mundo"}
    assert engine.calls == [16000]


def test_tiny_clip_returns_empty_text(server):
    _, url = server
    body, ctype = multipart({}, wav_bytes(tone(0.05)))
    with post(url, body, ctype) as response:
        assert json.loads(response.read()) == {"text": ""}


def test_missing_file_is_400_and_server_keeps_working(server):
    _, url = server
    body, ctype = multipart({"language": "auto"}, None)
    with pytest.raises(urllib.error.HTTPError) as error:
        post(url, body, ctype)
    assert error.value.code == 400
    body, ctype = multipart({}, wav_bytes(tone(1.0)))
    with post(url, body, ctype) as response:
        assert response.status == 200


def test_oversized_body_is_413(server):
    _, url = server
    request = urllib.request.Request(url + "/inference", data=b"x",
        headers={"Content-Type": "multipart/form-data; boundary=b", "Content-Length": str(ps.MAX_BODY_BYTES + 1)})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with pytest.raises(urllib.error.HTTPError) as error:
        opener.open(request, timeout=5)
    assert error.value.code == 413


def test_non_loopback_bind_is_refused():
    with pytest.raises(ValueError):
        ps.make_server(FakeEngine(), "0.0.0.0", 0)


def test_negative_content_length_is_400(server):
    import http.client
    _, url = server
    host, port = url.split("//")[1].split(":")
    connection = http.client.HTTPConnection(host, int(port), timeout=5)
    connection.putrequest("POST", "/inference")
    connection.putheader("Content-Type", "multipart/form-data; boundary=b")
    connection.putheader("Content-Length", "-1")
    connection.endheaders()
    assert connection.getresponse().status == 400


class NoneEngine:
    def transcribe(self, pcm):
        return None


def test_engine_none_result_returns_empty_text():
    httpd = ps.make_server(NoneEngine(), "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        body, ctype = multipart({}, wav_bytes(tone(1.0)))
        with post(f"http://127.0.0.1:{httpd.server_address[1]}", body, ctype) as response:
            assert json.loads(response.read()) == {"text": ""}
    finally:
        httpd.shutdown(); httpd.server_close()


class SlowEngine:
    def __init__(self):
        self.active = 0
        self.peak = 0
        self.guard = threading.Lock()

    def transcribe(self, pcm):
        import time
        with self.guard:
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(0.2)
        with self.guard:
            self.active -= 1
        return "ok"


def test_concurrent_requests_never_overlap_in_engine():
    engine = SlowEngine()
    httpd = ps.make_server(engine, "127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    url = f"http://127.0.0.1:{httpd.server_address[1]}"
    body, ctype = multipart({}, wav_bytes(tone(1.0)))
    try:
        workers = [threading.Thread(target=lambda: post(url, body, ctype).read()) for _ in range(3)]
        for w in workers: w.start()
        for w in workers: w.join(10)
        assert engine.peak == 1
    finally:
        httpd.shutdown(); httpd.server_close()
