# jira_generator_service.py
from services.config import load_config
import httpx

class TaskGeneratorService:
    def __init__(self, config=None):
        self.config = config or load_config()
        self.mode = self.config.get("mode", "mock").lower()

        llm_cfg = self.config.get("llm", {})
        self.base_url = llm_cfg.get("base_url", "http://localhost:8000")
        self.endpoint = llm_cfg.get("endpoint", "/generate-jira")
        self.timeout = llm_cfg.get("timeout", 10)
        self.prompt_path = llm_cfg.get("prompt_path", "resources/generate_jira_task.md")

    def build_task_payload(self, summary: str) -> dict:
        if self.mode in ("mock_llm", "mock"):
            return {
                "summary": f"generated {summary}",
                "description": "# [Concise, action-oriented summary]\n\n## Description\nBrief explanation of the task. What needs to be done and why?\n\n## Context\nWhat triggered this task? Is it related to a bug, a feature request, a customer need, or a refactor?\n\n## Acceptance Criteria / Definition of Done\n- [ ] Clear and testable success condition 1\n- [ ] Outcome or deliverable 2\n- [ ] Optional edge cases or error handling\n\n## Links & References\n- [Jira ticket / Design doc / PRD](https://)\n- Related tickets: ABC-123, XYZ-456",
                "type": "Bug"
            }
        
        # Load prompt template and inject summary
        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                template = f.read()
            prompt = template.replace("{{input}}", summary)
        except Exception as e:
            return {
                "summary": f"[Prompt Load Error] {summary}",
                "description": f"# Prompt error\n\nFailed to load or render prompt:\n\n{e}",
                "type": "Task"
            }

        # Live mode: call LLM
        url = self.base_url.rstrip("/") + self.endpoint
        try:
            response = httpx.post(
                url,
                json={"prompt": prompt},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ LLM call failed: {e}")
            return {
                "summary": f"[Fallback] {summary}",
                "description": f"# [LLM Error]\n\nThe LLM failed to respond.\n\nError: {e}",
                "type": "Task"
            }