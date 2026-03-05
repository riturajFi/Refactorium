from __future__ import annotations

from datetime import datetime, timezone

from .errors import EmptyRepoIDError, EmptySessionIDError
from .proposal_session import ProposalSession
from .state import State


def new_proposal_session(session_id: str, repo_id: str) -> ProposalSession:
    if session_id == "":
        raise EmptySessionIDError("session id is empty")
    if repo_id == "":
        raise EmptyRepoIDError("repo id is empty")

    now = datetime.now(timezone.utc)
    return ProposalSession(
        session_id=session_id,
        repo_id=repo_id,
        status=State.CREATED,
        created_at=now,
        updated_at=now,
    )
