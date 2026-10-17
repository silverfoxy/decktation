from pathlib import Path
import pytest
from test_deck_artifact import runner


def snapshot(phase='idle'):
    return {'visible': True, 'phase': phase, 'seconds': 28 if phase == 'recording' else None,
            'events': 0, 'native_focus': [{'label': 'capture-region', 'rect': [0, 0, 200, 100]}],
            'controls': {'start': [20, 20], 'stop': [40, 40]}}


def test_smoke_requires_consent_and_runtime_identity(tmp_path):
    r = runner()
    with pytest.raises(ValueError, match='allow-input'):
        r.smoke(None, tmp_path, allow_input=False)
    with pytest.raises(ValueError, match='runtime identity'):
        r.smoke(None, tmp_path, allow_input=True)


def test_scoped_bounded_smoke_success_and_capture_loss(tmp_path):
    r = runner()
    class CDP:
        def __init__(self, lose=False):
            self.phase = 'idle'
            self.lose = lose
            self.keys = []
        def evaluate(self, expression):
            state = snapshot(self.phase)
            if self.lose and self.keys:
                state['visible'] = False
            return state
        def call(self, method, params=None):
            if method == 'Input.dispatchMouseEvent' and params['type'] == 'mouseReleased':
                self.phase = 'recording' if self.phase == 'idle' else 'ready'
            if method == 'Input.dispatchKeyEvent':
                self.keys.append((params['key'], params['type']))
            if method == 'Page.captureScreenshot':
                return {'data': 'iVBORw0KGgo='}
            return {}
    cdp = CDP()
    result = r.smoke(cdp, tmp_path, allow_input=True, allow_unverified_runtime=True, phase_timeout=.2)
    assert result['flow'] == 'passed'
    assert result['verdict'] == 'inconclusive-runtime-identity'
    assert cdp.keys == [(k, t) for k in ('Escape', 'ArrowDown', 'Enter') for t in ('keyDown', 'keyUp')]
    assert (tmp_path / 'baseline.png').exists()
    with pytest.raises(ValueError, match='capture'):
        r.smoke(CDP(lose=True), tmp_path, allow_input=True, allow_unverified_runtime=True, phase_timeout=.1)
