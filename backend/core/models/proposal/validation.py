from __future__ import annotations

from collections.abc import Collection
from pathlib import PurePosixPath
import re

from .schema import Proposal

_DIFF_HEADER_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")

VALIDATION_CHECKLIST: tuple[str, ...] = (
    "Patch must follow unified diff format.",
    "All modified files must exist in the repository snapshot.",
    "Patch must not modify files outside the repository snapshot.",
)


class ProposalValidationError(ValueError):
    """Base error for invalid proposal outputs."""


class InvalidUnifiedDiffError(ProposalValidationError):
    """Raised when unified_diff is not a valid unified diff patch."""


class UnknownChangedFileError(ProposalValidationError):
    """Raised when proposal references files missing from snapshot."""


class OutOfSnapshotPathError(ProposalValidationError):
    """Raised when proposal path escapes snapshot boundaries."""


def validate_proposal(proposal: Proposal, snapshot_files: Collection[str]) -> None:
    snapshot_set = {_normalize_repo_path(path) for path in snapshot_files}
    changed_files = {_normalize_repo_path(path) for path in proposal["changed_files"]}

    _validate_unified_diff(proposal["unified_diff"])
    diff_files = _extract_diff_paths(proposal["unified_diff"])

    unknown_from_list = changed_files - snapshot_set
    if unknown_from_list:
        missing = ", ".join(sorted(unknown_from_list))
        raise UnknownChangedFileError(f"changed_files contains paths outside snapshot: {missing}")

    unknown_from_patch = diff_files - snapshot_set
    if unknown_from_patch:
        missing = ", ".join(sorted(unknown_from_patch))
        raise OutOfSnapshotPathError(f"patch modifies paths outside snapshot: {missing}")


def _validate_unified_diff(unified_diff: str) -> None:
    lines = unified_diff.splitlines()
    has_header = any(_DIFF_HEADER_RE.match(line) for line in lines)
    has_hunk = any(line.startswith("@@") for line in lines)
    if not has_header or not has_hunk:
        raise InvalidUnifiedDiffError("unified_diff must contain valid diff headers and hunks")


def _extract_diff_paths(unified_diff: str) -> set[str]:
    files: set[str] = set()
    for line in unified_diff.splitlines():
        match = _DIFF_HEADER_RE.match(line)
        if match is None:
            continue

        a_path = _normalize_repo_path(match.group(1))
        b_path = _normalize_repo_path(match.group(2))
        if a_path != b_path:
            raise InvalidUnifiedDiffError("renames are not supported in proposal patch")
        files.add(a_path)

    if not files:
        raise InvalidUnifiedDiffError("unified_diff must include at least one modified file")
    return files


def _normalize_repo_path(path: str) -> str:
    candidate = path.strip()
    parsed = PurePosixPath(candidate)
    parts = parsed.parts
    if candidate == "" or parsed.is_absolute() or any(part == ".." for part in parts):
        raise OutOfSnapshotPathError(f"invalid repository-relative path: {path!r}")
    return parsed.as_posix()
