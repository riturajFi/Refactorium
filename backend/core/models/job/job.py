from __future__ import annotations

from enum import Enum
from typing import TypedDict


class JobType(str, Enum):
    SNAPSHOT_CAPTURE = "SNAPSHOT_CAPTURE"


class Job(TypedDict):
    type: JobType
    session_id: str
    repo_id: str
    ref: str
