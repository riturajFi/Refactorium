from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from flask import Flask, Response, jsonify, request
from core.adapters.git_adapter import NonRemoteRepoIDError, normalize_remote_repo_id
from core.common.retry.retry import executeWithRetry
from core.models.job.job import JobType
from core.models.session.errors import EmptyRepoIDError
from core.models.session.factory import new_proposal_session
from core.runtime.store.store import SessionAlreadyExistsError, SessionNotFoundError, Store


class Server:
    """HTTP server exposing session endpoints via Flask."""

    def __init__(self, store: Store, queue) -> None:
        self._store = store
        self._queue = queue
        self._new_session_id = generate_session_id
        self._app = Flask(__name__)
        self._register_routes()

    def handler(self):
        return self._app

    def _register_routes(self) -> None:
        self._app.add_url_rule("/sessions", view_func=self._handle_sessions, methods=["POST"])
        self._app.add_url_rule(
            "/sessions/<session_id>",
            view_func=self._handle_session_by_id,
            methods=["GET"],
        )

        self._app.register_error_handler(404, self._handle_404)
        self._app.register_error_handler(405, self._handle_405)

    def _handle_404(self, _error) -> Response:
        return _plain_text(404, "not found")

    def _handle_405(self, _error) -> Response:
        return _plain_text(405, "method not allowed")

    def _handle_sessions(self):
        try:
            body = request.get_data(cache=False)
            req = json.loads(body.decode("utf-8") if body else "{}")
        except Exception:  # noqa: BLE001
            return _plain_text(400, "invalid request body")

        repo_id = str(req.get("repoId", ""))
        ref = str(req.get("ref", "")) if req.get("ref") is not None else ""

        try:
            proposal_session = self._create_and_store_session(repo_id, ref)
        except EmptyRepoIDError:
            return _plain_text(400, "repoId is required")
        except NonRemoteRepoIDError:
            return _plain_text(400, "repoId must be a remote repository identifier")
        except Exception:  # noqa: BLE001
            return _plain_text(500, "failed to create session")

        return _json_response(200, {"sessionId": proposal_session.session_id()})

    def _handle_session_by_id(self, session_id: str):
        try:
            found = self._store.get(session_id)
        except SessionNotFoundError:
            return _plain_text(404, "not found")
        except Exception:  # noqa: BLE001
            return _plain_text(500, "failed to fetch session")

        response = {
            "sessionId": found.session_id(),
            "repoId": found.repo_id(),
            "status": found.status().value,
            "createdAt": _format_time(found.created_at()),
            "updatedAt": _format_time(found.updated_at()),
        }

        snapshot, ok = found.snapshot_reference()
        if ok:
            response["snapshot"] = {
                "commitHash": snapshot["commit_hash"],
                "branchRef": snapshot["branch_ref"],
                "fileCount": snapshot["file_count"],
                "source": snapshot["source"].value,
            }

        return _json_response(200, response)

    def _create_and_store_session(self, repo_id: str, ref: str):
        if self._queue is None:
            raise RuntimeError("job queue is not configured")

        def create_one():
            session_id = self._new_session_id()
            proposal_session = new_proposal_session(session_id, repo_id)

            self._store.create(proposal_session)
            normalize_remote_repo_id(repo_id)

            self._queue.enqueue(
                {
                    "type": JobType.SNAPSHOT_CAPTURE,
                    "session_id": proposal_session.session_id(),
                    "repo_id": proposal_session.repo_id(),
                    "ref": ref,
                }
            )
            return proposal_session

        try:
            proposal_session = executeWithRetry(create_one).with_attempts(3).do()
        except SessionAlreadyExistsError as exc:
            raise RuntimeError("unable to create unique session id") from exc

        if proposal_session is None:
            raise RuntimeError("unable to create unique session id")

        return proposal_session


def generate_session_id() -> str:
    return os.urandom(16).hex()


def _json_response(status: int, payload: dict):
    return jsonify(payload), status


def _plain_text(status: int, message: str) -> Response:
    return Response(message, status=status, content_type="text/plain; charset=utf-8")


def _format_time(value: datetime) -> str:
    utc_value = value.astimezone(timezone.utc)
    return utc_value.isoformat().replace("+00:00", "Z")
