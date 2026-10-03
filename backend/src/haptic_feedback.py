"""Optional Steam Deck rumble cues via the vendor HID feature report."""

import fcntl
import os
import queue
import struct
import threading
import time

from controller_listener import find_steam_hidraw


class HapticFeedback:
    """Send bounded cues off the recording thread; ignore unsupported hardware."""

    RUMBLE_SPEED = 45000
    UPDATE_INTERVAL = 0.05

    def __init__(self, enabled=False, logger=None):
        self.enabled = bool(enabled)
        self.logger = logger
        self._events = queue.Queue(maxsize=4)
        self._worker = None
        self._worker_lock = threading.Lock()

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)

    def emit(self, event):
        if not self.enabled or event not in ("started", "stopped"):
            return
        try:
            self._events.put_nowait(event)
            with self._worker_lock:
                if self._worker is None or not self._worker.is_alive():
                    self._worker = threading.Thread(target=self._run, daemon=True)
                    self._worker.start()
        except Exception as error:
            self._warn(error)

    def _run(self):
        while True:
            try:
                event = self._events.get(timeout=1)
            except queue.Empty:
                with self._worker_lock:
                    if self._events.empty():
                        self._worker = None
                        return
                continue
            if not self.enabled:
                continue
            try:
                self._play(event)
            except Exception as error:
                self._warn(error)

    @staticmethod
    def _send_rumble(fd, speed):
        # Linux hid-steam's legacy ID_TRIGGER_RUMBLE_CMD (0xeb), report ID 0.
        report = bytearray(65)
        report[:12] = b"\x00" + struct.pack(
            "<BBBHHHBB", 0xEB, 9, 0, 0, speed, speed, 2, 0
        )
        request = 0xC0000000 | (65 << 16) | (ord("H") << 8) | 6
        fcntl.ioctl(fd, request, report)

    def _play(self, event):
        path = next((path for path, kind in find_steam_hidraw()
                     if kind == "steam_deck"), None)
        if path is None:
            return
        fd = os.open(path, os.O_RDWR)
        try:
            try:
                bursts = 1 if event == "started" else 2
                ticks = 3 if event == "started" else 2
                for burst in range(bursts):
                    for _ in range(ticks):
                        if not self.enabled:
                            return
                        self._send_rumble(fd, self.RUMBLE_SPEED)
                        time.sleep(self.UPDATE_INTERVAL)
                    self._send_rumble(fd, 0)
                    if burst + 1 < bursts:
                        time.sleep(0.075)
            finally:
                self._send_rumble(fd, 0)
        finally:
            os.close(fd)

    def _warn(self, error):
        if self.logger:
            self.logger.warning("Haptic feedback unavailable: %s", error)
