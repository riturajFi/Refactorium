from __future__ import annotations

import unittest

from core.models.proposal import (
    InvalidUnifiedDiffError,
    OutOfSnapshotPathError,
    UnknownChangedFileError,
    validate_proposal,
)


class ProposalValidationTests(unittest.TestCase):
    def test_validate_proposal_success(self) -> None:
        proposal = {
            "unified_diff": (
                "diff --git a/app.py b/app.py\n"
                "index 1111111..2222222 100644\n"
                "--- a/app.py\n"
                "+++ b/app.py\n"
                "@@ -1 +1 @@\n"
                "-print('hello')\n"
                "+print('world')\n"
            ),
            "explanation": "Extract duplicate logic into helper.",
            "changed_files": ["app.py"],
        }

        validate_proposal(proposal, {"app.py", "README.md"})

    def test_validate_proposal_rejects_invalid_unified_diff(self) -> None:
        proposal = {
            "unified_diff": "print('not a patch')\n",
            "explanation": "refactor",
            "changed_files": ["app.py"],
        }

        with self.assertRaises(InvalidUnifiedDiffError):
            validate_proposal(proposal, {"app.py"})

    def test_validate_proposal_rejects_changed_files_outside_snapshot(self) -> None:
        proposal = {
            "unified_diff": (
                "diff --git a/app.py b/app.py\n"
                "@@ -1 +1 @@\n"
                "-a\n"
                "+b\n"
            ),
            "explanation": "refactor",
            "changed_files": ["missing.py"],
        }

        with self.assertRaises(UnknownChangedFileError):
            validate_proposal(proposal, {"app.py"})

    def test_validate_proposal_rejects_patch_paths_outside_snapshot(self) -> None:
        proposal = {
            "unified_diff": (
                "diff --git a/missing.py b/missing.py\n"
                "@@ -1 +1 @@\n"
                "-a\n"
                "+b\n"
            ),
            "explanation": "refactor",
            "changed_files": ["app.py"],
        }

        with self.assertRaises(OutOfSnapshotPathError):
            validate_proposal(proposal, {"app.py"})

    def test_validate_proposal_rejects_path_traversal(self) -> None:
        proposal = {
            "unified_diff": (
                "diff --git a/../evil.py b/../evil.py\n"
                "@@ -1 +1 @@\n"
                "-a\n"
                "+b\n"
            ),
            "explanation": "refactor",
            "changed_files": ["../evil.py"],
        }

        with self.assertRaises(OutOfSnapshotPathError):
            validate_proposal(proposal, {"app.py"})


if __name__ == "__main__":
    unittest.main()
