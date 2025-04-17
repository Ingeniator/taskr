# jira_service.py
import random
import time
from jira import JIRA

from services.config import load_config

class JiraService:
    def __init__(self, config=None):
        self.config = config or load_config()
        self.base_url = self.config["jira"]["base_url"]
        self.project_key = self.config["jira"]["project_key"]

        self.mode = self.config.get("mode", "mock").lower()
        if self.mode in ("mock_llm", "live"):
            self.client = JIRA(
                server=self.config["jira"]["base_url"],
                basic_auth=(
                    self.config["jira"]["username"],
                    self.config["jira"]["api_token"]
                )
            )

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
        if self.mode in ("mock_jira", "mock"):
            time.sleep(0.5)  # simulate network delay
            return self.generate_mock_task(summary, description, issue_type, component)

        # Live mode: create real Jira issue 
        try:
            issue = self.client.create_issue(
                project=self.project_key,
                summary=summary,
                description=description,
                issuetype={"name": issue_type},
                components=[{"name": component}]
            )
            return {
                "key": issue.key,
                "summary": summary,
                "description": description,
                "type": issue_type,
                "component": component,
                "url": f"{self.base_url.rstrip('/')}/browse/{issue.key}"
            }
        except RequestException as e:
            raise RuntimeError(f"Jira request failed: {e}")
