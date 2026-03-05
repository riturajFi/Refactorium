from __future__ import annotations

import os
from pathlib import Path

from core.models.repository.factory import new_snapshot
from core.models.repository.snapshot import Snapshot

from .errors import EmptyAdapterRootError, EmptyRepoIDError
from .git_ops import run_git
from .utils import (
    hash_repo_id,
    normalize_remote_repo_id,
    read_working_tree,
    resolve_default_remote_branch_ref,
    with_authentication,
)


class GitAdapter:
    """Git-backed repository access adapter with local clone cache."""

    def __init__(self, root_dir: str) -> None:
        if root_dir.strip() == "":
            raise EmptyAdapterRootError("adapter root directory is empty")
        self._root_dir = root_dir

    def load_repository(self, repo_id: str) -> "_GitLoadedRepository":
        remote_repo_id = normalize_remote_repo_id(repo_id)
        if remote_repo_id.strip() == "":
            raise EmptyRepoIDError("repository id is empty")

        os.makedirs(self._root_dir, mode=0o755, exist_ok=True)

        local_path = Path(self._root_dir) / hash_repo_id(remote_repo_id)
        git_dir = local_path / ".git"
        authenticated_remote = with_authentication(remote_repo_id)

        if git_dir.exists():
            run_git(str(local_path), "remote", "set-url", "origin", authenticated_remote)
            run_git(str(local_path), "fetch", "--all", "--tags", "--prune")
        elif local_path.exists():
            raise RuntimeError(
                f"local repository path exists and is not a git repository: {local_path}"
            )
        else:
            run_git("", "clone", "--no-checkout", authenticated_remote, str(local_path))

        return _GitLoadedRepository(local_path=str(local_path), repo_id=remote_repo_id)


class _GitLoadedRepository:
    def __init__(self, local_path: str, repo_id: str) -> None:
        self._local_path = local_path
        self._repo_id = repo_id

    def get_snapshot(self, ref: str) -> Snapshot:
        target_ref = ref.strip()
        if target_ref == "":
            target_ref = resolve_default_remote_branch_ref(self._local_path)

        run_git(self._local_path, "checkout", "--force", target_ref)
        commit_hash = run_git(self._local_path, "rev-parse", "HEAD").strip()
        file_contents = read_working_tree(self._local_path)

        return new_snapshot(commit_hash=commit_hash, branch_ref=target_ref, files=file_contents)
