"""Tests for engine/consolidate.py — scheduled consolidation job."""
import sqlite3
import pytest
from engine.db import init_schema


@pytest.fixture
def cons_conn(tmp_path):
    import engine.db as _db
    import engine.paths as _paths
    db_path = tmp_path / "consolidate_test.db"
    _db.DB_PATH = db_path
    _paths.DB_PATH = db_path
    conn = sqlite3.connect(str(db_path))
    init_schema(conn)
    yield conn
    conn.close()


def test_consolidate_main_runs_clean(cons_conn, capsys):
    from engine.consolidate import consolidate_main
    consolidate_main()
    captured = capsys.readouterr()
    import json
    result = json.loads(captured.out)
    assert "archived_actions" in result
    assert "deleted_dangling" in result
    assert "snapshot" in result
    assert "cleaned_old_snapshots" in result


def test_consolidate_idempotent(cons_conn, capsys):
    from engine.consolidate import consolidate_main
    consolidate_main()
    consolidate_main()  # second run should not error
    # Snapshot should be skipped on second run (one-per-day guard)
    lines = capsys.readouterr().out.strip().split("\n")
    import json
    second = json.loads(lines[1])
    assert second["snapshot"]["skipped"] is True
