import json
from datetime import datetime, timezone, timedelta

from services.task_loader import load_todays_tasks


def _write_task(tmp_path, filename, task):
    (tmp_path / filename).write_text(json.dumps(task))


class TestLoadTodaysTasks:
    def test_empty_dir(self, tmp_path):
        assert load_todays_tasks(str(tmp_path)) == []

    def test_nonexistent_dir(self, tmp_path):
        assert load_todays_tasks(str(tmp_path / "nope")) == []

    def test_filters_today_only(self, tmp_path):
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        _write_task(tmp_path, "TASK-1.json", {
            "key": "TASK-1", "summary": "Today task",
            "description": "d", "type": "Bug", "component": "Core",
            "created_at": now.isoformat(),
        })
        _write_task(tmp_path, "TASK-2.json", {
            "key": "TASK-2", "summary": "Yesterday task",
            "description": "d", "type": "Task", "component": "Core",
            "created_at": yesterday.isoformat(),
        })

        tasks = load_todays_tasks(str(tmp_path))
        assert len(tasks) == 1
        assert tasks[0]["key"] == "TASK-1"

    def test_sorted_descending(self, tmp_path):
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(hours=2)

        _write_task(tmp_path, "TASK-1.json", {
            "key": "TASK-1", "summary": "Earlier",
            "description": "d", "type": "Bug", "component": "Core",
            "created_at": earlier.isoformat(),
        })
        _write_task(tmp_path, "TASK-2.json", {
            "key": "TASK-2", "summary": "Later",
            "description": "d", "type": "Task", "component": "Core",
            "created_at": now.isoformat(),
        })

        tasks = load_todays_tasks(str(tmp_path))
        assert len(tasks) == 2
        assert tasks[0]["key"] == "TASK-2"
        assert tasks[1]["key"] == "TASK-1"

    def test_skips_malformed_json(self, tmp_path):
        (tmp_path / "BAD.json").write_text("not json{{{")
        now = datetime.now(timezone.utc)
        _write_task(tmp_path, "TASK-1.json", {
            "key": "TASK-1", "summary": "Good",
            "description": "d", "type": "Bug", "component": "Core",
            "created_at": now.isoformat(),
        })

        tasks = load_todays_tasks(str(tmp_path))
        assert len(tasks) == 1

    def test_skips_missing_created_at(self, tmp_path):
        _write_task(tmp_path, "TASK-1.json", {
            "key": "TASK-1", "summary": "No date",
            "description": "d", "type": "Bug", "component": "Core",
        })

        assert load_todays_tasks(str(tmp_path)) == []

    def test_handles_mock_files(self, tmp_path):
        now = datetime.now(timezone.utc)
        _write_task(tmp_path, "MOCK-abc123.json", {
            "key": "MOCK-abc123", "summary": "Mock task",
            "description": "d", "type": "Task", "component": "Core",
            "created_at": now.isoformat(),
        })
        _write_task(tmp_path, "TASK-1.json", {
            "key": "TASK-1", "summary": "Regular task",
            "description": "d", "type": "Bug", "component": "Core",
            "created_at": now.isoformat(),
        })

        tasks = load_todays_tasks(str(tmp_path))
        assert len(tasks) == 2
        keys = {t["key"] for t in tasks}
        assert keys == {"MOCK-abc123", "TASK-1"}
