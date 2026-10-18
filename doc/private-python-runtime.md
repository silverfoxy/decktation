# Private Python runtime

## Why

Decky 3.3.0 runs the plugin with CPython 3.14. Decktation's native NumPy and
CFFI wheels were built for CPython 3.11. Those extensions cannot be imported
by a different Python ABI, even though their files are present. The first
failure is `No module named '_cffi_backend'`; NumPy would also be incompatible.

The Decky entry point now imports only `runtime_proxy`, which uses the Python
standard library. It starts the bundled CPython 3.11 interpreter as a private
process and forwards the existing RPC methods through local anonymous pipes.
Audio, models, controller state, settings and inference remain owned by the
same engine process. The frontend API and settings files are unchanged.

The worker receives Decky's user/settings paths and forwards logs to Decky's
logger. No Decky-internal Python modules are imported by the private engine.
No ports or network services are added by the bridge. A worker crash or missing
runtime returns an explicit backend error rather than an endless Connecting
status. There is no silent fallback to an incompatible system interpreter.

## Packaging and maintenance

`backend/prepare_runtime.py` downloads a fixed Linux x86_64 CPython build,
verifies its SHA-256 and creates the reduced runtime. The Docker build downloads
matching CPython 3.11 wheels and tests native imports with the shipped
interpreter. The entrypoint copies both into the ZIP. The runtime contains no
pip, development headers, GUI toolkit or test suite; unused duplicate runtime
libraries and debugging symbols are removed.

Python and bundled SSL/security components still need normal security updates.
When upgrading the private interpreter to a new minor version, update the wheel
ABI in the Dockerfile and packaging checks at the same time. Changes to Decky's
plugin API can still require bridge updates; this isolates Python ABI changes,
not arbitrary loader API changes.

Build dependencies and the interpreter are acquired only in the build
environment. The Deck does not install packages or download Python on startup.
The complete ZIP is required; the manual source-install scripts refuse missing
runtime assets before changing an installation.

## Checks

- `pytest tests/test_private_runtime.py`: real subprocess protocol, concurrent
  status/model operations, Unicode, settings paths, shutdown/EOF, worker crash,
  missing dependencies and complete backend RPC coverage.
- `bin/runtime/bin/python3.11 -I bin/runtime_worker.py --check`: validate imports
  with the private interpreter. Requires normal `DECKY_PLUGIN_DIR` and settings
  environment; does not start dictation or inject text.
- Install through Decky's ZIP installer on current Decky; confirm Ready, run
  Test Dictation (no text injection), then dictation in a safe game chat field.
- Check start/stop haptics, overlay, binding capture and review mode. Reload or
  disable the plugin and confirm no old engine/model/listener processes remain.
- Also test on the previous loader: the same package must work independently
  of the Python version embedded in Decky.
