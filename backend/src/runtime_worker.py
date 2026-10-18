"""Private Python process: JSON RPC on stdin/stdout, engine logs on stderr."""
import asyncio
import json
import logging
import os
import signal
import sys
import types
from pathlib import Path

# -I ignores PYTHONPATH and the script directory. Add only packaged sources.
backend = Path(__file__).resolve().parent
sys.path.insert(0, str(backend))
protocol = sys.stdout
sys.stdout = sys.stderr
logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                    format='%(levelname)s %(name)s: %(message)s')


def reply(message):
    protocol.write(json.dumps(message, ensure_ascii=False) + '\n')
    protocol.flush()


def decky_shim():
    # The backend only needs paths and logging, not Decky's internal modules.
    module = types.ModuleType('decky')
    module.logger = logging.getLogger('decktation.engine')
    for name, value in os.environ.items():
        if name.startswith('DECKY_'):
            setattr(module, name, value)
    settings = os.environ.get('DECKY_SETTINGS_DIR') or os.environ.get('DECKY_PLUGIN_SETTINGS_DIR')
    if settings:
        module.DECKY_SETTINGS_DIR = settings
    sys.modules['decky'] = sys.modules['decky_plugin'] = module


async def serve(plugin):
    from runtime_proxy import RPC_METHODS, LIFECYCLE_METHODS
    running = set()
    unloaded = False
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stopping.set)
    reader = asyncio.StreamReader(limit=8 * 1024 * 1024)
    transport, _ = await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin)

    async def dispatch(request):
        nonlocal unloaded
        request_id = request.get('id')
        try:
            method = request['method']
            if method not in RPC_METHODS + LIFECYCLE_METHODS:
                raise ValueError('Unknown runtime method')
            if method in ('_unload', '_uninstall'):
                unloaded = True
            result = await getattr(plugin, method)(*request.get('args', []), **request.get('kwargs', {}))
            if method == '_main' and type(plugin).voice_service is None:
                raise RuntimeError('The dictation engine failed to initialize. Check the plugin log.')
            reply({'id': request_id, 'result': result})
        except Exception as error:
            logging.exception('Runtime request failed: %s', request.get('method'))
            reply({'id': request_id, 'error': str(error)})

    reply({'ready': True})
    try:
        while not stopping.is_set():
            read = asyncio.create_task(reader.readline())
            stop = asyncio.create_task(stopping.wait())
            done, _ = await asyncio.wait((read, stop), return_when=asyncio.FIRST_COMPLETED)
            stop.cancel()
            if stopping.is_set():
                read.cancel()
                await asyncio.gather(read, stop, return_exceptions=True)
                break
            line = read.result()
            await asyncio.gather(stop, return_exceptions=True)
            if not line:
                break
            request = json.loads(line)
            task = asyncio.create_task(dispatch(request))
            running.add(task)
            task.add_done_callback(running.discard)
    finally:
        transport.close()
        if not unloaded:
            try:
                await asyncio.wait_for(plugin._unload(), 5)
            except Exception:
                logging.exception('Runtime cleanup failed')
        for task in list(running):
            task.cancel()
        await asyncio.gather(*running, return_exceptions=True)


def main():
    decky_shim()
    try:
        import decktation_backend
        if decktation_backend.WoWVoiceChat is None:
            raise RuntimeError('Cannot import the packaged audio dependencies; reinstall the complete plugin ZIP.')
        if '--check' in sys.argv:
            import numpy, sounddevice, ssl, ctypes, certifi
            reply({'python': sys.version.split()[0], 'numpy': numpy.__version__,
                   'sounddevice': sounddevice.__version__, 'ssl': ssl.OPENSSL_VERSION,
                   'certifi': Path(certifi.where()).is_file()})
            return
        asyncio.run(serve(decktation_backend.Plugin()))
    except Exception as error:
        logging.exception('Private runtime startup failed')
        reply({'startup_error': str(error)})
        raise SystemExit(1)


if __name__ == '__main__':
    main()
