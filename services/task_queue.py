import logging
import queue
from dataclasses import dataclass

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


@dataclass
class TaskPayload:
    summary: str
    description: str
    issue_type: str
    component: str


class TaskQueueWorker(QThread):
    task_completed = Signal(dict)
    task_failed = Signal(str, object)  # (error_message, payload)

    def __init__(self, jira_service):
        super().__init__()
        self._queue = queue.Queue()
        self._jira = jira_service

    def enqueue(self, payload: TaskPayload):
        self._queue.put(payload)

    def stop(self):
        self._queue.put(None)

    def run(self):
        while True:
            payload = self._queue.get()
            if payload is None:
                logger.info("TaskQueueWorker received stop sentinel, exiting.")
                break
            try:
                result = self._jira.submit_task(
                    payload.summary,
                    payload.description,
                    payload.issue_type,
                    payload.component,
                )
                self.task_completed.emit(result)
            except Exception as e:
                logger.error("Background task submission failed: %s", e, exc_info=True)
                self.task_failed.emit(str(e), payload)
