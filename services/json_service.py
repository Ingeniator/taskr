import os
import logging

from services.config import load_config
from services.task_service import TaskService

logger = logging.getLogger(__name__)


def _next_task_id(data_dir: str) -> int:
    """Return the next sequential task ID based on existing files in data_dir."""
    if not os.path.isdir(data_dir):
        return 1
    max_id = 0
    for name in os.listdir(data_dir):
        if name.startswith("TASK-") and name.endswith(".json"):
            try:
                num = int(name[len("TASK-"):-len(".json")])
                max_id = max(max_id, num)
            except ValueError:
                continue
    return max_id + 1


class JsonService(TaskService):
    def __init__(self):
        self.reload_config()

    def submit_task(self, summary: str, description: str, issue_type: str, component: str) -> dict:
        data_dir = os.path.expanduser(self.data_dir)
        os.makedirs(data_dir, exist_ok=True)

        task_id = _next_task_id(data_dir)
        key = f"TASK-{task_id}"
        file_path = os.path.join(data_dir, f"{key}.json")

        result = {
            "key": key,
            "summary": summary,
            "description": description,
            "type": issue_type,
            "component": component,
            "url": file_path,
        }
        self.save_task_json(result)
        return result

    def reload_config(self, config=None):
        logger.info("JsonService config is reloading.")
        self.config = config or load_config()
        task_cfg = self.config.get("task", {})
        self.data_dir = task_cfg.get("data_dir", "~/.config/CtrlLord/data")
