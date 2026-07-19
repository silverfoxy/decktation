FROM ghcr.io/steamdeckhomebrew/holo-base:latest

ARG YDOTOOL_COMMIT=57ba7d0af525e82da2de0e275d169477f293b197

RUN pacman -Sydd --noconfirm --dbpath /var/lib/pacman \
        git portaudio python-pip

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

ENTRYPOINT ["/backend/entrypoint.sh"]
