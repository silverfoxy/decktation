#!/bin/sh
set -eu

cd /backend
mkdir -p out/python out/lib out/licenses
cp -R /runtime/python/. out/python/

# Keep inference code and package license metadata, but omit installation-time
# tools, test suites, caches, and SymPy (used by ONNX conversion tooling, not
# by faster-whisper/ONNX Runtime inference). This substantially reduces store
# archive size and file count.
rm -rf out/python/bin out/python/av out/python/av.libs out/python/av-*.dist-info \
    out/python/sympy out/python/sympy-*.dist-info \
    out/python/mpmath out/python/mpmath-*.dist-info
# faster-whisper imports PyAV only to decode file paths. Decktation supplies
# decoded NumPy samples, so keep the decoder function available but lazy-load
# PyAV if another caller explicitly uses it.
sed -i '/^import av$/d' out/python/faster_whisper/audio.py
sed -i '/    resampler = av.audio.resampler.AudioResampler(/i\    global av\n    import av' \
    out/python/faster_whisper/audio.py
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
cp -L /usr/lib/libportaudio.so.2 out/lib/libportaudio.so.2
cp /ydotool-src/LICENSE out/licenses/ydotool-AGPL-3.0.txt
cp /usr/share/licenses/portaudio/LICENSE.txt out/licenses/portaudio-MIT.txt
