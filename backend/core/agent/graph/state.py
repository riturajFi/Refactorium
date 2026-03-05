from __future__ import annotations

from typing import TypedDict

from core.agent.spec import AgentStatus


class AgentState(TypedDict):
    """State model carried across graph nodes during exploration."""

    repository_tree: list[str]
    readme_summary: str
    explored_files: list[str]
    files_read: int
    duplicate_candidates: list[str]
    findings: list[str]
    tool_call_count: int
    iteration_count: int
    status: str


def new_agent_state() -> AgentState:
    """Create a fresh AgentState with safe defaults."""

    return {
        "repository_tree": [],
        "readme_summary": "",
        "explored_files": [],
        "files_read": 0,
        "duplicate_candidates": [],
        "findings": [],
        "tool_call_count": 0,
        "iteration_count": 0,
        "status": AgentStatus.EXPLORING.value,
    }
