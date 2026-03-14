"""Unit tests for engine/watcher.py — FilesDropHandler debounce + rate-limit + history guard."""
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from engine.watcher import FilesDropHandler
from engine.ratelimit import RateLimiter


def _make_event(path: str, is_directory: bool = False):
    """Create a minimal mock FileCreatedEvent."""
    event = MagicMock()
    event.src_path = path
    event.is_directory = is_directory
    return event


def _make_stat(ctime: float):
    """Return a mock stat_result with given st_ctime."""
    stat = MagicMock()
    stat.st_ctime = ctime
    return stat


def test_debounce_fires_after_delay(tmp_path):
    """FilesDropHandler fires callback after debounce delay fires (Timer callback executed)."""
    callback = MagicMock()
    rate_limiter = MagicMock()
    rate_limiter.allow.return_value = True

    # Use a very short debounce so we can control Timer directly
    with patch("engine.watcher.threading.Timer") as MockTimer, \
         patch("pathlib.Path.stat") as mock_stat:
        # Make the file appear new (ctime = now)
        mock_stat.return_value = _make_stat(time.time())

        # Capture the timer and its callback so we can invoke it manually
        timer_instance = MagicMock()
        captured_callbacks = []

        def capture_timer(delay, fn, args=None):
            captured_callbacks.append((fn, args or []))
            return timer_instance

        MockTimer.side_effect = capture_timer

        handler = FilesDropHandler(callback, rate_limiter, observer_start_time=time.monotonic())
        event = _make_event(str(tmp_path / "note.md"))
        handler.on_created(event)

        # Timer should have been created
        assert len(captured_callbacks) == 1, "Expected one Timer to be created"

        # Manually fire the debounce callback (simulates Timer expiry)
        fn, args = captured_callbacks[0]
        fn(*args)

        # Callback should have been called with a Path
        callback.assert_called_once()
        called_path = callback.call_args[0][0]
        assert isinstance(called_path, Path)
        assert called_path.name == "note.md"


def test_bulk_drop_debounce(tmp_path):
    """Multiple rapid events for same path cancel+restart timer; callback called at most once."""
    callback = MagicMock()
    rate_limiter = MagicMock()
    rate_limiter.allow.return_value = True

    with patch("engine.watcher.threading.Timer") as MockTimer, \
         patch("pathlib.Path.stat") as mock_stat:
        mock_stat.return_value = _make_stat(time.time())

        timer_instances = []
        captured_callbacks = []

        def make_timer(delay, fn, args=None):
            t = MagicMock()
            timer_instances.append(t)
            captured_callbacks.append((fn, args or []))
            return t

        MockTimer.side_effect = make_timer

        handler = FilesDropHandler(callback, rate_limiter, observer_start_time=time.monotonic())
        path = str(tmp_path / "doc.pdf")
        event = _make_event(path)

        # Fire three rapid events for the same path
        handler.on_created(event)
        handler.on_created(event)
        handler.on_created(event)

        # First two timers should have been cancelled (debounce reset)
        assert timer_instances[0].cancel.call_count >= 1
        assert timer_instances[1].cancel.call_count >= 1

        # Three timer creations
        assert len(timer_instances) == 3

        # Fire only the last timer (the one that would actually fire after debounce)
        fn, args = captured_callbacks[-1]
        fn(*args)

        # Callback should be called at most once
        assert callback.call_count <= 1


def test_multi_file_drop_all_processed(tmp_path):
    """Dropping N files near-simultaneously processes ALL N files (batch design)."""
    callback = MagicMock()
    rate_limiter = MagicMock()
    rate_limiter.allow.return_value = True

    with patch("engine.watcher.threading.Timer") as MockTimer, \
         patch("pathlib.Path.stat") as mock_stat:
        mock_stat.return_value = _make_stat(time.time())

        captured_timers = []

        def make_timer(delay, fn, args=None):
            t = MagicMock()
            captured_timers.append((t, fn, args or []))
            return t

        MockTimer.side_effect = make_timer

        handler = FilesDropHandler(callback, rate_limiter, observer_start_time=time.monotonic())

        # Simulate 5 files dropped together — each gets its own on_created event
        paths = [str(tmp_path / f"file{i}.md") for i in range(5)]
        for p in paths:
            handler.on_created(_make_event(p))

        # Fire the batch timer (last timer = the shared batch timer)
        _, fn, args = captured_timers[-1]
        fn(*args)

    # All 5 files must have triggered the callback
    assert callback.call_count == 5, f"Expected 5 calls, got {callback.call_count}"
    called_paths = {call_args[0][0].name for call_args in callback.call_args_list}
    expected_names = {f"file{i}.md" for i in range(5)}
    assert called_paths == expected_names


def test_rate_limit_defers_second_batch(tmp_path):
    """Second batch within rate-limit window is retried (deferred), not silently dropped."""
    callback = MagicMock()
    rate_limiter = MagicMock()
    # First batch: allowed; second batch: blocked
    rate_limiter.allow.side_effect = [True, False]

    with patch("engine.watcher.threading.Timer") as MockTimer, \
         patch("pathlib.Path.stat") as mock_stat:
        mock_stat.return_value = _make_stat(time.time())

        captured_timers = []

        def make_timer(delay, fn, args=None):
            t = MagicMock()
            captured_timers.append((t, fn, args or []))
            return t

        MockTimer.side_effect = make_timer

        handler = FilesDropHandler(callback, rate_limiter, observer_start_time=time.monotonic())

        # First batch: one file
        handler.on_created(_make_event(str(tmp_path / "first.md")))
        # Fire the batch timer for first batch
        _, fn, args = captured_timers[-1]
        fn(*args)

        first_batch_timer_count = len(captured_timers)

        # Second batch arrives while window still active
        handler.on_created(_make_event(str(tmp_path / "second.md")))
        # Fire the batch timer for second batch (allow() returns False this time)
        _, fn, args = captured_timers[-1]
        fn(*args)

    # First batch processed (callback called once for first.md)
    assert callback.call_count >= 1
    # A retry timer was scheduled after the failed batch (timer count grew)
    assert len(captured_timers) > first_batch_timer_count, (
        "Expected a retry timer to be scheduled when rate limit blocks second batch"
    )


def test_skips_files_older_than_watcher_start(tmp_path):
    """Handler skips files whose ctime predates the watcher start time."""
    callback = MagicMock()
    rate_limiter = MagicMock()
    rate_limiter.allow.return_value = True

    # Use a large fixed monotonic value to represent observer start time
    fake_monotonic_start = 1_000_000.0
    # ctime that maps to 10 seconds before the observer started:
    # wall_time_at_start = time.time() - (monotonic_now - start_time)
    # old_ctime = wall_time_at_start - 10  =>  old
    # We'll patch monotonic to return fake_monotonic_start both at init and in on_created.
    real_now = time.time()
    old_ctime = real_now - 10.0  # clearly older than "watcher start"

    with patch("engine.watcher.time.monotonic", return_value=fake_monotonic_start), \
         patch("engine.watcher.time.time", return_value=real_now), \
         patch("pathlib.Path.stat") as mock_stat:
        mock_stat.return_value = _make_stat(old_ctime)

        handler = FilesDropHandler(
            callback,
            rate_limiter,
            observer_start_time=fake_monotonic_start,
        )

        event = _make_event(str(tmp_path / "old_file.pdf"))
        handler.on_created(event)

    # Callback must NOT have been called — file predates watcher
    callback.assert_not_called()
    rate_limiter.allow.assert_not_called()
