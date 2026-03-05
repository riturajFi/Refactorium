from __future__ import annotations

import time
import unittest

from core.models.session.errors import (
    EmptyRepoIDError,
    EmptySessionIDError,
    InvalidSnapshotRefError,
    InvalidTargetStateError,
    InvalidTransitionError,
    NoopTransitionError,
)
from core.models.session.factory import new_proposal_session
from core.models.session.snapshot_reference import SnapshotSource
from core.models.session.state import State


class ProposalSessionTests(unittest.TestCase):
    def test_new_proposal_session_success(self) -> None:
        session = new_proposal_session("s-1", "repo-1")
        self.assertEqual(session.session_id(), "s-1")
        self.assertEqual(session.repo_id(), "repo-1")

    def test_new_proposal_session_initial_state_and_times(self) -> None:
        session = new_proposal_session("s-1", "repo-1")
        self.assertEqual(session.status(), State.CREATED)
        self.assertEqual(session.created_at(), session.updated_at())

    def test_new_proposal_session_rejects_empty_session_id(self) -> None:
        with self.assertRaises(EmptySessionIDError):
            new_proposal_session("", "repo-1")

    def test_new_proposal_session_rejects_empty_repo_id(self) -> None:
        with self.assertRaises(EmptyRepoIDError):
            new_proposal_session("s-1", "")

    def test_transition_created_to_running_succeeds(self) -> None:
        session = new_proposal_session("s-1", "repo-1")
        old_updated_at = session.updated_at()
        time.sleep(0.002)

        session.transition_to(State.RUNNING)

        self.assertEqual(session.status(), State.RUNNING)
        self.assertGreater(session.updated_at(), old_updated_at)

    def test_transition_running_to_completed_succeeds(self) -> None:
        session = new_proposal_session("s-1", "repo-1")
        session.transition_to(State.RUNNING)
        session.transition_to(State.COMPLETED)
        self.assertEqual(session.status(), State.COMPLETED)

    def test_transition_running_to_failed_succeeds(self) -> None:
        session = new_proposal_session("s-1", "repo-1")
        session.transition_to(State.RUNNING)
        session.transition_to(State.FAILED)
        self.assertEqual(session.status(), State.FAILED)

    def test_transition_running_to_snapshot_ready_succeeds(self) -> None:
        session = new_proposal_session("s-1", "repo-1")
        session.transition_to(State.RUNNING)
        session.transition_to(State.SNAPSHOT_READY)
        self.assertEqual(session.status(), State.SNAPSHOT_READY)

    def test_transition_created_to_completed_fails(self) -> None:
        session = new_proposal_session("s-1", "repo-1")
        with self.assertRaises(InvalidTransitionError):
            session.transition_to(State.COMPLETED)

    def test_transition_completed_to_failed_fails(self) -> None:
        session = new_proposal_session("s-1", "repo-1")
        session.transition_to(State.RUNNING)
        session.transition_to(State.COMPLETED)

        with self.assertRaises(InvalidTransitionError):
            session.transition_to(State.FAILED)

    def test_transition_failed_to_running_fails(self) -> None:
        session = new_proposal_session("s-1", "repo-1")
        session.transition_to(State.RUNNING)
        session.transition_to(State.FAILED)

        with self.assertRaises(InvalidTransitionError):
            session.transition_to(State.RUNNING)

    def test_transition_to_same_state_fails(self) -> None:
        session = new_proposal_session("s-1", "repo-1")
        with self.assertRaises(NoopTransitionError):
            session.transition_to(State.CREATED)

    def test_transition_to_invalid_state_fails(self) -> None:
        session = new_proposal_session("s-1", "repo-1")
        with self.assertRaises(InvalidTargetStateError):
            session.transition_to("PENDING")

    def test_attach_snapshot_moves_to_snapshot_ready_and_stores_reference(self) -> None:
        session = new_proposal_session("s-1", "repo-1")
        session.transition_to(State.RUNNING)

        session.attach_snapshot(
            {
                "commit_hash": "abc123",
                "branch_ref": "origin/main",
                "file_count": 2,
                "source": SnapshotSource.REMOTE,
            }
        )

        self.assertEqual(session.status(), State.SNAPSHOT_READY)
        snapshot_ref, ok = session.snapshot_reference()
        self.assertTrue(ok)
        self.assertEqual(snapshot_ref["commit_hash"], "abc123")
        self.assertEqual(snapshot_ref["branch_ref"], "origin/main")
        self.assertEqual(snapshot_ref["file_count"], 2)
        self.assertEqual(snapshot_ref["source"], SnapshotSource.REMOTE)

    def test_attach_snapshot_rejects_invalid_reference(self) -> None:
        session = new_proposal_session("s-1", "repo-1")
        session.transition_to(State.RUNNING)

        with self.assertRaises(InvalidSnapshotRefError):
            session.attach_snapshot(
                {
                    "commit_hash": "",
                    "branch_ref": "origin/main",
                    "file_count": 1,
                    "source": SnapshotSource.REMOTE,
                }
            )


if __name__ == "__main__":
    unittest.main()
