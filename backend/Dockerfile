FROM ghcr.io/steamdeckhomebrew/holo-base:latest

ARG YDOTOOL_COMMIT=57ba7d0af525e82da2de0e275d169477f293b197
ARG WHISPER_CPP_COMMIT=f24588a272ae8e23280d9c220536437164e6ed28

# holo-base already ships glslc, shaderc, the Vulkan headers, and binutils.
# Reinstalling those packages fails because their files are untracked by pacman.
RUN pacman -Sydd --noconfirm --dbpath /var/lib/pacman \
        alsa-lib cmake cppdap git libuv python-pip rhash spirv-headers vulkan-icd-loader xclip \
    && command -v strip \
    && cmake --version \
    && glslc --version

# Use ALSA (including the desktop PipeWire ALSA device), without starting
# JACK clients whose callbacks can crash while Decky replaces the plugin.
RUN git clone --depth 1 --branch v19.7.0 https://github.com/PortAudio/portaudio.git /portaudio-src \
    && cmake -S /portaudio-src -B /portaudio-build \
        -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
        -DPA_BUILD_SHARED=ON -DPA_BUILD_STATIC=OFF \
        -DPA_USE_ALSA=ON -DPA_USE_JACK=OFF -DPA_BUILD_EXAMPLES=OFF -DPA_BUILD_TESTS=OFF \
    && cmake --build /portaudio-build -j2

# The private interpreter and native wheels are deliberately the same ABI.
# Decky itself only loads the standard-library RPC bridge.
COPY prepare_runtime.py /tmp/decktation-prepare-runtime.py
RUN python3 /tmp/decktation-prepare-runtime.py /runtime/interpreter

COPY src/requirements.txt /tmp/decktation-requirements.txt

RUN mkdir -p /runtime/wheels /runtime/python \
    && python3 -m pip download \
        --no-cache-dir \
        --no-deps \
        --only-binary=:all: \
        --dest=/runtime/wheels \
        --implementation=cp \
        --python-version=311 \
        --abi=cp311 \
        --platform=manylinux_2_28_x86_64 \
        --platform=manylinux_2_27_x86_64 \
        --platform=manylinux_2_17_x86_64 \
        --platform=manylinux2014_x86_64 \
        -r /tmp/decktation-requirements.txt \
    && for wheel in /runtime/wheels/*.whl; do \
        python3 -m zipfile -e "$wheel" /runtime/python; \
    done \
    && for data_dir in /runtime/python/*.data; do \
        [ -d "$data_dir" ] || continue; \
        [ ! -d "$data_dir/purelib" ] || cp -a "$data_dir/purelib/." /runtime/python/; \
        [ ! -d "$data_dir/platlib" ] || cp -a "$data_dir/platlib/." /runtime/python/; \
        rm -rf "$data_dir"; \
    done

RUN git init /ydotool-src \
    && git -C /ydotool-src remote add origin https://github.com/ReimuNotMoe/ydotool.git \
    && git -C /ydotool-src fetch --depth 1 origin "${YDOTOOL_COMMIT}" \
    && git -C /ydotool-src checkout --detach FETCH_HEAD \
    && mkdir -p /ydotool-build \
    && cc -std=c99 -O2 -D_DEFAULT_SOURCE -DVERSION='"v1.0.4"' \
        -o /ydotool-build/ydotoold /ydotool-src/Daemon/ydotoold.c \
    && cc -std=c99 -O2 -D_DEFAULT_SOURCE -DVERSION='"v1.0.4"' \
        -I/ydotool-src/Client \
        -o /ydotool-build/ydotool \
        /ydotool-src/Client/ydotool.c \
        /ydotool-src/Client/tool_click.c \
        /ydotool-src/Client/tool_mousemove.c \
        /ydotool-src/Client/tool_type.c \
        /ydotool-src/Client/tool_key.c

RUN git init /xclip-src \
    && git -C /xclip-src remote add origin https://github.com/astrand/xclip.git \
    && git -C /xclip-src fetch --depth 1 origin 9aa7090c3b8b437c6489edca32ae43d82e0c1281 \
    && git -C /xclip-src checkout --detach FETCH_HEAD

# Benchmark-only Vulkan build. One binary exercises both paths: its normal
# mode uses Vulkan, while --no-gpu runs the same whisper.cpp revision/model on
# CPU for an apples-to-apples comparison on the Deck.
RUN git init /whisper.cpp \
    && git -C /whisper.cpp remote add origin https://github.com/ggml-org/whisper.cpp.git \
    && git -C /whisper.cpp fetch --depth 1 origin "${WHISPER_CPP_COMMIT}" \
    && git -C /whisper.cpp checkout --detach FETCH_HEAD \
    && cmake -S /whisper.cpp -B /whisper.cpp/build \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_SHARED_LIBS=OFF \
        -DGGML_NATIVE=OFF \
        -DGGML_VULKAN=ON \
        -DWHISPER_BUILD_TESTS=OFF \
        -DWHISPER_BUILD_SERVER=ON \
    && cmake --build /whisper.cpp/build --config Release --target whisper-server -j2

ENTRYPOINT ["/backend/entrypoint.sh"]
