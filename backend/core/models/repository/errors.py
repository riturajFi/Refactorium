from __future__ import annotations


class EmptyCommitHashError(ValueError):
    """Raised when snapshot commit hash is empty."""


class EmptyBranchRefError(ValueError):
    """Raised when snapshot branch ref is empty."""


class EmptyFilePathError(ValueError):
    """Raised when any snapshot file path is empty."""
