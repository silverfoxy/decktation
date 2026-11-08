"""Temporarily attenuate the desktop output while capturing dictation."""

import json
import subprocess
import threading


class RecordingVolume:
    def __init__(self, mode="off", logger=None):
        self.mode = mode if mode in ("off", "quiet", "mute") else "off"
        self.logger = logger
        self._lock = threading.Lock()
        self._original = None

    def _run(self, *args):
        return subprocess.run(
            ["pactl", *args], check=True, capture_output=True, text=True, timeout=2
        ).stdout

    def set_mode(self, mode):
        with self._lock:
            self._restore()
            self.mode = mode if mode in ("off", "quiet", "mute") else "off"

    def _warn(self, error):
        if self.logger:
            self.logger.warning("Could not adjust recording output volume: %s", error)

    def _restore(self):
        if self._original is None:
            return
        sink, volumes = self._original
        try:
            self._run("set-sink-volume", sink, *map(str, volumes))
        except Exception as error:
            self._warn(error)
        else:
            self._original = None

    def transition(self, state):
        with self._lock:
            if state != "started":
                self._restore()
                return
            if self.mode == "off" or self._original is not None:
                return
            try:
                sink_name = self._run("get-default-sink").strip()
                sinks = json.loads(self._run("--format=json", "list", "sinks"))
                sink = next(s for s in sinks if s["name"] == sink_name)
                volumes = [channel["value"] for channel in sink["volume"].values()]
                if not volumes:
                    return
                # Remember the specific sink and individual channel volumes,
                # so switching outputs never restores volume to the wrong device.
                self._original = (sink_name, volumes)
                factor = 0.2 if self.mode == "quiet" else 0
                self._run("set-sink-volume", sink_name,
                          *(str(round(v * factor)) for v in volumes))
            except Exception as error:
                self._warn(error)
                self._restore()
