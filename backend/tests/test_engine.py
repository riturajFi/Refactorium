from __future__ import annotations

import unittest

from refactorium.proposal import GenerationContext, NilCodeIndexError, new_proposal, validate_generation_input


class _FakeCodeIndex:
    def __init__(self, file_count: int) -> None:
        self._file_count = file_count

    def file_count(self) -> int:
        return self._file_count


class _FakeEngine:
    def generate(self, code_index: _FakeCodeIndex, ctx: GenerationContext):
        validate_generation_input(code_index, ctx)
        return new_proposal(
            "diff --git a/main.go b/main.go",
            "Refactors a branch for readability",
            1,
        )


class EngineTests(unittest.TestCase):
    def test_generation_context_validate_success(self) -> None:
        ctx: GenerationContext = {
            "repo_id": "https://github.com/example/repo.git",
            "session_id": "s-1",
        }
        validate_generation_input(_FakeCodeIndex(file_count=1), ctx)

    def test_generation_context_validate_rejects_empty_repo_id(self) -> None:
        ctx: GenerationContext = {"repo_id": "", "session_id": "s-1"}
        with self.assertRaises(ValueError):
            validate_generation_input(_FakeCodeIndex(file_count=1), ctx)

    def test_generation_context_validate_rejects_empty_session_id(self) -> None:
        ctx: GenerationContext = {"repo_id": "https://github.com/example/repo.git", "session_id": ""}
        with self.assertRaises(ValueError):
            validate_generation_input(_FakeCodeIndex(file_count=1), ctx)

    def test_validate_generation_input_rejects_nil_code_index(self) -> None:
        with self.assertRaises(NilCodeIndexError):
            validate_generation_input(
                None,
                {"repo_id": "https://github.com/example/repo.git", "session_id": "s-1"},
            )

    def test_engine_generates_proposal_from_code_index_and_context(self) -> None:
        engine = _FakeEngine()
        index = _FakeCodeIndex(file_count=10)
        ctx: GenerationContext = {
            "repo_id": "https://github.com/example/repo.git",
            "session_id": "s-1",
        }

        generated = engine.generate(index, ctx)
        self.assertNotEqual(generated.patch(), "")
        self.assertNotEqual(generated.explanation(), "")


if __name__ == "__main__":
    unittest.main()
