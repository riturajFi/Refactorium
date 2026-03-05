from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")
DEFAULT_ATTEMPTS = 3


class RetryBuilder(Generic[T]):
    def __init__(self, fn: Callable[[], T], attempts: int = DEFAULT_ATTEMPTS) -> None:
        self._fn = fn
        self._attempts = attempts

    def with_attempts(self, attempts: int) -> RetryBuilder[T]:
        self._attempts = attempts
        return self

    def do(self) -> T | None:
        if self._attempts <= 0:
            return None

        last_error: Exception | None = None
        for _ in range(self._attempts):
            try:
                return self._fn()
            except Exception as exc:  # noqa: BLE001
                last_error = exc

        if last_error is not None:
            raise last_error
        return None


def executeWithRetry(fn: Callable[[], T]) -> RetryBuilder[T]:
    return RetryBuilder(fn)
