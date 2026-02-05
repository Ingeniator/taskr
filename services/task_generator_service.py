# jira_generator_service.py
import logging
from services.config import load_config, get_resource_path
import httpx

logger = logging.getLogger(__name__)

REQUIRED_LLM_FIELDS = ("summary", "description", "type")


class TaskGeneratorService:
    def __init__(self):
        self.reload_config()

    def build_task_payload(self, summary: str) -> dict:
        if self.mode in ("mock"):
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
            logger.error("Failed to load prompt template: %s", e)
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
            data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error("LLM HTTP error: %s", e)
            return self._fallback(summary, f"LLM returned HTTP {e.response.status_code}")
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return self._fallback(summary, str(e))

        # Validate response schema
        missing = [f for f in REQUIRED_LLM_FIELDS if f not in data]
        if missing:
            logger.warning("LLM response missing fields: %s", missing)
            return {
                "summary": data.get("summary", summary),
                "description": data.get("description", ""),
                "type": data.get("type", "Task")
            }

        return data

    def reload_config(self, config=None):
        self.config = config or load_config()

        llm_cfg = self.config.get("llm", {})
        self.mode = llm_cfg.get("mode", "").lower()
        self.base_url = llm_cfg.get("base_url", "http://localhost:8008")
        self.endpoint = llm_cfg.get("endpoint", "/generate-jira")
        self.timeout = llm_cfg.get("timeout", 10)
        raw_prompt_path = llm_cfg.get("prompt_path", "resources/generate_jira_task.md")
        self.prompt_path = get_resource_path(raw_prompt_path)

    @staticmethod
    def _fallback(summary, error_msg):
        return {
            "summary": f"[Fallback] {summary}",
            "description": f"# [LLM Error]\n\nThe LLM failed to respond.\n\nError: {error_msg}",
            "type": "Task"
        }
