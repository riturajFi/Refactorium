from __future__ import annotations

from typing import Any

try:
    from langchain_core.tools import BaseTool, tool
    _TOOLING_IMPORT_ERROR: Exception | None = None
except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional dependency
    BaseTool = Any  # type: ignore[assignment]
    tool = None  # type: ignore[assignment]
    _TOOLING_IMPORT_ERROR = exc

from core.agent.graph.state import AgentState

from .repository import ToolLimits, grep, list_directory, read_file


def build_repository_tools(
    repo_root: str,
    state: AgentState,
    *,
    limits: ToolLimits | None = None,
) -> list[BaseTool]:
    """Create LangGraph-compatible read-only repository tools."""
    if tool is None:
        raise RuntimeError(
            "LangGraph tool wrappers require langgraph/langchain-core dependencies to be installed"
        ) from _TOOLING_IMPORT_ERROR

    @tool("list_directory")
    def list_directory_tool(path: str = ".") -> list[str]:
        """List files and folders in a repository directory."""

        return list_directory(repo_root, state, path)

    @tool("grep")
    def grep_tool(pattern: str) -> list[str]:
        """Search repository files for a plain-text pattern."""

        return grep(repo_root, state, pattern, limits=limits)

    @tool("read_file")
    def read_file_tool(path: str) -> str:
        """Read a repository file as UTF-8 text with safety limits."""

        return read_file(repo_root, state, path, limits=limits)

    return [list_directory_tool, grep_tool, read_file_tool]
