"""Test-only JSON-lines bridge: real lifecycle/IPC, deterministic input replay (no hardware)."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend' / 'src'))
import controller_listener
from controller_debug_session import ControllerDebugSession

with tempfile.TemporaryDirectory(prefix='controller-debug-contract-') as directory:
    now = [100.0]
    controller_listener.CONFIG_DIR = directory
    reader = controller_listener.ControllerDebug(['L1'], clock=lambda: now[0])
    owner = ControllerDebugSession(directory, clock=lambda: now[0])
    reader.refresh()
    for line in sys.stdin:
        command = json.loads(line)
        method, args = command['method'], command.get('args', [])
        if method == 'advance':
            now[0] += args[0]
            active = reader.refresh()
            if active and reader.terminal_pending:
                reader.finish_if_drained(pending=False)
            result = {'advanced': True}
        elif method == 'input':
            reader.device('replayed-controller', 'accepted', keys=[0x130])
            reader.key('replayed-controller', 0x130, 1, 'A', now[0])
            reader.refresh()
            result = {'replayed': True}
        elif method == 'start':
            result = owner.start({'os_id': 'fixture-os', 'kernel_release': 'fixture-kernel'})
        elif method == 'resume':
            result = owner.resume()
        elif method == 'get':
            result = owner.get(*args)
        elif method == 'stop':
            result = owner.stop(*args)
        else:
            raise AssertionError(method)
        print(json.dumps(result), flush=True)
