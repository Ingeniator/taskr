
# tests/test_config.py

import os
import sys
import pytest
import toml
from unittest.mock import patch, mock_open, MagicMock

from services.config import validate_config, load_config, get_resource_path, setup_logging


VALID_CONFIG = {
    "jira": {
        "base_url": "https://jira.example.com",
        "project_key": "PROJ",
        "username": "user",
        "token": "token123",
    },
    "llm": {
        "base_url": "http://localhost:8001",
        "endpoint": "/generate-jira",
        "timeout": 10,
    },
    "ui": {
        "issue_types": ["Task", "Bug", "Story"],
        "components": ["Core", "UI"],
    },
}


class TestValidateConfig:
    def test_valid_config_passes(self):
        validate_config(VALID_CONFIG)  # should not raise

    def test_missing_jira_section(self):
        config = {k: v for k, v in VALID_CONFIG.items() if k != "jira"}
        with pytest.raises(ValueError, match="Missing required section.*jira"):
            validate_config(config)

    def test_missing_llm_section(self):
        config = {k: v for k, v in VALID_CONFIG.items() if k != "llm"}
        with pytest.raises(ValueError, match="Missing required section.*llm"):
            validate_config(config)

    def test_missing_ui_section(self):
        config = {k: v for k, v in VALID_CONFIG.items() if k != "ui"}
        with pytest.raises(ValueError, match="Missing required section.*ui"):
            validate_config(config)

    def test_missing_jira_base_url(self):
        config = {
            "jira": {"project_key": "PROJ"},
            "llm": VALID_CONFIG["llm"],
            "ui": VALID_CONFIG["ui"],
        }
        with pytest.raises(ValueError, match="Missing required key 'base_url' in.*jira"):
            validate_config(config)

    def test_missing_jira_project_key(self):
        config = {
            "jira": {"base_url": "https://jira.example.com"},
            "llm": VALID_CONFIG["llm"],
            "ui": VALID_CONFIG["ui"],
        }
        with pytest.raises(ValueError, match="Missing required key 'project_key' in.*jira"):
            validate_config(config)

    def test_missing_llm_base_url(self):
        config = {
            "jira": VALID_CONFIG["jira"],
            "llm": {"endpoint": "/gen"},
            "ui": VALID_CONFIG["ui"],
        }
        with pytest.raises(ValueError, match="Missing required key 'base_url' in.*llm"):
            validate_config(config)

    def test_missing_llm_endpoint(self):
        config = {
            "jira": VALID_CONFIG["jira"],
            "llm": {"base_url": "http://localhost"},
            "ui": VALID_CONFIG["ui"],
        }
        with pytest.raises(ValueError, match="Missing required key 'endpoint' in.*llm"):
            validate_config(config)

    def test_missing_ui_issue_types(self):
        config = {
            "jira": VALID_CONFIG["jira"],
            "llm": VALID_CONFIG["llm"],
            "ui": {"components": ["Core"]},
        }
        with pytest.raises(ValueError, match="Missing required key 'issue_types' in.*ui"):
            validate_config(config)

    def test_missing_ui_components(self):
        config = {
            "jira": VALID_CONFIG["jira"],
            "llm": VALID_CONFIG["llm"],
            "ui": {"issue_types": ["Task"]},
        }
        with pytest.raises(ValueError, match="Missing required key 'components' in.*ui"):
            validate_config(config)

    def test_empty_config(self):
        with pytest.raises(ValueError, match="Missing required section"):
            validate_config({})

    def test_multiple_errors_collected(self):
        with pytest.raises(ValueError) as exc_info:
            validate_config({})
        errors = str(exc_info.value)
        assert "jira" in errors
        assert "llm" in errors
        assert "ui" in errors

    def test_extra_keys_allowed(self):
        config = {**VALID_CONFIG, "extra": {"foo": "bar"}}
        validate_config(config)  # should not raise


class TestLoadConfig:
    def test_loads_existing_config(self, tmp_path):
        config_file = tmp_path / "config" / "config.toml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(toml.dumps(VALID_CONFIG))

        with patch("services.config.CONFIG_PATH", str(config_file)):
            config = load_config()

        assert config["jira"]["base_url"] == "https://jira.example.com"
        assert config["ui"]["issue_types"] == ["Task", "Bug", "Story"]

    def test_copies_default_when_missing(self, tmp_path):
        config_file = tmp_path / "config" / "config.toml"
        default_file = tmp_path / "default" / "config.toml"
        default_file.parent.mkdir(parents=True)
        default_file.write_text(toml.dumps(VALID_CONFIG))

        with patch("services.config.CONFIG_PATH", str(config_file)), \
             patch("services.config.get_resource_path", return_value=str(default_file)):
            config = load_config()

        assert config_file.exists()
        assert config["jira"]["project_key"] == "PROJ"

    def test_raises_on_invalid_config(self, tmp_path):
        config_file = tmp_path / "config" / "config.toml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(toml.dumps({"jira": {"base_url": "x"}}))

        with patch("services.config.CONFIG_PATH", str(config_file)):
            with pytest.raises(ValueError, match="Config validation failed"):
                load_config()


class TestGetResourcePath:
    def test_normal_mode(self):
        path = get_resource_path("resources/template.md")
        assert path.endswith("resources/template.md")
        assert os.path.isabs(path)

    def test_pyinstaller_mode(self):
        with patch.object(sys, '_MEIPASS', "/bundled/app", create=True):
            path = get_resource_path("resources/template.md")
        assert path == "/bundled/app/resources/template.md"


class TestSetupLogging:
    def test_adds_handlers(self):
        import logging
        root = logging.getLogger()
        initial_count = len(root.handlers)
        setup_logging()
        assert len(root.handlers) >= initial_count + 2  # file + console

        # Cleanup: remove added handlers
        for handler in root.handlers[initial_count:]:
            root.removeHandler(handler)
            handler.close()
