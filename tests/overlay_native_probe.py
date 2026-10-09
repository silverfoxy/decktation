"""Run under xvfb-run to verify the live GTK overlay against real X11 properties."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

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
    window.tick()
    for app in [570, 769]:
        subprocess.run(['xprop', '-root', '-f', 'GAMESCOPE_FOCUSED_APP', '32c', '-set', 'GAMESCOPE_FOCUSED_APP', str(app)], check=True)
        actual = window.focused_app()
        assert actual == app, (actual, app)
        surface = module.cairo.ImageSurface(module.cairo.FORMAT_ARGB32, 1280, 800)
        window.draw_indicator(None, module.cairo.Context(surface))
        status = json.loads((state.parent / 'ack' / 'status').read_text())
        assert status['focus_app'] == app and status['ready'] is True and status['id'] == 'draft', status
        assert not (state.parent / 'ack' / 'status.new').exists()
    window.close_focus_connection()
    print('Real GTK/X11 check passed: focus IDs decode correctly and acknowledgments publish atomically.')
