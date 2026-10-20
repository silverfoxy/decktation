"""Synthetic SDL checks exercise actual C ABI/events without physical hardware."""
import ctypes as C
import ctypes.util
import importlib.util
from pathlib import Path
import shutil
import subprocess

import pytest
from sdl_gamepad import SdlGamepads, Event, ButtonEvent, AxisEvent

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compare_inputs', ROOT / 'scripts/compare_controller_inputs.py')
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


@pytest.fixture(scope='module')
def virtual_api(tmp_path_factory):
    if not ctypes.util.find_library('SDL3') or not shutil.which('cc') or not shutil.which('pkg-config'):
        pytest.skip('Optional real SDL tests require SDL3 development files and a C compiler')
    flags = subprocess.run(['pkg-config', '--cflags', '--libs', 'sdl3'], capture_output=True, text=True)
    if flags.returncode:
        pytest.skip('SDL3 development files are unavailable')
    library = tmp_path_factory.mktemp('sdl-virtual') / 'fixture.so'
    import shlex
    subprocess.run(['cc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror',
                    str(ROOT / 'tests/sdl_virtual_gamepad.c'), '-o', str(library),
                    *shlex.split(flags.stdout)], check=True, capture_output=True)
    api = C.CDLL(str(library))
    api.test_attach.restype = C.c_uint32
    api.test_button.argtypes, api.test_button.restype = [C.c_int, C.c_bool], C.c_bool
    api.test_axis.argtypes, api.test_axis.restype = [C.c_int, C.c_int], C.c_bool
    api.test_detach.argtypes, api.test_detach.restype = [C.c_uint32], C.c_bool
    return api


@pytest.fixture
def virtual(virtual_api):
    sdl = SdlGamepads(hidapi=False)
    instance = virtual_api.test_attach()
    assert instance
    try:
        yield sdl, virtual_api, instance
    finally:
        virtual_api.test_detach(instance)
        sdl.close()


def test_ctypes_layout_matches_sdl_headers(virtual_api):
    assert C.sizeof(Event) == virtual_api.test_event_size()
    assert ButtonEvent.button.offset == virtual_api.test_button_offset()
    assert AxisEvent.value.offset == virtual_api.test_axis_value_offset()


def test_real_sdl_hotplug_paddles_triggers_and_fast_releases(virtual):
    sdl, api, instance = virtual
    source = f'sdl:{instance}'
    connection = next(record for record in sdl.poll() if record.get('source') == source and record['event'] == 'connected')
    assert connection['identity'] == {'vendor_id': 0x1234, 'product_id': 0x5678}
    assert {'A', 'L1', 'R1', 'L2', 'R2', 'L4', 'R4', 'L5', 'R5'} <= set(connection['supported_buttons'])
    assert 'Left Trackpad' not in connection['supported_buttons']
    assert not any(connection['initial'].values())
    # Both edges enter SDL's queue before Python drains it.
    for index in (0, 9, 10, 16, 17, 18, 19, 20):
        assert api.test_button(index, True)
        assert api.test_button(index, False)
    assert api.test_axis(4, 32767)
    assert api.test_axis(4, -32768)
    records = sdl.poll()
    transitions = [record for record in records if record['event'] == 'transition' and record['source'] == source]
    for button in ('A', 'L1', 'R1', 'L4', 'R4', 'L5', 'R5', 'SDL Touchpad', 'L2'):
        assert [record['pressed'] for record in transitions if record['button'] == button] == [True, False]
    assert any(record['event'] == 'raw_button' for record in records)
    assert api.test_detach(instance)
    assert any(record['event'] == 'disconnected' and record['source'] == source for record in sdl.poll())


def test_summary_does_not_combine_sources_or_count_raw_events_as_actions():
    emitted = []
    observer = comparison.Comparison(['L4', 'R4'], emitted.append, clock=lambda: 1)
    for source in ('sdl:1', 'legacy:/dev/hidraw0'):
        observer.record({'event': 'connected', 'source': source, 'supported_buttons': ['L4', 'R4'], 'initial': {}})
    def edge(source, button, pressed):
        observer.record({'event': 'transition', 'source': source, 'button': button, 'pressed': pressed})
    edge('sdl:1', 'L4', True)
    edge('legacy:/dev/hidraw0', 'R4', True)
    assert all(entry['combo_presses'] == 0 for entry in observer.sources.values())
    edge('sdl:1', 'R4', True)
    edge('sdl:1', 'R4', True)  # repeated state is not another press
    observer.record({'event': 'raw_button', 'source': 'sdl:1', 'button_index': 16, 'pressed': True})
    edge('sdl:1', 'R4', False)
    snapshot = observer.summary()['sources']['sdl:1']
    assert snapshot['combo_presses'] == snapshot['combo_releases'] == 1
    assert snapshot['presses'] == {'L4': 1, 'R4': 1}
    assert snapshot['releases'] == {'R4': 1}
    observer.record({'event': 'disconnected', 'source': 'sdl:1'})
    assert 'sdl:1' not in observer.tracker.sources
    assert observer.summary()['sources']['sdl:1']['disconnects'] == 1


@pytest.mark.parametrize('value', ['nan', 'inf', '-1', '3601'])
def test_duration_is_bounded(value):
    with pytest.raises(SystemExit):
        comparison.arguments(['--seconds', value])


def test_missing_sdl_fails_clearly_without_legacy_readers(capsys):
    assert comparison.main(['--seconds', '0', '--sdl-library', '/does/not/exist']) == 1
    output = capsys.readouterr().out
    assert 'Cannot load SDL 3' in output
    assert '"event": "connected"' not in output


def test_legacy_pipe_delivers_press_release_and_disconnect(monkeypatch):
    import os
    records = []
    reader, writer = os.pipe()
    os.set_blocking(reader, False)
    class Pad:
        fd = reader
        identity = {'bus': 3, 'vendor_id': 0x1234, 'product_id': 0x5678}
        supported_buttons = {'L4', 'R4'}
        def __init__(self, path, profile):
            pass
        def read_states(self):
            payload = os.read(self.fd, 32)
            if not payload:
                raise OSError('disconnected')
            yield {'L4': True, 'R4': True}
            yield {'L4': False, 'R4': False}
        def close(self):
            os.close(self.fd)
    monkeypatch.setattr(comparison, 'find_hidraw', lambda: iter([('/dev/hidraw0', 'legion_go_s')]))
    monkeypatch.setattr(comparison.glob, 'glob', lambda _: [])
    monkeypatch.setattr(comparison, 'HidGamepad', Pad)
    legacy = comparison.LegacyReaders(records.append)
    try:
        legacy.scan()
        os.write(writer, b'synthetic')
        legacy.poll()
        assert [(r['button'], r['pressed']) for r in records if r['event'] == 'transition'] == [
            ('L4', True), ('R4', True), ('L4', False), ('R4', False)]
        os.close(writer)
        writer = None
        legacy.poll()
        assert records[-1]['event'] == 'disconnected'
        assert not legacy.devices
    finally:
        legacy.close()
        if writer is not None:
            os.close(writer)


def test_sdl_off_mode_overrides_inherited_driver_hint(virtual_api, monkeypatch):
    monkeypatch.setenv('SDL_JOYSTICK_HIDAPI_XBOX', '1')
    sdl = SdlGamepads(hidapi=False)
    try:
        assert sdl.hints['SDL_JOYSTICK_HIDAPI_XBOX'] == '0'
    finally:
        sdl.close()
