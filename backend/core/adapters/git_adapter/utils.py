from __future__ import annotations

import hashlib
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .errors import EmptyRepoIDError, NonRemoteRepoIDError
from .git_ops import run_git


def normalize_remote_repo_id(repo_id: str) -> str:
    trimmed = repo_id.strip()
    if trimmed == "":
        raise EmptyRepoIDError("repository id is empty")

    if trimmed.startswith(("http://", "https://", "ssh://", "git@", "file://")):
        return trimmed

    if trimmed.count("/") >= 2 and "." in trimmed:
        return "https://" + trimmed

    raise NonRemoteRepoIDError(f'repository id must reference a remote repository: "{repo_id}"')


def with_authentication(repo_id: str) -> str:
    token = os.getenv("GIT_AUTH_TOKEN", "").strip()
    if token == "":
        return repo_id

    parsed = urlsplit(repo_id)
    if parsed.scheme not in {"http", "https"}:
        return repo_id
    if parsed.username is not None:
        return repo_id

    netloc = parsed.netloc
    if "@" in netloc:
        return repo_id

    injected_netloc = f"x-access-token:{token}@{netloc}"
    return urlunsplit((parsed.scheme, injected_netloc, parsed.path, parsed.query, parsed.fragment))


def resolve_default_remote_branch_ref(repo_path: str) -> str:
    try:
        branch_ref = run_git(repo_path, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    except RuntimeError:
        return "origin/HEAD"

    trimmed = branch_ref.strip()
    if trimmed == "":
        return "origin/HEAD"
    return trimmed


def read_working_tree(root: str) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for current_root, dirs, file_names in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]

        for file_name in file_names:
            file_path = Path(current_root) / file_name
            if not file_path.is_file():
                continue

            relative_path = file_path.relative_to(root).as_posix()
            files[relative_path] = file_path.read_bytes()

    return files


def hash_repo_id(repo_id: str) -> str:
    return hashlib.sha256(repo_id.encode("utf-8")).hexdigest()
