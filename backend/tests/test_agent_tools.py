from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.agent.graph.state import new_agent_state
from core.agent.tools import grep, list_directory, read_file


class AgentToolsTests(unittest.TestCase):
    def test_list_directory_returns_entries_and_records_tool_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.txt").write_text("x", encoding="utf-8")
            (root / "dir").mkdir()

            state = new_agent_state()
            entries = list_directory(str(root), state, ".")

            self.assertIn("a.txt", entries)
            self.assertIn("dir/", entries)
            self.assertEqual(state["tool_call_count"], 1)

    def test_read_file_returns_content_and_updates_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "src.py").write_text("print('ok')\n", encoding="utf-8")

            state = new_agent_state()
            content = read_file(str(root), state, "src.py")

            self.assertIn("print('ok')", content)
            self.assertEqual(state["files_read"], ["src.py"])
            self.assertEqual(state["explored_files"], ["src.py"])
            self.assertEqual(state["tool_call_count"], 1)

    def test_read_file_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "safe.txt").write_text("safe", encoding="utf-8")

            state = new_agent_state()

            with self.assertRaises(ValueError):
                read_file(str(root), state, "../etc/passwd")

    def test_read_file_enforces_max_file_size(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "big.txt").write_text("abcdef", encoding="utf-8")

            state = new_agent_state()

            with self.assertRaises(ValueError):
                read_file(str(root), state, "big.txt", limits={"max_file_size_bytes": 3})

    def test_read_file_enforces_max_files_read_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.txt").write_text("a", encoding="utf-8")
            (root / "b.txt").write_text("b", encoding="utf-8")

            state = new_agent_state()
            read_file(str(root), state, "a.txt", limits={"max_files_read": 1})

            with self.assertRaises(RuntimeError):
                read_file(str(root), state, "b.txt", limits={"max_files_read": 1})

    def test_grep_returns_matches_and_records_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "one.py").write_text("alpha\nneedle here\n", encoding="utf-8")
            (root / "two.py").write_text("no match\n", encoding="utf-8")

            state = new_agent_state()
            matches = grep(str(root), state, "needle")

            self.assertEqual(len(matches), 1)
            self.assertIn("one.py:2:needle here", matches[0])
            self.assertEqual(state["search_patterns"], ["needle"])
            self.assertEqual(state["tool_call_count"], 1)


if __name__ == "__main__":
    unittest.main()
