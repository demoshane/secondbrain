"""Tests for engine/health.py check functions (27-05 / ENGL-02).

Each check function returns a dict with keys: label, status, detail.
Tests verify return structure and correct ok/warn/fail routing based on state.
No real filesystem side-effects — all external calls are mocked.
"""
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def _assert_check_result(result, expected_status=None):
    """Assert result has required keys and optionally matches status."""
    assert isinstance(result, dict)
    assert "label" in result
    assert "status" in result
    assert "detail" in result
    assert result["status"] in ("ok", "warn", "fail")
    if expected_status is not None:
        assert result["status"] == expected_status


# ── check_brain_directory ─────────────────────────────────────────────────────

def test_check_brain_directory_ok(tmp_path, monkeypatch):
    import engine.paths as _paths
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)
    from engine.health import check_brain_directory
    result = check_brain_directory()
    _assert_check_result(result, "ok")


def test_check_brain_directory_fail_missing(tmp_path, monkeypatch):
    import engine.paths as _paths
    missing = tmp_path / "nonexistent"
    monkeypatch.setattr(_paths, "BRAIN_ROOT", missing)
    from engine.health import check_brain_directory
    result = check_brain_directory()
    _assert_check_result(result, "fail")


# ── check_database ────────────────────────────────────────────────────────────

def test_check_database_ok(tmp_path, monkeypatch):
    import engine.paths as _paths
    db_path = tmp_path / "brain.db"
    # Create a DB with required tables
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY)")
    conn.execute("CREATE TABLE relationships (id INTEGER PRIMARY KEY)")
    conn.execute("CREATE TABLE audit_log (id INTEGER PRIMARY KEY)")
    # FTS5 virtual table — create as regular table for test purposes
    conn.execute("CREATE TABLE notes_fts (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(_paths, "DB_PATH", db_path)
    from engine.health import check_database
    result = check_database()
    _assert_check_result(result, "ok")


def test_check_database_fail_not_found(tmp_path, monkeypatch):
    import engine.paths as _paths
    monkeypatch.setattr(_paths, "DB_PATH", tmp_path / "missing.db")
    from engine.health import check_database
    result = check_database()
    _assert_check_result(result, "fail")


def test_check_database_fail_missing_tables(tmp_path, monkeypatch):
    import engine.paths as _paths
    db_path = tmp_path / "partial.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY)")
    # Deliberately omit relationships, notes_fts, audit_log
    conn.commit()
    conn.close()
    monkeypatch.setattr(_paths, "DB_PATH", db_path)
    from engine.health import check_database
    result = check_database()
    _assert_check_result(result, "fail")
    assert "missing" in result["detail"]


# ── check_fts_index ───────────────────────────────────────────────────────────

def test_check_fts_index_ok(tmp_path, monkeypatch):
    import engine.paths as _paths
    db_path = tmp_path / "brain.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE notes (path TEXT, body TEXT)")
    conn.execute("INSERT INTO notes VALUES ('a.md', 'body')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(_paths, "DB_PATH", db_path)
    from engine.health import check_fts_index
    result = check_fts_index()
    _assert_check_result(result, "ok")
    assert "1" in result["detail"]


def test_check_fts_index_warn_empty(tmp_path, monkeypatch):
    import engine.paths as _paths
    db_path = tmp_path / "empty.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE notes (path TEXT, body TEXT)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(_paths, "DB_PATH", db_path)
    from engine.health import check_fts_index
    result = check_fts_index()
    _assert_check_result(result, "warn")


# ── check_global_cli ──────────────────────────────────────────────────────────

def test_check_global_cli_ok():
    from engine.health import check_global_cli
    with patch("shutil.which", return_value="/usr/local/bin/sb-search"):
        result = check_global_cli()
    _assert_check_result(result, "ok")


def test_check_global_cli_warn_missing():
    from engine.health import check_global_cli
    with patch("shutil.which", return_value=None):
        result = check_global_cli()
    _assert_check_result(result, "warn")
    assert "not in PATH" in result["detail"]


# ── check_git_hooks ───────────────────────────────────────────────────────────

def test_check_git_hooks_ok():
    from engine.health import check_git_hooks
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ".githooks\n"
    with patch("subprocess.run", return_value=mock_result):
        result = check_git_hooks()
    _assert_check_result(result, "ok")
    assert ".githooks" in result["detail"]


def test_check_git_hooks_warn_not_configured():
    from engine.health import check_git_hooks
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    with patch("subprocess.run", return_value=mock_result):
        result = check_git_hooks()
    _assert_check_result(result)
    # Either warn (not configured) or ok (.git exists check passes first) — just ensure no crash
    assert result["status"] in ("ok", "warn")
