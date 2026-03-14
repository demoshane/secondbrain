import pytest
import engine.watcher  # noqa: F401 — import guard


@pytest.mark.xfail(strict=False, reason="stub — CAP-04 implementation pending")
def test_debounce_fires_after_delay():
    """FilesDropHandler fires callback after debounce delay."""
    raise NotImplementedError


@pytest.mark.xfail(strict=False, reason="stub — CAP-04 implementation pending")
def test_bulk_drop_debounce():
    """Multiple rapid events collapse to one callback per file."""
    raise NotImplementedError


@pytest.mark.xfail(strict=False, reason="stub — CAP-04 implementation pending")
def test_rate_limit_gates_ai_call():
    """RateLimiter suppresses second call within 5s window."""
    raise NotImplementedError


@pytest.mark.xfail(strict=False, reason="stub — CAP-04 implementation pending")
def test_skips_files_older_than_watcher_start():
    """Handler skips files that existed before watcher started (FSEvents history guard)."""
    raise NotImplementedError
