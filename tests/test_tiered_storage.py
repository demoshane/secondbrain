"""Tests for tiered storage: archived flag + search exclusion."""
import sqlite3
import pytest
from engine.db import init_schema, migrate_add_archived_column


@pytest.fixture
def conn():
    """In-memory SQLite connection with full schema."""
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    import engine.db as _db
    import engine.paths as _paths
    from pathlib import Path
    # Ensure migrations reference a tmp path so migrate_paths_to_relative is a no-op
    _db.DB_PATH = Path(":memory:")
    _paths.DB_PATH = Path(":memory:")
    init_schema(c)
    yield c
    c.close()


def _insert_note(conn, path, title, body="test body", archived=0):
    conn.execute(
        """INSERT INTO notes (path, type, title, body, archived)
           VALUES (?, 'note', ?, ?, ?)""",
        (path, title, body, archived),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Migration tests
# ---------------------------------------------------------------------------

class TestArchivedMigration:
    def test_migrate_adds_archived_column(self, tmp_path):
        """migrate_add_archived_column creates the column with default 0."""
        c = sqlite3.connect(str(tmp_path / "test.db"))
        # Create minimal notes table without archived column
        c.execute("""
            CREATE TABLE notes (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL DEFAULT 'note',
                title TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT ''
            )
        """)
        cols_before = {row[1] for row in c.execute("PRAGMA table_info(notes)").fetchall()}
        assert "archived" not in cols_before

        migrate_add_archived_column(c)

        cols_after = {row[1] for row in c.execute("PRAGMA table_info(notes)").fetchall()}
        assert "archived" in cols_after

    def test_migrate_archived_idempotent(self, conn):
        """migrate_add_archived_column is idempotent — no error on second run."""
        migrate_add_archived_column(conn)  # already called by init_schema
        migrate_add_archived_column(conn)  # second call should not raise

    def test_new_notes_default_archived_zero(self, conn):
        """Notes inserted without explicit archived value default to archived=0."""
        conn.execute(
            "INSERT INTO notes (path, title, body) VALUES (?, ?, ?)",
            ("test/note.md", "Test", "body"),
        )
        conn.commit()
        row = conn.execute("SELECT archived FROM notes WHERE path=?", ("test/note.md",)).fetchone()
        assert row[0] == 0


# ---------------------------------------------------------------------------
# Search exclusion tests
# ---------------------------------------------------------------------------

class TestArchivedSearchExclusion:
    def test_active_note_appears_in_search(self, conn):
        """Active note (archived=0) is included in search_notes results."""
        from engine.search import search_notes
        _insert_note(conn, "active/note.md", "unique query term alpha", archived=0)
        results = search_notes(conn, "unique query term alpha")
        paths = [r["path"] for r in results]
        assert "active/note.md" in paths

    def test_archived_note_excluded_from_search(self, conn):
        """Archived note (archived=1) is excluded from search_notes results."""
        from engine.search import search_notes
        _insert_note(conn, "archived/note.md", "unique query term beta", archived=1)
        results = search_notes(conn, "unique query term beta")
        paths = [r["path"] for r in results]
        assert "archived/note.md" not in paths

    def test_mixed_notes_only_active_returned(self, conn):
        """With both active and archived notes, only active are returned."""
        from engine.search import search_notes
        _insert_note(conn, "active/gamma.md", "gamma gamma gamma", archived=0)
        _insert_note(conn, "archived/gamma.md", "gamma gamma gamma", archived=1)
        results = search_notes(conn, "gamma gamma gamma")
        paths = [r["path"] for r in results]
        assert "active/gamma.md" in paths
        assert "archived/gamma.md" not in paths


# ---------------------------------------------------------------------------
# Health check tests
# ---------------------------------------------------------------------------

class TestArchivedHealthCount:
    def test_get_archived_count_returns_zero_when_none(self, conn):
        """get_archived_count returns 0 when no archived notes exist."""
        from engine.brain_health import get_archived_count
        _insert_note(conn, "a/note.md", "active", archived=0)
        assert get_archived_count(conn) == 0

    def test_get_archived_count_returns_correct_count(self, conn):
        """get_archived_count returns exact count of archived notes."""
        from engine.brain_health import get_archived_count
        _insert_note(conn, "a/one.md", "one", archived=1)
        _insert_note(conn, "a/two.md", "two", archived=1)
        _insert_note(conn, "a/active.md", "active", archived=0)
        assert get_archived_count(conn) == 2


# ---------------------------------------------------------------------------
# API include_archived tests (mocked Flask context)
# ---------------------------------------------------------------------------

class TestListNotesIncludeArchived:
    def test_list_notes_excludes_archived_by_default(self, conn, monkeypatch):
        """GET /notes with default params excludes archived notes."""
        import engine.api as _api
        monkeypatch.setattr(_api, "get_connection", lambda: conn)
        _insert_note(conn, "a/active.md", "Active Note", archived=0)
        _insert_note(conn, "a/archived.md", "Archived Note", archived=1)

        with _api.app.test_client() as client:
            resp = client.get("/notes")
            assert resp.status_code == 200
            data = resp.get_json()
            paths = [n["path"] for n in data["notes"]]
            assert "a/active.md" in paths
            assert "a/archived.md" not in paths

    def test_list_notes_include_archived_true(self, conn, monkeypatch):
        """GET /notes?include_archived=true returns all notes."""
        import engine.api as _api
        monkeypatch.setattr(_api, "get_connection", lambda: conn)
        _insert_note(conn, "b/active.md", "Active", archived=0)
        _insert_note(conn, "b/archived.md", "Archived", archived=1)

        with _api.app.test_client() as client:
            resp = client.get("/notes?include_archived=true")
            assert resp.status_code == 200
            data = resp.get_json()
            paths = [n["path"] for n in data["notes"]]
            assert "b/active.md" in paths
            assert "b/archived.md" in paths
