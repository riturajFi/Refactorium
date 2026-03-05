from __future__ import annotations

import unittest

from core.models.job.job import Job, JobType
from core.models.session.factory import new_proposal_session
from core.models.repository.factory import new_snapshot
from core.models.session.state import State
from core.runtime.queue.queue import new_in_memory_broker
from core.runtime.store.store import InMemoryStore
from core.runtime.worker.service import WorkerService as Service


class WorkerServiceTests(unittest.TestCase):
    def test_worker_processes_snapshot_job_and_updates_session(self) -> None:
        store = InMemoryStore()
        proposal_session = new_proposal_session("s-1", "https://github.com/example/repo.git")
        store.create(proposal_session)

        repo_access = _FakeRepoAccess(
            snapshot=_must_snapshot(
                "commit-1",
                "origin/main",
                {
                    "README.md": b"hello",
                    "a.go": b"package main",
                },
            )
        )
        service = Service(new_in_memory_broker(1), store, repo_access)

        service.process_job(
            {
                "type": JobType.SNAPSHOT_CAPTURE,
                "session_id": "s-1",
                "repo_id": "https://github.com/example/repo.git",
                "ref": "origin/main",
            }
        )

        found = store.get("s-1")
        self.assertEqual(found.status(), State.SNAPSHOT_READY)
        snapshot_ref, ok = found.snapshot_reference()
        self.assertTrue(ok)
        self.assertEqual(snapshot_ref["commit_hash"], "commit-1")
        self.assertEqual(snapshot_ref["file_count"], 2)

    def test_worker_marks_session_failed_on_repository_error(self) -> None:
        store = InMemoryStore()
        proposal_session = new_proposal_session("s-2", "https://github.com/example/repo.git")
        store.create(proposal_session)

        service = Service(new_in_memory_broker(1), store, _FakeRepoAccess(load_error=RuntimeError("repo down")))

        with self.assertRaises(RuntimeError):
            service.process_job(
                {
                    "type": JobType.SNAPSHOT_CAPTURE,
                    "session_id": "s-2",
                    "repo_id": "https://github.com/example/repo.git",
                    "ref": "",
                }
            )

        found = store.get("s-2")
        self.assertEqual(found.status(), State.FAILED)

    def test_worker_executes_registered_handler_for_job_type(self) -> None:
        store = InMemoryStore()
        service = Service(new_in_memory_broker(1), store, _FakeRepoAccess(snapshot=None))

        calls: list[Job] = []

        def _custom_handler(job: Job) -> None:
            calls.append(job)

        service.register_handler(JobType.SNAPSHOT_CAPTURE, _custom_handler)
        job: Job = {
            "type": JobType.SNAPSHOT_CAPTURE,
            "session_id": "s-3",
            "repo_id": "https://github.com/example/repo.git",
            "ref": "",
        }

        service.process_job(job)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], job)


class _FakeRepoAccess:
    def __init__(self, snapshot=None, load_error: Exception | None = None, get_error: Exception | None = None):
        self._snapshot = snapshot
        self._load_error = load_error
        self._get_error = get_error

    def load_repository(self, _repo_id: str):
        if self._load_error is not None:
            raise self._load_error
        return _FakeLoadedRepository(self._snapshot, self._get_error)


class _FakeLoadedRepository:
    def __init__(self, snapshot, get_error: Exception | None) -> None:
        self._snapshot = snapshot
        self._get_error = get_error

    def get_snapshot(self, _ref: str):
        if self._get_error is not None:
            raise self._get_error
        return self._snapshot


def _must_snapshot(commit_hash: str, branch_ref: str, files: dict[str, bytes]):
    return new_snapshot(commit_hash, branch_ref, files)


if __name__ == "__main__":
    unittest.main()
