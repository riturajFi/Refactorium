from __future__ import annotations

"""Validation rules for agent-generated refactor proposals.

This module enforces a small, explicit checklist:
1. The patch must look like a unified diff.
2. Proposal-declared changed files must exist in the snapshot.
3. Patch-touched files must stay within snapshot boundaries.

Mini example:
- valid header: `diff --git a/app.py b/app.py`
- invalid path: `../secrets.txt` (rejected as out of snapshot)
"""

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
    """Validate a proposal against snapshot file boundaries.

    `snapshot_files` should be the repository files available in the captured
    snapshot that the proposal is allowed to modify.

    Mini example:
    - snapshot_files: `{"app.py", "utils/helpers.py"}`
    - proposal["changed_files"]: `["app.py"]` -> allowed
    - proposal["changed_files"]: `["missing.py"]` -> raises `UnknownChangedFileError`
    """
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
    """Require both file headers and at least one hunk marker."""
    # Mini examples:
    # valid:
    #   diff --git a/app.py b/app.py
    #   @@ -1 +1 @@
    # invalid (no header/hunk):
    #   print("not a patch")
    lines = unified_diff.splitlines()
    has_header = any(_DIFF_HEADER_RE.match(line) for line in lines)
    has_hunk = any(line.startswith("@@") for line in lines)
    if not has_header or not has_hunk:
        raise InvalidUnifiedDiffError("unified_diff must contain valid diff headers and hunks")


def _extract_diff_paths(unified_diff: str) -> set[str]:
    """Extract touched file paths from `diff --git` headers.

    Current scope keeps changes minimal by disallowing rename-style headers
    where `a/<path>` and `b/<path>` differ.

    Mini example:
    - allowed: `diff --git a/app.py b/app.py`
    - rejected rename: `diff --git a/old.py b/new.py`
    """
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
    """Normalize and validate repository-relative POSIX paths."""
    # Mini examples:
    # accepted: "src/main.py" -> "src/main.py"
    # rejected: "/etc/passwd", "../tmp/x.py", ""
    candidate = path.strip()
    parsed = PurePosixPath(candidate)
    parts = parsed.parts
    if candidate == "" or parsed.is_absolute() or any(part == ".." for part in parts):
        raise OutOfSnapshotPathError(f"invalid repository-relative path: {path!r}")
    return parsed.as_posix()
