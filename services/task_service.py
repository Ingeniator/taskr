import json
import os
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TaskService(ABC):
    @abstractmethod
    def submit_task(self, summary: str, description: str, issue_type: str, component: str) -> dict:
        """Submit a task and return dict with keys: key, summary, description, type, component, url."""

    @abstractmethod
    def reload_config(self, config=None):
        """Reload service configuration."""

    def save_task_json(self, result: dict):
        """Save task result as JSON file in data_dir (if configured)."""
        data_dir = getattr(self, "data_dir", None)
        if not data_dir:
            return
        data_dir = os.path.expanduser(data_dir)
        os.makedirs(data_dir, exist_ok=True)
        payload = {**result, "created_at": datetime.now(timezone.utc).isoformat()}
        path = os.path.join(data_dir, f"{result['key']}.json")
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
        logger.info("Saved task JSON to %s", path)
