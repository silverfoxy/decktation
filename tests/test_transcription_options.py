import wow_voice_chat
import pytest
from wow_voice_chat import WoWVoiceChat


class FakeWorker:
    def __init__(self, text="hello"):
        self.text = text
        self.calls = []
        self.process = type("Process", (), {"pid": 123})()

    def transcribe(self, audio, language, prompt):
        self.calls.append({"language": language, "prompt": prompt})
        return self.text


class FakeAudio(list):
    dtype = "float32"


def resident_service(text="hello", **kwargs):
    service = WoWVoiceChat(lazy_load=True, **kwargs)
    service.whisper_worker = FakeWorker(text)
    service.inference_device = "cpu"
    service.save_audio_to_wav = lambda *args, **kwargs: None
    service._prepare_audio = lambda audio, sample_rate: FakeAudio([0.0, 0.1])
    return service


def test_transcription_defaults_auto_detect_and_transcribe():
    service = resident_service()

    assert service.transcribe_audio([0.0, 0.1]) == "hello"
    assert service.whisper_worker.calls == [{"language": None, "prompt": ""}]


@pytest.mark.parametrize("source, expected", [
    ("[blank_audio]", ""),
    ("  [BLANK_AUDIO]\n[Music] (laughter)  ", ""),
    ("[silence] [no speech] [applause] [inaudible]", ""),
    ("[music] hello [laughter] there [blank_audio]", "hello there"),
    ("hello[music]there", "hello there"),
    ("Use [party] and (raid) chat", "Use [party] and (raid) chat"),
    ("The music is loud", "The music is loud"),
])
def test_transcription_removes_only_recognized_audio_cues(source, expected):
    service = resident_service(source)
    assert service.transcribe_audio([0.0, 0.1]) == expected


def test_transcription_capitalizes_standalone_i():
    service = resident_service("party i think i'm ready, i really do")

    assert service.transcribe_audio([0.0, 0.1]) == (
        "party I think I'm ready, I really do"
    )


def test_transcription_does_not_change_i_inside_words():
    service = resident_service("i use an iPhone in wiki raids")

    assert service.transcribe_audio([0.0, 0.1]) == "I use an iPhone in wiki raids"


def test_transcription_can_preselect_language():
    service = resident_service(transcription_language="fr")

    assert service.transcribe_audio([0.0, 0.1]) == "hello"
    assert service.whisper_worker.calls == [{"language": "fr", "prompt": ""}]


@pytest.mark.parametrize("source, expected", [
    ("Hello comma how are you question mark", "Hello, how are you?"),
    ("Hello, comma. How are you, question mark?", "Hello, How are you?"),
    ("Ready PERIOD.", "Ready."),
    ("Ready full-stop", "Ready."),
    ("Go exclamation point", "Go!"),
    ("Go exclamation mark!", "Go!"),
    ("Loot colon gold semicolon gems ellipsis", "Loot: gold; gems..."),
    ("Hello comma\nI am ready period", "Hello, I am ready."),
    ("Wait ellipsis question mark", "Wait...?"),
    ("comma", ","),
    ("periodic colonial commas question marks", "periodic colonial commas question marks"),
    ("Already punctuated, correctly?", "Already punctuated, correctly?"),
    ("Привет comma 世界 question mark", "Привет, 世界?"),
])
def test_spoken_punctuation_in_resident_transcription(source, expected):
    service = resident_service(source, spoken_punctuation=True)
    assert service.transcribe_audio([0.0, 0.1]) == expected
    # This feature does not change Whisper's prompt or require a second model.
    assert service.whisper_worker.calls == [{"language": None, "prompt": ""}]


def test_spoken_punctuation_is_optional_and_updates_without_model_reload():
    service = resident_service("A period of time comma")
    assert service.transcribe_audio([0.0, 0.1]) == "A period of time comma"
    worker = service.whisper_worker
    service.spoken_punctuation = True
    assert service.transcribe_audio([0.0, 0.1]) == "A. of time,"
    service.spoken_punctuation = False
    assert service.transcribe_audio([0.0, 0.1]) == "A period of time comma"
    assert service.whisper_worker is worker


def test_spoken_punctuation_respects_language_selection():
    service = resident_service("Hello comma", spoken_punctuation=True,
                               transcription_language="fr")
    assert service.transcribe_audio([0.0, 0.1]) == "Hello comma"
    service.set_transcription_options("en")
    assert service.transcribe_audio([0.0, 0.1]) == "Hello,"
    service.set_transcription_options("auto")
    assert service.transcribe_audio([0.0, 0.1]) == "Hello,"


@pytest.mark.parametrize("prefix", ["", "party ", "party colon "])
def test_casual_chat_preserves_spoken_period_in_review_and_send(prefix):
    service = resident_service(
        prefix + "Ready period.", spoken_punctuation=True, review_mode=True,
        preset={"casual_case": True, "channels": {"say": "/s ", "party": "/p "}},
    )
    text = service.transcribe_audio([0.0, 0.1])
    service.queue_transcription(text)
    draft = service.pending_snapshot()
    assert draft["text"] == "ready."
    sent = []
    service.send_to_wow_chat = lambda message, channel=None: sent.append((message, channel)) or True
    assert service.confirm_pending(draft["id"])
    assert sent == [("ready.", "party" if prefix else "say")]


@pytest.mark.parametrize("source, expected", [
    ("Ready.", "ready"),
    ("Hello comma I am ready.", "hello, I am ready"),
    ("Ready period", "ready."),
    ("Ready full stop.", "ready."),
    ("Wait ellipsis.", "wait..."),
    ("Ready period Go.", "ready. Go"),
])
def test_casual_chat_distinguishes_spoken_and_whisper_periods(source, expected):
    service = resident_service(source, spoken_punctuation=True,
                               preset={"casual_case": True})
    text = service.transcribe_audio([0.0, 0.1])
    assert service.parse_channel_and_text(text)[1] == expected
    # Public previews still serialize as ordinary text.
    import json
    assert json.loads(json.dumps({"text": text}))["text"] == str(text)


def test_spoken_period_provenance_stays_with_each_recording():
    service = resident_service("Ready period", spoken_punctuation=True,
                               preset={"casual_case": True})
    spoken = service.transcribe_audio([0.0, 0.1])
    service.whisper_worker.text = "Ready."
    inferred = service.transcribe_audio([0.0, 0.1])
    service.spoken_punctuation = False
    assert service.parse_channel_and_text(spoken)[1] == "ready."
    assert service.parse_channel_and_text(inferred)[1] == "ready"


@pytest.mark.parametrize("source, expected", [
    ("command gg", "/gg"),
    ("command ready", "/ready"),
    ("Command, GG.", "/gg"),
    ("command whisper Thrall Hello there.", "/whisper Thrall Hello there"),
    ("command period", "/period"),
    ("command 1 hello", "/1 hello"),
    ("command slash gg", "/gg"),
    ("Command, slash GG.", "/gg"),
    ("command slash ready!", "/ready"),
    ("command /gg.", "/gg"),
    ("command slash whisper Thrall Hello there.", "/whisper Thrall Hello there"),
    ("command slash period", "/period"),
    ("command slash 1 hello", "/1 hello"),
])
@pytest.mark.parametrize("spoken_punctuation", [False, True])
def test_explicit_slash_command_transcription(source, expected, spoken_punctuation):
    service = resident_service(source, spoken_punctuation=spoken_punctuation,
                               preset={"casual_case": True})
    text = service.transcribe_audio([0.0, 0.1])
    assert text == expected
    # Routing belongs to the recording even if settings change before sending.
    service.set_transcription_options("fr")
    assert service.parse_channel_and_text(text) == ("command", expected)


@pytest.mark.parametrize("source", [
    "slash gg", "the command slash gg", "command slash", "command slash .",
    "command", "command .", "the command gg", "command gg/ready",
    "command slash gg/ready", "commanding slash gg",
])
def test_only_a_complete_explicit_command_prefix_is_converted(source):
    service = resident_service(source)
    assert service.transcribe_audio([0.0, 0.1]) == source


def test_spoken_command_language_and_argument_punctuation():
    service = resident_service("command slash whisper Thrall Hi comma ready period.",
                               spoken_punctuation=True)
    text = service.transcribe_audio([0.0, 0.1])
    assert text == "/whisper Thrall Hi, ready."
    assert service.parse_channel_and_text(text) == ("command", str(text))
    service.set_transcription_options("fr")
    assert service.transcribe_audio([0.0, 0.1]) == service.whisper_worker.text


def test_non_english_transcription_skips_english_prompt_but_keeps_hotwords():
    service = resident_service(
        transcription_language="fa",
        preset={
            "whisper_prompt": "English-only prompt",
            "hotwords": ["Sylvanas"],
            "context_file": "wow_context.json",
        },
    )
    service.load_context = lambda: True
    service.context = {"zone": "Azeroth", "boss": "Illidan"}

    assert service.transcribe_audio([0.0, 0.1]) == "hello"

    assert service.whisper_worker.calls == [
        {"language": "fa", "prompt": "Sylvanas, Azeroth, Illidan"}
    ]


def test_setting_auto_language_restores_configured_prompt():
    service = WoWVoiceChat(
        lazy_load=True,
        transcription_language="es",
        preset={"whisper_prompt": "Game chat"},
    )

    service.set_transcription_options("auto")

    assert service.transcription_language is None
    assert service.build_prompt_from_context() == ("Game chat", None)


def test_explicit_english_uses_configured_prompt():
    service = WoWVoiceChat(
        lazy_load=True,
        transcription_language="en",
        preset={"whisper_prompt": "Game chat"},
    )

    assert service.build_prompt_from_context() == ("Game chat", None)


def test_model_load_uses_selected_model_size(monkeypatch, tmp_path):
    server = tmp_path / "whisper-server"
    server.touch()
    calls = []
    monkeypatch.setattr(wow_voice_chat, "_whisper_server_path", lambda: server)
    monkeypatch.setattr(WoWVoiceChat, "_vulkan_available", lambda self: False)
    monkeypatch.setattr(
        WoWVoiceChat, "_ensure_whisper_model",
        lambda self: tmp_path / f"ggml-{self.model_size}.bin",
    )
    monkeypatch.setattr(
        wow_voice_chat, "ResidentWhisper",
        lambda binary, model, environment, use_gpu: calls.append(
            (binary, model, use_gpu)
        ) or FakeWorker(),
    )
    service = WoWVoiceChat(lazy_load=True, model_size="small")

    assert service._load_model() is True
    assert calls == [(server, tmp_path / "ggml-small.bin", False)]
    assert service.inference_device == "cpu"


def test_model_load_falls_back_to_cpu_when_vulkan_startup_fails(monkeypatch, tmp_path):
    server = tmp_path / "whisper-server"
    server.touch()
    model = tmp_path / "ggml-base.bin"
    calls = []
    monkeypatch.setattr(wow_voice_chat, "_whisper_server_path", lambda: server)
    monkeypatch.setattr(WoWVoiceChat, "_vulkan_available", lambda self: True)
    monkeypatch.setattr(WoWVoiceChat, "_ensure_whisper_model", lambda self: model)

    def create_worker(binary, selected_model, environment, use_gpu):
        calls.append(use_gpu)
        if use_gpu:
            raise RuntimeError("Vulkan initialization failed")
        return FakeWorker()

    monkeypatch.setattr(wow_voice_chat, "ResidentWhisper", create_worker)
    service = WoWVoiceChat(lazy_load=True)

    assert service._load_model() is True
    assert calls == [True, False]
    assert service.inference_device == "cpu"


def test_set_model_size_reloads_loaded_model(monkeypatch, tmp_path):
    server = tmp_path / "whisper-server"
    server.touch()
    workers = []
    monkeypatch.setattr(wow_voice_chat, "_whisper_server_path", lambda: server)
    monkeypatch.setattr(WoWVoiceChat, "_vulkan_available", lambda self: False)
    monkeypatch.setattr(
        WoWVoiceChat, "_ensure_whisper_model",
        lambda self: tmp_path / f"ggml-{self.model_size}.bin",
    )
    def create_worker(binary, model, environment, use_gpu):
        worker = FakeWorker()
        worker.model = model
        worker.close = lambda: None
        workers.append(worker)
        return worker
    monkeypatch.setattr(wow_voice_chat, "ResidentWhisper", create_worker)
    service = WoWVoiceChat(lazy_load=True, model_size="base")

    assert service._load_model() is True
    assert service.set_model_size("medium") is True

    assert [worker.model.name for worker in workers] == [
        "ggml-base.bin", "ggml-medium.bin"
    ]
