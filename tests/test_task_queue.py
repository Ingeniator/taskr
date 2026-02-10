import pytest
from unittest.mock import MagicMock

from PySide6.QtCore import QCoreApplication

from services.task_queue import TaskQueueWorker, TaskPayload


@pytest.fixture(scope="session")
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


@pytest.fixture
def mock_jira():
    jira = MagicMock()
    jira.submit_task.return_value = {
        "key": "MOCK-1",
        "url": "https://jira.example.com/browse/MOCK-1",
        "summary": "Test",
        "description": "Desc",
        "type": "Task",
        "component": "Core",
    }
    return jira


@pytest.fixture
def payload():
    return TaskPayload(
        summary="Test task",
        description="A description",
        issue_type="Task",
        component="Core",
    )


class TestTaskQueueWorker:
    def test_enqueue_and_complete_signal(self, qapp, mock_jira, payload):
        worker = TaskQueueWorker(mock_jira)
        results = []
        worker.task_completed.connect(results.append)

        worker.enqueue(payload)
        worker.stop()
        worker.start()
        worker.wait(5000)
        qapp.processEvents()

        assert len(results) == 1
        assert results[0]["key"] == "MOCK-1"
        mock_jira.submit_task.assert_called_once_with(
            "Test task", "A description", "Task", "Core"
        )

    def test_enqueue_and_failure_signal(self, qapp, payload):
        jira = MagicMock()
        jira.submit_task.side_effect = Exception("Network error")

        worker = TaskQueueWorker(jira)
        errors = []
        worker.task_failed.connect(lambda msg, p: errors.append((msg, p)))

        worker.enqueue(payload)
        worker.stop()
        worker.start()
        worker.wait(5000)
        qapp.processEvents()

        assert len(errors) == 1
        assert "Network error" in errors[0][0]
        assert errors[0][1] is payload

    def test_multiple_tasks_processed_in_order(self, qapp, mock_jira):
        call_order = []

        def tracking_submit(summary, desc, itype, comp):
            call_order.append(summary)
            return {
                "key": f"MOCK-{len(call_order)}",
                "url": f"https://jira.example.com/browse/MOCK-{len(call_order)}",
                "summary": summary,
                "description": desc,
                "type": itype,
                "component": comp,
            }

        mock_jira.submit_task.side_effect = tracking_submit

        worker = TaskQueueWorker(mock_jira)
        results = []
        worker.task_completed.connect(results.append)

        for i in range(3):
            worker.enqueue(TaskPayload(f"Task {i}", "desc", "Task", "Core"))
        worker.stop()
        worker.start()
        worker.wait(5000)
        qapp.processEvents()

        assert call_order == ["Task 0", "Task 1", "Task 2"]
        assert len(results) == 3

    def test_stop_sentinel_exits_cleanly(self, qapp, mock_jira):
        worker = TaskQueueWorker(mock_jira)
        worker.stop()
        worker.start()
        finished = worker.wait(5000)
        assert finished is True

    def test_worker_continues_after_failure(self, qapp):
        jira = MagicMock()
        jira.submit_task.side_effect = [
            Exception("Fail first"),
            {
                "key": "MOCK-2",
                "url": "https://jira.example.com/browse/MOCK-2",
                "summary": "Second",
                "description": "Desc",
                "type": "Task",
                "component": "Core",
            },
        ]

        worker = TaskQueueWorker(jira)
        errors = []
        results = []
        worker.task_failed.connect(lambda msg, p: errors.append(msg))
        worker.task_completed.connect(results.append)

        worker.enqueue(TaskPayload("First", "d", "Task", "Core"))
        worker.enqueue(TaskPayload("Second", "d", "Task", "Core"))
        worker.stop()
        worker.start()
        worker.wait(5000)
        qapp.processEvents()

        assert len(errors) == 1
        assert "Fail first" in errors[0]
        assert len(results) == 1
        assert results[0]["key"] == "MOCK-2"
