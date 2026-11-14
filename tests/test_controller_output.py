from controller_output import resolve_output
import struct
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
import controller_output as module


def output(path):
    return {'path': path, 'identity': {'bus': 3, 'vendor_id': 0x28de,
                                      'product_id': 0x11ff}}


def test_direct_source_wins_even_with_multiple_outputs():
    first, second = output('/dev/input/event10'), output('/dev/input/event11')
    result = resolve_output(second, [first, second])
    assert result['status'] == 'same_device'
    assert result['target'] == second


def test_single_output_is_labelled_as_fallback_not_proven_pair():
    pad = output('/dev/input/event10')
    result = resolve_output({'path': '/dev/hidraw0'}, [pad])
    assert result['status'] == 'single_candidate'
    assert result['target'] == pad


def test_sdl_source_matches_its_kernel_path_with_multiple_outputs():
    first, second = output('/dev/input/event10'), output('/dev/input/event11')
    source = {'path': 'sdl:42', 'evdev_path': second['path'],
              'identity': {'bus': None, 'vendor_id': 0x28de, 'product_id': 0x11ff}}
    result = resolve_output(source, [first, second])
    assert result['status'] == 'same_device'
    assert result['target'] == second


def test_multiple_outputs_do_not_guess_from_physical_source():
    result = resolve_output({'path': '/dev/hidraw0'},
                            [output('/dev/input/event10'), output('/dev/input/event11')])
    assert result['status'] == 'ambiguous'
    assert result['target'] is None


def test_missing_source_and_missing_outputs_are_distinct():
    assert resolve_output(None, [output('/dev/input/event10')])['target'] is None
    assert resolve_output({'path': '/dev/hidraw0'}, [])['status'] == 'unavailable'


def test_reused_path_with_different_identity_is_not_a_direct_match():
    result = resolve_output({'path': '/dev/input/event10', 'identity': {'bus': 5}},
                            [output('/dev/input/event10'), output('/dev/input/event11')])
    assert result['status'] == 'ambiguous'


@pytest.fixture
def destination(monkeypatch):
    target = output('/dev/input/event10')
    target.update(device_number=3402, inode=123, sysfs_path='/sys/devices/virtual/input/input30')
    target['identity']['hardware_version'] = 1
    fake_os = SimpleNamespace(
        open=lambda *args: 42, close=MagicMock(),
        O_RDWR=module.os.O_RDWR, O_NONBLOCK=module.os.O_NONBLOCK,
        fstat=lambda fd: SimpleNamespace(st_mode=0o020660, st_rdev=3402, st_ino=123),
        path=SimpleNamespace(basename=module.os.path.basename,
                             realpath=lambda path: '/sys/devices/virtual/input/input30'))
    monkeypatch.setattr(module, 'os', fake_os)
    def read(fd, number, size):
        if number == 2:
            return struct.pack('4H', 3, 0x28de, 0x11ff, 1)
        values = {0x21: (304, 305), 0x23: (0, 1)}.get(number, ())
        data = bytearray(size)
        for bit in values:
            data[bit // 8] |= 1 << (bit % 8)
        return data
    monkeypatch.setattr(module, 'ioctl_read', read)
    return {'status': 'single_candidate', 'target': target}


def test_verified_device_is_closed_after_use(destination):
    with module.open_output(destination) as fd:
        assert fd == 42
    module.os.close.assert_called_once_with(42)


@pytest.mark.parametrize('field,value', [('inode', 999), ('device_number', 99),
                                        ('sysfs_path', '/another/device')])
def test_reconnected_device_is_rejected(destination, field, value):
    destination['target'][field] = value
    with pytest.raises(module.ControllerOutputError):
        with module.open_output(destination):
            pytest.fail('must not yield')
    module.os.close.assert_called_once_with(42)


@pytest.mark.parametrize('button,code', [('press_a', 304), ('press_b', 305)])
def test_pulse_releases_when_hold_is_interrupted(monkeypatch, button, code):
    monkeypatch.setattr(module, 'write_json', MagicMock())
    monkeypatch.setattr(module.os, 'readlink', lambda path: '/dev/input/event10')
    monkeypatch.setattr(module, 'ioctl_read', lambda *args: bytes(96))
    packets = []
    monkeypatch.setattr(module.os, 'write', lambda fd, data: packets.append(data) or len(data))
    monkeypatch.setattr(module.time, 'sleep', MagicMock(side_effect=KeyboardInterrupt))
    with pytest.raises(KeyboardInterrupt):
        getattr(module, button)(42)
    assert [module.EVENT.unpack(data[:module.EVENT.size])[3:5] for data in packets] == [(code, 1), (code, 0)]


@pytest.mark.parametrize('button,code', [('press_a', 304), ('press_b', 305)])
def test_held_button_does_not_get_released_by_injection(monkeypatch, button, code):
    data = bytearray(96)
    data[code // 8] = 1 << (code % 8)
    monkeypatch.setattr(module, 'ioctl_read', lambda *args: data)
    write = MagicMock()
    monkeypatch.setattr(module.os, 'write', write)
    with pytest.raises(module.ControllerOutputError, match='held'):
        getattr(module, button)(42)
    write.assert_not_called()


def test_injected_buttons_are_ignored_only_on_destination_during_sequence(monkeypatch):
    monkeypatch.setattr(module, 'read_json', lambda path: {
        'path': '/dev/input/event10', 'until': 101})
    monkeypatch.setattr(module.time, 'monotonic', lambda: 100)
    states = {'A': True, 'B': True, 'L1': True}
    assert module.without_injected_buttons('/dev/input/event10', states) == {'A': False, 'B': False, 'L1': True}
    assert module.without_injected_buttons('/dev/hidraw3', states) == states
    monkeypatch.setattr(module.time, 'monotonic', lambda: 102)
    assert module.without_injected_buttons('/dev/input/event10', states) == states
