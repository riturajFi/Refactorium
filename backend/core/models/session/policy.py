from __future__ import annotations

from .errors import InvalidSnapshotRefError, InvalidTransitionError
from .snapshot_reference import SnapshotReference, SnapshotSource
from .state import State

ALLOWED_TRANSITIONS: dict[State, set[State]] = {
    State.CREATED: {State.RUNNING, State.SNAPSHOT_READY},
    State.RUNNING: {State.SNAPSHOT_READY, State.COMPLETED, State.FAILED},
    State.SNAPSHOT_READY: {State.COMPLETED, State.FAILED},
}


def ensure_transition_allowed(current: State, target: State) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current)
    if allowed is None or target not in allowed:
        raise InvalidTransitionError(
            f'invalid session state transition: "{current.value}" -> "{target.value}"'
        )


def validate_snapshot_reference(reference: SnapshotReference) -> None:
    if reference["commit_hash"] == "":
        raise InvalidSnapshotRefError("invalid snapshot reference: empty commit hash")
    if reference["branch_ref"] == "":
        raise InvalidSnapshotRefError("invalid snapshot reference: empty branch ref")
    if reference["file_count"] < 0:
        raise InvalidSnapshotRefError("invalid snapshot reference: negative file count")
    if reference["source"] != SnapshotSource.REMOTE:
        raise InvalidSnapshotRefError(
            f'invalid snapshot reference: unsupported source "{reference["source"]}"'
        )
