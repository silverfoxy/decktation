# Third-party notices

Decktation's store artifact includes unmodified `ydotool` and `ydotoold`
version 1.0.4, built from commit
`57ba7d0af525e82da2de0e275d169477f293b197`.

- Source: <https://github.com/ReimuNotMoe/ydotool/tree/v1.0.4>
- License: GNU Affero General Public License v3.0 or later
- Build recipe: `backend/Dockerfile`
- Packaged license: `bin/licenses/ydotool-AGPL-3.0.txt`

The Python packages included under `bin/python` retain their package metadata,
license classifiers, and license files as provided by their respective wheels.

The store artifact also includes the unmodified SteamOS/Arch Linux PortAudio
shared library used by `sounddevice`:

- Upstream source: <https://github.com/PortAudio/portaudio>
- SteamOS package: `portaudio`
- License: MIT
- Packaged license: `bin/licenses/portaudio-MIT.txt`

The private interpreter under `bin/runtime` is CPython 3.11.17 from Astral's
python-build-standalone release 20261013 (Linux x86_64 GNU). The download is
SHA-256 pinned in `backend/prepare_runtime.py`. This runtime is independent of
Decky's Python; native packages under `bin/python` target its CPython 3.11 ABI.

- Source and build instructions: <https://github.com/astral-sh/python-build-standalone/tree/20261013>
- CPython source: <https://github.com/python/cpython/tree/v3.11.17>
- CPython license: `bin/licenses/runtime/LICENSE.cpython.txt`
- Statically bundled component notices: `bin/licenses/runtime/`

The interpreter is stripped of debugging symbols. Development headers, shared
libpython (the executable does not depend on it), pip, setuptools, Tk/Tcl,
IDLE, documentation, tests and bytecode caches are omitted. Retained standard
library modules and native extensions support the engine's HTTPS, subprocess,
threading, audio, JSON and file-handling needs. No system Python installation
or runtime package download is required on the device.
