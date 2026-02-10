# jira_service.py
import random
import time
import logging
from atlassian import Jira

from services.config import load_config
from services.task_service import TaskService

logger = logging.getLogger(__name__)


class JiraService(TaskService):
    def __init__(self):
        self.reload_config()

    def generate_mock_task(self, summary: str, description: str, issue_type: str, component: str) -> dict:
        key = f"MOCK-{random.randint(100, 999)}"
        return {
            "key": key,
            "summary": summary,
            "description": description,
            "type": issue_type,
            "component": component,
            "url": f"{self.base_url}/browse/{key}"
        }

    def submit_task(self, summary: str, description: str, issue_type: str, component: str) -> dict:
        if self.mode == "mock":
            time.sleep(0.5)  # simulate network delay
            result = self.generate_mock_task(summary, description, issue_type, component)
            self.save_task_json(result)
            return result

        if not self.client:
            self.client = Jira(
                url=self.base_url,
                username=self.username,
                token=self.token
            )
        logger.info("Creating issue in project %s", self.project_key)
        try:
            issue = self.client.create_issue(fields={
                "project": {"key": self.project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
                "components": [{"name": component}] if component else []
            })
        except Exception as e:
            logger.error("Failed to create Jira issue: %s (type=%s, args=%s)", e, type(e).__name__, e.args)
            raise
        issue_key = issue.get("key", "UNKNOWN")
        logger.info("Created issue %s", issue_key)
        result = {
            "key": issue_key,
            "summary": summary,
            "description": description,
            "type": issue_type,
            "component": component,
            "url": f"{self.base_url.rstrip('/')}/browse/{issue_key}"
        }
        self.save_task_json(result)
        return result

    def reload_config(self, config=None):
        logger.info("JiraService config is reloading.")
        self.config = config or load_config()
        cfg = self.config.get("jira", {})
        self.base_url = cfg.get("base_url", "")
        self.project_key = cfg.get("project_key", "")
        self.mode = cfg.get("mode", "").lower()
        self.username = cfg.get("username", "")
        self.token = cfg.get("token", "")
        self.client = None
        task_cfg = self.config.get("task", {})
        self.data_dir = task_cfg.get("data_dir", "")
