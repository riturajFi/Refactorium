from __future__ import annotations

import unittest

from core.agent.spec import (
    AgentExplorationState,
    AgentExecutionLimits,
    AgentStatus,
    NoCandidateThresholds,
    evaluate_agent_status,
    is_exploration_limit_reached,
    new_agent_exploration_state,
    validate_agent_execution_limits,
    validate_no_candidate_thresholds,
)


class AgentSpecTests(unittest.TestCase):
    def test_limits_validate_success(self) -> None:
        limits: AgentExecutionLimits = {
            "max_tool_calls": 10,
            "max_files_read": 10,
            "max_exploration_steps": 10,
        }
        validate_agent_execution_limits(limits)

    def test_limits_validate_rejects_non_positive_values(self) -> None:
        with self.assertRaises(ValueError):
            validate_agent_execution_limits(
                {"max_tool_calls": 0, "max_files_read": 10, "max_exploration_steps": 10}
            )

        with self.assertRaises(ValueError):
            validate_agent_execution_limits(
                {"max_tool_calls": 10, "max_files_read": 0, "max_exploration_steps": 10}
            )

        with self.assertRaises(ValueError):
            validate_agent_execution_limits(
                {"max_tool_calls": 10, "max_files_read": 10, "max_exploration_steps": 0}
            )

    def test_no_candidate_thresholds_validate_rejects_non_positive_values(self) -> None:
        with self.assertRaises(ValueError):
            validate_no_candidate_thresholds({"min_files_explored": 0, "min_search_calls": 2})

        with self.assertRaises(ValueError):
            validate_no_candidate_thresholds({"min_files_explored": 10, "min_search_calls": 0})

    def test_is_exploration_limit_reached_when_any_budget_is_exhausted(self) -> None:
        limits: AgentExecutionLimits = {"max_tool_calls": 5, "max_files_read": 5, "max_exploration_steps": 5}
        state = new_agent_exploration_state()
        state["tool_calls_used"] = 5
        state["files_read"] = 1
        state["exploration_steps"] = 1
        reached = is_exploration_limit_reached(
            state,
            limits,
        )
        self.assertTrue(reached)

    def test_evaluate_agent_status_duplicate_detected(self) -> None:
        state = new_agent_exploration_state()
        state["duplicate_logic_confident"] = True
        state["duplicate_candidate_count"] = 2
        status = evaluate_agent_status(
            state,
            {"max_tool_calls": 10, "max_files_read": 10, "max_exploration_steps": 10},
        )
        self.assertEqual(status, AgentStatus.READY_FOR_PATCH_GENERATION)

    def test_evaluate_agent_status_limit_reached(self) -> None:
        state = new_agent_exploration_state()
        state["tool_calls_used"] = 10
        status = evaluate_agent_status(
            state,
            {"max_tool_calls": 10, "max_files_read": 50, "max_exploration_steps": 50},
        )
        self.assertEqual(status, AgentStatus.EXPLORATION_LIMIT_REACHED)

    def test_evaluate_agent_status_no_refactor_found(self) -> None:
        thresholds: NoCandidateThresholds = {"min_files_explored": 15, "min_search_calls": 3}
        state = new_agent_exploration_state()
        state["files_read"] = 15
        state["grep_search_calls"] = 3
        state["duplicate_candidate_count"] = 0
        status = evaluate_agent_status(
            state,
            {"max_tool_calls": 100, "max_files_read": 100, "max_exploration_steps": 100},
            thresholds,
        )
        self.assertEqual(status, AgentStatus.NO_REFACTOR_FOUND)

    def test_evaluate_agent_status_duplicates_found(self) -> None:
        state = new_agent_exploration_state()
        state["duplicate_candidate_count"] = 2
        status = evaluate_agent_status(
            state,
            {"max_tool_calls": 20, "max_files_read": 20, "max_exploration_steps": 20},
        )
        self.assertEqual(status, AgentStatus.DUPLICATES_FOUND)

    def test_evaluate_agent_status_keeps_exploring(self) -> None:
        state = new_agent_exploration_state()
        state["files_read"] = 4
        state["grep_search_calls"] = 1
        state["duplicate_candidate_count"] = 0
        status = evaluate_agent_status(
            state,
            {"max_tool_calls": 20, "max_files_read": 20, "max_exploration_steps": 20},
        )
        self.assertEqual(status, AgentStatus.EXPLORING)


if __name__ == "__main__":
    unittest.main()
