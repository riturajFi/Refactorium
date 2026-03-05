from __future__ import annotations

from threading import RLock

from core.models.session.proposal_session import ProposalSession


class NilSessionError(ValueError):
    """Raised when session argument is None."""


class SessionAlreadyExistsError(ValueError):
    """Raised when creating duplicate session id."""


class SessionNotFoundError(ValueError):
    """Raised when session does not exist."""


class Store:
    """Persistence contract for ProposalSession."""

    def create(self, proposal_session: ProposalSession) -> None:
        raise NotImplementedError

    def get(self, session_id: str) -> ProposalSession:
        raise NotImplementedError

    def update(self, proposal_session: ProposalSession) -> None:
        raise NotImplementedError


class InMemoryStore(Store):
    """In-memory session store for process lifetime."""

    def __init__(self) -> None:
        self._mu = RLock()
        self._sessions: dict[str, ProposalSession] = {}

    def create(self, proposal_session: ProposalSession) -> None:
        if proposal_session is None:
            raise NilSessionError("session is nil")

        with self._mu:
            session_id = proposal_session.session_id()
            if session_id in self._sessions:
                raise SessionAlreadyExistsError(f'session already exists: "{session_id}"')

            self._sessions[session_id] = proposal_session.clone()

    def get(self, session_id: str) -> ProposalSession:
        with self._mu:
            stored = self._sessions.get(session_id)
            if stored is None:
                raise SessionNotFoundError(f'session not found: "{session_id}"')

            return stored.clone()

    def update(self, proposal_session: ProposalSession) -> None:
        if proposal_session is None:
            raise NilSessionError("session is nil")

        with self._mu:
            session_id = proposal_session.session_id()
            if session_id not in self._sessions:
                raise SessionNotFoundError(f'session not found: "{session_id}"')
            self._sessions[session_id] = proposal_session.clone()
