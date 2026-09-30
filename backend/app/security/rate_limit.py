import threading
import time
from collections import defaultdict, deque


class FailureLimiter:
    """Counts failed attempts per key in a sliding window (brute-force protection for login)."""

    def __init__(self, max_failures: int, window_seconds: int) -> None:
        self._max = max_failures
        self._window = window_seconds
        self._failures: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        attempts = self._failures[key]
        while attempts and attempts[0] <= now - self._window:
            attempts.popleft()
        return attempts

    def is_blocked(self, *keys: str) -> bool:
        now = time.monotonic()
        with self._lock:
            return any(len(self._prune(key, now)) >= self._max for key in keys)

    def record_failure(self, *keys: str) -> None:
        now = time.monotonic()
        with self._lock:
            for key in keys:
                self._prune(key, now).append(now)

    def reset(self, *keys: str) -> None:
        with self._lock:
            for key in keys:
                self._failures.pop(key, None)


class RequestLimiter(FailureLimiter):
    """Caps requests per key in a sliding window (cost/abuse protection for LLM and voice calls)."""

    def allow(self, key: str) -> bool:
        if self.is_blocked(key):
            return False
        self.record_failure(key)  # every request counts, not only failures
        return True
