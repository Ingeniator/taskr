import json
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def load_todays_tasks(data_dir: str) -> list[dict]:
    """Load all tasks created today (UTC) from JSON files in data_dir."""
    data_dir = os.path.expanduser(data_dir)
    if not os.path.isdir(data_dir):
        return []

    today = datetime.now(timezone.utc).date()
    tasks = []

    for name in os.listdir(data_dir):
        if not name.endswith(".json"):
            continue
        path = os.path.join(data_dir, name)
        try:
            with open(path) as f:
                task = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Skipping malformed file %s: %s", name, e)
            continue

        created_at = task.get("created_at")
        if not created_at:
            logger.warning("Skipping %s: missing created_at", name)
            continue

        try:
            dt = datetime.fromisoformat(created_at)
        except ValueError:
            logger.warning("Skipping %s: invalid created_at format", name)
            continue

        if dt.date() == today:
            tasks.append(task)

    tasks.sort(key=lambda t: t["created_at"], reverse=True)
    return tasks
