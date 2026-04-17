"""Tests for Phase 56 Plan 01: capture_session persistence + find_temporal_neighbors()."""

import datetime
import sqlite3

import pytest


@pytest.fixture
def db(db_conn):
    """In-memory DB with schema, ready for temporal neighbor tests."""
    from engine.db import init_schema

    init_schema(db_conn)
    return db_conn


def _insert_note(conn, path, title, note_type="note", created_at=None, capture_session=None):
    """Insert a minimal note row for testing."""
    created_at = created_at or datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT INTO notes (path, type, title, body, tags, people, created_at, updated_at, sensitivity, importance, capture_session)"
        " VALUES (?, ?, ?, '', '[]', '[]', ?, ?, 'public', 'medium', ?)",
        (path, note_type, title, created_at, created_at, capture_session),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# DB migration tests
# ---------------------------------------------------------------------------


class TestCaptureSessionMigration:
    def test_column_exists_after_init(self, db):
        cols = {r[1] for r in db.execute("PRAGMA table_info(notes)").fetchall()}
        assert "capture_session" in cols

    def test_column_nullable(self, db):
        _insert_note(db, "test/note.md", "No session")
        row = db.execute("SELECT capture_session FROM notes WHERE path = ?", ("test/note.md",)).fetchone()
        assert row[0] is None

    def test_column_stores_value(self, db):
        _insert_note(db, "test/note.md", "With session", capture_session="abc-123")
        row = db.execute("SELECT capture_session FROM notes WHERE path = ?", ("test/note.md",)).fetchone()
        assert row[0] == "abc-123"

    def test_migration_idempotent(self, db):
        from engine.db import migrate_add_capture_session

        # Running twice should not raise
        migrate_add_capture_session(db)
        migrate_add_capture_session(db)
        cols = {r[1] for r in db.execute("PRAGMA table_info(notes)").fetchall()}
        assert "capture_session" in cols


# ---------------------------------------------------------------------------
# capture_note() capture_session persistence
# ---------------------------------------------------------------------------


class TestCaptureNoteSession:
    def test_capture_without_session(self, db, brain_root, monkeypatch):
        import engine.paths as _paths
        import engine.db as _db

        monkeypatch.setattr(_paths, "BRAIN_ROOT", brain_root)
        monkeypatch.setattr(_db, "DB_PATH", brain_root / ".index" / "brain.db")
        monkeypatch.setattr(_paths, "DB_PATH", brain_root / ".index" / "brain.db")

        from engine.capture import capture_note

        path = capture_note(
            "note", "Test Note", "body", [], [], "public", brain_root, db,
        )
        row = db.execute(
            "SELECT capture_session FROM notes WHERE title = 'Test Note'"
        ).fetchone()
        assert row[0] is None

    def test_capture_with_session(self, db, brain_root, monkeypatch):
        import engine.paths as _paths
        import engine.db as _db

        monkeypatch.setattr(_paths, "BRAIN_ROOT", brain_root)
        monkeypatch.setattr(_db, "DB_PATH", brain_root / ".index" / "brain.db")
        monkeypatch.setattr(_paths, "DB_PATH", brain_root / ".index" / "brain.db")

        from engine.capture import capture_note

        path = capture_note(
            "note", "Session Note", "body", [], [], "public", brain_root, db,
            capture_session="sess-uuid-42",
        )
        row = db.execute(
            "SELECT capture_session FROM notes WHERE title = 'Session Note'"
        ).fetchone()
        assert row[0] == "sess-uuid-42"


# ---------------------------------------------------------------------------
# find_temporal_neighbors() tests
# ---------------------------------------------------------------------------


def _ts(minutes_offset: int = 0) -> str:
    """Return ISO timestamp offset from a fixed reference point."""
    base = datetime.datetime(2026, 4, 17, 12, 0, 0, tzinfo=datetime.UTC)
    dt = base + datetime.timedelta(minutes=minutes_offset)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class TestFindTemporalNeighbors:
    def test_no_notes_returns_empty(self, db):
        from engine.intelligence import find_temporal_neighbors

        result = find_temporal_neighbors(db, _ts(0))
        assert result == []

    def test_notes_within_window(self, db):
        from engine.intelligence import find_temporal_neighbors

        _insert_note(db, "a.md", "Note A", created_at=_ts(0))
        _insert_note(db, "b.md", "Note B", created_at=_ts(3))
        _insert_note(db, "c.md", "Note C", created_at=_ts(7))

        result = find_temporal_neighbors(db, _ts(5), window_minutes=15)
        paths = [r["path"] for r in result]
        assert "a.md" in paths
        assert "b.md" in paths
        assert "c.md" in paths

    def test_notes_outside_window_excluded(self, db):
        from engine.intelligence import find_temporal_neighbors

        _insert_note(db, "close.md", "Close", created_at=_ts(2))
        _insert_note(db, "far.md", "Far Away", created_at=_ts(30))

        result = find_temporal_neighbors(db, _ts(0), window_minutes=15)
        paths = [r["path"] for r in result]
        assert "close.md" in paths
        assert "far.md" not in paths

    def test_exclude_path(self, db):
        from engine.intelligence import find_temporal_neighbors

        _insert_note(db, "self.md", "Self", created_at=_ts(0))
        _insert_note(db, "other.md", "Other", created_at=_ts(1))

        result = find_temporal_neighbors(db, _ts(0), exclude_path="self.md")
        paths = [r["path"] for r in result]
        assert "self.md" not in paths
        assert "other.md" in paths

    def test_sorted_by_proximity(self, db):
        from engine.intelligence import find_temporal_neighbors

        _insert_note(db, "far.md", "Far", created_at=_ts(10))
        _insert_note(db, "close.md", "Close", created_at=_ts(1))
        _insert_note(db, "mid.md", "Mid", created_at=_ts(5))

        result = find_temporal_neighbors(db, _ts(0), window_minutes=15)
        paths = [r["path"] for r in result]
        assert paths == ["close.md", "mid.md", "far.md"]

    def test_boundary_at_window_edge(self, db):
        from engine.intelligence import find_temporal_neighbors

        # Exactly at 15 minutes (900 seconds) — should be included
        _insert_note(db, "edge.md", "Edge", created_at=_ts(15))

        result = find_temporal_neighbors(db, _ts(0), window_minutes=15)
        paths = [r["path"] for r in result]
        assert "edge.md" in paths

    def test_window_zero_only_exact(self, db):
        from engine.intelligence import find_temporal_neighbors

        _insert_note(db, "exact.md", "Exact", created_at=_ts(0))
        _insert_note(db, "near.md", "Near", created_at=_ts(1))

        result = find_temporal_neighbors(db, _ts(0), window_minutes=0)
        paths = [r["path"] for r in result]
        assert "exact.md" in paths
        assert "near.md" not in paths

    def test_excludes_synthesis_notes(self, db):
        from engine.intelligence import find_temporal_neighbors

        _insert_note(db, "real.md", "Real Note", created_at=_ts(1))
        _insert_note(db, "synth.md", "Synthesis", note_type="synthesis", created_at=_ts(2))

        result = find_temporal_neighbors(db, _ts(0), window_minutes=15)
        paths = [r["path"] for r in result]
        assert "real.md" in paths
        assert "synth.md" not in paths

    def test_limit_caps_results(self, db):
        from engine.intelligence import find_temporal_neighbors

        for i in range(20):
            _insert_note(db, f"n{i}.md", f"Note {i}", created_at=_ts(i))

        result = find_temporal_neighbors(db, _ts(10), window_minutes=15, limit=5)
        assert len(result) == 5

    def test_returns_correct_fields(self, db):
        from engine.intelligence import find_temporal_neighbors

        _insert_note(db, "meetings/standup.md", "Daily Standup", note_type="meeting", created_at=_ts(2))

        result = find_temporal_neighbors(db, _ts(0), window_minutes=15)
        assert len(result) == 1
        note = result[0]
        assert note["path"] == "meetings/standup.md"
        assert note["title"] == "Daily Standup"
        assert note["type"] == "meeting"
        assert "created_at" in note
        assert "delta_seconds" in note
        assert isinstance(note["delta_seconds"], int)

    def test_bidirectional_window(self, db):
        """Notes captured BEFORE the reference time are also found."""
        from engine.intelligence import find_temporal_neighbors

        _insert_note(db, "before.md", "Before", created_at=_ts(-5))
        _insert_note(db, "after.md", "After", created_at=_ts(5))

        result = find_temporal_neighbors(db, _ts(0), window_minutes=15)
        paths = [r["path"] for r in result]
        assert "before.md" in paths
        assert "after.md" in paths
