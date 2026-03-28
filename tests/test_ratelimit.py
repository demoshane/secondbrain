"""Tests for engine/ratelimit.py — COV-09."""
import time
import pytest
from engine.ratelimit import RateLimiter


def test_first_call_allowed():
    """Rate limiter allows the first call within the window."""
    rl = RateLimiter(max_calls=3, window_seconds=10.0)
    assert rl.allow() is True


def test_calls_within_limit_allowed():
    """All calls up to max_calls are allowed."""
    rl = RateLimiter(max_calls=3, window_seconds=10.0)
    results = [rl.allow() for _ in range(3)]
    assert all(results)


def test_exceeding_limit_blocked():
    """Call exceeding max_calls within window is blocked."""
    rl = RateLimiter(max_calls=3, window_seconds=10.0)
    for _ in range(3):
        rl.allow()
    # 4th call should be blocked
    assert rl.allow() is False


def test_zero_limit_always_blocked():
    """max_calls=0 blocks all calls immediately."""
    rl = RateLimiter(max_calls=0, window_seconds=10.0)
    assert rl.allow() is False


def test_window_expiry_resets_limit(monkeypatch):
    """After window expires, calls are allowed again."""
    rl = RateLimiter(max_calls=1, window_seconds=0.05)
    assert rl.allow() is True   # consumes the slot
    assert rl.allow() is False  # blocked within window

    # Advance time past the window by monkey-patching time.monotonic
    original_monotonic = time.monotonic
    start = original_monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: start + 1.0)

    assert rl.allow() is True  # window expired, slot available again
