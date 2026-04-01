"""Regression test: no absolute paths in DB path columns.

Catches the class of bugs where code stores '/Users/.../SecondBrain/...' instead
of relative paths like 'ideas/my-note.md'. This was the root cause of ~25 bugs
found during the April 2026 audit.
"""
import sqlite3
import pytest
from pathlib import Path

from engine.db import get_connection, init_schema
from engine.capture import capture_note


@pytest.fixture
def brain_db(tmp_path, monkeypatch):
    """Isolated brain DB + BRAIN_ROOT for path integrity tests."""
    import engine.db as _db
    import engine.paths as _paths

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", db_path)
    monkeypatch.setattr(_paths, "DB_PATH", db_path)
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)
    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))

    conn = get_connection()
    init_schema(conn)
    conn.commit()
    return conn


def _check_no_absolute_paths(conn, table: str, column: str):
    """Assert no rows in table.column start with '/' (absolute path)."""
    rows = conn.execute(
        f"SELECT {column} FROM {table} WHERE {column} LIKE '/%'"  # noqa: S608
    ).fetchall()
    if rows:
        examples = [r[0] for r in rows[:5]]
        pytest.fail(
            f"{table}.{column} contains {len(rows)} absolute path(s): {examples}"
        )


class TestNoAbsolutePathsAfterCapture:
    """After capture_note(), no DB table should contain absolute paths."""

    def test_capture_stores_relative_paths(self, brain_db, tmp_path, monkeypatch):
        import engine.paths as _paths
        monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)

        # Capture a note
        result = capture_note(
            note_type="idea",
            title="Test Path Integrity",
            body="This note tests path storage.",
            tags=["test"],
            people=["Test Person"],
            content_sensitivity="public",
            brain_root=tmp_path,
            conn=brain_db,
        )

        # The return value is an absolute Path (by design)
        assert result.is_absolute()

        # But every DB table must store relative paths
        _check_no_absolute_paths(brain_db, "notes", "path")
        _check_no_absolute_paths(brain_db, "note_tags", "note_path")
        _check_no_absolute_paths(brain_db, "note_people", "note_path")
        _check_no_absolute_paths(brain_db, "relationships", "source_path")
        _check_no_absolute_paths(brain_db, "relationships", "target_path")
        # note_embeddings and note_chunks are populated async; skip here

    def test_update_note_stores_relative_paths(self, brain_db, tmp_path, monkeypatch):
        import engine.paths as _paths
        monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)

        path = capture_note(
            note_type="note",
            title="Update Test",
            body="original",
            tags=["a"],
            people=[],
            content_sensitivity="public",
            brain_root=tmp_path,
            conn=brain_db,
        )

        from engine.capture import update_note
        update_note(
            note_path=str(path),
            title="Update Test Edited",
            body="edited",
            tags=["a", "b"],
            conn=brain_db,
            brain_root=tmp_path,
        )

        _check_no_absolute_paths(brain_db, "notes", "path")
        _check_no_absolute_paths(brain_db, "note_tags", "note_path")


class TestJunctionTableTriggers:
    """Verify SQLite triggers auto-sync note_tags and note_people from JSON columns."""

    def test_insert_populates_note_tags(self, brain_db, tmp_path, monkeypatch):
        import engine.paths as _paths
        monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)

        capture_note(
            note_type="idea", title="Trigger Tags Test", body="test",
            tags=["alpha", "beta"], people=[],
            content_sensitivity="public", brain_root=tmp_path, conn=brain_db,
        )
        rows = brain_db.execute("SELECT tag FROM note_tags ORDER BY tag").fetchall()
        assert [r[0] for r in rows] == ["alpha", "beta"]

    def test_insert_populates_note_people(self, brain_db, tmp_path, monkeypatch):
        import engine.paths as _paths
        monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)

        capture_note(
            note_type="meeting", title="Trigger People Test", body="test",
            tags=[], people=["Alice", "Bob"],
            content_sensitivity="public", brain_root=tmp_path, conn=brain_db,
        )
        rows = brain_db.execute("SELECT person FROM note_people ORDER BY person").fetchall()
        assert [r[0] for r in rows] == ["Alice", "Bob"]

    def test_update_syncs_note_tags(self, brain_db, tmp_path, monkeypatch):
        import engine.paths as _paths
        monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)

        path = capture_note(
            note_type="idea", title="Tag Update Test", body="v1",
            tags=["old"], people=[],
            content_sensitivity="public", brain_root=tmp_path, conn=brain_db,
        )
        from engine.paths import store_path
        rel = store_path(path.resolve())
        import json
        brain_db.execute(
            "UPDATE notes SET tags=? WHERE path=?",
            (json.dumps(["new-a", "new-b"]), rel),
        )
        brain_db.commit()
        rows = brain_db.execute(
            "SELECT tag FROM note_tags WHERE note_path=? ORDER BY tag", (rel,)
        ).fetchall()
        assert [r[0] for r in rows] == ["new-a", "new-b"]

    def test_raw_sql_insert_populates_junction(self, brain_db):
        """Even a raw SQL INSERT into notes (like reindex) triggers junction sync."""
        import json
        brain_db.execute(
            "INSERT INTO notes (path, type, title, body, tags, people, sensitivity) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test/raw.md", "note", "Raw Insert", "body",
             json.dumps(["t1", "t2"]), json.dumps(["Person A"]), "public"),
        )
        brain_db.commit()
        tags = brain_db.execute(
            "SELECT tag FROM note_tags WHERE note_path='test/raw.md' ORDER BY tag"
        ).fetchall()
        people = brain_db.execute(
            "SELECT person FROM note_people WHERE note_path='test/raw.md'"
        ).fetchall()
        assert [r[0] for r in tags] == ["t1", "t2"]
        assert [r[0] for r in people] == ["Person A"]
