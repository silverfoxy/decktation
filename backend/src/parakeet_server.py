"""Resident Parakeet V3 worker speaking the whisper-server HTTP subset Decktation uses."""
import argparse
import http.server
import io
import json
import logging
import os
import threading
import wave

import numpy as np

logger = logging.getLogger("parakeet_server")

MAX_BODY_BYTES = 20 * 1024 * 1024
MAX_AUDIO_SECONDS = 300  # 20 MB of 16 kHz mono is about 10 min; long dictation must not be dropped
TARGET_RATE = 16000
MIN_SAMPLES = TARGET_RATE // 10  # shorter clips return empty text


class BadRequest(Exception):
    pass


class TooLarge(Exception):
    pass


def parse_multipart(body, content_type):
    marker = "boundary="
    if marker not in content_type:
        raise BadRequest("missing multipart boundary")
    boundary = content_type.split(marker, 1)[1].split(";", 1)[0].strip().strip('"')
    if not boundary:
        raise BadRequest("empty multipart boundary")
    delimiter = b"--" + boundary.encode()
    parts = {}
    for chunk in body.split(delimiter)[1:]:
        if chunk.startswith(b"--"):
            break
        chunk = chunk[2:] if chunk.startswith(b"\r\n") else chunk
        head, separator, value = chunk.partition(b"\r\n\r\n")
        if not separator:
            raise BadRequest("malformed multipart part")
        if value.endswith(b"\r\n"):
            value = value[:-2]
        name = None
        for line in head.decode("latin-1").split("\r\n"):
            if line.lower().startswith("content-disposition:"):
                for item in line.split(";"):
                    item = item.strip()
                    if item.startswith("name="):
                        name = item[5:].strip('"')
        if name:
            parts[name] = value
    return parts


def wav_to_pcm16k(data):
    try:
        with wave.open(io.BytesIO(data), "rb") as handle:
            channels = handle.getnchannels()
            width = handle.getsampwidth()
            rate = handle.getframerate()
            frames = handle.getnframes()
            if rate <= 0 or channels <= 0:
                raise BadRequest("invalid WAV header")
            if frames / rate > MAX_AUDIO_SECONDS:
                raise TooLarge("audio longer than %d s" % MAX_AUDIO_SECONDS)
            raw = handle.readframes(frames)
    except (wave.Error, EOFError) as error:
        raise BadRequest(f"unreadable WAV: {error}") from error
    if width != 2:
        raise BadRequest("only 16-bit PCM WAV is supported")
    raw = raw[: len(raw) - len(raw) % (width * channels)]  # truncated files can end mid-frame
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        samples = samples[: len(samples) - len(samples) % channels].reshape(-1, channels).mean(axis=1)
    if rate != TARGET_RATE and len(samples):
        count = int(round(len(samples) * TARGET_RATE / rate))
        source = np.arange(len(samples)) / rate
        target = np.arange(count) / TARGET_RATE
        samples = np.interp(target, source, samples)
    return np.ascontiguousarray(samples, dtype=np.float32)


class ParakeetEngine:
    def __init__(self, model_path):
        import transcribe_cpp  # bundled pure-Python binding, needs TRANSCRIBE_LIBRARY
        self._model = transcribe_cpp.Model(str(model_path), backend="cpu")
        threads = max(1, min(4, (os.cpu_count() or 4) // 2))
        self._session = self._model.session(n_threads=threads)
        logger.info("transcribe.cpp %s commit %s loaded %s threads=%d",
                    transcribe_cpp.native_version(), transcribe_cpp.native_commit(), model_path, threads)

    def transcribe(self, pcm):
        return self._session.run(pcm).text


def make_server(engine, host, port):
    if host != "127.0.0.1":
        raise ValueError("parakeet_server binds 127.0.0.1 only")
    engine_lock = threading.Lock()  # one native session; never run it on two threads

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            logger.info("%s " + fmt, self.address_string(), *args)

        def _reply(self, status, payload):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/health":
                self._reply(200, {"status": "ok"})
            else:
                self._reply(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/inference":
                self._reply(404, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length < 0:
                self.close_connection = True
                self._reply(400, {"error": "bad Content-Length"})
                return
            if length > MAX_BODY_BYTES:
                self.close_connection = True
                self._reply(413, {"error": "request too large"})
                return
            body = self.rfile.read(length)
            try:
                parts = parse_multipart(body, self.headers.get("Content-Type", ""))
                audio = parts.get("file")
                if not audio:
                    raise BadRequest("missing file part")
                language = parts.get("language", b"").decode("utf-8", "replace")
                pcm = wav_to_pcm16k(audio)
            except TooLarge as error:
                self._reply(413, {"error": str(error)})
                return
            except BadRequest as error:
                self._reply(400, {"error": str(error)})
                return
            if len(pcm) < MIN_SAMPLES:
                self._reply(200, {"text": ""})
                return
            try:
                with engine_lock:
                    text = engine.transcribe(pcm) or ""
            except Exception as error:  # engine failure must not kill the worker
                logger.exception("inference failed")
                self._reply(500, {"error": f"inference failed: {error}"})
                return
            logger.info("inference: samples=%d requested_language=%s chars=%d",
                        len(pcm), language or "auto", len(text))
            self._reply(200, {"text": text.strip()})

    return http.server.ThreadingHTTPServer((host, port), Handler)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    engine = ParakeetEngine(args.model)
    server = make_server(engine, args.host, args.port)
    logger.info("Parakeet worker listening on %s:%d", args.host, args.port)
    server.serve_forever()


if __name__ == "__main__":
    main()
