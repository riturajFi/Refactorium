from __future__ import annotations

import unittest

from core.agent.graph import (
    apply_agent_message_annotations,
    new_agent_state,
    sync_agent_status,
)
from core.agent.spec import AgentStatus


class AgentToolLoopTests(unittest.TestCase):
    def test_sync_agent_status_marks_limit_reached(self) -> None:
        state = new_agent_state()
        state["tool_call_count"] = 5

        status = sync_agent_status(
            state,
            limits={"max_tool_calls": 5, "max_files_read": 50, "max_exploration_steps": 50},
        )

        self.assertEqual(status, AgentStatus.EXPLORATION_LIMIT_REACHED)
        self.assertEqual(state["status"], AgentStatus.EXPLORATION_LIMIT_REACHED.value)

    def test_sync_agent_status_marks_no_refactor_after_thresholds(self) -> None:
        state = new_agent_state()
        state["files_read"] = ["a.py", "b.py"]
        state["search_patterns"] = ["duplicate-check"]

        status = sync_agent_status(
            state,
            limits={"max_tool_calls": 20, "max_files_read": 20, "max_exploration_steps": 20},
            no_candidate_thresholds={"min_files_explored": 2, "min_search_calls": 1},
        )

        self.assertEqual(status, AgentStatus.NO_REFACTOR_FOUND)
        self.assertEqual(state["status"], AgentStatus.NO_REFACTOR_FOUND.value)

    def test_apply_agent_message_annotations_updates_candidates_and_confidence(self) -> None:
        state = new_agent_state()
        apply_agent_message_annotations(
            state,
            (
                "FINDING: Same shape across request handlers\n"
                "DUPLICATE_CANDIDATE: api/a.py:10-26 ~ api/b.py:12-28\n"
                "DUPLICATE_LOGIC_CONFIDENT: true"
            ),
        )

        self.assertEqual(
            state["duplicate_candidates"],
            ["api/a.py:10-26 ~ api/b.py:12-28"],
        )
        self.assertIn("Same shape across request handlers", state["findings"])

        status = sync_agent_status(
            state,
            limits={"max_tool_calls": 20, "max_files_read": 20, "max_exploration_steps": 20},
            no_candidate_thresholds={"min_files_explored": 2, "min_search_calls": 1},
        )
        self.assertEqual(status, AgentStatus.READY_FOR_PATCH_GENERATION)
        self.assertEqual(state["status"], AgentStatus.READY_FOR_PATCH_GENERATION.value)


if __name__ == "__main__":
    unittest.main()
