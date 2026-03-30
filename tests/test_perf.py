"""Unit tests for engine/perf.py and engine/test_utils.py."""
from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def perf_dir(tmp_path, monkeypatch) -> Path:
    """Isolated PERF_DIR for storage/rotation tests."""
    d = tmp_path / "perf_results"
    d.mkdir()
    import engine.perf as perf_mod
    monkeypatch.setattr(perf_mod, "PERF_DIR", d)
    return d


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Temp SQLite DB with full schema. Patches engine.db.DB_PATH and engine.paths.DB_PATH."""
    import engine.db as db_mod
    import engine.paths as paths_mod
    from engine.db import init_schema

    db_file = tmp_path / "test_brain.db"
    conn = sqlite3.connect(str(db_file))
    init_schema(conn)
    conn.close()

    monkeypatch.setattr(db_mod, "DB_PATH", db_file)
    monkeypatch.setattr(paths_mod, "DB_PATH", db_file)
    monkeypatch.setattr(paths_mod, "BRAIN_ROOT", tmp_path / "brain")
    (tmp_path / "brain").mkdir(exist_ok=True)
    return db_file


# ---------------------------------------------------------------------------
# test_utils.py tests
# ---------------------------------------------------------------------------

def test_cleanup_test_notes(isolated_db, tmp_path, monkeypatch):
    """cleanup_test_notes deletes matching notes from DB (all cascade tables) and disk."""
    import engine.db as db_mod
    brain_root = tmp_path / "brain"
    brain_root.mkdir(exist_ok=True)

    import engine.paths as paths_mod
    monkeypatch.setattr(paths_mod, "BRAIN_ROOT", brain_root)

    # Insert 2 notes with __perf_test__ prefix
    conn = sqlite3.connect(str(isolated_db))
    for i in range(2):
        note_path = f"notes/__perf_test__note{i}.md"
        conn.execute(
            "INSERT INTO notes (path, title, type, body, tags) VALUES (?, ?, ?, ?, ?)",
            (note_path, f"__perf_test__note{i}", "note", "test body", "[]"),
        )
        # Create physical file
        note_file = brain_root / note_path
        note_file.parent.mkdir(parents=True, exist_ok=True)
        note_file.write_text("---\ntitle: test\n---\nbody", encoding="utf-8")
    conn.commit()
    conn.close()

    from engine.test_utils import cleanup_test_notes
    count = cleanup_test_notes("__perf_test__")

    assert count == 2

    # Verify DB is clean
    conn = sqlite3.connect(str(isolated_db))
    remaining = conn.execute("SELECT COUNT(*) FROM notes WHERE title LIKE '__perf_test__%'").fetchone()[0]
    conn.close()
    assert remaining == 0


def test_cleanup_returns_zero_when_nothing_matches(isolated_db):
    """Returns 0 when no notes match the prefix."""
    from engine.test_utils import cleanup_test_notes
    count = cleanup_test_notes("__no_such_prefix_xyz__")
    assert count == 0


# ---------------------------------------------------------------------------
# save_result / load_result / list_result_dates
# ---------------------------------------------------------------------------

def test_save_result(perf_dir):
    """save_result writes YYYY-MM-DD.json to PERF_DIR."""
    from engine.perf import save_result

    data = {"run_at": "2026-03-30T12:00:00Z", "tool_results": []}
    path = save_result(data)

    today = datetime.date.today().isoformat()
    assert path.name == f"{today}.json"
    assert path.exists()
    saved = json.loads(path.read_text())
    assert saved["run_at"] == data["run_at"]


def test_load_result_returns_none_for_missing(perf_dir):
    """load_result returns None when date file doesn't exist."""
    from engine.perf import load_result
    assert load_result("1999-01-01") is None


def test_list_result_dates(perf_dir):
    """list_result_dates returns sorted stems from PERF_DIR."""
    from engine.perf import list_result_dates

    for date in ("2026-03-28", "2026-03-30", "2026-03-29"):
        (perf_dir / f"{date}.json").write_text("{}", encoding="utf-8")

    dates = list_result_dates()
    assert dates == ["2026-03-28", "2026-03-29", "2026-03-30"]


def test_list_result_dates_empty(perf_dir):
    """list_result_dates returns [] when PERF_DIR is empty."""
    from engine.perf import list_result_dates
    assert list_result_dates() == []


# ---------------------------------------------------------------------------
# rotate_old_results
# ---------------------------------------------------------------------------

def test_rotate_old_results(perf_dir):
    """Deletes files older than 30 days, always keeps the most recent file."""
    from engine.perf import rotate_old_results

    today = datetime.date.today()
    # 3 old files (>30 days), 1 recent file
    old_dates = [(today - datetime.timedelta(days=31 + i)).isoformat() for i in range(3)]
    recent_date = today.isoformat()

    all_dates = old_dates + [recent_date]
    for d in all_dates:
        (perf_dir / f"{d}.json").write_text("{}", encoding="utf-8")

    deleted = rotate_old_results()
    assert deleted == 3  # 3 old files deleted

    # Most recent (today) must remain
    assert (perf_dir / f"{recent_date}.json").exists()
    # All old files gone
    for d in old_dates:
        assert not (perf_dir / f"{d}.json").exists()


def test_rotate_always_keeps_last_file(perf_dir):
    """Even if the only file is old, rotate keeps it (last file protection)."""
    from engine.perf import rotate_old_results

    old_date = (datetime.date.today() - datetime.timedelta(days=60)).isoformat()
    (perf_dir / f"{old_date}.json").write_text("{}", encoding="utf-8")

    deleted = rotate_old_results()
    assert deleted == 0
    assert (perf_dir / f"{old_date}.json").exists()


# ---------------------------------------------------------------------------
# get_latest_with_previous
# ---------------------------------------------------------------------------

def test_get_latest_with_previous(perf_dir):
    """Returns both latest and previous when 2+ result files exist."""
    from engine.perf import get_latest_with_previous

    (perf_dir / "2026-03-29.json").write_text('{"run_at": "prev", "tool_results": []}')
    (perf_dir / "2026-03-30.json").write_text('{"run_at": "latest", "tool_results": []}')

    result = get_latest_with_previous()
    assert result["latest"]["run_at"] == "latest"
    assert result["previous"]["run_at"] == "prev"


def test_get_latest_with_previous_single_file(perf_dir):
    """previous is None when only one result file exists."""
    from engine.perf import get_latest_with_previous

    (perf_dir / "2026-03-30.json").write_text('{"run_at": "only", "tool_results": []}')

    result = get_latest_with_previous()
    assert result["latest"]["run_at"] == "only"
    assert result["previous"] is None


def test_get_latest_with_previous_no_files(perf_dir):
    """Both None when PERF_DIR is empty."""
    from engine.perf import get_latest_with_previous
    result = get_latest_with_previous()
    assert result == {"latest": None, "previous": None}


# ---------------------------------------------------------------------------
# compute_delta / _determine_status
# ---------------------------------------------------------------------------

def test_delta_computation():
    """compute_delta returns correct delta values and statuses."""
    from engine.perf import compute_delta

    latest = {
        "run_at": "2026-03-30T12:00:00Z",
        "tool_results": [
            {"tool": "sb_search", "elapsed_ms": 150.0, "limit_ms": 2000, "status": "pass", "error": None},
            {"tool": "sb_recap", "elapsed_ms": 25000.0, "limit_ms": 20000, "status": "warn", "error": None},
        ],
    }
    previous = {
        "run_at": "2026-03-29T12:00:00Z",
        "tool_results": [
            {"tool": "sb_search", "elapsed_ms": 120.0, "limit_ms": 2000, "status": "pass", "error": None},
            {"tool": "sb_recap", "elapsed_ms": 18000.0, "limit_ms": 20000, "status": "pass", "error": None},
        ],
    }

    deltas = compute_delta(latest, previous)
    delta_map = {d["tool"]: d for d in deltas}

    assert delta_map["sb_search"]["delta_ms"] == pytest.approx(30.0)
    assert delta_map["sb_search"]["latest_ms"] == 150.0
    assert delta_map["sb_search"]["previous_ms"] == 120.0

    assert delta_map["sb_recap"]["delta_ms"] == pytest.approx(7000.0)
    assert delta_map["sb_recap"]["status"] == "warn"


def test_delta_computation_no_previous():
    """With no previous result, delta_ms and previous_ms are None."""
    from engine.perf import compute_delta

    latest = {
        "run_at": "2026-03-30T12:00:00Z",
        "tool_results": [
            {"tool": "sb_search", "elapsed_ms": 150.0, "limit_ms": 2000, "status": "pass", "error": None},
        ],
    }

    deltas = compute_delta(latest, None)
    assert deltas[0]["previous_ms"] is None
    assert deltas[0]["delta_ms"] is None


def test_error_recovery():
    """_determine_status returns 'error' when error is set, regardless of elapsed."""
    from engine.perf import _determine_status
    assert _determine_status(100.0, 2000, "something broke") == "error"
    assert _determine_status(100.0, 2000, None) == "pass"
    assert _determine_status(3000.0, 2000, None) == "warn"


# ---------------------------------------------------------------------------
# _time_tool
# ---------------------------------------------------------------------------

def test_time_tool_success():
    """_time_tool measures elapsed time and returns None error for successful calls."""
    from engine.perf import _time_tool
    import time

    def fast_fn():
        time.sleep(0.01)

    elapsed_ms, error = _time_tool(fast_fn)
    assert elapsed_ms >= 10.0
    assert error is None


def test_time_tool_error():
    """_time_tool captures exception message and returns it as error string."""
    from engine.perf import _time_tool

    def failing_fn():
        raise ValueError("test failure")

    elapsed_ms, error = _time_tool(failing_fn)
    assert error is not None
    assert "test failure" in error


def test_time_tool_async():
    """_time_tool handles async functions via asyncio.run."""
    from engine.perf import _time_tool

    async def async_fn():
        return "ok"

    elapsed_ms, error = _time_tool(async_fn)
    assert error is None
    assert elapsed_ms >= 0


# ---------------------------------------------------------------------------
# run_benchmarks — filter + full suite (PERF-09, PERF-10)
# ---------------------------------------------------------------------------

_CANNED_READ = [{"tool": "sb_search", "elapsed_ms": 100.0, "limit_ms": 2000, "status": "pass", "error": None}]
_CANNED_WRITE = [{"tool": "sb_capture", "elapsed_ms": 200.0, "limit_ms": 5000, "status": "pass", "error": None}]
_CANNED_AI = [{"tool": "sb_recap", "elapsed_ms": 5000.0, "limit_ms": 20000, "status": "pass", "error": None}]


def test_run_benchmarks_with_filter():
    """--tool filter restricts results to the matching tool only (PERF-10)."""
    from engine import perf as perf_mod

    with patch.object(perf_mod, "_benchmark_read_tools", return_value=_CANNED_READ), \
         patch.object(perf_mod, "_benchmark_write_tools", return_value=_CANNED_WRITE), \
         patch.object(perf_mod, "_benchmark_ai_tools", return_value=_CANNED_AI):

        result = perf_mod.run_benchmarks(tool_filter="sb_search")

    assert "run_at" in result
    assert len(result["tool_results"]) == 1
    assert result["tool_results"][0]["tool"] == "sb_search"


def test_full_suite_runs():
    """run_benchmarks() with no filter includes all tool_results and has 'run_at' (PERF-09)."""
    from engine import perf as perf_mod

    with patch.object(perf_mod, "_benchmark_read_tools", return_value=_CANNED_READ), \
         patch.object(perf_mod, "_benchmark_write_tools", return_value=_CANNED_WRITE), \
         patch.object(perf_mod, "_benchmark_ai_tools", return_value=_CANNED_AI):

        result = perf_mod.run_benchmarks(tool_filter=None)

    assert "run_at" in result
    assert len(result["tool_results"]) == 3
    tool_names = {r["tool"] for r in result["tool_results"]}
    assert "sb_search" in tool_names
    assert "sb_capture" in tool_names
    assert "sb_recap" in tool_names


# ---------------------------------------------------------------------------
# --cleanup flag (main)
# ---------------------------------------------------------------------------

def test_cleanup_flag(capsys):
    """main() with --cleanup calls cleanup_test_notes and exits 0."""
    from engine import perf as perf_mod

    with patch.object(perf_mod, "cleanup_test_notes" if hasattr(perf_mod, "cleanup_test_notes") else "engine.test_utils.cleanup_test_notes", create=True):
        # Import cleanup from test_utils and patch it
        import engine.test_utils as tu_mod
        with patch.object(tu_mod, "cleanup_test_notes", return_value=3) as mock_cleanup:
            # Patch the import inside main() by patching the module reference
            with patch("engine.perf.cleanup_test_notes", mock_cleanup, create=True):
                with pytest.raises(SystemExit) as exc_info:
                    import sys
                    sys.argv = ["sb-perf", "--cleanup"]
                    perf_mod.main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "3" in captured.out


# ---------------------------------------------------------------------------
# --json output (PERF-11)
# ---------------------------------------------------------------------------

_CANNED_RESULT = {
    "run_at": "2026-03-30T12:00:00Z",
    "tool_results": [
        {"tool": "sb_search", "elapsed_ms": 100.0, "limit_ms": 2000, "status": "pass", "error": None},
    ],
}


def test_json_output(perf_dir, capsys):
    """main() with --json outputs valid JSON with 'run_at' and 'tool_results' keys (PERF-11)."""
    from engine import perf as perf_mod
    import sys

    with patch.object(perf_mod, "run_benchmarks", return_value=_CANNED_RESULT), \
         patch.object(perf_mod, "save_result", return_value=perf_dir / "2026-03-30.json"), \
         patch.object(perf_mod, "rotate_old_results", return_value=0), \
         patch("engine.test_utils.cleanup_test_notes", return_value=0):

        sys.argv = ["sb-perf", "--json"]
        with pytest.raises(SystemExit) as exc_info:
            perf_mod.main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert "run_at" in output
    assert "tool_results" in output
    assert output["run_at"] == "2026-03-30T12:00:00Z"
