# jira_service.py
import random
import time
from atlassian import Jira

from services.config import load_config

class JiraService:
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
            return self.generate_mock_task(summary, description, issue_type, component)

        if not self.client:
            self.client = Jira(
                url = self.base_url,
                username = self.username,
                token = self.token
            )
        print(f"creating issue {self.project_key}")
        try:
            issue = self.client.create_issue(fields={
                "project": {"key": self.project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
                "components": [{"name": component}] if component else []
            })
        except Exception as e:
            print("❌ Exception occurred:")
            print(f"Type: {type(e)}")
            print(f"Args: {e.args}")
            raise
        issue_key = issue.get("key", "UNKNOWN")
        print(issue_key)
        return {
            "key": issue_key,
            "summary": summary,
            "description": description,
            "type": issue_type,
            "component": component,
            "url": f"{self.base_url.rstrip('/')}/browse/{issue_key}"
        }

    def reload_config(self):
        print("🔄 JiraService config is reloading.")
        self.config = load_config()
        cfg = self.config.get("jira", {})
        self.base_url = cfg.get("base_url", "")
        self.project_key = cfg.get("project_key", "")
        self.mode = cfg.get("mode", "").lower()
        self.username = cfg.get("username", "")
        self.token = cfg.get("token", "")
        self.client = None