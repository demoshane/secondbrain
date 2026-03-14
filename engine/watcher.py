"""File watcher daemon for brain/files/ — detects dropped files and triggers AI categorization (CAP-04).

Run as: sb-watch (separate daemon process, not part of sb-capture)
"""
import threading
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from engine.ratelimit import RateLimiter

DEBOUNCE_SECONDS = 5.0


class FilesDropHandler(FileSystemEventHandler):
    """Watch brain/files/ for new files; debounce + rate-limit AI categorization.

    Uses a single shared batch timer: all files dropped within DEBOUNCE_SECONDS are
    collected into _pending_paths and processed together in one batch. The rate limiter
    gates batches (not individual files). If a batch is rate-limited, it is retried after
    the window expires rather than silently dropped.

    Args:
        on_new_file: Callable[Path] -> None — called for each stable file.
        rate_limiter: RateLimiter(max_calls=1, window_seconds=5.0) — gates AI calls per batch.
        observer_start_time: monotonic time when observer was started (FSEvents history guard).
    """

    def __init__(self, on_new_file, rate_limiter: RateLimiter, observer_start_time: float | None = None):
        self._on_new_file = on_new_file
        self._rate_limiter = rate_limiter
        self._pending_paths: set[str] = set()
        self._batch_timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._start_time = observer_start_time or time.monotonic()

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        path = event.src_path
        # FSEvents history guard: skip files that existed before watcher started
        try:
            ctime = Path(path).stat().st_ctime
            if ctime < (time.time() - (time.monotonic() - self._start_time) - 1):
                return
        except OSError:
            return
        # Accumulate path; reset the single shared debounce timer
        with self._lock:
            self._pending_paths.add(path)
            if self._batch_timer is not None:
                self._batch_timer.cancel()
            timer = threading.Timer(DEBOUNCE_SECONDS, self._fire_batch)
            self._batch_timer = timer
        timer.start()

    def _fire_batch(self) -> None:
        """Process all accumulated paths as one batch. Defers if rate-limited."""
        with self._lock:
            batch = set(self._pending_paths)
            self._pending_paths.clear()
            self._batch_timer = None

        if not batch:
            return

        if self._rate_limiter.allow():
            for path in batch:
                self._on_new_file(Path(path))
        else:
            # Rate-limited: put paths back and schedule a retry after window expires
            with self._lock:
                self._pending_paths.update(batch)
                retry_timer = threading.Timer(
                    self._rate_limiter._window, self._fire_batch
                )
                self._batch_timer = retry_timer
            retry_timer.start()


def start_watcher(watch_dir: Path, on_new_file) -> Observer:
    """Start a watchdog Observer for watch_dir. Returns the Observer (caller must call .stop())."""
    rate_limiter = RateLimiter(max_calls=1, window_seconds=5.0)
    start_time = time.monotonic()
    handler = FilesDropHandler(on_new_file, rate_limiter, observer_start_time=start_time)
    observer = Observer()
    observer.schedule(handler, str(watch_dir), recursive=False)
    observer.start()
    return observer


def main() -> None:
    """CLI entry point: sb-watch daemon. Watches BRAIN_ROOT/files/ for dropped files."""
    from engine.paths import BRAIN_ROOT
    from engine.router import get_adapter
    from engine.paths import CONFIG_PATH

    watch_dir = BRAIN_ROOT / "files"
    watch_dir.mkdir(parents=True, exist_ok=True)

    def on_new_file(path: Path) -> None:
        print(f"\n[sb-watch] New file detected: {path.name}")
        answer = input("Categorize this file as a brain note? [y/N]: ").strip().lower()
        if answer != "y":
            return
        title = input("Title for this note: ").strip()
        if not title:
            return
        from engine.capture import capture_note
        from engine.db import get_connection, init_schema
        conn = get_connection()
        init_schema(conn)
        adapter = get_adapter("public", CONFIG_PATH)
        system = "You are a file categorization assistant. Given a filename, suggest 2-3 tags."
        try:
            tags_str = adapter.generate(
                user_content=f"File: {path.name}\nTitle: {title}",
                system_prompt=system,
            )
            tags = [t.strip() for t in tags_str.split(",") if t.strip()][:3]
        except Exception as e:
            print(f"[sb-watch] AI tagging skipped: {type(e).__name__}")
            tags = []
        capture_note("note", title, f"File: {path}", tags, [], "private", BRAIN_ROOT, conn)
        conn.close()
        print("[sb-watch] Brain note created.")

    print(f"[sb-watch] Watching {watch_dir} for new files (Ctrl+C to stop)...")
    observer = start_watcher(watch_dir, on_new_file)
    try:
        while observer.is_alive():
            observer.join(timeout=1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
