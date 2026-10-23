"""Reproduce chat-open/insert races without asserting the game's private UI state."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

import pytest
from wow_voice_chat import WoWVoiceChat

PRESETS = json.loads((Path(__file__).parents[1] / 'defaults/game_presets.json').read_text())
ENTER = ["key", "28:1", "28:0"]
PASTE = ["key", "29:1", "47:1", "47:0", "29:0"]


@pytest.mark.parametrize('preset_name', ['wow', 'guildwars2'])
@pytest.mark.parametrize('mode', ['paste', 'ydotool'])
def test_chat_open_has_bounded_settle_time_before_text_insertion(preset_name, mode):
    """An immediate key after Enter can reach gameplay before chat takes focus."""
    events = []
    preset = PRESETS[preset_name]
    service = WoWVoiceChat(preset=preset, lazy_load=True, text_insertion_mode=mode)

    def run(args, **kwargs):
        events.append(('key', args[1:]))
        return MagicMock(returncode=0)

    @contextmanager
    def temporary_clipboard(text, plugin_dir):
        yield {}

    with patch('wow_voice_chat.os.path.exists', return_value=True), \
         patch('wow_voice_chat.subprocess.run', side_effect=run), \
         patch('wow_voice_chat.temporary_clipboard', side_effect=temporary_clipboard), \
         patch('wow_voice_chat.time.sleep', side_effect=lambda seconds: events.append(('wait', seconds))):
        assert service.send_to_wow_chat('hello', channel='say')

    assert events[0] == ('key', ENTER)
    assert events[1][0] == 'wait' and 0.15 <= events[1][1] <= 1.0
    assert events[2][0] == 'key'
    assert events[2][1] == (PASTE if mode == 'paste' else
                            ['type', '-d', '1', '-H', '0', '-f', '-'])


def test_generic_focused_field_never_waits_for_chat_or_presses_enter():
    events = []
    svc = WoWVoiceChat(preset=PRESETS['generic'], lazy_load=True,
                       text_insertion_mode='ydotool')
    with patch('wow_voice_chat.os.path.exists', return_value=True), \
         patch('wow_voice_chat.subprocess.run', side_effect=lambda args, **kw: events.append(args[1:]) or MagicMock(returncode=0)), \
         patch('wow_voice_chat.time.sleep', side_effect=AssertionError('no chat to open')):
        assert svc.send_to_wow_chat('hello')
    assert events == [['type', '-d', '1', '-H', '0', '-f', '-']]
