from __future__ import annotations

import json
import unittest

from core.models.session.state import State, parse_state


class SessionStateTests(unittest.TestCase):
    def test_state_is_valid(self) -> None:
        test_cases = [
            (State.CREATED, True),
            (State.RUNNING, True),
            (State.SNAPSHOT_READY, True),
            (State.COMPLETED, True),
            (State.FAILED, True),
        ]

        for state, want in test_cases:
            self.assertEqual(state.is_valid(), want)

    def test_parse_state(self) -> None:
        state = parse_state("RUNNING")
        self.assertEqual(state, State.RUNNING)

        with self.assertRaises(ValueError):
            parse_state("UNKNOWN")

    def test_state_json_round_trip(self) -> None:
        payload = {"state": State.COMPLETED.value}
        data = json.dumps(payload)
        parsed = json.loads(data)
        out_state = parse_state(parsed["state"])
        self.assertEqual(out_state, State.COMPLETED)

    def test_state_unmarshal_rejects_invalid(self) -> None:
        payload = json.loads('{"state":"PENDING"}')
        with self.assertRaises(ValueError):
            parse_state(payload["state"])


if __name__ == "__main__":
    unittest.main()
