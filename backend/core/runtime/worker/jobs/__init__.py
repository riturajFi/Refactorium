from __future__ import annotations

from typing import Callable

from core.models.job.job import Job, JobType
from core.models.repository.interface import Access
from core.runtime.store.store import Store

from .snapshot_capture import build_snapshot_capture_handler, snapshot_job

JobHandler = Callable[[Job], None]


def build_default_handlers(store: Store, repo_access: Access) -> dict[JobType, JobHandler]:
    return {
        JobType.SNAPSHOT_CAPTURE: build_snapshot_capture_handler(store, repo_access),
    }


__all__ = [
    "JobHandler",
    "build_default_handlers",
    "build_snapshot_capture_handler",
    "snapshot_job",
]
