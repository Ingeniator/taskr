import json
import os

import pytest

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

import ui.playbook_dashboard as pd
from ui.playbook_dashboard import PlaybookDashboard


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


SAMPLE_PLAYBOOKS = [
    {
        "name": "Deploy",
        "description": "Deploy to staging",
        "cwd": "/tmp/myapp",
        "steps": [
            {"name": "Build", "run": "make build"},
            {"name": "Deploy", "run": "./deploy.sh"},
        ],
        "params": [],
        "file_path": "/tmp/playbooks/deploy.yml",
    },
    {
        "name": "Test Suite",
        "description": "Run all tests",
        "cwd": "/tmp/myapp",
        "steps": [
            {"name": "Lint", "run": "flake8"},
            {"name": "Unit tests", "run": "pytest"},
            {"name": "Integration", "run": "pytest tests/integration/"},
        ],
        "params": [
            {"name": "VERBOSE", "label": "Verbose mode", "default": "0"},
        ],
        "file_path": "/tmp/playbooks/test.yml",
    },
]


class TestPlaybookDashboard:
    def test_load_playbooks_populates_list(self, qapp):
        w = PlaybookDashboard()
        w.load_playbooks(SAMPLE_PLAYBOOKS)
        assert w._list.count() == 2

    def test_selection_updates_detail(self, qapp):
        w = PlaybookDashboard()
        w.load_playbooks(SAMPLE_PLAYBOOKS)

        w._list.setCurrentRow(1)
        qapp.processEvents()

        assert w._name_label.text() == "Test Suite"
        assert "Run all tests" in w._desc_label.text()
        assert len(w._step_labels) == 3

    def test_empty_state(self, qapp):
        w = PlaybookDashboard()
        w.load_playbooks([])
        assert w._stack.currentIndex() == 0

    def test_escape_closes(self, qapp):
        w = PlaybookDashboard()
        w.show()
        assert w.isVisible()

        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        w.keyPressEvent(event)
        assert not w.isVisible()

    def test_step_labels_show_pending_icon(self, qapp):
        w = PlaybookDashboard()
        w.load_playbooks(SAMPLE_PLAYBOOKS)

        w._list.setCurrentRow(0)
        qapp.processEvents()

        assert len(w._step_labels) == 2
        for lbl in w._step_labels:
            assert "\u25CB" in lbl.text()  # pending circle

    def test_switching_playbook_updates_steps(self, qapp):
        w = PlaybookDashboard()
        w.load_playbooks(SAMPLE_PLAYBOOKS)

        w._list.setCurrentRow(0)
        qapp.processEvents()
        assert len(w._step_labels) == 2

        w._list.setCurrentRow(1)
        qapp.processEvents()
        assert len(w._step_labels) == 3

    def test_param_fields_shown_for_playbook_with_params(self, qapp):
        w = PlaybookDashboard()
        w.load_playbooks(SAMPLE_PLAYBOOKS)

        w._list.setCurrentRow(1)  # Test Suite has params
        qapp.processEvents()

        assert len(w._param_fields) == 1
        env_name, field = w._param_fields[0]
        assert env_name == "VERBOSE"
        assert field.text() == "0"

    def test_no_param_fields_for_playbook_without_params(self, qapp):
        w = PlaybookDashboard()
        w.load_playbooks(SAMPLE_PLAYBOOKS)

        w._list.setCurrentRow(0)  # Deploy has no params
        qapp.processEvents()

        assert len(w._param_fields) == 0

    def test_param_fields_cleared_on_switch(self, qapp):
        w = PlaybookDashboard()
        w.load_playbooks(SAMPLE_PLAYBOOKS)

        w._list.setCurrentRow(1)  # Test Suite (has params)
        qapp.processEvents()
        assert len(w._param_fields) == 1

        w._list.setCurrentRow(0)  # Deploy (no params)
        qapp.processEvents()
        assert len(w._param_fields) == 0

    def test_saved_params_restored_on_selection(self, qapp, tmp_path, monkeypatch):
        cache_file = str(tmp_path / "playbook_params.json")
        monkeypatch.setattr(pd, "_PARAMS_CACHE", cache_file)

        # Pre-populate saved params
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump({"/tmp/playbooks/test.yml": {"VERBOSE": "1"}}, f)

        w = PlaybookDashboard()
        w.load_playbooks(SAMPLE_PLAYBOOKS)

        w._list.setCurrentRow(1)  # Test Suite
        qapp.processEvents()

        # Should use saved "1" instead of default "0"
        assert w._param_fields[0][1].text() == "1"

    def test_params_saved_on_run(self, qapp, tmp_path, monkeypatch):
        cache_file = str(tmp_path / "playbook_params.json")
        monkeypatch.setattr(pd, "_PARAMS_CACHE", cache_file)

        w = PlaybookDashboard()
        w.load_playbooks(SAMPLE_PLAYBOOKS)

        w._list.setCurrentRow(1)  # Test Suite
        qapp.processEvents()

        # Change the field value
        w._param_fields[0][1].setText("42")

        # Trigger run (will fail to actually run but should save params)
        w._on_run()
        # Stop immediately
        fp = SAMPLE_PLAYBOOKS[1]["file_path"]
        runner = w._runners.get(fp)
        if runner:
            runner.stop()
            runner.wait(2000)

        with open(cache_file) as f:
            cache = json.load(f)
        assert cache["/tmp/playbooks/test.yml"]["VERBOSE"] == "42"
