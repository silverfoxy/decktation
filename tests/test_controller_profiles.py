"""Profiles extend discovery/readers without model branches in the listener."""
from dataclasses import replace
import os

import pytest
import controller_profiles as profiles
from controller_listener import controller_details


def test_new_profile_discovers_and_reads_without_listener_changes(monkeypatch, tmp_path):
    profile = replace(profiles.PROFILES_BY_KIND['legion_go_s'], kind='test_pad',
                      vendor=0x1234, products=(0x5678,), usb_interface=None,
                      buttons=frozenset({'A'}), report_size=8,
                      decode=lambda report: {'A': report[0] == 1})
    device = tmp_path / 'hidraw0' / 'device'
    device.mkdir(parents=True)
    (device / 'uevent').write_text('HID_ID=0003:00001234:00005678\n')
    monkeypatch.setattr(profiles, 'PROFILES', (profile,))
    monkeypatch.setitem(profiles.PROFILES_BY_KIND, profile.kind, profile)
    monkeypatch.setattr(profiles.glob, 'glob', lambda _: ['/dev/hidraw0'])
    assert list(profiles.find_hidraw(str(tmp_path))) == [('/dev/hidraw0', 'test_pad')]
    opened = []
    monkeypatch.setattr(profiles.os, 'open', lambda path, flags: opened.append(flags) or 42)
    monkeypatch.setattr(profiles.os, 'read', lambda fd, size: bytes([1]) + bytes(size - 1))
    reader = profiles.HidGamepad('/dev/hidraw0', profile)
    assert opened == [os.O_RDONLY | os.O_NONBLOCK]
    assert list(reader.read_states()) == [{'A': True}]
    assert controller_details(reader, profile.kind)['supported_buttons'] == ['A']


@pytest.mark.parametrize('kind', tuple(profiles.PROFILES_BY_KIND))
def test_reader_handles_eof_and_profile_access(monkeypatch, kind):
    profile = profiles.PROFILES_BY_KIND[kind]
    opened = []
    monkeypatch.setattr(profiles.os, 'open', lambda path, flags: opened.append(flags) or 42)
    monkeypatch.setattr(profiles.os, 'read', lambda fd, size: b'')
    reader = profiles.HidGamepad('/dev/hidraw0', profile)
    assert opened == [profile.access | os.O_NONBLOCK]
    assert reader.supported_buttons == set(profile.buttons)
    with pytest.raises(OSError, match='disconnected'):
        list(reader.read_states())


def test_non_controller_interface_cannot_match_legion_profile(tmp_path):
    profile = profiles.PROFILES_BY_KIND['legion_go_s']
    properties = {'HID_ID': '0003:00001A86:0000E310'}
    (tmp_path / 'bInterfaceNumber').write_text('02\n')
    (tmp_path / 'device').mkdir()
    assert not profile.matches(properties, str(tmp_path / 'device'))
