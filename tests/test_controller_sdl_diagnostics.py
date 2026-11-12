import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from controller_debug_report import InputReport, collect_runtime_metadata, sanitize_report
from controller_sdl_diagnostics import hint_evidence, sanitize_sdl


def test_hint_filters_exclude_files_mappings_and_arbitrary_strings():
    ignore = 'SDL_GAMECONTROLLER_IGNORE_DEVICES'
    hints = {
        ignore: hint_evidence(ignore, '0x17EF/0x6182,PRIVATE,/home/private/filter'),
        'SDL_GAMECONTROLLER_IGNORE_DEVICES_EXCEPT': hint_evidence(
            'SDL_GAMECONTROLLER_IGNORE_DEVICES_EXCEPT', '@/home/private/filters'),
        'SDL_GAMECONTROLLERCONFIG': hint_evidence('SDL_GAMECONTROLLERCONFIG', 'PRIVATE mapping'),
        'SDL_JOYSTICK_HIDAPI': hint_evidence('SDL_JOYSTICK_HIDAPI', '1'),
        'SDL_JOYSTICK_HIDAPI_STEAM': hint_evidence('SDL_JOYSTICK_HIDAPI_STEAM', None),
        'SECRET': {'state': 'PRIVATE'},
    }
    value = sanitize_sdl({'version': 3004018, 'hints': hints, 'path': 'PRIVATE'})
    assert value['hints'][ignore] == {'state': 'list', 'devices': ['0x17ef/0x6182'],
                                     'truncated': False, 'invalid': True}
    assert value['hints']['SDL_GAMECONTROLLER_IGNORE_DEVICES_EXCEPT'] == {'state': 'file'}
    assert value['hints']['SDL_GAMECONTROLLERCONFIG'] == {'state': 'set'}
    assert value['hints']['SDL_JOYSTICK_HIDAPI'] == {'state': '1'}
    assert value['hints']['SDL_JOYSTICK_HIDAPI_STEAM'] == {'state': 'unset'}
    assert 'PRIVATE' not in json.dumps(value) and '/home/' not in json.dumps(value)
    assert sanitize_sdl(value) == value


def test_sdl_evidence_is_bounded_and_resanitized_for_upload():
    ignore = 'SDL_GAMECONTROLLER_IGNORE_DEVICES'
    report = InputReport('capture', 0, ['L1'])
    report.input_backend = 'sdl'
    report.sdl = {'hints': {ignore: hint_evidence(ignore, ','.join(['0x045e/0x02e3'] * 1000))},
                  'joystick_count': 1000, 'gamepad_count': 2, 'version': 3004018}
    report.device('private', 'open_failed', {'sdl_error': 'permission_denied', 'sdl_is_gamepad': True})
    result = report.snapshot(1)
    assert len(result['sdl']['hints'][ignore]['devices']) == 16
    assert result['sdl']['hints'][ignore]['truncated'] is True
    assert result['devices'][0]['sdl_error'] == 'permission_denied'
    assert sanitize_report(result) == result
    assert len(json.dumps(result).encode()) <= 32768


@pytest.mark.parametrize('bad', [[], {}, None, 12])
def test_untrusted_sdl_fields_cannot_crash_or_escape_sanitizer(bad):
    result = sanitize_report({'input_backend': 'sdl', 'sdl': {
        'version': bad, 'hints': {'SDL_JOYSTICK_HIDAPI': {'state': bad}}},
        'devices': [{'source': 'source_1', 'sdl_error': bad}]})
    assert result['sdl']['hints'] == {}
    assert 'sdl_error' not in result['devices'][0]


def test_inputplumber_version_is_optional_and_strictly_parsed(monkeypatch):
    import controller_debug_report as module
    probe = Mock(return_value=SimpleNamespace(returncode=0, stdout='inputplumber v0.78.0\n'))
    monkeypatch.setattr(module.subprocess, 'run', probe)
    assert collect_runtime_metadata('test')['inputplumber_version'] == 'v0.78.0'
    assert probe.call_args.kwargs['timeout'] == 1
    probe.return_value.stdout = 'inputplumber v0.78.0 /home/PRIVATE'
    assert 'inputplumber_version' not in collect_runtime_metadata('test')
    probe.side_effect = FileNotFoundError
    assert 'inputplumber_version' not in collect_runtime_metadata('test')
