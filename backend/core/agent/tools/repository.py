from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

from core.agent.graph.state import AgentState, record_file_read, record_grep_search


class ToolLimits(TypedDict):
    max_file_size_bytes: int
    max_files_read: int
    max_grep_matches: int


DEFAULT_TOOL_LIMITS: ToolLimits = {
    "max_file_size_bytes": 256 * 1024,
    "max_files_read": 30,
    "max_grep_matches": 200,
}


def list_directory(repo_root: str, state: AgentState, path: str = ".") -> list[str]:
    """Read-only tool: list files/folders inside a repository directory."""

    target = _resolve_within_repo(repo_root, path)
    if not target.is_dir():
        raise ValueError(f"not a directory: {path}")

    state["tool_call_count"] += 1

    entries: list[str] = []
    for entry in sorted(target.iterdir(), key=lambda item: item.name):
        suffix = "/" if entry.is_dir() else ""
        entries.append(entry.name + suffix)
    return entries


def read_file(
    repo_root: str,
    state: AgentState,
    path: str,
    *,
    limits: ToolLimits | None = None,
) -> str:
    """Read-only tool: return file contents with size/read-count protections."""

    effective_limits = _effective_limits(limits)

    target = _resolve_within_repo(repo_root, path)
    if not target.is_file():
        raise ValueError(f"not a file: {path}")

    if target.stat().st_size > effective_limits["max_file_size_bytes"]:
        raise ValueError(f"file exceeds size limit: {path}")

    if len(state["files_read"]) >= effective_limits["max_files_read"]:
        raise RuntimeError("file-read limit reached")

    text = target.read_text(encoding="utf-8", errors="replace")
    record_file_read(state, _to_repo_relative(repo_root, target))
    return text


def grep(
    repo_root: str,
    state: AgentState,
    pattern: str,
    *,
    limits: ToolLimits | None = None,
) -> list[str]:
    """Read-only tool: plain-text search across repository files."""

    query = pattern.strip()
    if query == "":
        raise ValueError("pattern is empty")

    effective_limits = _effective_limits(limits)
    record_grep_search(state, query)

    matches: list[str] = []
    for file_path in _iter_repo_files(repo_root):
        if file_path.stat().st_size > effective_limits["max_file_size_bytes"]:
            continue

        rel = _to_repo_relative(repo_root, file_path)
        content = file_path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(content.splitlines(), start=1):
            if query not in line:
                continue
            matches.append(f"{rel}:{line_no}:{line.strip()}")
            if len(matches) >= effective_limits["max_grep_matches"]:
                return matches
    return matches


def _effective_limits(limits: ToolLimits | None) -> ToolLimits:
    if limits is None:
        return DEFAULT_TOOL_LIMITS

    max_file_size_bytes = limits.get("max_file_size_bytes", DEFAULT_TOOL_LIMITS["max_file_size_bytes"])
    max_files_read = limits.get("max_files_read", DEFAULT_TOOL_LIMITS["max_files_read"])
    max_grep_matches = limits.get("max_grep_matches", DEFAULT_TOOL_LIMITS["max_grep_matches"])

    if max_file_size_bytes < 1:
        raise ValueError("max_file_size_bytes must be >= 1")
    if max_files_read < 1:
        raise ValueError("max_files_read must be >= 1")
    if max_grep_matches < 1:
        raise ValueError("max_grep_matches must be >= 1")

    return {
        "max_file_size_bytes": max_file_size_bytes,
        "max_files_read": max_files_read,
        "max_grep_matches": max_grep_matches,
    }


def _resolve_within_repo(repo_root: str, path: str) -> Path:
    root = Path(repo_root).resolve()
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes repository root: {path}") from exc
    return candidate


def _to_repo_relative(repo_root: str, path: Path) -> str:
    root = Path(repo_root).resolve()
    return path.resolve().relative_to(root).as_posix()


def _iter_repo_files(repo_root: str):
    root = Path(repo_root).resolve()
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__"}]
        current = Path(current_root)
        for file_name in files:
            yield current / file_name
