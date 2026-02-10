import toml
import os
import sys
import shutil
import logging
from platformdirs import user_config_path

logger = logging.getLogger(__name__)

CONFIG_DIR = user_config_path(appname="CtrlLord", appauthor="CtrlLord")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config/config.toml")

REQUIRED_SECTIONS = {
    "jira": ["base_url", "project_key"],
    "llm": ["base_url", "endpoint"],
    "ui": ["issue_types", "components"],
    "task": ["backend", "data_dir"],
}


def get_resource_path(rel_path):
    if hasattr(sys, '_MEIPASS'):
        logger.debug("Running from PyInstaller bundle: %s", sys._MEIPASS)
        return os.path.join(sys._MEIPASS, rel_path)
    # Resolve relative to the project root (where ctrllord.py lives)
    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(package_dir, rel_path)


def setup_logging():
    """Configure logging with file and console handlers."""
    log_path = "/tmp/ctrllord.log"
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_path, mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "[%(levelname)s] %(name)s: %(message)s"
    ))
    root.addHandler(console_handler)


def validate_config(config):
    """Validate that required sections and keys exist in config."""
    errors = []
    for section, keys in REQUIRED_SECTIONS.items():
        if section not in config:
            errors.append(f"Missing required section: [{section}]")
            continue
        for key in keys:
            if key not in config[section]:
                errors.append(f"Missing required key '{key}' in [{section}]")
    if errors:
        raise ValueError("Config validation failed:\n" + "\n".join(errors))


def load_config():
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        default_config_path = get_resource_path("config/config.toml")
        logger.info("Copying default config from %s", default_config_path)
        shutil.copy(default_config_path, CONFIG_PATH)
    with open(CONFIG_PATH, "r") as f:
        config = toml.load(f)
    validate_config(config)
    return config
