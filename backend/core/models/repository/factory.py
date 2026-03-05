from __future__ import annotations

from .policy import validate_snapshot_inputs
from .snapshot import Snapshot


def new_snapshot(commit_hash: str, branch_ref: str, files: dict[str, bytes]) -> Snapshot:
    validate_snapshot_inputs(commit_hash, branch_ref, files)

    normalized: dict[str, bytes] = {}
    for path, content in files.items():
        normalized[path] = bytes(content)

    return Snapshot(commit_hash=commit_hash, branch_ref=branch_ref, files=normalized)
