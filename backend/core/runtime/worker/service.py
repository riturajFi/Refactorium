from __future__ import annotations

import logging
from threading import Event

from core.models.job.job import Job, JobType
from core.models.repository.interface import Access
from core.runtime.queue.queue import QueueClosedError
from core.runtime.store.store import Store

from .jobs import JobHandler, build_default_handlers


class WorkerService:
    """Processes asynchronous proposal/session jobs."""

    def __init__(
        self,
        queue,
        store: Store,
        repo_access: Access,
        handlers: dict[JobType, JobHandler] | None = None,
    ) -> None:
        self._queue = queue
        self._handlers: dict[JobType, JobHandler] = build_default_handlers(store, repo_access)
        if handlers is not None:
            self._handlers.update(handlers)

    def register_handler(self, job_type: JobType, handler: JobHandler) -> None:
        self._handlers[job_type] = handler

    def run(self, stop_event: Event) -> None:
        while not stop_event.is_set():
            try:
                job = self._queue.dequeue(timeout=0.1)
            except TimeoutError:
                continue
            except QueueClosedError:
                return

            try:
                self.process_job(job)
            except Exception as exc:  # noqa: BLE001
                logging.warning(
                    "worker_job_failed type=%s session_id=%s err=%s",
                    job["type"],
                    job["session_id"],
                    exc,
                )

    def process_job(self, job: Job) -> None:
        handler = self._handlers.get(job["type"])
        if handler is None:
            raise ValueError(f'unsupported job type: "{job["type"]}"')
        handler(job)
