from __future__ import annotations

from .errors import EmptyBranchRefError, EmptyCommitHashError, EmptyFilePathError


def validate_snapshot_inputs(commit_hash: str, branch_ref: str, files: dict[str, bytes]) -> None:
    if commit_hash == "":
        raise EmptyCommitHashError("snapshot commit hash is empty")
    if branch_ref == "":
        raise EmptyBranchRefError("snapshot branch reference is empty")
    for path in files:
        if path == "":
            raise EmptyFilePathError("snapshot file path is empty")
