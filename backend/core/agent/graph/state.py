from __future__ import annotations

import json
from typing import TypedDict

from core.agent.spec import AgentStatus

STATE_UPDATE_RULES: tuple[str, ...] = (
    "On file read: append file path to files_read and increment tool_call_count.",
    "On grep search: append search pattern to search_patterns and increment tool_call_count.",
    "On duplicate detection: append candidate entry to duplicate_candidates.",
)

VALID_AGENT_STATE_STATUSES: tuple[str, ...] = tuple(status.value for status in AgentStatus)


class AgentState(TypedDict):
    """State model carried across graph nodes during exploration."""

    repository_tree: list[str]
    readme_summary: str
    explored_files: list[str]
    files_read: list[str]
    search_patterns: list[str]
    duplicate_candidates: list[str]
    findings: list[str]
    tool_call_count: int
    iteration_count: int
    status: str


def validate_agent_state(state: AgentState) -> None:
    required_fields = {
        "repository_tree",
        "readme_summary",
        "explored_files",
        "files_read",
        "search_patterns",
        "duplicate_candidates",
        "findings",
        "tool_call_count",
        "iteration_count",
        "status",
    }
    missing = required_fields - set(state.keys())
    if missing:
        raise ValueError(f"agent state missing fields: {', '.join(sorted(missing))}")
    if state["status"] not in VALID_AGENT_STATE_STATUSES:
        raise ValueError(f"invalid agent state status: {state['status']!r}")


def new_agent_state(repository_tree: list[str] | None = None) -> AgentState:
    """Create the initial graph state for agent exploration."""

    return {
        "repository_tree": [] if repository_tree is None else list(repository_tree),
        "readme_summary": "",
        "explored_files": [],
        "files_read": [],
        "search_patterns": [],
        "duplicate_candidates": [],
        "findings": [],
        "tool_call_count": 0,
        "iteration_count": 0,
        "status": AgentStatus.EXPLORING.value,
    }


def state_to_json(state: AgentState) -> str:
    """Serialize AgentState to JSON for storage and debugging."""

    validate_agent_state(state)
    return json.dumps(state, ensure_ascii=False)


def state_from_json(payload: str) -> AgentState:
    """Restore AgentState from a serialized JSON payload."""

    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise ValueError("agent state payload must decode to an object")
    state = parsed  # runtime validation below
    validate_agent_state(state)  # type: ignore[arg-type]
    return state  # type: ignore[return-value]


def record_file_read(state: AgentState, file_path: str) -> None:
    """Rule: add file path to files_read and increment tool_call_count."""

    path = file_path.strip()
    if path == "":
        raise ValueError("file_path is empty")
    state["files_read"].append(path)
    if path not in state["explored_files"]:
        state["explored_files"].append(path)
    state["tool_call_count"] += 1


def record_grep_search(state: AgentState, pattern: str) -> None:
    """Rule: record grep pattern and increment tool_call_count."""

    query = pattern.strip()
    if query == "":
        raise ValueError("pattern is empty")
    state["search_patterns"].append(query)
    state["tool_call_count"] += 1


def record_duplicate_candidate(state: AgentState, candidate: str) -> None:
    """Rule: add duplicate candidate entry."""

    entry = candidate.strip()
    if entry == "":
        raise ValueError("candidate is empty")
    state["duplicate_candidates"].append(entry)
