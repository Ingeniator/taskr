
# tests/test_task_generator_service.py

import pytest
from unittest.mock import patch, MagicMock
import httpx

from services.task_generator_service import TaskGeneratorService, REQUIRED_LLM_FIELDS


MOCK_CONFIG = {
    "jira": {"base_url": "https://jira.example.com", "project_key": "P"},
    "llm": {
        "base_url": "http://localhost:8001",
        "endpoint": "/generate-jira",
        "timeout": 10,
        "mode": "mock",
        "prompt_path": "resources/generate_jira_task.md",
    },
    "ui": {"issue_types": ["Task"], "components": ["Core"]},
}

LIVE_CONFIG = {
    **MOCK_CONFIG,
    "llm": {**MOCK_CONFIG["llm"], "mode": "live"},
}


@pytest.fixture
def mock_service():
    with patch("services.task_generator_service.load_config", return_value=MOCK_CONFIG):
        return TaskGeneratorService()


@pytest.fixture
def live_service():
    with patch("services.task_generator_service.load_config", return_value=LIVE_CONFIG):
        return TaskGeneratorService()


class TestTaskGeneratorInit:
    def test_init_loads_config(self, mock_service):
        assert mock_service.mode == "mock"
        assert mock_service.base_url == "http://localhost:8001"
        assert mock_service.endpoint == "/generate-jira"
        assert mock_service.timeout == 10
        assert mock_service.prompt_path.endswith("resources/generate_jira_task.md")

    def test_defaults_for_missing_keys(self):
        config = {
            "jira": {"base_url": "x", "project_key": "P"},
            "llm": {},
            "ui": {"issue_types": [], "components": []},
        }
        with patch("services.task_generator_service.load_config", return_value=config):
            svc = TaskGeneratorService()
        assert svc.mode == ""
        assert svc.base_url == "http://localhost:8008"
        assert svc.endpoint == "/generate-jira"
        assert svc.timeout == 10


class TestMockMode:
    def test_returns_generated_summary(self, mock_service):
        result = mock_service.build_task_payload("fix login")
        assert result["summary"] == "generated fix login"

    def test_returns_description_template(self, mock_service):
        result = mock_service.build_task_payload("any task")
        assert "Description" in result["description"]
        assert "Acceptance Criteria" in result["description"]

    def test_returns_bug_type(self, mock_service):
        result = mock_service.build_task_payload("anything")
        assert result["type"] == "Bug"

    def test_has_all_required_fields(self, mock_service):
        result = mock_service.build_task_payload("test task")
        for field in REQUIRED_LLM_FIELDS:
            assert field in result


class TestLiveMode:
    def test_successful_llm_call(self, live_service, tmp_path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("Generate task for: {{input}}")
        live_service.prompt_path = str(prompt_file)

        llm_response = {
            "summary": "Implement login",
            "description": "## Details\nLogin implementation",
            "type": "Story",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = llm_response
        mock_response.raise_for_status = MagicMock()

        with patch("services.task_generator_service.httpx.post", return_value=mock_response) as mock_post:
            result = live_service.build_task_payload("login feature")

        mock_post.assert_called_once_with(
            "http://localhost:8001/generate-jira",
            json={"prompt": "Generate task for: login feature"},
            timeout=10,
        )
        assert result == llm_response

    def test_prompt_template_injection(self, live_service, tmp_path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("Task: {{input}} - please generate")
        live_service.prompt_path = str(prompt_file)

        mock_response = MagicMock()
        mock_response.json.return_value = {"summary": "s", "description": "d", "type": "Task"}
        mock_response.raise_for_status = MagicMock()

        with patch("services.task_generator_service.httpx.post", return_value=mock_response) as mock_post:
            live_service.build_task_payload("my task")

        call_args = mock_post.call_args
        prompt_sent = call_args[1]["json"]["prompt"]
        assert "my task" in prompt_sent
        assert "{{input}}" not in prompt_sent

    def test_url_construction_strips_trailing_slash(self, live_service, tmp_path):
        live_service.base_url = "http://localhost:8001/"
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("{{input}}")
        live_service.prompt_path = str(prompt_file)

        mock_response = MagicMock()
        mock_response.json.return_value = {"summary": "s", "description": "d", "type": "Task"}
        mock_response.raise_for_status = MagicMock()

        with patch("services.task_generator_service.httpx.post", return_value=mock_response) as mock_post:
            live_service.build_task_payload("test")

        url_used = mock_post.call_args[0][0]
        assert url_used == "http://localhost:8001/generate-jira"


class TestLiveModeErrors:
    def test_prompt_load_failure(self, live_service):
        live_service.prompt_path = "/nonexistent/prompt.md"
        result = live_service.build_task_payload("my task")
        assert "[Prompt Load Error]" in result["summary"]
        assert "my task" in result["summary"]
        assert result["type"] == "Task"

    def test_http_status_error(self, live_service, tmp_path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("{{input}}")
        live_service.prompt_path = str(prompt_file)

        mock_request = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch("services.task_generator_service.httpx.post") as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "Server Error", request=mock_request, response=mock_resp
            )
            result = live_service.build_task_payload("test")

        assert "[Fallback]" in result["summary"]
        assert "test" in result["summary"]
        assert "500" in result["description"]
        assert result["type"] == "Task"

    def test_network_error(self, live_service, tmp_path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("{{input}}")
        live_service.prompt_path = str(prompt_file)

        with patch("services.task_generator_service.httpx.post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")
            result = live_service.build_task_payload("test")

        assert "[Fallback]" in result["summary"]
        assert "Connection refused" in result["description"]

    def test_timeout_error(self, live_service, tmp_path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("{{input}}")
        live_service.prompt_path = str(prompt_file)

        with patch("services.task_generator_service.httpx.post") as mock_post:
            mock_post.side_effect = httpx.ReadTimeout("Timeout")
            result = live_service.build_task_payload("test")

        assert "[Fallback]" in result["summary"]
        assert result["type"] == "Task"

    def test_invalid_json_response(self, live_service, tmp_path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("{{input}}")
        live_service.prompt_path = str(prompt_file)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch("services.task_generator_service.httpx.post", return_value=mock_response):
            result = live_service.build_task_payload("test")

        assert "[Fallback]" in result["summary"]


class TestMissingResponseFields:
    def test_missing_summary_uses_input(self, live_service, tmp_path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("{{input}}")
        live_service.prompt_path = str(prompt_file)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"description": "d", "type": "Bug"}

        with patch("services.task_generator_service.httpx.post", return_value=mock_response):
            result = live_service.build_task_payload("my input")

        assert result["summary"] == "my input"

    def test_missing_description_defaults_empty(self, live_service, tmp_path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("{{input}}")
        live_service.prompt_path = str(prompt_file)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"summary": "s", "type": "Task"}

        with patch("services.task_generator_service.httpx.post", return_value=mock_response):
            result = live_service.build_task_payload("test")

        assert result["description"] == ""

    def test_missing_type_defaults_to_task(self, live_service, tmp_path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("{{input}}")
        live_service.prompt_path = str(prompt_file)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"summary": "s", "description": "d"}

        with patch("services.task_generator_service.httpx.post", return_value=mock_response):
            result = live_service.build_task_payload("test")

        assert result["type"] == "Task"

    def test_all_fields_missing(self, live_service, tmp_path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text("{{input}}")
        live_service.prompt_path = str(prompt_file)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"extra": "field"}

        with patch("services.task_generator_service.httpx.post", return_value=mock_response):
            result = live_service.build_task_payload("original")

        assert result["summary"] == "original"
        assert result["description"] == ""
        assert result["type"] == "Task"


class TestFallback:
    def test_fallback_format(self):
        result = TaskGeneratorService._fallback("my task", "some error")
        assert result["summary"] == "[Fallback] my task"
        assert "some error" in result["description"]
        assert "LLM Error" in result["description"]
        assert result["type"] == "Task"


class TestReloadConfig:
    def test_reload_with_new_config(self, mock_service):
        new_config = {
            "llm": {
                "base_url": "http://new-host:9000",
                "endpoint": "/new-endpoint",
                "timeout": 30,
                "mode": "live",
                "prompt_path": "/new/prompt.md",
            }
        }
        mock_service.reload_config(config=new_config)
        assert mock_service.base_url == "http://new-host:9000"
        assert mock_service.endpoint == "/new-endpoint"
        assert mock_service.timeout == 30
        assert mock_service.mode == "live"
        assert mock_service.prompt_path == "/new/prompt.md"

    def test_reload_without_config_calls_load_config(self, mock_service):
        with patch("services.task_generator_service.load_config", return_value=LIVE_CONFIG) as mock_load:
            mock_service.reload_config()
            mock_load.assert_called_once()
