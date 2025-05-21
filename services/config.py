import yaml
import os
import sys
import shutil
CONFIG_PATH = os.path.expanduser("~/Library/Application Support/JiraQuickTask/config.yaml")

def get_resource_path(rel_path):
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller bundle
        return os.path.join(sys._MEIPASS, rel_path)
    return os.path.join(os.path.abspath("."), rel_path)

def load_config():
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        default_config_path=get_resource_path("config/config.yaml")
        shutil.copy(default_config_path, CONFIG_PATH)
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)
