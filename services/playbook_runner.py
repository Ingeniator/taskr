import os
import subprocess
import logging

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


class PlaybookRunner(QThread):
    step_started = Signal(int, str)     # step index, step name
    step_finished = Signal(int, bool)   # step index, success
    log_line = Signal(str)              # single output line
    playbook_finished = Signal(bool)    # overall success

    def __init__(self, playbook: dict, env_overrides: dict | None = None, parent=None):
        super().__init__(parent)
        self._playbook = playbook
        self._env_overrides = env_overrides or {}
        self._process = None
        self._stopped = False

    def run(self):
        steps = self._playbook["steps"]
        cwd = self._playbook.get("cwd")

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env.update(self._env_overrides)

        for i, step in enumerate(steps):
            if self._stopped:
                self.playbook_finished.emit(False)
                return

            self.step_started.emit(i, step["name"])

            try:
                self._process = subprocess.Popen(
                    ["bash", "-c", step["run"]],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=cwd,
                    env=env,
                    bufsize=1,
                    text=True,
                )

                for line in self._process.stdout:
                    if self._stopped:
                        self._process.terminate()
                        self.playbook_finished.emit(False)
                        return
                    self.log_line.emit(line.rstrip("\n"))

                self._process.wait()
                success = self._process.returncode == 0

            except Exception as e:
                logger.error("Step %d (%s) error: %s", i, step["name"], e)
                self.log_line.emit(f"Error: {e}")
                success = False

            self._process = None
            self.step_finished.emit(i, success)

            if not success:
                self.playbook_finished.emit(False)
                return

        self.playbook_finished.emit(True)

    def stop(self):
        self._stopped = True
        proc = self._process
        if proc is not None:
            try:
                proc.terminate()
            except OSError:
                pass
