from __future__ import annotations

from collections import deque
from threading import Condition
from time import monotonic

from core.models.job.job import Job, JobType


class QueueClosedError(RuntimeError):
    """Raised when queue is closed and cannot produce jobs."""


class JobQueue:
    def enqueue(self, job: Job) -> None:
        raise NotImplementedError

    def dequeue(self, timeout: float | None = None) -> Job:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class InMemoryQueue(JobQueue):
    """In-process queue implementation for local/single-node usage."""

    def __init__(self, buffer_size: int) -> None:
        if buffer_size < 1:
            buffer_size = 1

        self._buffer_size = buffer_size
        self._jobs: deque[Job] = deque()
        self._closed = False
        self._cond = Condition()

    def enqueue(self, job: Job) -> None:
        with self._cond:
            if self._closed:
                raise QueueClosedError("job queue closed")

            while len(self._jobs) >= self._buffer_size and not self._closed:
                self._cond.wait(timeout=0.1)

            if self._closed:
                raise QueueClosedError("job queue closed")

            self._jobs.append(job)
            self._cond.notify_all()

    def dequeue(self, timeout: float | None = None) -> Job:
        deadline = None if timeout is None else monotonic() + timeout

        with self._cond:
            while True:
                if self._jobs:
                    job = self._jobs.popleft()
                    self._cond.notify_all()
                    return job

                if self._closed:
                    raise QueueClosedError("job queue closed")

                if deadline is not None:
                    remaining = deadline - monotonic()
                    if remaining <= 0:
                        raise TimeoutError("dequeue timeout")
                    self._cond.wait(timeout=remaining)
                else:
                    self._cond.wait()

    def close(self) -> None:
        with self._cond:
            self._closed = True
            self._cond.notify_all()


Broker = JobQueue
InMemoryBroker = InMemoryQueue


def new_in_memory_queue(buffer_size: int) -> InMemoryQueue:
    return InMemoryQueue(buffer_size)


def new_in_memory_broker(buffer_size: int) -> InMemoryQueue:
    return InMemoryQueue(buffer_size)


def validate_snapshot_job(job: Job) -> None:
    if job["type"] != JobType.SNAPSHOT_CAPTURE:
        raise ValueError(f'unsupported job type: "{job["type"]}"')
    if job["session_id"] == "":
        raise ValueError("session id is empty")
    if job["repo_id"] == "":
        raise ValueError("repo id is empty")
