import hashlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import decktation_backend
import wow_voice_chat


def test_parakeet_registry_values():
    model = wow_voice_chat.PARAKEET_MODEL
    assert model["id"] == "parakeet-v3"
    assert model["filename"] == "parakeet-tdt-0.6b-v3-Q8_0.gguf"
    assert model["url"].endswith("/handy-computer/parakeet-tdt-0.6b-v3-gguf/resolve/main/parakeet-tdt-0.6b-v3-Q8_0.gguf")
    assert model["sha256"] == "5859f77944efcd8eafa23a6350731960b2b55b2203df51f319665c807d802cc7"


def test_supported_sizes_keep_whisper_and_add_parakeet():
    assert decktation_backend.SUPPORTED_WHISPER_MODEL_SIZES == {"parakeet-v3", "parakeet-ultra", "base", "small", "medium"}
    assert decktation_backend._normalize_model_size("base") == "base"
    assert decktation_backend._normalize_model_size("Parakeet-V3") == "parakeet-v3"
    assert decktation_backend._normalize_model_size(None) == "base"


def make_service(tmp_path, monkeypatch):
    monkeypatch.setenv("DECKY_USER_HOME", str(tmp_path))
    service = wow_voice_chat.WoWVoiceChat.__new__(wow_voice_chat.WoWVoiceChat)
    service.model_size = "parakeet-v3"
    service.model_cancel_event = MagicMock(); service.model_cancel_event.is_set.return_value = False
    service.model_stage_lock = __import__("threading").Lock()
    service.model_stage = "idle"
    return service


def test_ensure_parakeet_downloads_and_verifies(tmp_path, monkeypatch):
    payload = b"gguf-bytes"
    monkeypatch.setitem(wow_voice_chat.PARAKEET_MODEL, "sha256", hashlib.sha256(payload).hexdigest())
    monkeypatch.setattr(wow_voice_chat, "_download_vulkan_model",
                        lambda url, dest, cancel=None: Path(dest).write_bytes(payload))
    service = make_service(tmp_path, monkeypatch)
    model = service._ensure_parakeet_model()
    assert model == tmp_path / ".cache/decktation/transcribe.cpp/parakeet-tdt-0.6b-v3-Q8_0.gguf"
    assert model.read_bytes() == payload


def test_ensure_parakeet_rejects_bad_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(wow_voice_chat, "_download_vulkan_model",
                        lambda url, dest, cancel=None: Path(dest).write_bytes(b"corrupt"))
    service = make_service(tmp_path, monkeypatch)
    with pytest.raises(RuntimeError, match="checksum"):
        service._ensure_parakeet_model()
    cache = tmp_path / ".cache/decktation/transcribe.cpp"
    assert not any(cache.iterdir())


def test_corrupt_cached_model_is_redownloaded(tmp_path, monkeypatch):
    payload = b"good"
    monkeypatch.setitem(wow_voice_chat.PARAKEET_MODEL, "sha256", hashlib.sha256(payload).hexdigest())
    cache = tmp_path / ".cache/decktation/transcribe.cpp"; cache.mkdir(parents=True)
    (cache / "parakeet-tdt-0.6b-v3-Q8_0.gguf").write_bytes(b"truncated")
    monkeypatch.setattr(wow_voice_chat, "_download_vulkan_model",
                        lambda url, dest, cancel=None: Path(dest).write_bytes(payload))
    service = make_service(tmp_path, monkeypatch)
    assert service._ensure_parakeet_model().read_bytes() == payload


def test_parakeet_environment_points_at_bundle(monkeypatch, tmp_path):
    monkeypatch.setattr(wow_voice_chat, "_plugin_root", lambda: tmp_path)
    env = wow_voice_chat._parakeet_environment()
    assert env["TRANSCRIBE_LIBRARY"] == str(tmp_path / "bin/lib/libtranscribe.so")
    assert env["PYTHONPATH"].split(":")[0] == str(tmp_path / "bin/python")
    assert env["LD_LIBRARY_PATH"].split(":")[0] == str(tmp_path / "bin/lib")


def test_client_error_from_cpu_worker_keeps_worker_loaded():
    import urllib.error
    service = wow_voice_chat.WoWVoiceChat.__new__(wow_voice_chat.WoWVoiceChat)
    service.inference_device = "cpu"
    service.whisper_worker = worker = MagicMock()
    def fail(*_args):
        raise urllib.error.HTTPError("http://127.0.0.1/inference", 413, "too large", {}, None)
    service._transcribe_with_worker = fail
    with pytest.raises(urllib.error.HTTPError):
        service._transcribe_whisper(b"", None, None)
    assert service.whisper_worker is worker


def test_server_error_from_cpu_worker_still_stops_worker():
    import urllib.error
    service = wow_voice_chat.WoWVoiceChat.__new__(wow_voice_chat.WoWVoiceChat)
    service.inference_device = "cpu"
    service.whisper_worker = MagicMock()
    service.whisper_model = None
    def fail(*_args):
        raise urllib.error.HTTPError("http://127.0.0.1/inference", 500, "boom", {}, None)
    service._transcribe_with_worker = fail
    with pytest.raises(urllib.error.HTTPError):
        service._transcribe_whisper(b"", None, None)
    assert service.whisper_worker is None


def test_parakeet_ultra_registry_values():
    model = wow_voice_chat.PARAKEET_MODELS["parakeet-ultra"]
    assert model["filename"] == "parakeet-ultra-Q8_0.gguf"
    assert model["url"].endswith("/handy-computer/parakeet-ultra-gguf/resolve/main/parakeet-ultra-Q8_0.gguf")
    assert model["sha256"] == "007a59761e9258779f189df396b50d12b83bb5b79e66df4b955c230d2f2a0a59"
    assert wow_voice_chat.PARAKEET_MODELS["parakeet-v3"] is wow_voice_chat.PARAKEET_MODEL
    assert decktation_backend._normalize_model_size("parakeet-ultra") == "parakeet-ultra"


def test_ensure_parakeet_uses_selected_variant(tmp_path, monkeypatch):
    payload = b"ultra"
    monkeypatch.setitem(wow_voice_chat.PARAKEET_MODELS["parakeet-ultra"], "sha256", hashlib.sha256(payload).hexdigest())
    seen = []
    def download(url, dest, cancel=None):
        seen.append(url); Path(dest).write_bytes(payload)
    monkeypatch.setattr(wow_voice_chat, "_download_vulkan_model", download)
    service = make_service(tmp_path, monkeypatch)
    service.model_size = "parakeet-ultra"
    model = service._ensure_parakeet_model()
    assert model.name == "parakeet-ultra-Q8_0.gguf"
    assert seen and "parakeet-ultra-gguf" in seen[0]
