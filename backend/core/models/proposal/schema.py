from __future__ import annotations

from typing import TypedDict


class Proposal(TypedDict):
    """Schema for a refactor proposal produced by the agent.

    Fields:
    - unified_diff: unified-diff patch text for the proposed code change.
    - explanation: concise reasoning for why the refactor is needed and safe.
    - changed_files: repository-relative file paths modified by the patch.
    """

    unified_diff: str
    explanation: str
    changed_files: list[str]
