from __future__ import annotations

import json
import unittest

from cmd.server.http_server import Server
from core.models.job.job import Job, JobType
from core.models.session.factory import new_proposal_session
from core.models.session.snapshot_reference import SnapshotSource
from core.models.session.state import State
from core.runtime.store.store import InMemoryStore


class APIServerTests(unittest.TestCase):
    def test_create_session_api_returns_200_and_enqueues_snapshot_job(self) -> None:
        store = InMemoryStore()
        queue = _FakeQueue()
        server = Server(store, queue)
        client = server.handler().test_client()

        response = client.post(
            "/sessions",
            data=json.dumps({"repoId": "https://github.com/example/repo.git"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        create_resp = response.get_json()
        assert create_resp is not None
        self.assertNotEqual(create_resp["sessionId"], "")

        stored = store.get(create_resp["sessionId"])
        self.assertEqual(stored.status(), State.CREATED)

        self.assertEqual(len(queue.jobs), 1)
        self.assertEqual(queue.jobs[0]["session_id"], create_resp["sessionId"])
        self.assertEqual(queue.jobs[0]["type"], JobType.SNAPSHOT_CAPTURE)

    def test_get_session_status_api_returns_snapshot_metadata(self) -> None:
        store = InMemoryStore()
        server = Server(store, _FakeQueue())
        client = server.handler().test_client()

        proposal_session = new_proposal_session("session-42", "https://github.com/example/repo.git")
        proposal_session.transition_to(State.RUNNING)
        proposal_session.attach_snapshot(
            {
                "commit_hash": "commit-42",
                "branch_ref": "origin/main",
                "file_count": 1,
                "source": SnapshotSource.REMOTE,
            }
        )
        store.create(proposal_session)

        response = client.get("/sessions/session-42")
        self.assertEqual(response.status_code, 200)
        get_resp = response.get_json()
        assert get_resp is not None
        self.assertEqual(get_resp["status"], State.SNAPSHOT_READY.value)
        self.assertEqual(get_resp["snapshot"]["commitHash"], "commit-42")
        self.assertEqual(get_resp["snapshot"]["fileCount"], 1)
        self.assertEqual(get_resp["snapshot"]["source"], "REMOTE")

    def test_create_session_api_non_remote_repo_id_returns_400(self) -> None:
        store = InMemoryStore()
        server = Server(store, _FakeQueue())
        client = server.handler().test_client()

        response = client.post(
            "/sessions",
            data=json.dumps({"repoId": "local/path"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_get_session_status_api_invalid_session_id_returns_404(self) -> None:
        store = InMemoryStore()
        server = Server(store, _FakeQueue())
        client = server.handler().test_client()

        response = client.get("/sessions/unknown")
        self.assertEqual(response.status_code, 404)


class _FakeQueue:
    def __init__(self) -> None:
        self.jobs: list[Job] = []

    def enqueue(self, job: Job) -> None:
        self.jobs.append(job)

    def dequeue(self, timeout: float | None = None):  # noqa: ARG002
        raise RuntimeError("not used")

    def close(self) -> None:
        return


if __name__ == "__main__":
    unittest.main()
