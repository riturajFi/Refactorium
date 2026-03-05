from __future__ import annotations

from enum import Enum
from typing import TypedDict


class SnapshotSource(str, Enum):
    REMOTE = "REMOTE"


class SnapshotReference(TypedDict):
    commit_hash: str
    branch_ref: str
    file_count: int
    source: SnapshotSource
