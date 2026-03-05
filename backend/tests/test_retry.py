from __future__ import annotations

import unittest

from core.common.retry.retry import executeWithRetry


class RetryTests(unittest.TestCase):
    def test_do_retries_until_success(self) -> None:
        attempts = {"count": 0}

        def fn() -> int:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise RuntimeError("retryable")
            return 42

        got = executeWithRetry(fn).with_attempts(3).do()

        self.assertEqual(got, 42)
        self.assertEqual(attempts["count"], 3)

    def test_do_retries_on_every_error_until_exhausted(self) -> None:
        class TerminalError(Exception):
            pass

        attempts = {"count": 0}

        def fn() -> int:
            attempts["count"] += 1
            raise TerminalError("terminal")

        with self.assertRaises(TerminalError):
            executeWithRetry(fn).with_attempts(3).do()

        self.assertEqual(attempts["count"], 3)

    def test_do_returns_last_error_after_exhausting_retries(self) -> None:
        class RetryableError(Exception):
            pass

        attempts = {"count": 0}

        def fn() -> int:
            attempts["count"] += 1
            raise RetryableError("retryable")

        with self.assertRaises(RetryableError):
            executeWithRetry(fn).with_attempts(3).do()

        self.assertEqual(attempts["count"], 3)


if __name__ == "__main__":
    unittest.main()
