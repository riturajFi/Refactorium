from __future__ import annotations

from enum import Enum


class State(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    SNAPSHOT_READY = "SNAPSHOT_READY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    def is_valid(self) -> bool:
        return self in {
            State.CREATED,
            State.RUNNING,
            State.SNAPSHOT_READY,
            State.COMPLETED,
            State.FAILED,
        }


def parse_state(value: str) -> State:
    try:
        parsed = State(value)
    except ValueError as exc:
        raise ValueError(f'invalid session state: "{value}"') from exc

    if not parsed.is_valid():
        raise ValueError(f'invalid session state: "{value}"')
    return parsed
