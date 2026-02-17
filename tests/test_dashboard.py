import pytest

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from ui.dashboard import TaskDashboard


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


SAMPLE_TASKS = [
    {
        "key": "TASK-2",
        "summary": "Fix login bug",
        "description": "Users cannot log in with SSO.",
        "type": "Bug",
        "component": "Auth",
        "created_at": "2025-01-01T12:00:00+00:00",
    },
    {
        "key": "TASK-1",
        "summary": "Add dashboard",
        "description": "Create a dashboard view.",
        "type": "Story",
        "component": "Core",
        "created_at": "2025-01-01T10:00:00+00:00",
    },
]


class TestTaskDashboard:
    def test_load_tasks_populates_list(self, qapp):
        w = TaskDashboard()
        w.load_tasks(SAMPLE_TASKS)
        assert w._list.count() == 2

    def test_selecting_task_updates_detail(self, qapp):
        w = TaskDashboard()
        w.load_tasks(SAMPLE_TASKS)

        w._list.setCurrentRow(1)
        qapp.processEvents()

        assert w._title_label.text() == "Add dashboard"
        assert w._key_label.text() == "TASK-1"
        assert "Story" in w._meta_label.text()
        assert "dashboard view" in w._description.toPlainText()

    def test_copy_key_to_clipboard(self, qapp):
        w = TaskDashboard()
        w.load_tasks(SAMPLE_TASKS)

        w._list.setCurrentRow(0)
        qapp.processEvents()

        w._copy_key()
        assert QApplication.clipboard().text() == "TASK-2"

    def test_empty_tasks_shows_empty_state(self, qapp):
        w = TaskDashboard()
        w.load_tasks([])
        assert w._stack.currentIndex() == 0

    def test_escape_closes(self, qapp):
        w = TaskDashboard()
        w.show()
        assert w.isVisible()

        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        w.keyPressEvent(event)
        assert not w.isVisible()
