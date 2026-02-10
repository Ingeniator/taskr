
# tests/test_json_service.py

import json
import os
import pytest
from unittest.mock import patch

from services.json_service import JsonService, _next_task_id
from services.task_service import TaskService


MOCK_CONFIG = {
    "jira": {"base_url": "https://jira.example.com", "project_key": "PROJ"},
    "llm": {"base_url": "http://localhost", "endpoint": "/gen"},
    "ui": {"issue_types": ["Task"], "components": ["Core"]},
    "task": {"backend": "json", "data_dir": ""},
}


@pytest.fixture
def service(tmp_path):
    config = {**MOCK_CONFIG, "task": {"backend": "json", "data_dir": str(tmp_path)}}
    with patch("services.json_service.load_config", return_value=config):
        svc = JsonService()
    return svc


class TestJsonServiceIsTaskService:
    def test_is_subclass_of_task_service(self):
        assert issubclass(JsonService, TaskService)


class TestNextTaskId:
    def test_returns_1_for_empty_dir(self, tmp_path):
        assert _next_task_id(str(tmp_path)) == 1

    def test_returns_1_for_nonexistent_dir(self, tmp_path):
        assert _next_task_id(str(tmp_path / "nonexistent")) == 1

    def test_sequential_after_existing(self, tmp_path):
        (tmp_path / "TASK-1.json").write_text("{}")
        (tmp_path / "TASK-3.json").write_text("{}")
        assert _next_task_id(str(tmp_path)) == 4

    def test_ignores_non_task_files(self, tmp_path):
        (tmp_path / "README.md").write_text("")
        (tmp_path / "TASK-2.json").write_text("{}")
        (tmp_path / "other-5.json").write_text("{}")
        assert _next_task_id(str(tmp_path)) == 3


class TestSubmitTask:
    def test_creates_json_file(self, service, tmp_path):
        result = service.submit_task("My Summary", "My Desc", "Task", "Core")
        assert result["key"] == "TASK-1"
        assert result["summary"] == "My Summary"
        assert result["description"] == "My Desc"
        assert result["type"] == "Task"
        assert result["component"] == "Core"

        file_path = tmp_path / "TASK-1.json"
        assert file_path.exists()
        data = json.loads(file_path.read_text())
        assert data["key"] == "TASK-1"
        assert data["summary"] == "My Summary"
        assert "created_at" in data

    def test_sequential_keys(self, service, tmp_path):
        service.submit_task("First", "Desc", "Task", "Core")
        service.submit_task("Second", "Desc", "Bug", "UI")
        assert (tmp_path / "TASK-1.json").exists()
        assert (tmp_path / "TASK-2.json").exists()

    def test_url_is_file_path(self, service, tmp_path):
        result = service.submit_task("Sum", "Desc", "Task", "")
        assert result["url"] == str(tmp_path / "TASK-1.json")

    def test_creates_data_dir_if_missing(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        config = {**MOCK_CONFIG, "task": {"backend": "json", "data_dir": str(nested)}}
        with patch("services.json_service.load_config", return_value=config):
            svc = JsonService()
        svc.submit_task("Sum", "Desc", "Task", "")
        assert (nested / "TASK-1.json").exists()

    def test_empty_component(self, service):
        result = service.submit_task("Sum", "Desc", "Bug", "")
        assert result["component"] == ""


class TestReloadConfig:
    def test_reload_updates_data_dir(self, service):
        new_config = {**MOCK_CONFIG, "task": {"backend": "json", "data_dir": "/new/path"}}
        service.reload_config(config=new_config)
        assert service.data_dir == "/new/path"

    def test_reload_without_config_calls_load_config(self, service):
        with patch("services.json_service.load_config", return_value=MOCK_CONFIG) as mock_load:
            service.reload_config()
            mock_load.assert_called_once()

    def test_defaults_data_dir_when_missing(self):
        config = {
            "jira": {"base_url": "x", "project_key": "X"},
            "llm": {"base_url": "x", "endpoint": "/x"},
            "ui": {"issue_types": [], "components": []},
            "task": {"backend": "json"},
        }
        with patch("services.json_service.load_config", return_value=config):
            svc = JsonService()
        assert svc.data_dir == "~/.config/CtrlLord/data"
