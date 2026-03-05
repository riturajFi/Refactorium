from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from core.adapters.git import GitAdapter, NonRemoteRepoIDError


class GitAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git not installed in environment")

    def test_git_adapter_snapshot_includes_paths_and_contents_from_remote(self) -> None:
        remote_url, source_repo, branch_name, _ = _init_remote_repo(self)
        expected_commit = _git_in_repo(self, source_repo, "rev-parse", "HEAD")

        adapter = GitAdapter(tempfile.mkdtemp())
        loaded = adapter.load_repository(remote_url)

        snapshot = loaded.get_snapshot("")

        self.assertEqual(snapshot.commit_hash(), expected_commit)
        self.assertEqual(snapshot.branch_ref(), f"origin/{branch_name}")

        files = sorted(snapshot.files())
        self.assertEqual(files, ["README.md", "nested/file.txt"])

        readme, ok = snapshot.content("README.md")
        self.assertTrue(ok)
        self.assertEqual(readme, b"hello\n")

        nested, ok = snapshot.content("nested/file.txt")
        self.assertTrue(ok)
        self.assertEqual(nested, b"nested\n")

    def test_git_adapter_refetch_same_ref_returns_identical_snapshot(self) -> None:
        remote_url, _, branch_name, _ = _init_remote_repo(self)

        adapter = GitAdapter(tempfile.mkdtemp())
        loaded = adapter.load_repository(remote_url)

        first = loaded.get_snapshot(f"origin/{branch_name}")

        loaded_again = adapter.load_repository(remote_url)
        second = loaded_again.get_snapshot(f"origin/{branch_name}")

        self.assertEqual(first.commit_hash(), second.commit_hash())
        self.assertEqual(first.branch_ref(), second.branch_ref())
        self.assertEqual(first.files(), second.files())

    def test_git_adapter_fetches_latest_remote_ref_and_does_not_mutate_remote(self) -> None:
        remote_url, source_repo, branch_name, bare_remote = _init_remote_repo(self)

        adapter = GitAdapter(tempfile.mkdtemp())
        adapter.load_repository(remote_url)

        _write_file(self, Path(source_repo) / "new.txt", "new-content\n")
        _git_in_repo(self, source_repo, "add", ".")
        _git_in_repo(self, source_repo, "commit", "-m", "second")
        _git_in_repo(self, source_repo, "push", "origin", "HEAD")
        latest_commit = _git_in_repo(self, source_repo, "rev-parse", "HEAD")
        remote_head_before = _git_in_repo(self, bare_remote, "rev-parse", "HEAD")

        loaded = adapter.load_repository(remote_url)
        snapshot = loaded.get_snapshot(f"origin/{branch_name}")

        self.assertEqual(snapshot.commit_hash(), latest_commit)

        content, ok = snapshot.content("new.txt")
        self.assertTrue(ok)
        self.assertEqual(content, b"new-content\n")

        remote_head_after = _git_in_repo(self, bare_remote, "rev-parse", "HEAD")
        self.assertEqual(remote_head_after, remote_head_before)

    def test_git_adapter_rejects_non_remote_repo_id(self) -> None:
        adapter = GitAdapter(tempfile.mkdtemp())

        with self.assertRaises(NonRemoteRepoIDError):
            adapter.load_repository("/tmp/not-remote")

    def test_git_adapter_handles_large_remote_repository(self) -> None:
        remote_url, source_repo, branch_name, _ = _init_remote_repo(self)

        for i in range(300):
            _write_file(self, Path(source_repo) / "bulk" / f"file-{i:03d}.txt", "x\n")

        _git_in_repo(self, source_repo, "add", ".")
        _git_in_repo(self, source_repo, "commit", "-m", "bulk files")
        _git_in_repo(self, source_repo, "push", "origin", "HEAD")

        adapter = GitAdapter(tempfile.mkdtemp())
        loaded = adapter.load_repository(remote_url)

        snapshot = loaded.get_snapshot(f"origin/{branch_name}")

        self.assertGreaterEqual(len(snapshot.files()), 302)


def _init_remote_repo(testcase: unittest.TestCase) -> tuple[str, str, str, str]:
    source_repo = tempfile.mkdtemp()
    bare_remote = tempfile.mkdtemp()

    _git(testcase, "init", source_repo)
    _git_in_repo(testcase, source_repo, "config", "user.email", "test@example.com")
    _git_in_repo(testcase, source_repo, "config", "user.name", "Test User")

    _write_file(testcase, Path(source_repo) / "README.md", "hello\n")
    _write_file(testcase, Path(source_repo) / "nested" / "file.txt", "nested\n")

    _git_in_repo(testcase, source_repo, "add", ".")
    _git_in_repo(testcase, source_repo, "commit", "-m", "initial")
    branch_name = _git_in_repo(testcase, source_repo, "rev-parse", "--abbrev-ref", "HEAD")

    _git(testcase, "init", "--bare", bare_remote)
    _git_in_repo(testcase, source_repo, "remote", "add", "origin", f"file://{bare_remote}")
    _git_in_repo(testcase, source_repo, "push", "-u", "origin", "HEAD")

    return f"file://{bare_remote}", source_repo, branch_name, bare_remote


def _write_file(testcase: unittest.TestCase, path: Path, content: str) -> None:
    testcase.assertIsNotNone(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _git_in_repo(testcase: unittest.TestCase, repo_dir: str, *args: str) -> str:
    return _git(testcase, "-C", repo_dir, *args)


def _git(testcase: unittest.TestCase, *args: str) -> str:
    proc = subprocess.run(["git", *args], capture_output=True, text=True)
    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        testcase.fail(f"git {' '.join(args)} failed: {output}")
    return output.strip().splitlines()[-1] if output.strip() else ""


if __name__ == "__main__":
    unittest.main()
