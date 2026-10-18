"""Standard-library-only Decky bridge to the plugin's private Python runtime.

Never import the audio engine here: Decky's interpreter may use a different ABI.
"""
import asyncio
import json
import logging
import os
import signal
from pathlib import Path

RPC_METHODS = (
    'set_enabled', 'get_button_config', 'set_share_diagnostics', 'set_haptic_feedback',
    'start_controller_debug', 'resume_controller_debug', 'get_controller_debug',
    'stop_controller_debug', 'upload_controller_debug', 'start_binding_capture',
    'cancel_binding_capture', 'get_binding_capture', 'set_button_config',
    'set_overlay_transcribing_label', 'set_recording_indicator', 'set_confirm_mode',
    'set_sending_mode', 'cancel_draft', 'arm_draft', 'set_review_context',
    'send_armed_draft', 'set_manual_send', 'set_remember_last_channel',
    'set_spoken_punctuation', 'set_transcription_options', 'set_model_size',
    'get_presets', 'get_active_preset', 'set_active_preset', 'start_recording',
    'stop_recording', 'is_recording', 'update_context', 'get_plugin_update',
    'prepare_plugin_update', 'get_status', 'load_model', 'get_last_transcription',
)
LIFECYCLE_METHODS = ('_migration', '_main', '_unload', '_uninstall')


def worker_environment(decky):
    """Keep user/session settings; discard PyInstaller's private runtime paths."""
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(('_PYI_', 'PYTHON')) or key in ('_MEIPASS2', 'TCL_LIBRARY', 'TK_LIBRARY'):
            env.pop(key, None)
    original = env.pop('LD_LIBRARY_PATH_ORIG', None)
    env.pop('LD_LIBRARY_PATH', None)
    if original:
        env['LD_LIBRARY_PATH'] = original
    for name in ('DECKY_USER_HOME', 'DECKY_SETTINGS_DIR', 'DECKY_PLUGIN_SETTINGS_DIR',
                 'DECKY_PLUGIN_RUNTIME_DIR', 'DECKY_PLUGIN_LOG_DIR', 'DECKY_HOME', 'DECKY_USER'):
        value = getattr(decky, name, None)
        if value is not None:
            env[name] = str(value)
    return env


class RuntimeBridge:
    def __init__(self, plugin_path, decky):
        self.root = Path(plugin_path)
        self.decky = decky
        self.logger = getattr(decky, 'logger', logging.getLogger('decktation.runtime'))
        self.process = None
        self.reader = self.logs = None
        self.pending = {}
        self.sequence = 0
        self.lock = asyncio.Lock()
        self.ready = None
        self.failure = None
        self.closing = False

    def _fail(self, reason):
        self.failure = 'Decktation runtime unavailable: ' + str(reason)
        self.logger.error(self.failure)
        for future in list(self.pending.values()):
            if not future.done():
                future.set_exception(RuntimeError(self.failure))
        if self.ready is not None and not self.ready.done():
            self.ready.set_exception(RuntimeError(self.failure))

    async def _read_responses(self):
        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    if not self.closing:
                        self._fail('the private Python process exited; reload the plugin.')
                    return
                message = json.loads(line)
                if message.get('ready') is True:
                    if not self.ready.done():
                        self.ready.set_result(True)
                    continue
                if 'startup_error' in message:
                    self._fail(message['startup_error'])
                    return
                future = self.pending.get(message.get('id'))
                if future is not None and not future.done():
                    if 'error' in message:
                        future.set_exception(RuntimeError(message['error']))
                    else:
                        future.set_result(message.get('result'))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if not self.closing:
                self._fail(error)

    async def _read_logs(self):
        while True:
            line = await self.process.stderr.readline()
            if not line:
                return
            self.logger.info('[runtime] %s', line.decode('utf-8', 'replace').rstrip())

    async def _ensure_started(self):
        async with self.lock:
            if self.failure:
                raise RuntimeError(self.failure)
            if self.process is not None:
                return
            interpreter = self.root / 'bin/runtime/bin/python3.11'
            worker = self.root / 'bin/runtime_worker.py'
            if not interpreter.is_file() or not worker.is_file():
                self._fail('the packaged Python runtime is missing. Reinstall the complete plugin ZIP.')
                raise RuntimeError(self.failure)
            self.ready = asyncio.get_running_loop().create_future()
            try:
                self.process = await asyncio.create_subprocess_exec(
                    str(interpreter), '-I', '-u', str(worker),
                    env=worker_environment(self.decky), cwd=str(self.root),
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE, limit=8 * 1024 * 1024,
                    start_new_session=True,
                )
                self.reader = asyncio.create_task(self._read_responses())
                self.logs = asyncio.create_task(self._read_logs())
                await asyncio.wait_for(asyncio.shield(self.ready), 30)
            except Exception as error:
                self._fail(error)
                # Consume a startup exception even if a timeout won the race.
                if self.ready.done() and not self.ready.cancelled():
                    self.ready.exception()
                await self.close()
                raise RuntimeError(self.failure) from error

    async def call(self, method, *args, **kwargs):
        try:
            if method not in RPC_METHODS + LIFECYCLE_METHODS:
                raise ValueError('Unknown runtime method')
            if self.closing:
                raise RuntimeError('Decktation is stopping')
            await self._ensure_started()
            if self.failure:
                raise RuntimeError(self.failure)
            self.sequence += 1
            request_id = self.sequence
            future = asyncio.get_running_loop().create_future()
            self.pending[request_id] = future
            try:
                message = json.dumps({'id': request_id, 'method': method,
                                      'args': args, 'kwargs': kwargs}, ensure_ascii=False)
                self.process.stdin.write((message + '\n').encode('utf-8'))
                await self.process.stdin.drain()
                # Model download/loading may legitimately take several minutes.
                timeout = 15 if method == 'get_status' else 600
                return await asyncio.wait_for(future, timeout)
            finally:
                self.pending.pop(request_id, None)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            return {'success': False, 'service_ready': False,
                    'error': str(error) or 'Decktation runtime request timed out.'}

    async def close(self):
        self.closing = True
        process = self.process
        if process is not None:
            if process.stdin:
                process.stdin.close()
            try:
                await asyncio.wait_for(process.wait(), 5)
            except asyncio.TimeoutError:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(process.wait(), 2)
                except asyncio.TimeoutError:
                    os.killpg(process.pid, signal.SIGKILL)
                    await process.wait()
            # The worker may have crashed before cleaning up its native children.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        for task in (self.reader, self.logs):
            if task is not None and not task.done():
                task.cancel()
        await asyncio.gather(*(t for t in (self.reader, self.logs) if t is not None), return_exceptions=True)
        for future in list(self.pending.values()):
            if not future.done():
                future.set_exception(RuntimeError('Decktation is stopping'))


class Plugin:
    """Decky API v1 facade. All engine calls stay in the private interpreter."""
    def __init__(self):
        try:
            import decky
        except ImportError:
            import decky_plugin as decky
        self.bridge = RuntimeBridge(os.environ['DECKY_PLUGIN_DIR'], decky)

    async def _migration(self):
        return await self.bridge.call('_migration')

    async def _main(self):
        result = await self.bridge.call('_main')
        if isinstance(result, dict) and result.get('success') is False:
            self.bridge._fail(result.get('error', 'Engine initialization failed'))
        return result

    async def _unload(self):
        try:
            if self.bridge.process is not None and not self.bridge.failure:
                await asyncio.wait_for(self.bridge.call('_unload'), 5)
        finally:
            await self.bridge.close()

    async def _uninstall(self):
        try:
            if self.bridge.process is not None and not self.bridge.failure and not self.bridge.closing:
                await asyncio.wait_for(self.bridge.call('_uninstall'), 5)
        finally:
            await self.bridge.close()

    def __getattr__(self, name):
        if name not in RPC_METHODS:
            raise AttributeError(name)
        async def forwarded(*args, **kwargs):
            return await self.bridge.call(name, *args, **kwargs)
        return forwarded
