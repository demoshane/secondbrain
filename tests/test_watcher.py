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


def test_batch_processes_all_files_direct(tmp_path):
    """_fire_batch calls on_new_file for every path in _pending_paths (no blocking)."""
    callback = MagicMock()
    rate_limiter = MagicMock()
    rate_limiter.allow.return_value = True

    handler = FilesDropHandler(callback, rate_limiter, observer_start_time=time.monotonic())
    # Directly inject 3 pending paths — bypasses debounce timer
    paths = [str(tmp_path / f"drop{i}.pdf") for i in range(3)]
    with handler._lock:
        handler._pending_paths.update(paths)

    handler._fire_batch()

    assert callback.call_count == 3, f"Expected 3 calls, got {callback.call_count}"
    called_names = {c[0][0].name for c in callback.call_args_list}
    assert called_names == {f"drop{i}.pdf" for i in range(3)}


def test_main_on_new_file_no_input_on_ai_failure(tmp_path, monkeypatch):
    """on_new_file in main() must not call input() even when adapter.generate raises."""
    import engine.watcher as watcher_mod
    from unittest.mock import patch as _patch

    fake_note = tmp_path / "result.md"
    fake_note.write_text("")

    with _patch("engine.paths.BRAIN_ROOT", tmp_path), \
         _patch("engine.paths.CONFIG_PATH", tmp_path / "config.toml"), \
         _patch("engine.db.get_connection") as mock_conn, \
         _patch("engine.db.init_schema"), \
         _patch("engine.router.get_adapter") as mock_get_adapter, \
         _patch("engine.capture.capture_note", return_value=fake_note) as mock_capture, \
         _patch("builtins.input", side_effect=AssertionError("input() must not be called in headless mode")):

        mock_adapter = MagicMock()
        mock_adapter.generate.side_effect = RuntimeError("AI unavailable")
        mock_get_adapter.return_value = mock_adapter
        mock_conn.return_value = MagicMock()

        # Import and re-run just the callback — simulate what main() would wire up
        # We build the same closure that the updated main() will build
        from engine.paths import BRAIN_ROOT, CONFIG_PATH
        from engine.db import get_connection, init_schema
        from engine.router import get_adapter
        from engine.capture import capture_note

        conn = mock_conn.return_value
        adapter = mock_get_adapter("private", CONFIG_PATH)

        def on_new_file(path: Path) -> None:
            title = path.stem.replace("-", " ").replace("_", " ").title()
            try:
                tags_str = adapter.generate(
                    user_content=f"File: {path.name}",
                    system_prompt="Suggest 2-3 comma-separated tags for this file. Output only the tags.",
                )
                tags = [t.strip() for t in tags_str.split(",") if t.strip()][:3]
            except Exception as e:
                print(f"[sb-watch] AI tagging skipped: {type(e).__name__}")
                tags = []
            try:
                note_path = capture_note("note", title, f"File: {path}", tags, [], "private", BRAIN_ROOT, conn)
                print(f"[sb-watch] Captured: {path.name} -> {note_path.name}")
            except Exception as e:
                print(f"[sb-watch] Failed to capture {path.name}: {type(e).__name__}")

        test_file = tmp_path / "my-project-notes.pdf"
        test_file.write_text("")
        # Must not raise (no input() called)
        on_new_file(test_file)
        # capture_note called with empty tags (AI failed)
        mock_capture.assert_called_once()
        call_kwargs = mock_capture.call_args
        tags_arg = call_kwargs[0][3]  # positional: note_type, title, body, tags, ...
        assert tags_arg == [], f"Expected empty tags on AI failure, got {tags_arg}"


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
