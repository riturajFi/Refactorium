from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentExecutionLimits:
    """Configuration specification for controlling agent exploration."""

    max_tool_calls: int
    max_files_read: int
    max_exploration_steps: int

    def validate(self) -> None:
        if self.max_tool_calls < 1:
            raise ValueError("max_tool_calls must be >= 1")
        if self.max_files_read < 1:
            raise ValueError("max_files_read must be >= 1")
        if self.max_exploration_steps < 1:
            raise ValueError("max_exploration_steps must be >= 1")


DEFAULT_AGENT_LIMITS = AgentExecutionLimits(
    max_tool_calls=40,
    max_files_read=30,
    max_exploration_steps=25,
)
