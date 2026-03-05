from __future__ import annotations

import unittest

from core.models.repository.errors import (
    EmptyBranchRefError,
    EmptyCommitHashError,
    EmptyFilePathError,
)
from core.models.repository.factory import new_snapshot


class SnapshotTests(unittest.TestCase):
    def test_new_snapshot_rejects_invalid_input(self) -> None:
        with self.assertRaises(EmptyCommitHashError):
            new_snapshot("", "origin/main", {"a.txt": b"x"})

        with self.assertRaises(EmptyBranchRefError):
            new_snapshot("abc", "", {"a.txt": b"x"})

        with self.assertRaises(EmptyFilePathError):
            new_snapshot("abc", "origin/main", {"": b"x"})

    def test_snapshot_is_immutable_via_returned_values(self) -> None:
        original = {
            "b.txt": b"beta",
            "a.txt": b"alpha",
        }

        snapshot = new_snapshot("commit-1", "origin/main", original)

        self.assertEqual(snapshot.branch_ref(), "origin/main")

        original["a.txt"] = b"Xlpha"
        original["new.txt"] = b"new"

        files = snapshot.files()
        self.assertEqual(files, ["a.txt", "b.txt"])

        files[0] = "mutated"
        files_again = snapshot.files()
        self.assertEqual(files_again[0], "a.txt")

        content, ok = snapshot.content("a.txt")
        self.assertTrue(ok)
        self.assertEqual(content, b"alpha")

        content_mutated = bytearray(content)
        content_mutated[0] = ord("Z")

        content_again, _ = snapshot.content("a.txt")
        self.assertEqual(content_again, b"alpha")

        content_map = snapshot.file_content_map()
        content_map["a.txt"] = b"Ylpha"
        content_map["other.txt"] = b"other"

        content_after_map_mutation, _ = snapshot.content("a.txt")
        self.assertEqual(content_after_map_mutation, b"alpha")
        _, exists = snapshot.content("other.txt")
        self.assertFalse(exists)


if __name__ == "__main__":
    unittest.main()
