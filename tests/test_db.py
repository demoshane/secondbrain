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
