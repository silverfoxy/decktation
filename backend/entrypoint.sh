#!/bin/sh
set -eu

cd /backend
mkdir -p out/python out/lib out/licenses
cp -R /runtime/python/. out/python/

# Decky places backend/out under the installed plugin's bin/ directory. Keep
# substantive Python backend source in backend/src; root main.py is only the
# Decky Loader entry point.
cp src/resident_whisper.py src/audio_runtime.py src/decktation_backend.py src/wow_voice_chat.py src/clipboard_injection.py src/controller_listener.py \
    src/recording_mode.py src/binding_capture.py src/haptic_feedback.py \
    src/deck_hid.py src/gamepad_evdev.py src/telemetry.py src/convert_wow_context.py \
    src/recording_overlay.py src/recording_overlay_manager.py src/overlay_render.py src/review_gesture.py out/

# Omit installation-time tools, tests, and caches from the bundled Python
# runtime. Inference itself is provided by whisper.cpp.
rm -rf out/python/bin
find out/python -type d \( -name __pycache__ -o -name tests -o -name test \) \
    -prune -exec rm -rf '{}' +
find out/python -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

# Decky Loader currently embeds CPython 3.11. Fail the store build instead of
# silently shipping extension modules for the builder image's newer Python.
if find out/python -type f -name '*cpython-313*' | grep -q .; then
    echo "error: Python 3.13 extension found in the Decky Python 3.11 bundle" >&2
    exit 1
fi
if ! find out/python -type f -name '*cpython-311*' | grep -q .; then
    echo "error: no Python 3.11 extension modules found in runtime bundle" >&2
    exit 1
fi

cp /ydotool-build/ydotool /ydotool-build/ydotoold out/
cp /whisper.cpp/build/bin/whisper-server out/
cp /usr/bin/xclip out/
cp -L /portaudio-build/libportaudio.so out/lib/libportaudio.so.2
cp /ydotool-src/LICENSE out/licenses/ydotool-AGPL-3.0.txt
cp /xclip-src/COPYING out/licenses/xclip-GPL-2.0.txt
cp /portaudio-src/LICENSE.txt out/licenses/portaudio-MIT.txt
