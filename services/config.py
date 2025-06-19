import toml
import os
import sys
import shutil
from platformdirs import user_config_path
CONFIG_DIR = user_config_path(appname="CtrlLord", appauthor="CtrlLord")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config/config.toml")

def get_resource_path(rel_path):
    if hasattr(sys, '_MEIPASS'):
        print("🧩 Running from:", sys._MEIPASS)
        # PyInstaller bundle
        return os.path.join(sys._MEIPASS, rel_path)
    return os.path.join(os.path.abspath("."), rel_path)

def load_config():
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        default_config_path=get_resource_path("config/config.toml")
        print("🔍 Looking for default config at:", default_config_path)
        print("🧪 File exists:", os.path.exists(default_config_path))
        shutil.copy(default_config_path, CONFIG_PATH)
    with open(CONFIG_PATH, "r") as f:
        return toml.load(f)
