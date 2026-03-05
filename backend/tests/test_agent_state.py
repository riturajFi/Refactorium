from __future__ import annotations

import unittest

from core.agent.graph.state import (
    STATE_UPDATE_RULES,
    VALID_AGENT_STATE_STATUSES,
    new_agent_state,
    record_duplicate_candidate,
    record_file_read,
    record_grep_search,
    state_from_json,
    state_to_json,
)
from core.agent.spec import AgentStatus


class AgentStateTests(unittest.TestCase):
    def test_new_agent_state_contains_required_fields_with_defaults(self) -> None:
        state = new_agent_state()

        self.assertEqual(state["repository_tree"], [])
        self.assertEqual(state["readme_summary"], "")
        self.assertEqual(state["explored_files"], [])
        self.assertEqual(state["files_read"], [])
        self.assertEqual(state["search_patterns"], [])
        self.assertEqual(state["duplicate_candidates"], [])
        self.assertEqual(state["findings"], [])
        self.assertEqual(state["tool_call_count"], 0)
        self.assertEqual(state["iteration_count"], 0)
        self.assertEqual(state["status"], AgentStatus.EXPLORING.value)

    def test_new_agent_state_accepts_repository_tree_from_previous_milestone(self) -> None:
        tree = ["README.md", "backend/cmd/server/main.py"]
        state = new_agent_state(tree)
        self.assertEqual(state["repository_tree"], tree)

    def test_record_file_read_updates_state(self) -> None:
        state = new_agent_state()
        record_file_read(state, "backend/core/agent/spec.py")
        self.assertEqual(state["files_read"], ["backend/core/agent/spec.py"])
        self.assertEqual(state["explored_files"], ["backend/core/agent/spec.py"])
        self.assertEqual(state["tool_call_count"], 1)

    def test_record_grep_search_updates_state(self) -> None:
        state = new_agent_state()
        record_grep_search(state, "executeWithRetry")
        self.assertEqual(state["search_patterns"], ["executeWithRetry"])
        self.assertEqual(state["tool_call_count"], 1)

    def test_record_duplicate_candidate_updates_state(self) -> None:
        state = new_agent_state()
        record_duplicate_candidate(state, "backend/a.py:10-20 ~ backend/b.py:30-40")
        self.assertEqual(
            state["duplicate_candidates"],
            ["backend/a.py:10-20 ~ backend/b.py:30-40"],
        )

    def test_state_update_rules_documented(self) -> None:
        self.assertEqual(len(STATE_UPDATE_RULES), 3)

    def test_valid_agent_state_status_values(self) -> None:
        self.assertEqual(
            VALID_AGENT_STATE_STATUSES,
            (
                "exploring",
                "duplicates_found",
                "ready_for_patch_generation",
                "exploration_limit_reached",
                "no_refactor_found",
            ),
        )

    def test_state_json_round_trip(self) -> None:
        state = new_agent_state(["README.md"])
        record_file_read(state, "README.md")
        record_grep_search(state, "TODO")
        payload = state_to_json(state)
        restored = state_from_json(payload)
        self.assertEqual(restored, state)

    def test_state_from_json_rejects_non_object(self) -> None:
        with self.assertRaises(ValueError):
            state_from_json('["not-an-object"]')

    def test_state_from_json_rejects_invalid_status(self) -> None:
        payload = (
            '{"repository_tree":[],"readme_summary":"","explored_files":[],"files_read":[],'
            '"search_patterns":[],"duplicate_candidates":[],"findings":[],"tool_call_count":0,'
            '"iteration_count":0,"status":"bad"}'
        )
        with self.assertRaises(ValueError):
            state_from_json(payload)


if __name__ == "__main__":
    unittest.main()
