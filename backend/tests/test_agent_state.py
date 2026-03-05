from __future__ import annotations

import unittest

from core.agent.graph.state import new_agent_state
from core.agent.spec import AgentStatus


class AgentStateTests(unittest.TestCase):
    def test_new_agent_state_contains_required_fields_with_defaults(self) -> None:
        state = new_agent_state()

        self.assertEqual(state["repository_tree"], [])
        self.assertEqual(state["readme_summary"], "")
        self.assertEqual(state["explored_files"], [])
        self.assertEqual(state["files_read"], 0)
        self.assertEqual(state["duplicate_candidates"], [])
        self.assertEqual(state["findings"], [])
        self.assertEqual(state["tool_call_count"], 0)
        self.assertEqual(state["iteration_count"], 0)
        self.assertEqual(state["status"], AgentStatus.EXPLORING.value)


if __name__ == "__main__":
    unittest.main()
