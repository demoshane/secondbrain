import sqlite3
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.db import init_schema


def test_schema_complete(db_conn):
    init_schema(db_conn)
    tables = {r[0] for r in db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','shadow')"
    ).fetchall()}
    for expected in ["notes", "relationships", "audit_log"]:
        assert expected in tables, f"Table {expected} missing"
    # FTS5 virtual table shows as 'table' in sqlite_master
    all_names = {r[0] for r in db_conn.execute(
        "SELECT name FROM sqlite_master"
    ).fetchall()}
    assert "notes_fts" in all_names


def test_schema_idempotent(db_conn):
    init_schema(db_conn)
    init_schema(db_conn)  # second call must not raise


def test_fts5_triggers_exist(db_conn):
    init_schema(db_conn)
    triggers = {r[0] for r in db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger'"
    ).fetchall()}
    for t in ["notes_ai", "notes_ad", "notes_au"]:
        assert t in triggers, f"Trigger {t} missing"


@pytest.mark.xfail(strict=False, reason="GPAG-03: assignee_path migration not yet implemented")
def test_migrate_assignee_path(tmp_path):
    import sqlite3
    from engine.db import init_schema
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    init_schema(conn)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(action_items)").fetchall()}
    assert "assignee_path" in cols
    # Idempotency: second call must not raise
    init_schema(conn)
    cols2 = {row[1] for row in conn.execute("PRAGMA table_info(action_items)").fetchall()}
    assert "assignee_path" in cols2
    conn.close()


@pytest.mark.xfail(strict=False, reason="GPAG-03: due_date migration not yet implemented")
def test_migrate_due_date(tmp_path):
    import sqlite3
    from engine.db import init_schema
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    init_schema(conn)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(action_items)").fetchall()}
    assert "due_date" in cols
    # Idempotency: second call must not raise
    init_schema(conn)
    cols2 = {row[1] for row in conn.execute("PRAGMA table_info(action_items)").fetchall()}
    assert "due_date" in cols2
    conn.close()
