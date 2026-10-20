#!/bin/sh
set -eu

cd /backend
mkdir -p out/python out/lib out/licenses/runtime
cp -R /runtime/python/. out/python/
cp -R /runtime/interpreter out/runtime
cp runtime-licenses/* out/licenses/runtime/
cp out/runtime/LICENSE.txt out/licenses/runtime/LICENSE.cpython.txt

# Decky places backend/out under the installed plugin's bin/ directory. Keep
# substantive Python backend source in backend/src; root main.py is only the
# Decky Loader entry point.
cp src/runtime_proxy.py src/runtime_worker.py src/resident_whisper.py src/audio_runtime.py src/decktation_backend.py src/plugin_update.py src/wow_voice_chat.py src/clipboard_injection.py src/controller_listener.py src/binding_capture.py src/controller_debug_report.py src/controller_debug_session.py \
    src/haptic_feedback.py \
    src/deck_hid.py src/gamepad_evdev.py src/legion_go_s.py src/controller_profiles.py src/telemetry.py src/convert_wow_context.py \
    src/recording_overlay.py src/recording_overlay_manager.py src/overlay_render.py src/review_gesture.py out/

# Omit installation-time tools, tests, and caches from the bundled Python
# runtime. Inference itself is provided by whisper.cpp.
rm -rf out/python/bin
find out/python -type d \( -name __pycache__ -o -name tests -o -name test \) \
    -prune -exec rm -rf '{}' +
find out/python -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

# The engine runs in our private CPython 3.11, independently of Decky.
# Reject a mismatched wheel ABI before publishing the archive.
if find out/python -type f -name '*cpython-313*' | grep -q .; then
    echo "error: Python 3.13 extension found in the Decky Python 3.11 bundle" >&2
    exit 1
fi
if ! find out/python -type f -name '*cpython-311*' | grep -q .; then
    echo "error: no Python 3.11 extension modules found in runtime bundle" >&2
    exit 1
fi

cp /ydotool-build/ydotool /ydotool-build/ydotoold out/
# Build against the same SteamOS-like image used by Decky; do not ship a
# binary built against the developer VM's libc.
mkdir -p out/.gamescope-build
wayland-scanner client-header src/gamescope-input-method.xml out/.gamescope-build/gamescope-input-method-client-protocol.h
wayland-scanner private-code src/gamescope-input-method.xml out/.gamescope-build/gamescope-input-method-protocol.c
cc -std=c11 -O2 -Wall -Wextra -Werror -Iout/.gamescope-build \
    src/gamescope_inject.c out/.gamescope-build/gamescope-input-method-protocol.c \
    -lwayland-client -o out/gamescope-inject
rm -rf out/.gamescope-build
cp src/gamescope-input-method.xml out/licenses/gamescope-input-method-MIT.xml
cp /whisper.cpp/build/bin/whisper-server out/
cp /usr/bin/xclip out/
cp -L /portaudio-build/libportaudio.so out/lib/libportaudio.so.2
cp /ydotool-src/LICENSE out/licenses/ydotool-AGPL-3.0.txt
cp /xclip-src/COPYING out/licenses/xclip-GPL-2.0.txt
cp /portaudio-src/LICENSE.txt out/licenses/portaudio-MIT.txt

# Validate imports with the shipped interpreter, not the builder or Decky's Python.
out/runtime/bin/python3.11 -I - <<'CHECK'
import sys
import ctypes.util
sys.path.insert(0, '/backend/out/python')
original_find_library = ctypes.util.find_library
ctypes.util.find_library = lambda name: ('/backend/out/lib/libportaudio.so.2'
    if name == 'portaudio' else original_find_library(name))
import numpy, sounddevice, ssl, certifi
assert sys.version_info[:2] == (3, 11)
print('Private runtime imports OK')
CHECK
