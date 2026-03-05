from __future__ import annotations

import unittest

from core.models.repository.factory import new_snapshot
from core.models.repository.interface import Access, LoadedRepository


class _FakeLoadedRepository:
    def __init__(self, repo_id: str) -> None:
        self._repo_id = repo_id

    def get_snapshot(self, ref: str):
        return new_snapshot(
            f"commit-{self._repo_id}-{ref}",
            ref,
            {"README.md": b"hello"},
        )


class _FakeAccess:
    def load_repository(self, repo_id: str):
        return _FakeLoadedRepository(repo_id)


class RepositoryInterfaceTests(unittest.TestCase):
    def test_repository_contracts_can_be_implemented(self) -> None:
        access: Access = _FakeAccess()
        loaded: LoadedRepository = access.load_repository("repo-1")

        snapshot = loaded.get_snapshot("main")

        self.assertNotEqual(snapshot.commit_hash(), "")
        self.assertEqual(len(snapshot.files()), 1)


if __name__ == "__main__":
    unittest.main()
