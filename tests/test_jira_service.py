
# tests/test_jira_service.py

import pytest
from unittest.mock import patch, MagicMock

from services.jira_service import JiraService


MOCK_CONFIG = {
    "jira": {
        "base_url": "https://jira.example.com",
        "project_key": "PROJ",
        "mode": "mock",
        "username": "user",
        "token": "secret",
    },
    "llm": {"base_url": "http://localhost", "endpoint": "/gen"},
    "ui": {"issue_types": ["Task"], "components": ["Core"]},
}

LIVE_CONFIG = {
    **MOCK_CONFIG,
    "jira": {**MOCK_CONFIG["jira"], "mode": "live"},
}


@pytest.fixture
def mock_service():
    with patch("services.jira_service.load_config", return_value=MOCK_CONFIG):
        return JiraService()


@pytest.fixture
def live_service():
    with patch("services.jira_service.load_config", return_value=LIVE_CONFIG):
        return JiraService()


class TestJiraServiceInit:
    def test_init_loads_config(self, mock_service):
        assert mock_service.base_url == "https://jira.example.com"
        assert mock_service.project_key == "PROJ"
        assert mock_service.mode == "mock"
        assert mock_service.username == "user"
        assert mock_service.token == "secret"
        assert mock_service.client is None

    def test_init_defaults_for_missing_keys(self):
        minimal_config = {
            "jira": {},
            "llm": {"base_url": "http://x", "endpoint": "/e"},
            "ui": {"issue_types": [], "components": []},
        }
        with patch("services.jira_service.load_config", return_value=minimal_config):
            svc = JiraService()
        assert svc.base_url == ""
        assert svc.project_key == ""
        assert svc.mode == ""
        assert svc.username == ""
        assert svc.token == ""


class TestGenerateMockTask:
    def test_returns_expected_fields(self, mock_service):
        result = mock_service.generate_mock_task("Sum", "Desc", "Bug", "Core")
        assert result["summary"] == "Sum"
        assert result["description"] == "Desc"
        assert result["type"] == "Bug"
        assert result["component"] == "Core"
        assert result["key"].startswith("MOCK-")
        assert "browse/MOCK-" in result["url"]

    def test_key_is_random(self, mock_service):
        keys = {
            mock_service.generate_mock_task("S", "D", "T", "C")["key"]
            for _ in range(20)
        }
        assert len(keys) > 1  # at least 2 distinct keys across 20 runs

    def test_url_uses_base_url(self, mock_service):
        result = mock_service.generate_mock_task("S", "D", "T", "C")
        assert result["url"].startswith("https://jira.example.com/browse/")


class TestSubmitTaskMockMode:
    def test_returns_mock_result(self, mock_service):
        result = mock_service.submit_task("My Summary", "My Desc", "Task", "UI")
        assert result["key"].startswith("MOCK-")
        assert result["summary"] == "My Summary"
        assert result["description"] == "My Desc"
        assert result["type"] == "Task"
        assert result["component"] == "UI"

    def test_empty_component(self, mock_service):
        result = mock_service.submit_task("Sum", "Desc", "Bug", "")
        assert result["component"] == ""


class TestSubmitTaskLiveMode:
    def test_creates_jira_issue(self, live_service):
        mock_client = MagicMock()
        mock_client.create_issue.return_value = {"key": "PROJ-42"}
        live_service.client = mock_client

        result = live_service.submit_task("Fix bug", "Description", "Bug", "Core")

        mock_client.create_issue.assert_called_once_with(fields={
            "project": {"key": "PROJ"},
            "summary": "Fix bug",
            "description": "Description",
            "issuetype": {"name": "Bug"},
            "components": [{"name": "Core"}],
        })
        assert result["key"] == "PROJ-42"
        assert result["url"] == "https://jira.example.com/browse/PROJ-42"

    def test_creates_issue_without_component(self, live_service):
        mock_client = MagicMock()
        mock_client.create_issue.return_value = {"key": "PROJ-10"}
        live_service.client = mock_client

        result = live_service.submit_task("Task", "Desc", "Story", "")

        call_args = mock_client.create_issue.call_args
        assert call_args[1]["fields"]["components"] == []
        assert result["key"] == "PROJ-10"

    def test_initializes_client_on_first_call(self, live_service):
        assert live_service.client is None
        with patch("services.jira_service.Jira") as MockJira:
            mock_instance = MagicMock()
            mock_instance.create_issue.return_value = {"key": "PROJ-1"}
            MockJira.return_value = mock_instance

            live_service.submit_task("Sum", "Desc", "Task", "")

            MockJira.assert_called_once_with(
                url="https://jira.example.com",
                username="user",
                token="secret",
            )

    def test_raises_on_jira_api_error(self, live_service):
        mock_client = MagicMock()
        mock_client.create_issue.side_effect = Exception("API error")
        live_service.client = mock_client

        with pytest.raises(Exception, match="API error"):
            live_service.submit_task("Sum", "Desc", "Bug", "Core")

    def test_handles_missing_key_in_response(self, live_service):
        mock_client = MagicMock()
        mock_client.create_issue.return_value = {}  # no "key" field
        live_service.client = mock_client

        result = live_service.submit_task("Sum", "Desc", "Task", "")
        assert result["key"] == "UNKNOWN"

    def test_url_strips_trailing_slash(self):
        config = {
            **LIVE_CONFIG,
            "jira": {**LIVE_CONFIG["jira"], "base_url": "https://jira.example.com/"},
        }
        with patch("services.jira_service.load_config", return_value=config):
            svc = JiraService()
        mock_client = MagicMock()
        mock_client.create_issue.return_value = {"key": "PROJ-5"}
        svc.client = mock_client

        result = svc.submit_task("Sum", "Desc", "Task", "")
        assert result["url"] == "https://jira.example.com/browse/PROJ-5"


class TestReloadConfig:
    def test_reload_with_new_config(self, mock_service):
        new_config = {
            "jira": {
                "base_url": "https://new-jira.com",
                "project_key": "NEW",
                "mode": "live",
                "username": "newuser",
                "token": "newtoken",
            }
        }
        mock_service.reload_config(config=new_config)
        assert mock_service.base_url == "https://new-jira.com"
        assert mock_service.project_key == "NEW"
        assert mock_service.mode == "live"
        assert mock_service.client is None  # reset on reload

    def test_reload_resets_client(self, live_service):
        live_service.client = MagicMock()
        live_service.reload_config(config=MOCK_CONFIG)
        assert live_service.client is None

    def test_reload_without_config_calls_load_config(self, mock_service):
        with patch("services.jira_service.load_config", return_value=LIVE_CONFIG) as mock_load:
            mock_service.reload_config()
            mock_load.assert_called_once()
