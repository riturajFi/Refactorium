from __future__ import annotations

from enum import Enum
from typing import TypedDict


class AgentExecutionLimits(TypedDict):
    """Configuration specification for controlling agent exploration."""

    max_tool_calls: int
    max_files_read: int
    max_exploration_steps: int


DEFAULT_AGENT_LIMITS: AgentExecutionLimits = {
    "max_tool_calls": 40,
    "max_files_read": 30,
    "max_exploration_steps": 25,
}


class NoCandidateThresholds(TypedDict):
    """Reasonable exploration definition before emitting a no-op proposal."""

    min_files_explored: int
    min_search_calls: int


DEFAULT_NO_CANDIDATE_THRESHOLDS: NoCandidateThresholds = {
    "min_files_explored": 15,
    "min_search_calls": 3,
}


class AgentExplorationState(TypedDict):
    """State counters used by the stopping-rules specification."""

    tool_calls_used: int
    files_read: int
    exploration_steps: int
    grep_search_calls: int
    duplicate_candidate_count: int
    duplicate_logic_confident: bool


def new_agent_exploration_state() -> AgentExplorationState:
    return {
        "tool_calls_used": 0,
        "files_read": 0,
        "exploration_steps": 0,
        "grep_search_calls": 0,
        "duplicate_candidate_count": 0,
        "duplicate_logic_confident": False,
    }


class AgentStatus(str, Enum):
    EXPLORING = "exploring"
    DUPLICATES_FOUND = "duplicates_found"
    READY_FOR_PATCH_GENERATION = "ready_for_patch_generation"
    EXPLORATION_LIMIT_REACHED = "exploration_limit_reached"
    NO_REFACTOR_FOUND = "no_refactor_found"


def validate_agent_execution_limits(limits: AgentExecutionLimits) -> None:
    if limits["max_tool_calls"] < 1:
        raise ValueError("max_tool_calls must be >= 1")
    if limits["max_files_read"] < 1:
        raise ValueError("max_files_read must be >= 1")
    if limits["max_exploration_steps"] < 1:
        raise ValueError("max_exploration_steps must be >= 1")


def validate_no_candidate_thresholds(thresholds: NoCandidateThresholds) -> None:
    if thresholds["min_files_explored"] < 1:
        raise ValueError("min_files_explored must be >= 1")
    if thresholds["min_search_calls"] < 1:
        raise ValueError("min_search_calls must be >= 1")


def is_exploration_limit_reached(state: AgentExplorationState, limits: AgentExecutionLimits) -> bool:
    return (
        state["tool_calls_used"] >= limits["max_tool_calls"]
        or state["files_read"] >= limits["max_files_read"]
        or state["exploration_steps"] >= limits["max_exploration_steps"]
    )


def evaluate_agent_status(
    state: AgentExplorationState,
    limits: AgentExecutionLimits,
    no_candidate_thresholds: NoCandidateThresholds | None = None,
) -> AgentStatus:
    """Task 5 stopping rule specification for LangGraph conditional edges.

    Priority order:
    1. Duplicate logic identified -> ready_for_patch_generation
    2. Exploration budget exhausted -> exploration_limit_reached
    3. Reasonable exploration with no candidates -> no_refactor_found
    4. Duplicate candidates exist -> duplicates_found
    5. Otherwise -> exploring
    """

    thresholds = (
        DEFAULT_NO_CANDIDATE_THRESHOLDS
        if no_candidate_thresholds is None
        else no_candidate_thresholds
    )

    validate_agent_execution_limits(limits)
    validate_no_candidate_thresholds(thresholds)

    if state["duplicate_logic_confident"] and state["duplicate_candidate_count"] >= 1:
        return AgentStatus.READY_FOR_PATCH_GENERATION

    if is_exploration_limit_reached(state, limits):
        return AgentStatus.EXPLORATION_LIMIT_REACHED

    no_candidates = state["duplicate_candidate_count"] == 0
    enough_files = state["files_read"] >= thresholds["min_files_explored"]
    enough_searches = state["grep_search_calls"] >= thresholds["min_search_calls"]
    if no_candidates and enough_files and enough_searches:
        return AgentStatus.NO_REFACTOR_FOUND

    if state["duplicate_candidate_count"] > 0:
        return AgentStatus.DUPLICATES_FOUND

    return AgentStatus.EXPLORING
