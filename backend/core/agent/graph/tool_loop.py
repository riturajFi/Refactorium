# ============================================================
# FUTURE IMPORTS
# ============================================================

from __future__ import annotations


# ============================================================
# STANDARD LIBRARY IMPORTS
# ============================================================

import json
from typing import Annotated, Any, TypedDict


# ============================================================
# LANGCHAIN / LANGGRAPH IMPORTS
# ============================================================

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


# ============================================================
# PROJECT IMPORTS — AGENT STATE
# ============================================================

from core.agent.graph.state import (
    AgentState,
    record_duplicate_candidate,
    validate_agent_state,
)


# ============================================================
# PROJECT IMPORTS — PROMPTS
# ============================================================

from core.agent.prompts import prompt as DUPLICATE_LOGIC_REFACTOR_PROMPT


# ============================================================
# PROJECT IMPORTS — AGENT SPEC / LIMITS
# ============================================================

from core.agent.spec import (
    AgentExecutionLimits,
    AgentStatus,
    DEFAULT_AGENT_LIMITS,
    DEFAULT_NO_CANDIDATE_THRESHOLDS,
    NoCandidateThresholds,
    evaluate_agent_status,
    validate_agent_execution_limits,
    validate_no_candidate_thresholds,
)


# ============================================================
# PROJECT IMPORTS — TOOLS
# ============================================================

from core.agent.tools import ToolLimits, build_repository_tools


# ============================================================
# DEFAULT USER OBJECTIVE
# ============================================================

DEFAULT_USER_OBJECTIVE = (
    "Explore this repository to find duplicate logic. "
    "Use only list_directory, grep, and read_file while gathering evidence."
)


# ============================================================
# INTERNAL CONSTANTS
# ============================================================

_CANDIDATE_PREFIX = "DUPLICATE_CANDIDATE:"
_FINDING_PREFIX = "FINDING:"
_CONFIDENCE_PREFIX = "DUPLICATE_LOGIC_CONFIDENT:"
_CONFIDENCE_MARKER = "duplicate_logic_confident=true"

_TOOL_RESULT_PREFIX = "tool_result:"

_TERMINAL_STATUSES: set[AgentStatus] = {
    AgentStatus.READY_FOR_PATCH_GENERATION,
    AgentStatus.EXPLORATION_LIMIT_REACHED,
    AgentStatus.NO_REFACTOR_FOUND,
}


# ============================================================
# GRAPH STATE
# ============================================================

class AgentToolLoopGraphState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ============================================================
# AGENT STATUS SYNCHRONIZATION
# ============================================================

def sync_agent_status(
    state: AgentState,
    *,
    limits: AgentExecutionLimits | None = None,
    no_candidate_thresholds: NoCandidateThresholds | None = None,
) -> AgentStatus:
    """
    Convert AgentState counters into AgentStatus.
    Persist the result back into the state.
    """

    validate_agent_state(state)

    effective_limits = DEFAULT_AGENT_LIMITS if limits is None else limits
    thresholds = (
        DEFAULT_NO_CANDIDATE_THRESHOLDS
        if no_candidate_thresholds is None
        else no_candidate_thresholds
    )

    validate_agent_execution_limits(effective_limits)
    validate_no_candidate_thresholds(thresholds)

    status = evaluate_agent_status(
        {
            "tool_calls_used": state["tool_call_count"],
            "files_read": len(state["files_read"]),
            "exploration_steps": state["iteration_count"],
            "grep_search_calls": len(state["search_patterns"]),
            "duplicate_candidate_count": len(state["duplicate_candidates"]),
            "duplicate_logic_confident": _is_duplicate_logic_confident(state),
        },
        effective_limits,
        thresholds,
    )

    state["status"] = status.value
    return status


# ============================================================
# AGENT MESSAGE ANNOTATION PARSER
# ============================================================

def apply_agent_message_annotations(state: AgentState, message_content: Any) -> None:
    """
    Parse special markers from LLM output and update AgentState.
    """

    text = _content_to_text(message_content)

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "":
            continue

        upper = line.upper()

        # ---- duplicate candidate marker ----
        if upper.startswith(_CANDIDATE_PREFIX):
            candidate = line[len(_CANDIDATE_PREFIX):].strip()
            if candidate != "":
                record_duplicate_candidate(state, candidate)
            continue

        # ---- generic finding marker ----
        if upper.startswith(_FINDING_PREFIX):
            finding = line[len(_FINDING_PREFIX):].strip()
            if finding != "":
                state["findings"].append(finding)
            continue

        # ---- confidence marker ----
        if upper.startswith(_CONFIDENCE_PREFIX):
            confidence = line[len(_CONFIDENCE_PREFIX):].strip().lower()
            if confidence in {"true", "yes", "1", "high", "confident"}:
                state["findings"].append(_CONFIDENCE_MARKER)


# ============================================================
# GRAPH CONSTRUCTION
# ============================================================

def build_agent_tool_loop(
    repo_root: str,
    llm: Any,
    state: AgentState,
    *,
    limits: AgentExecutionLimits | None = None,
    no_candidate_thresholds: NoCandidateThresholds | None = None,
    tool_limits: ToolLimits | None = None,
) -> Any:
    """
    Build the LangGraph reasoning + tool execution loop.
    """

    validate_agent_state(state)

    effective_limits = DEFAULT_AGENT_LIMITS if limits is None else limits
    thresholds = (
        DEFAULT_NO_CANDIDATE_THRESHOLDS
        if no_candidate_thresholds is None
        else no_candidate_thresholds
    )

    validate_agent_execution_limits(effective_limits)
    validate_no_candidate_thresholds(thresholds)

    # --------------------------------------------------------
    # TOOL SETUP
    # --------------------------------------------------------

    tools = build_repository_tools(repo_root, state, limits=tool_limits)

    if not hasattr(llm, "bind_tools"):
        raise TypeError("llm must expose bind_tools(tools)")

    llm_with_tools = llm.bind_tools(tools)

    if not hasattr(llm_with_tools, "invoke"):
        raise TypeError("bound llm must expose invoke(messages)")

    tool_node = ToolNode(tools)

    # --------------------------------------------------------
    # GRAPH NODES
    # --------------------------------------------------------

    def check_status_node(_: AgentToolLoopGraphState) -> dict[str, Any]:
        sync_agent_status(
            state,
            limits=effective_limits,
            no_candidate_thresholds=thresholds,
        )
        return {}

    def route_after_status(_: AgentToolLoopGraphState) -> str:
        current = AgentStatus(state["status"])
        return "stop" if current in _TERMINAL_STATUSES else "continue"

    def llm_reasoning_node(graph_state: AgentToolLoopGraphState) -> dict[str, Any]:
        state["iteration_count"] += 1

        response = llm_with_tools.invoke(graph_state["messages"])

        apply_agent_message_annotations(
            state,
            getattr(response, "content", ""),
        )

        return {"messages": [response]}

    def route_after_llm(graph_state: AgentToolLoopGraphState) -> str:
        messages = graph_state.get("messages", [])

        if len(messages) == 0:
            return "check_status"

        last_message = messages[-1]

        return "tools" if _message_has_tool_calls(last_message) else "check_status"

    def capture_tool_results_node(graph_state: AgentToolLoopGraphState) -> dict[str, Any]:
        _record_latest_tool_results(state, graph_state.get("messages", []))
        return {}

    # --------------------------------------------------------
    # GRAPH STRUCTURE
    # --------------------------------------------------------

    graph_builder = StateGraph(AgentToolLoopGraphState)

    graph_builder.add_node("check_status", check_status_node)
    graph_builder.add_node("llm_reasoning", llm_reasoning_node)
    graph_builder.add_node("tools", tool_node)
    graph_builder.add_node("capture_tool_results", capture_tool_results_node)

    graph_builder.set_entry_point("check_status")

    graph_builder.add_conditional_edges(
        "check_status",
        route_after_status,
        {
            "continue": "llm_reasoning",
            "stop": END,
        },
    )

    graph_builder.add_conditional_edges(
        "llm_reasoning",
        route_after_llm,
        {
            "tools": "tools",
            "check_status": "check_status",
        },
    )

    graph_builder.add_edge("tools", "capture_tool_results")
    graph_builder.add_edge("capture_tool_results", "check_status")

    return graph_builder.compile()


# ============================================================
# GRAPH EXECUTION
# ============================================================

def run_agent_tool_loop(
    repo_root: str,
    llm: Any,
    state: AgentState,
    *,
    limits: AgentExecutionLimits | None = None,
    no_candidate_thresholds: NoCandidateThresholds | None = None,
    tool_limits: ToolLimits | None = None,
    objective: str | None = None,
) -> AgentState:
    """
    Execute the graph until a terminal exploration status.
    """

    graph = build_agent_tool_loop(
        repo_root,
        llm,
        state,
        limits=limits,
        no_candidate_thresholds=no_candidate_thresholds,
        tool_limits=tool_limits,
    )

    graph.invoke(
        {"messages": _initial_messages(state, objective=objective)}
    )

    sync_agent_status(
        state,
        limits=limits,
        no_candidate_thresholds=no_candidate_thresholds,
    )

    return state


# ============================================================
# INITIAL PROMPT CONSTRUCTION
# ============================================================

def _initial_messages(
    state: AgentState,
    *,
    objective: str | None,
) -> list[BaseMessage]:

    prompt = DEFAULT_USER_OBJECTIVE if objective is None else objective.strip()

    if prompt == "":
        prompt = DEFAULT_USER_OBJECTIVE

    tree_preview = _repository_tree_preview(state["repository_tree"])

    if tree_preview != "":
        prompt = f"{prompt}\n\nRepository tree preview:\n{tree_preview}"

    return [
        SystemMessage(content=DUPLICATE_LOGIC_REFACTOR_PROMPT),
        HumanMessage(content=prompt),
    ]


# ============================================================
# REPOSITORY TREE PREVIEW
# ============================================================

def _repository_tree_preview(repository_tree: list[str]) -> str:

    if len(repository_tree) == 0:
        return ""

    max_entries = 120

    preview_lines = [
        f"- {item}" for item in repository_tree[:max_entries]
    ]

    if len(repository_tree) > max_entries:
        preview_lines.append(
            f"- ... ({len(repository_tree) - max_entries} more entries)"
        )

    return "\n".join(preview_lines)


# ============================================================
# MESSAGE UTILITIES
# ============================================================

def _message_has_tool_calls(message: Any) -> bool:
    tool_calls = getattr(message, "tool_calls", None)
    return isinstance(tool_calls, list) and len(tool_calls) > 0


# ============================================================
# TOOL RESULT RECORDING
# ============================================================

def _record_latest_tool_results(
    state: AgentState,
    messages: list[Any],
) -> None:

    latest_tool_messages: list[Any] = []

    for message in reversed(messages):
        if _is_tool_message(message):
            latest_tool_messages.append(message)
            continue
        break

    for message in reversed(latest_tool_messages):
        summary = _tool_result_summary(message)
        state["findings"].append(summary)


def _is_tool_message(message: Any) -> bool:
    return isinstance(message, ToolMessage) or hasattr(message, "tool_call_id")


def _tool_result_summary(message: Any) -> str:

    tool_name = getattr(message, "name", None)

    if not isinstance(tool_name, str) or tool_name.strip() == "":
        tool_name = "tool"

    content = _content_to_text(getattr(message, "content", ""))

    compact = " ".join(content.split())

    if len(compact) > 220:
        compact = compact[:217] + "..."

    return f"{_TOOL_RESULT_PREFIX}{tool_name}:{compact}"


# ============================================================
# CONTENT NORMALIZATION
# ============================================================

def _content_to_text(content: Any) -> str:

    if isinstance(content, str):
        return content

    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=True)

    if isinstance(content, list):
        fragments: list[str] = []

        for item in content:

            if isinstance(item, str):
                fragments.append(item)
                continue

            if isinstance(item, dict):
                text = item.get("text")

                if isinstance(text, str):
                    fragments.append(text)
                    continue

                fragments.append(json.dumps(item, ensure_ascii=True))
                continue

            fragments.append(str(item))

        return "\n".join(fragments)

    return str(content)


# ============================================================
# DUPLICATE LOGIC CONFIDENCE CHECK
# ============================================================

def _is_duplicate_logic_confident(state: AgentState) -> bool:

    if len(state["duplicate_candidates"]) >= 2:
        return True

    for finding in state["findings"]:
        if finding.strip().lower() == _CONFIDENCE_MARKER:
            return True

    return False


# ============================================================
# PUBLIC EXPORTS
# ============================================================

__all__ = [
    "AgentToolLoopGraphState",
    "DEFAULT_USER_OBJECTIVE",
    "apply_agent_message_annotations",
    "build_agent_tool_loop",
    "run_agent_tool_loop",
    "sync_agent_status",
]