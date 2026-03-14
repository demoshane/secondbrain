import time
from collections import deque


class RateLimiter:
    """Sliding-window rate limiter for AI adapter calls.

    Designed for Phase 4 file watcher — prevents runaway API calls on
    bulk file operations (AI-09). Not thread-safe (single-threaded use only).

    Args:
        max_calls: Maximum allowed calls within window_seconds.
        window_seconds: Duration of the sliding window in seconds.
    """

    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self._max_calls = max_calls
        self._window = window_seconds
        self._timestamps: deque[float] = deque()

    def allow(self) -> bool:
        """Return True if a call is permitted; False if rate limit exceeded."""
        now = time.monotonic()
        # Evict timestamps outside the window
        while self._timestamps and now - self._timestamps[0] >= self._window:
            self._timestamps.popleft()
        if len(self._timestamps) < self._max_calls:
            self._timestamps.append(now)
            return True
        return False
