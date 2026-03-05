from __future__ import annotations

from datetime import datetime, timezone

from .errors import InvalidTargetStateError, NoopTransitionError
from .policy import ensure_transition_allowed, validate_snapshot_reference
from .snapshot_reference import SnapshotReference, SnapshotSource
from .state import State


class ProposalSession:
    """Proposal session metadata and lifecycle state."""

    def __init__(
        self,
        session_id: str,
        repo_id: str,
        status: State,
        created_at: datetime,
        updated_at: datetime,
        snapshot: SnapshotReference | None = None,
    ) -> None:
        self._session_id = session_id
        self._repo_id = repo_id
        self._status = status
        self._created_at = created_at
        self._updated_at = updated_at
        self._snapshot = snapshot

    def session_id(self) -> str:
        return self._session_id

    def repo_id(self) -> str:
        return self._repo_id

    def status(self) -> State:
        return self._status

    def created_at(self) -> datetime:
        return self._created_at

    def updated_at(self) -> datetime:
        return self._updated_at

    def snapshot_reference(self) -> tuple[SnapshotReference, bool]:
        if self._snapshot is None:
            return {
                "commit_hash": "",
                "branch_ref": "",
                "file_count": 0,
                "source": SnapshotSource.REMOTE,
            }, False

        copied: SnapshotReference = {
            "commit_hash": self._snapshot["commit_hash"],
            "branch_ref": self._snapshot["branch_ref"],
            "file_count": self._snapshot["file_count"],
            "source": self._snapshot["source"],
        }
        return copied, True

    def attach_snapshot(self, reference: SnapshotReference) -> None:
        validate_snapshot_reference(reference)
        self.transition_to(State.SNAPSHOT_READY)
        self._snapshot = {
            "commit_hash": reference["commit_hash"],
            "branch_ref": reference["branch_ref"],
            "file_count": reference["file_count"],
            "source": reference["source"],
        }

    def transition_to(self, next_state: State | str) -> None:
        try:
            target = next_state if isinstance(next_state, State) else State(next_state)
        except ValueError as exc:
            raise InvalidTargetStateError(f'invalid target session state: "{next_state}"') from exc

        if self._status == target:
            raise NoopTransitionError(f'no-op session state transition: "{target.value}"')

        ensure_transition_allowed(self._status, target)
        self._status = target
        self._updated_at = datetime.now(timezone.utc)

    def clone(self) -> ProposalSession:
        snapshot_copy = None
        if self._snapshot is not None:
            snapshot_copy = {
                "commit_hash": self._snapshot["commit_hash"],
                "branch_ref": self._snapshot["branch_ref"],
                "file_count": self._snapshot["file_count"],
                "source": self._snapshot["source"],
            }

        return ProposalSession(
            session_id=self._session_id,
            repo_id=self._repo_id,
            status=self._status,
            created_at=self._created_at,
            updated_at=self._updated_at,
            snapshot=snapshot_copy,
        )
