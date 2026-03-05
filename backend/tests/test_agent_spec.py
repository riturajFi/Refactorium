from __future__ import annotations

import unittest

from core.agent.spec import AgentExecutionLimits


class AgentSpecTests(unittest.TestCase):
    def test_limits_validate_success(self) -> None:
        limits = AgentExecutionLimits(max_tool_calls=10, max_files_read=10, max_exploration_steps=10)
        limits.validate()

    def test_limits_validate_rejects_non_positive_values(self) -> None:
        with self.assertRaises(ValueError):
            AgentExecutionLimits(max_tool_calls=0, max_files_read=10, max_exploration_steps=10).validate()

        with self.assertRaises(ValueError):
            AgentExecutionLimits(max_tool_calls=10, max_files_read=0, max_exploration_steps=10).validate()

        with self.assertRaises(ValueError):
            AgentExecutionLimits(max_tool_calls=10, max_files_read=10, max_exploration_steps=0).validate()


if __name__ == "__main__":
    unittest.main()
