"""Ordered, unprivileged status notifications for optional integrations."""

import logging
import os
import queue
import shlex
import signal
import subprocess
import threading

from clipboard_injection import _session_account

logger = logging.getLogger(__name__)
HOOK_TIMEOUT = 3


class StatusHook:
    def __init__(self):
        self.events = queue.Queue()
        self.lock = threading.Lock()
        self.worker = None

    def submit(self, command, event, user_home=None):
        if not command or not command.strip():
            return
        with self.lock:
            self.events.put((command, event, user_home))
            if self.worker is None:
                self.worker = threading.Thread(target=self._work, name="decktation-status-hook", daemon=True)
                self.worker.start()

    def _work(self):
        while True:
            command, event, user_home = self.events.get()
            try:
                self._run(command, event, user_home)
            except Exception:
                logger.exception("Status hook failed for %s", event)
            finally:
                self.events.task_done()

    def _run(self, command, event, user_home):
        # Do not pass the privileged plugin environment (or its secrets) to hooks.
        account = _session_account({"DECKY_USER_HOME": user_home})
        if account.pw_uid == 0:
            raise RuntimeError("Refusing to run a status hook as root")
        runtime = f"/run/user/{account.pw_uid}"
        env = {
            "HOME": account.pw_dir, "USER": account.pw_name,
            "LOGNAME": account.pw_name, "PATH": "/usr/local/bin:/usr/bin:/bin",
            "XDG_RUNTIME_DIR": runtime,
            "DBUS_SESSION_BUS_ADDRESS": f"unix:path={runtime}/bus",
            "DECKTATION_EVENT": event,
        }
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "LANG"):
            if name in os.environ:
                env[name] = os.environ[name]
        identity = {}
        if os.geteuid() == 0:
            identity = dict(user=account.pw_uid, group=account.pw_gid, extra_groups=[])
        with subprocess.Popen(
            shlex.split(command), env=env, cwd=account.pw_dir,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True, **identity,
        ) as process:
            try:
                code = process.wait(timeout=HOOK_TIMEOUT)
                if code:
                    logger.warning("Status hook for %s exited with %s", event, code)
            except subprocess.TimeoutExpired:
                # Kill the whole group so helper children cannot apply stale events.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                logger.warning("Status hook for %s timed out", event)
