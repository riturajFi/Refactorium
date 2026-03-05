from __future__ import annotations

import unittest
from datetime import datetime, timezone

from refactorium.proposal import (
    EmptyExplanationError,
    EmptyPatchError,
    InvalidTimestampError,
    InvalidVersionError,
    Metadata,
    new_proposal,
    new_proposal_with_metadata,
)


class ProposalTests(unittest.TestCase):
    def test_new_proposal_success(self) -> None:
        proposal = new_proposal("diff --git a/a.txt b/a.txt", "Renames variable for clarity", 1)

        self.assertNotEqual(proposal.patch(), "")
        self.assertEqual(proposal.explanation(), "Renames variable for clarity")
        self.assertEqual(proposal.metadata()["version"], 1)
        self.assertIsNotNone(proposal.metadata()["timestamp"])

    def test_new_proposal_rejects_empty_patch(self) -> None:
        with self.assertRaises(EmptyPatchError):
            new_proposal("", "explanation", 1)

    def test_new_proposal_rejects_empty_explanation(self) -> None:
        with self.assertRaises(EmptyExplanationError):
            new_proposal("patch", "", 1)

    def test_new_proposal_rejects_invalid_version(self) -> None:
        with self.assertRaises(InvalidVersionError):
            new_proposal("patch", "explanation", 0)

    def test_new_proposal_with_metadata_rejects_invalid_timestamp(self) -> None:
        with self.assertRaises(InvalidTimestampError):
            new_proposal_with_metadata(
                "patch",
                "explanation",
                {"timestamp": None, "version": 1},  # type: ignore[typeddict-item]
            )

    def test_metadata_returned_as_copy(self) -> None:
        original_ts = datetime(2026, 3, 3, 10, 0, 0, tzinfo=timezone.utc)
        proposal = new_proposal_with_metadata(
            "patch",
            "explanation",
            {"timestamp": original_ts, "version": 2},
        )

        metadata = proposal.metadata()
        metadata = {"timestamp": datetime(2030, 1, 1, tzinfo=timezone.utc), "version": 99}
        self.assertEqual(metadata["version"], 99)

        self.assertEqual(proposal.metadata()["version"], 2)
        self.assertEqual(proposal.metadata()["timestamp"], original_ts)


if __name__ == "__main__":
    unittest.main()
