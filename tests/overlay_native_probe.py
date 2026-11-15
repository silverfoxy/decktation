"""Run under xvfb-run to verify the live GTK overlay against real X11 properties."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from Xlib import X, display

os.environ['GDK_BACKEND'] = 'x11'
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend/src'))
with tempfile.TemporaryDirectory(prefix='decktation-overlay-check-') as folder:
    state = Path(folder) / 'state'
    (state.parent / 'ack').mkdir()
    state.write_text(json.dumps({'mode': 'review', 'id': 'draft', 'text': 'Hello', 'binding': 'L2+R2+X'}))
    sys.argv = ['recording_overlay.py', str(state), str(os.getpid())]
    spec = importlib.util.spec_from_file_location('tested_overlay', 'backend/src/recording_overlay.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.Gtk.init_check([])
    window = module.Indicator()
    xdisplay = display.Display()

    def assert_mapped(expected):
        module.Gdk.Display.get_default().sync()
        xid = module.GdkX11.X11Window.get_xid(window.get_window())
        native = xdisplay.create_resource_object('window', xid)
        mapped = native.get_attributes().map_state
        assert mapped == (X.IsViewable if expected else X.IsUnmapped), mapped
        # Gamescope can select unmapped external overlays and retain their last
        # frame. Map state alone does not prove that a hidden overlay is gone.
        overlay = native.get_full_property(xdisplay.intern_atom('GAMESCOPE_EXTERNAL_OVERLAY'), X.AnyPropertyType)
        assert overlay is not None and list(overlay.value) == [int(expected)], overlay
        opacity = native.get_full_property(xdisplay.intern_atom('_NET_WM_WINDOW_OPACITY'), X.AnyPropertyType)
        if expected:
            assert opacity is None or list(opacity.value) == [0xffffffff], opacity
        else:
            assert opacity is not None and list(opacity.value) == [0], opacity

    assert_mapped(False)
    window.tick()
    assert_mapped(True)
    for app in [570, 769]:
        subprocess.run(['xprop', '-root', '-f', 'GAMESCOPE_FOCUSED_APP', '32c', '-set', 'GAMESCOPE_FOCUSED_APP', str(app)], check=True)
        actual = window.focused_app()
        assert actual == app, (actual, app)
        surface = module.cairo.ImageSurface(module.cairo.FORMAT_ARGB32, 1280, 800)
        window.draw_indicator(None, module.cairo.Context(surface))
        status = json.loads((state.parent / 'ack' / 'status').read_text())
        assert status['focus_app'] == app and status['ready'] is True and status['id'] == 'draft', status
        assert not (state.parent / 'ack' / 'status.new').exists()
    for mode in ('compact', 'transcribing'):
        window.mode = mode
        surface = module.cairo.ImageSurface(module.cairo.FORMAT_ARGB32, 1280, 800)
        window.draw_indicator(None, module.cairo.Context(surface))
        surface.flush()
        assert any(surface.get_data()), f'{mode} overlay must paint visible pixels'
    # Hiding must unmap the X window, including automatic result expiry. Reuse
    # the same realized window so its overlay property and input shape survive.
    native_window = window.get_window()
    for payload, visible in [
        ({'mode': 'hidden'}, False),
        ({'mode': 'compact'}, True),
        ({'mode': 'transcribing'}, True),
        ({'mode': 'result', 'message': 'Sent', 'expires': 0}, False),
        ({'mode': 'review', 'id': 'again', 'text': 'Hello'}, True),
        ({'mode': 'hidden'}, False),
    ]:
        state.write_text(json.dumps(payload))
        window.tick()
        assert_mapped(visible)
        assert window.get_window() == native_window
    # Exercise the real GLib timer: Cancelled is initially visible, then expires
    # without a new state-file write or a manual tick call.
    result = {'mode': 'result', 'message': 'Cancelled', 'expires': module.time.time() + 0.15}
    state.write_text(json.dumps(result))
    window.tick()
    assert_mapped(True)
    loop = module.GLib.MainLoop()
    module.GLib.timeout_add(300, lambda: (loop.quit(), False)[1])
    loop.run()
    assert state.read_text() == json.dumps(result)
    assert window.mode == 'hidden'
    assert_mapped(False)
    window.close_focus_connection()
    xdisplay.close()
    print('Real GTK/X11 check passed: map/unmap lifecycle, focus IDs, and atomic acknowledgments.')
