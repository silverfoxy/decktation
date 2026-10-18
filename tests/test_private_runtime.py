"""Real pipe/process tests for the ABI-independent Decky facade."""
import ast
import asyncio
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend/src'))
from runtime_proxy import RuntimeBridge, RPC_METHODS, worker_environment


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    backend = tmp_path / 'bin'
    (backend / 'runtime/bin').mkdir(parents=True)
    (backend / 'runtime/bin/python3.11').symlink_to(sys.executable)
    for name in ('runtime_proxy.py', 'runtime_worker.py'):
        shutil.copy2(ROOT / 'backend/src' / name, backend / name)
    (backend / 'decktation_backend.py').write_text('''
import asyncio, os
from pathlib import Path
WoWVoiceChat = object
print('Engine log, not a JSON response')
class Plugin:
    voice_service = None
    async def _migration(self): pass
    async def _main(self):
        type(self).voice_service = object()
    async def get_status(self):
        return {'success': True, 'service_ready': True, 'home': os.environ['DECKY_USER_HOME']}
    async def update_context(self, context):
        await asyncio.sleep(context.get('delay', 0))
        return {'success': True, 'context': context}
    async def load_model(self):
        await asyncio.sleep(0.1)
        return {'success': True}
    async def set_model_size(self, modelSize):
        if modelSize == 'crash': os._exit(9)
        raise RuntimeError('expected engine error')
    async def _unload(self):
        Path(os.environ['DECKY_PLUGIN_DIR'], 'unloaded').write_text('clean')
    async def _uninstall(self): await self._unload()
''')
    monkeypatch.setenv('DECKY_PLUGIN_DIR', str(tmp_path))
    decky = types.SimpleNamespace(logger=logging.getLogger('test.runtime'),
                                  DECKY_USER_HOME='/custom/user', DECKY_SETTINGS_DIR=str(tmp_path / 'settings'))
    return tmp_path, decky


def test_bridge_preserves_concurrency_unicode_settings_and_cleanup(runtime):
    root, decky = runtime
    async def run():
        bridge = RuntimeBridge(root, decky)
        try:
            await bridge.call('_migration')
            await bridge.call('_main')
            model = asyncio.create_task(bridge.call('load_model'))
            status, context = await asyncio.gather(bridge.call('get_status'), bridge.call('update_context', {'text': 'Mañana 漢字 😀'}))
            assert status['home'] == '/custom/user'
            assert status['service_ready']
            assert context['context']['text'] == 'Mañana 漢字 😀'
            assert not model.done(), 'status polling must not wait for inference/model loading'
            assert (await model)['success']
            assert not (await bridge.call('set_model_size', 'bad'))['success']
            assert (await bridge.call('get_status'))['success'], 'method failures must not kill the engine'
            await bridge.call('_unload')
        finally:
            await bridge.close()
        assert bridge.process.returncode == 0
        assert (root / 'unloaded').read_text() == 'clean'
    asyncio.run(run())


def test_worker_crash_and_missing_runtime_return_actionable_status(runtime):
    root, decky = runtime
    async def run():
        bridge = RuntimeBridge(root, decky)
        await bridge.call('_main')
        crashed = await bridge.call('set_model_size', 'crash')
        assert not crashed['success']
        status = await bridge.call('get_status')
        assert not status['service_ready'] and 'exited' in status['error']
        await bridge.close()
        missing = RuntimeBridge(root / 'missing', decky)
        status = await missing.call('get_status')
        assert not status['success'] and 'complete plugin ZIP' in status['error']
        await missing.close()
    asyncio.run(run())


def test_missing_native_dependencies_and_failed_initialization_do_not_hang(runtime):
    root, decky = runtime
    backend = root / 'bin/decktation_backend.py'
    backend.write_text('WoWVoiceChat = None\n')
    async def run():
        bridge = RuntimeBridge(root, decky)
        result = await bridge.call('get_status')
        assert not result['success'] and 'audio dependencies' in result['error']
        await bridge.close()
    asyncio.run(run())


def test_parent_pipe_closure_unloads_worker(runtime):
    root, decky = runtime
    async def run():
        bridge = RuntimeBridge(root, decky)
        await bridge.call('_main')
        await bridge.close()
        assert (root / 'unloaded').exists()
    asyncio.run(run())


def test_bridge_interface_covers_backend_and_has_no_native_imports():
    backend = ast.parse((ROOT / 'backend/src/decktation_backend.py').read_text())
    plugin = next(node for node in backend.body if isinstance(node, ast.ClassDef) and node.name == 'Plugin')
    methods = {node.name for node in plugin.body if isinstance(node, ast.AsyncFunctionDef) and not node.name.startswith('_')}
    assert set(RPC_METHODS) == methods
    source = (ROOT / 'main.py').read_text()
    assert 'from runtime_proxy import Plugin' in source
    proxy = ast.parse((ROOT / 'backend/src/runtime_proxy.py').read_text())
    imports = {node.names[0].name.split('.')[0] for node in ast.walk(proxy) if isinstance(node, ast.Import)}
    assert not imports & {'numpy', 'sounddevice', 'cffi', 'decktation_backend'}


def test_frozen_runtime_environment_does_not_leak(monkeypatch):
    monkeypatch.setenv('_PYI_APPLICATION_HOME_DIR', '/tmp/_MEIbad')
    monkeypatch.setenv('PYTHONHOME', '/bad/python')
    monkeypatch.setenv('PYTHONPATH', '/bad/packages')
    monkeypatch.setenv('LD_LIBRARY_PATH', '/tmp/_MEIbad')
    monkeypatch.setenv('LD_LIBRARY_PATH_ORIG', '/original/libs')
    env = worker_environment(types.SimpleNamespace(DECKY_USER_HOME='/new/user'))
    assert not any(k.startswith(('_PYI_', 'PYTHON')) for k in env)
    assert env['LD_LIBRARY_PATH'] == '/original/libs'
    assert env['DECKY_USER_HOME'] == '/new/user'


def test_initialization_failure_is_visible_in_facade_status(runtime, monkeypatch):
    root, decky = runtime
    backend = root / 'bin/decktation_backend.py'
    source = backend.read_text().replace('type(self).voice_service = object()', 'pass')
    backend.write_text(source)
    monkeypatch.setitem(sys.modules, 'decky', decky)
    from runtime_proxy import Plugin
    async def run():
        plugin = Plugin()
        try:
            result = await plugin._main()
            assert not result['success']
            status = await plugin.get_status()
            assert not status['success'] and not status['service_ready']
            assert 'initialize' in status['error']
        finally:
            await plugin._unload()
    asyncio.run(run())
