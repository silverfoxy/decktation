"""Own the desktop user's Gamescope recording indicator process."""
import os
import json
import pwd
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path


class RecordingOverlay:
    def __init__(self, plugin_path, logger, decky_user_home=None, enabled=True):
        self.plugin_path = Path(plugin_path)
        self.logger = logger
        self.enabled = enabled
        self.process = None
        self.directory = None
        self.display = None
        self.session_user = self._resolve_session_user(decky_user_home)
        self.lock = threading.RLock()
        self.preview = None
        self.desired_state = "hidden"
        self.discovery_thread = None
        self.next_discovery = 0
        if self.enabled:
            self._start_display_discovery()

    def _resolve_session_user(self, decky_user_home):
        """Resolve Decky's configured desktop account without assuming its name."""
        candidate_uids = []
        if decky_user_home:
            try:
                candidate_uids.append(os.stat(decky_user_home).st_uid)
            except OSError as exc:
                self.logger.warning("Could not inspect Decky user home: %s", exc)
        if os.environ.get("SUDO_UID", "").isdigit():
            candidate_uids.append(int(os.environ["SUDO_UID"]))
        try:
            candidate_uids.extend(
                int(path.name) for path in Path("/run/user").iterdir()
                if path.name.isdigit() and path.name != "0"
            )
        except OSError:
            pass

        for uid in dict.fromkeys(candidate_uids):
            if uid == 0:
                continue
            try:
                return pwd.getpwuid(uid)
            except KeyError:
                continue
        self.logger.warning("Recording overlay: no desktop session user found")
        return None

    def _env(self, display):
        user = self.session_user
        return {
            "DISPLAY": display,
            "GDK_BACKEND": "x11",
            "HOME": user.pw_dir,
            "USER": user.pw_name,
            "LOGNAME": user.pw_name,
            "XDG_RUNTIME_DIR": f"/run/user/{user.pw_uid}",
            "PATH": "/usr/bin:/bin",
        }

    def _display_candidates(self):
        override = os.environ.get("DECKTATION_OVERLAY_DISPLAY")
        if override:
            return [override]

        candidates = [os.environ.get("DISPLAY")]
        runtime_dir = Path(f"/run/user/{self.session_user.pw_uid}")
        if any(runtime_dir.glob("gamescope-*")):
            candidates.append(":1")
        candidates.extend(
            f":{path.name[1:]}"
            for path in sorted(Path("/tmp/.X11-unix").glob("X[0-9]*"))
        )
        return list(dict.fromkeys(candidate for candidate in candidates if candidate))

    def _find_display(self):
        override = os.environ.get("DECKTATION_OVERLAY_DISPLAY")
        candidates = self._display_candidates()
        for display in candidates:
            try:
                result = subprocess.run(
                    ["/usr/bin/xprop", "-root", "GAMESCOPE_XWAYLAND_SERVER_ID"],
                    env=self._env(display), user=self.session_user.pw_uid,
                    group=self.session_user.pw_gid, extra_groups=[],
                    capture_output=True, text=True, timeout=0.5, check=False,
                )
                if result.returncode == 0 and (
                    override or result.stdout.strip().endswith("= 0")
                ):
                    return display
            except (OSError, subprocess.TimeoutExpired) as exc:
                self.logger.warning("Recording overlay display check failed: %s", exc)
        self.logger.warning("Recording overlay: no Gamescope main Xwayland display found")
        return None

    def _start_display_discovery(self):
        if not self.session_user or self.display:
            return
        if self.discovery_thread and self.discovery_thread.is_alive():
            return
        if time.monotonic() < self.next_discovery:
            return
        self.discovery_thread = threading.Thread(
            target=self._discover_display,
            name="decktation-overlay-display",
            daemon=True,
        )
        self.discovery_thread.start()

    def _discover_display(self):
        display = self._find_display()
        with self.lock:
            self.discovery_thread = None
            if not display:
                self.next_discovery = time.monotonic() + 30
                return
            self.display = display
            if self.enabled and self.desired_state in ("compact", "transcribing", "review", "countdown", "result"):
                self._show_ready(self.desired_state)

    def _write_state(self, state):
        self.directory.mkdir(mode=0o755, exist_ok=True)
        state_file = self.directory / "state"
        temp_file = self.directory / "state.new"
        payload = dict(self.preview) if self.preview and state in ("review", "countdown", "result") else {"mode": state}
        temp_file.write_text(json.dumps(payload, ensure_ascii=False) + "\n")
        os.chmod(temp_file, 0o644)
        temp_file.replace(state_file)

    def show(self, state):
        with self.lock:
            try:
                self.desired_state = state
                if not self.enabled or state not in ("compact", "transcribing", "review", "countdown", "result"):
                    return
                if self.display:
                    self._show_ready(state)
                else:
                    self._start_display_discovery()
            except Exception as exc:
                self.logger.warning("Recording overlay unavailable: %s", exc)

    def _show_ready(self, state):
        if self.directory is None:
            self.directory = Path(tempfile.mkdtemp(prefix="decktation-overlay-"))
            os.chmod(self.directory, 0o755)
            # The child owns only its acknowledgment directory, allowing atomic
            # publication without permission to change the root-owned state file.
            acknowledgments = self.directory / "ack"
            acknowledgments.mkdir(mode=0o755)
            if self.session_user:
                os.chown(acknowledgments, self.session_user.pw_uid, self.session_user.pw_gid)
        self._write_state(state)
        if self.process and self.process.poll() is None:
            return
        script = self.plugin_path / "bin" / "recording_overlay.py"
        if not script.is_file():
            self.logger.warning("Recording overlay script missing: %s", script)
            return
        try:
            log = (self.directory / "overlay.log").open("a")
            try:
                self.process = subprocess.Popen(
                    ["/usr/bin/python3", str(script), str(self.directory / "state"), str(os.getpid())],
                    env=self._env(self.display), cwd=self.directory,
                    user=self.session_user.pw_uid, group=self.session_user.pw_gid,
                    extra_groups=[], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    start_new_session=True, close_fds=True,
                )
            finally:
                log.close()
        except OSError as exc:
            self.logger.warning("Recording overlay failed to start: %s", exc)

    def show_result(self, message):
        with self.lock:
            self.preview = {"mode": "result", "message": message, "expires": time.time() + 1.2}
            self.show("result")

    def show_preview(self, draft, binding):
        with self.lock:
            self.preview = dict(draft, binding=binding, cancel_progress=0)
            self.show(draft["mode"])

    def set_send_block_reason(self, reason):
        with self.lock:
            if self.preview and self.preview.get("send_block_reason", "") != reason:
                self.preview["send_block_reason"] = reason
                if self.directory:
                    self._write_state(self.desired_state)

    def set_cancel_progress(self, progress):
        with self.lock:
            if self.preview and self.preview.get("cancel_progress") != progress:
                self.preview["cancel_progress"] = progress
                if self.directory:
                    self._write_state(self.desired_state)

    def preview_status(self, draft_id):
        with self.lock:
            if not self.process or self.process.poll() is not None or not self.directory:
                return {"visible": False, "ready": False}
            try:
                status = json.loads((self.directory / "ack" / "status").read_text())
                current = (status.get("id") == draft_id and
                           0 <= time.time() - status.get("time", 0) < 1.5)
                return {"visible": current, "ready": current and status.get("ready") is True,
                        "focus_app": status.get("focus_app") if current else None}
            except (OSError, ValueError, TypeError):
                return {"visible": False, "ready": False}

    def preview_ready(self, draft_id):
        return self.preview_status(draft_id).get("ready", False)

    def hide(self):
        with self.lock:
            try:
                self.desired_state = "hidden"
                self.preview = None
                if self.directory:
                    self._write_state("hidden")
            except Exception as exc:
                self.logger.warning("Could not hide recording overlay: %s", exc)

    def set_enabled(self, enabled):
        with self.lock:
            self.enabled = bool(enabled)
            if not self.enabled:
                self.hide()
            else:
                self._start_display_discovery()

    def stop(self):
        with self.lock:
            self._stop()

    def _stop(self):
        self.enabled = False
        self.desired_state = "hidden"
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        self.process = None
        if self.directory:
            shutil.rmtree(self.directory)
            self.directory = None
