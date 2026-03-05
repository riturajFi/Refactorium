from __future__ import annotations


class EmptySessionIDError(ValueError):
    """Raised when session id is empty."""


class EmptyRepoIDError(ValueError):
    """Raised when repo id is empty."""


class InvalidTransitionError(ValueError):
    """Raised when requested state transition is invalid."""


class NoopTransitionError(ValueError):
    """Raised when transition target equals current state."""


class InvalidTargetStateError(ValueError):
    """Raised when transition target is not a valid state."""


class InvalidSnapshotRefError(ValueError):
    """Raised when snapshot reference metadata is invalid."""
