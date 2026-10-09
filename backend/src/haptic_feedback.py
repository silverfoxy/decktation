"""Optional, source-bound controller feedback outside the recording thread."""

import ctypes
import fcntl
import glob
import json
import os
import queue
import struct
import threading
import time

from controller_listener import find_steam_hidraw
from gamepad_evdev import bits, ioctl_read, EVENT


class _Trigger(ctypes.Structure):
    _fields_ = [('button', ctypes.c_uint16), ('interval', ctypes.c_uint16)]


class _Replay(ctypes.Structure):
    _fields_ = [('length', ctypes.c_uint16), ('delay', ctypes.c_uint16)]


class _Rumble(ctypes.Structure):
    _fields_ = [('strong', ctypes.c_uint16), ('weak', ctypes.c_uint16)]


class _EffectData(ctypes.Union):
    # ff_periodic_effect contains a pointer and is the largest union member.
    _fields_ = [('rumble', _Rumble), ('padding', ctypes.c_uint8 * 32),
                ('alignment', ctypes.c_void_p)]


class _Effect(ctypes.Structure):
    _fields_ = [('type', ctypes.c_uint16), ('id', ctypes.c_int16),
                ('direction', ctypes.c_uint16), ('trigger', _Trigger),
                ('replay', _Replay), ('data', _EffectData)]


FF_RUMBLE = 0x50
EV_FF = 0x15
EVIOCSFF = (1 << 30) | (ctypes.sizeof(_Effect) << 16) | (ord('E') << 8) | 0x80
EVIOCRMFF = (1 << 30) | (4 << 16) | (ord('E') << 8) | 0x81


def _physical_parent(path):
    """Only match event nodes under the same kernel HID/input device."""
    name = os.path.basename(path)
    if not name.startswith('event') or not name[5:].isdigit():
        return None
    sys_path = f'/sys/class/input/{name}/device'
    if not os.path.exists(sys_path):
        return None
    return os.path.dirname(os.path.realpath(sys_path))


def _identity(fd):
    bus, vendor, product, _ = struct.unpack('4H', ioctl_read(fd, 0x02, 8))
    return {'bus': bus, 'vendor_id': vendor, 'product_id': product}


def _ff_capable(fd):
    return EV_FF in bits(ioctl_read(fd, 0x20, 8)) and FF_RUMBLE in bits(ioctl_read(fd, 0x20 + EV_FF, 16))


def _ff_path(source):
    path = source['path']
    identity = source['identity']
    # A Steam Input virtual pad can be used when its *own* event node exposes
    # FF_RUMBLE. This keeps the input/output mapping on one kernel device;
    # never infer a physical HID path or another virtual pad's index.
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        try:
            if _identity(fd) == identity and _ff_capable(fd):
                return path, None
        finally:
            os.close(fd)
    except OSError:
        pass
    if identity.get('bus') == 6 or (identity.get('vendor_id'), identity.get('product_id')) == (0x28de, 0x11ff):
        return None, 'virtual controller has no force feedback on its input interface'
    parent = _physical_parent(path)
    if parent is None:
        return None, 'controller has no identifiable physical input device'
    matches = []
    for candidate in glob.glob('/dev/input/event*'):
        if _physical_parent(candidate) != parent:
            continue
        try:
            fd = os.open(candidate, os.O_RDONLY | os.O_NONBLOCK)
            try:
                if _identity(fd) == identity and _ff_capable(fd):
                    matches.append(candidate)
            finally:
                os.close(fd)
        except OSError:
            continue
    if len(matches) == 1:
        return matches[0], None
    if matches:
        return None, 'multiple force-feedback interfaces match this controller'
    return None, 'EV_FF/FF_RUMBLE unavailable for this controller'


def _evdev_label(source):
    identity = source['identity']
    vendor = identity.get('vendor_id')
    product = identity.get('product_id')
    if (vendor, product) == (0x28de, 0x11ff):
        return 'steam-input-virtual'
    return {0x045e: 'xbox', 0x054c: 'playstation',
            0x057e: 'nintendo'}.get(vendor, 'generic-gamepad')


class HapticFeedback:
    """Queue one bounded backend cue for the controller that started dictation."""

    RUMBLE_SPEED = 45000
    UPDATE_INTERVAL = 0.05

    def __init__(self, enabled=False, logger=None):
        self.enabled = bool(enabled)
        self.logger = logger
        self._events = queue.Queue(maxsize=4)
        self._worker = None
        self._worker_lock = threading.Lock()
        self._session = None
        self._generation = 0

    def set_enabled(self, enabled):
        with self._worker_lock:
            self.enabled = bool(enabled)
            if not self.enabled:
                self._generation += 1
                self._session = None

    def begin_session(self, source_file, max_age=2):
        source = None
        try:
            # Timestamped recording events carry their initiating source so
            # later controller input cannot overwrite it before backend polling.
            if isinstance(source_file, dict):
                value = dict(source_file)
            else:
                with open(source_file) as file:
                    value = json.load(file)
            if (isinstance(value, dict) and isinstance(value.get('path'), str)
                    and isinstance(value.get('identity'), dict)
                    and isinstance(value.get('time'), (int, float))
                    and 0 <= time.time() - value['time'] <= max_age
                    and value.get('kind') in ('steam_deck', 'steam_controller_wired',
                                              'steam_controller_wireless',
                                              'steam_controller_2026_puck', 'evdev_gamepad')):
                source = value
        except (OSError, ValueError, TypeError):
            pass
        with self._worker_lock:
            self._session = source
        if source is None:
            self._info('no recently identified controller; cue skipped')

    def end_session(self):
        with self._worker_lock:
            self._session = None

    def emit(self, event):
        if event not in ('started', 'stopped'):
            return
        try:
            with self._worker_lock:
                if not self.enabled:
                    return
                source = self._session
                generation = self._generation
                if event == 'stopped':
                    self._session = None
                if source is None:
                    return
                self._events.put_nowait((event, source, generation))
                if self._worker is None or not self._worker.is_alive():
                    self._worker = threading.Thread(target=self._run, daemon=True)
                    self._worker.start()
        except Exception as error:
            self._warn(error)

    def _active(self, generation):
        return self.enabled and generation == self._generation

    def _run(self):
        while True:
            try:
                event, source, generation = self._events.get(timeout=1)
            except queue.Empty:
                with self._worker_lock:
                    if self._events.empty():
                        self._worker = None
                        return
                continue
            if not self._active(generation):
                continue
            try:
                self._play(event, source, generation)
            except Exception as error:
                self._warn(error)

    @staticmethod
    def _send_rumble(fd, speed):
        # Existing, physically validated Steam Deck command; report ID 0.
        report = bytearray(65)
        report[:12] = b'\x00' + struct.pack('<BBBHHHBB', 0xEB, 9, 0, 0, speed, speed, 2, 0)
        request = 0xC0000000 | (65 << 16) | (ord('H') << 8) | 6
        fcntl.ioctl(fd, request, report)

    @staticmethod
    def _send_legacy_pulse(fd, duration_us=15000):
        # Original (2015) Steam Controller, hid-steam ID_TRIGGER_HAPTIC_PULSE.
        # Pad 2 addresses both sides. One pulse is firmware bounded.
        report = bytearray(65)
        report[:11] = b'\x00' + struct.pack('<BBBHHHb', 0x8F, 8, 2,
                                            duration_us, 0, 1, 0)
        request = 0xC0000000 | (65 << 16) | (ord('H') << 8) | 6
        fcntl.ioctl(fd, request, report)

    @staticmethod
    def _send_triton_rumble(fd, speed):
        # 2026 Puck uses HID output report 0x80, not the legacy feature report.
        report = struct.pack('<BBHHBHB', 0x80, 0, 0, speed, 0, speed, 0)
        os.write(fd, report)

    def _play(self, event, source, generation):
        kind, path = source['kind'], source['path']
        if kind in ('steam_deck', 'steam_controller_wired',
                    'steam_controller_wireless', 'steam_controller_2026_puck'):
            if (path, kind) not in find_steam_hidraw():
                self._info(f'{kind}: source disconnected; cue skipped')
                return
            backend = ('deck-hid-rumble' if kind == 'steam_deck' else
                       'triton-hid-rumble' if kind == 'steam_controller_2026_puck' else
                       'legacy-controller-hid-pulse')
            self._info(f'{kind}: {backend}')
            fd = os.open(path, os.O_RDWR)
            try:
                if kind == 'steam_deck':
                    self._deck_pattern(fd, event, generation)
                elif kind == 'steam_controller_2026_puck':
                    self._triton_pattern(fd, event, generation)
                else:
                    self._legacy_pattern(fd, event, generation)
            finally:
                os.close(fd)
            return
        if kind == 'evdev_gamepad':
            label = _evdev_label(source)
            ff_path, reason = _ff_path(source)
            if ff_path is None:
                self._info(f'{label}: {reason}')
                return
            self._info(f'{label}: FF_RUMBLE')
            self._evdev_pattern(ff_path, event, generation, source['identity'])

    def _deck_pattern(self, fd, event, generation):
        try:
            bursts = 1 if event == 'started' else 2
            ticks = 3 if event == 'started' else 2
            for burst in range(bursts):
                for _ in range(ticks):
                    if not self._active(generation):
                        return
                    self._send_rumble(fd, self.RUMBLE_SPEED)
                    time.sleep(self.UPDATE_INTERVAL)
                self._send_rumble(fd, 0)
                if burst + 1 < bursts:
                    time.sleep(0.075)
        finally:
            self._send_rumble(fd, 0)

    def _legacy_pattern(self, fd, event, generation):
        for index in range(1 if event == 'started' else 2):
            if not self._active(generation):
                return
            self._send_legacy_pulse(fd)
            if event == 'stopped' and index == 0:
                time.sleep(0.075)

    def _triton_pattern(self, fd, event, generation):
        try:
            bursts = 1 if event == 'started' else 2
            ticks = 3 if event == 'started' else 2
            for burst in range(bursts):
                for _ in range(ticks):
                    if not self._active(generation):
                        return
                    self._send_triton_rumble(fd, self.RUMBLE_SPEED)
                    time.sleep(self.UPDATE_INTERVAL)
                self._send_triton_rumble(fd, 0)
                if burst + 1 < bursts:
                    time.sleep(0.075)
        finally:
            self._send_triton_rumble(fd, 0)

    def _evdev_pattern(self, path, event, generation, expected_identity):
        fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        effect_id = None
        try:
            if _identity(fd) != expected_identity or not _ff_capable(fd):
                return
            effect = _Effect()
            effect.type = FF_RUMBLE
            effect.id = -1
            effect.replay.length = 150 if event == 'started' else 100
            effect.data.rumble.strong = 45000
            effect.data.rumble.weak = 45000
            fcntl.ioctl(fd, EVIOCSFF, effect)
            effect_id = effect.id
            for index in range(1 if event == 'started' else 2):
                if not self._active(generation):
                    return
                os.write(fd, EVENT.pack(0, 0, EV_FF, effect_id, 1))
                time.sleep(effect.replay.length / 1000)
                os.write(fd, EVENT.pack(0, 0, EV_FF, effect_id, 0))
                if event == 'stopped' and index == 0:
                    time.sleep(0.075)
        finally:
            if effect_id is not None:
                try:
                    os.write(fd, EVENT.pack(0, 0, EV_FF, effect_id, 0))
                    fcntl.ioctl(fd, EVIOCRMFF, struct.pack('i', effect_id))
                except OSError as error:
                    self._warn(error)
            os.close(fd)

    def _info(self, message):
        if self.logger:
            self.logger.info('Haptic feedback: %s', message)

    def _warn(self, error):
        if self.logger:
            self.logger.warning('Haptic feedback unavailable: %s', error)
