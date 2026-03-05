from __future__ import annotations

import unittest

from core.models.session.snapshot_reference import SnapshotSource
from core.models.session.state import State
from core.models.session.factory import new_proposal_session
from core.runtime.store.store import InMemoryStore, SessionNotFoundError


class SessionStoreTests(unittest.TestCase):
    def test_in_memory_store_create_and_get(self) -> None:
        store = InMemoryStore()
        session = new_proposal_session("session-1", "repo-1")

        store.create(session)
        loaded = store.get("session-1")

        self.assertEqual(loaded.session_id(), "session-1")
        self.assertEqual(loaded.status(), State.CREATED)

    def test_in_memory_store_update_persists_state(self) -> None:
        store = InMemoryStore()
        session = new_proposal_session("session-2", "repo-1")
        store.create(session)

        loaded = store.get("session-2")
        loaded.transition_to(State.RUNNING)
        store.update(loaded)

        updated = store.get("session-2")
        self.assertEqual(updated.status(), State.RUNNING)

    def test_in_memory_store_get_missing_session(self) -> None:
        store = InMemoryStore()
        with self.assertRaises(SessionNotFoundError):
            store.get("does-not-exist")

    def test_in_memory_store_persists_snapshot_reference(self) -> None:
        store = InMemoryStore()
        session = new_proposal_session("session-3", "https://github.com/example/repo.git")
        session.transition_to(State.RUNNING)
        session.attach_snapshot(
            {
                "commit_hash": "deadbeef",
                "branch_ref": "origin/main",
                "file_count": 10,
                "source": SnapshotSource.REMOTE,
            }
        )

        store.create(session)

        loaded = store.get("session-3")
        snapshot_ref, ok = loaded.snapshot_reference()
        self.assertTrue(ok)
        self.assertEqual(snapshot_ref["commit_hash"], "deadbeef")
        self.assertEqual(snapshot_ref["file_count"], 10)


if __name__ == "__main__":
    unittest.main()
