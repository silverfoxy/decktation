"""Tests for the opt-in remembered chat channel / command behavior."""

from wow_voice_chat import WoWVoiceChat


PRESET = {
    "default_command": "/s ",
    "commands": {"/s ": "say", "/p ": "party", "/raid ": "raid", "": "type"},
}


def test_unprefixed_text_uses_last_channel_when_enabled():
    service = WoWVoiceChat(preset=PRESET, lazy_load=True, remember_last_channel=True,
                           last_channel="/p ")
    assert service.parse_channel_and_text("let's go") == ("/p ", "let's go")


def test_spoken_channel_replaces_remembered_channel():
    remembered = []
    service = WoWVoiceChat(preset=PRESET, lazy_load=True, remember_last_channel=True,
                           last_channel="/p ", channel_rememberer=remembered.append)
    service.send_to_wow_chat("raid stack on me")
    assert service.last_channel == "/raid "
    assert remembered == ["/raid "]


def test_remembered_channel_is_not_used_when_disabled():
    service = WoWVoiceChat(preset=PRESET, lazy_load=True, remember_last_channel=False,
                           last_channel="/p ")
    assert service.parse_channel_and_text("hello") == ("/s ", "hello")
