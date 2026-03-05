from __future__ import annotations


class Snapshot:
    """Immutable repository view at a specific commit."""

    def __init__(self, commit_hash: str, branch_ref: str, files: dict[str, bytes]) -> None:
        self._commit_hash = commit_hash
        self._branch_ref = branch_ref
        self._file_content = {path: bytes(content) for path, content in files.items()}
        self._file_list = sorted(files.keys())

    def commit_hash(self) -> str:
        return self._commit_hash

    def branch_ref(self) -> str:
        return self._branch_ref

    def files(self) -> list[str]:
        return list(self._file_list)

    def content(self, path: str) -> tuple[bytes, bool]:
        content = self._file_content.get(path)
        if content is None:
            return b"", False
        return bytes(content), True

    def file_content_map(self) -> dict[str, bytes]:
        return {path: bytes(content) for path, content in self._file_content.items()}
