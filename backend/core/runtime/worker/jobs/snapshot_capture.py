from __future__ import annotations

import json
import logging
from typing import Callable

from core.models.job.job import Job, JobType
from core.models.session.proposal_session import ProposalSession
from core.models.session.errors import NoopTransitionError
from core.models.repository.interface import Access
from core.models.session.snapshot_reference import SnapshotReference, SnapshotSource
from core.models.session.state import State
from core.runtime.store.store import Store

JobHandler = Callable[[Job], None]

# -----------Public API: handler registration + job factory.-----------


def build_snapshot_capture_handler(store: Store, repo_access: Access) -> JobHandler:
    def _handle(job: Job) -> None:
        _validate_snapshot_job(job)
        session = store.get(job["session_id"])
        if _is_terminal_for_snapshot(session):
            return

        _move_to_running_if_needed(session, store)
        snapshot = _capture_snapshot(job, repo_access, session, store)
        snapshot_ref = _build_snapshot_reference(snapshot)
        _log_snapshot_capture(session, snapshot_ref, snapshot)
        _attach_snapshot_reference(session, snapshot_ref, store)

    return _handle


def snapshot_job(session_id: str, repo_id: str, ref: str = "") -> Job:
    return {
        "type": JobType.SNAPSHOT_CAPTURE,
        "session_id": session_id,
        "repo_id": repo_id,
        "ref": ref,
    }

# -----------Orchestration helpers-----------


def _is_terminal_for_snapshot(session: ProposalSession) -> bool:
    return session.status() in {State.SNAPSHOT_READY, State.COMPLETED}


def _move_to_running_if_needed(session: ProposalSession, store: Store) -> None:
    if session.status() == State.CREATED:
        try:
            session.transition_to(State.RUNNING)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"transition to running: {exc}") from exc

    try:
        store.update(session)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"persist running state: {exc}") from exc


def _capture_snapshot(job: Job, repo_access: Access, session: ProposalSession, store: Store):
    try:
        loaded_repo = repo_access.load_repository(job["repo_id"])
    except Exception as exc:  # noqa: BLE001
        _mark_failed(session, store)
        raise RuntimeError(f"load remote repository: {exc}") from exc

    try:
        return loaded_repo.get_snapshot(job["ref"])
    except Exception as exc:  # noqa: BLE001
        _mark_failed(session, store)
        raise RuntimeError(f"capture snapshot: {exc}") from exc


def _build_snapshot_reference(snapshot) -> SnapshotReference:
    return {
        "commit_hash": snapshot.commit_hash(),
        "branch_ref": snapshot.branch_ref(),
        "file_count": len(snapshot.files()),
        "source": SnapshotSource.REMOTE,
    }


def _log_snapshot_capture(session: ProposalSession, snapshot_ref: SnapshotReference, snapshot) -> None:
    logging.info(
        (
            "snapshot_captured session_id=%s repo_id=%s branch_ref=%s "
            "commit_hash=%s file_count=%d source=%s"
        ),
        session.session_id(),
        session.repo_id(),
        snapshot_ref["branch_ref"],
        snapshot_ref["commit_hash"],
        snapshot_ref["file_count"],
        snapshot_ref["source"].value,
    )
    logging.info(
        "snapshot_full_dump session_id=%s snapshot=%s",
        session.session_id(),
        _format_snapshot_dump(snapshot),
    )


def _attach_snapshot_reference(
    session: ProposalSession,
    snapshot_ref: SnapshotReference,
    store: Store,
) -> None:
    try:
        session.attach_snapshot(snapshot_ref)
    except Exception as exc:  # noqa: BLE001
        _mark_failed(session, store)
        raise RuntimeError(f"attach snapshot: {exc}") from exc

    try:
        store.update(session)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"persist snapshot state: {exc}") from exc


# -----------Guard rails-----------


def _validate_snapshot_job(job: Job) -> None:
    if job["type"] != JobType.SNAPSHOT_CAPTURE:
        raise ValueError(f'unsupported job type: "{job["type"]}"')
    if job["session_id"] == "":
        raise ValueError("session id is empty")
    if job["repo_id"] == "":
        raise ValueError("repo id is empty")

# -----------Failure handling-----------


def _mark_failed(proposal_session: ProposalSession | None, store: Store) -> None:
    if proposal_session is None:
        return

    if proposal_session.status() != State.FAILED:
        try:
            proposal_session.transition_to(State.FAILED)
        except NoopTransitionError:
            pass

    store.update(proposal_session)

# -----------Logging payload formatter-----------


def _format_snapshot_dump(snapshot) -> str:
    files = snapshot.file_content_map()
    serialized_files: dict[str, str] = {}
    for path, content in files.items():
        serialized_files[path] = content.decode("utf-8", errors="replace")

    payload = {
        "commitHash": snapshot.commit_hash(),
        "branchRef": snapshot.branch_ref(),
        "fileCount": len(snapshot.files()),
        "files": serialized_files,
    }
    return json.dumps(payload, ensure_ascii=False)
