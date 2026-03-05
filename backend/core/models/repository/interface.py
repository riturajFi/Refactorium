from __future__ import annotations

from typing import Protocol

from .snapshot import Snapshot


class LoadedRepository(Protocol):
    """Loaded repository that can produce snapshots."""

    def get_snapshot(self, ref: str) -> Snapshot:
        ...


class Access(Protocol):
    """Repository access contract for loading repositories."""

    def load_repository(self, repo_id: str) -> LoadedRepository:
        ...
