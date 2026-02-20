import pytest

from PySide6.QtWidgets import QApplication

from services.playbook_runner import PlaybookRunner


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _collect_signals(runner):
    """Connect to all runner signals and return collection lists."""
    started = []
    finished = []
    logs = []
    done = []

    runner.step_started.connect(lambda i, n: started.append((i, n)))
    runner.step_finished.connect(lambda i, s: finished.append((i, s)))
    runner.log_line.connect(lambda t: logs.append(t))
    runner.playbook_finished.connect(lambda s: done.append(s))

    return started, finished, logs, done


def _run_and_wait(runner, qapp):
    """Start runner, wait for it to finish, then process pending events."""
    runner.start()
    runner.wait(5000)
    qapp.processEvents()


class TestPlaybookRunner:
    def test_multi_step_success(self, qapp, tmp_path):
        playbook = {
            "cwd": str(tmp_path),
            "steps": [
                {"name": "Step 1", "run": "echo hello"},
                {"name": "Step 2", "run": "echo world"},
            ],
        }
        runner = PlaybookRunner(playbook)
        started, finished, logs, done = _collect_signals(runner)

        _run_and_wait(runner, qapp)

        assert len(started) == 2
        assert len(finished) == 2
        assert finished[0] == (0, True)
        assert finished[1] == (1, True)
        assert len(done) == 1
        assert done[0] is True
        assert "hello" in logs
        assert "world" in logs

    def test_stop_on_failure(self, qapp, tmp_path):
        playbook = {
            "cwd": str(tmp_path),
            "steps": [
                {"name": "Fail", "run": "exit 1"},
                {"name": "Never", "run": "echo never"},
            ],
        }
        runner = PlaybookRunner(playbook)
        started, finished, logs, done = _collect_signals(runner)

        _run_and_wait(runner, qapp)

        assert len(started) == 1
        assert len(finished) == 1
        assert finished[0] == (0, False)
        assert len(done) == 1
        assert done[0] is False

    def test_missing_command(self, qapp, tmp_path):
        playbook = {
            "cwd": str(tmp_path),
            "steps": [
                {"name": "Bad", "run": "nonexistent_command_xyz_123"},
            ],
        }
        runner = PlaybookRunner(playbook)
        started, finished, logs, done = _collect_signals(runner)

        _run_and_wait(runner, qapp)

        assert len(finished) == 1
        assert finished[0] == (0, False)
        assert len(done) == 1
        assert done[0] is False

    def test_env_overrides(self, qapp, tmp_path):
        playbook = {
            "cwd": str(tmp_path),
            "steps": [
                {"name": "Print var", "run": "echo $MY_VAR"},
            ],
        }
        runner = PlaybookRunner(playbook, env_overrides={"MY_VAR": "injected_value"})
        started, finished, logs, done = _collect_signals(runner)

        _run_and_wait(runner, qapp)

        assert "injected_value" in logs
        assert done[0] is True
