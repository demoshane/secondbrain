"""Tests for _json_list, _now_utc, and touch_note_access helpers in engine/db.py."""
import re
import sqlite3

from engine.db import _json_list, _now_utc, touch_note_access, get_connection, init_schema


class TestJsonList:
    def test_none_returns_empty(self):
        assert _json_list(None) == []

    def test_empty_string_returns_empty(self):
        assert _json_list("") == []

    def test_empty_json_array_returns_empty(self):
        assert _json_list("[]") == []

    def test_json_string_parses(self):
        assert _json_list('["a", "b"]') == ["a", "b"]

    def test_already_list_returned_as_is(self):
        lst = ["x", "y"]
        assert _json_list(lst) is lst

    def test_nested_values(self):
        assert _json_list('[1, 2, 3]') == [1, 2, 3]


class TestNowUtc:
    def test_returns_string(self):
        assert isinstance(_now_utc(), str)

    def test_matches_expected_format(self):
        result = _now_utc()
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", result), (
            f"Unexpected format: {result!r}"
        )

    def test_two_calls_are_close(self):
        t1 = _now_utc()
        t2 = _now_utc()
        # Both should share the same date prefix (won't cross midnight in a test run)
        assert t1[:10] == t2[:10]


class TestTouchNoteAccess:
    def _make_db(self, tmp_path, monkeypatch):
        import engine.db as _db
        import engine.paths as _paths
        db_file = tmp_path / "test.db"
        monkeypatch.setattr(_db, "DB_PATH", db_file)
        monkeypatch.setattr(_paths, "DB_PATH", db_file)
        conn = get_connection(str(db_file))
        init_schema(conn)
        return conn

    def test_access_increments_count(self, tmp_path, monkeypatch):
        conn = self._make_db(tmp_path, monkeypatch)
        conn.execute(
            "INSERT INTO notes (path, title, type, body) VALUES (?,?,?,?)",
            ("test/note.md", "Test", "note", "body"),
        )
        conn.commit()
        assert touch_note_access(conn, "test/note.md") is True
        row = conn.execute("SELECT access_count, last_accessed_at FROM notes WHERE path=?", ("test/note.md",)).fetchone()
        assert row[0] == 1
        assert row[1] is not None
        # Second access
        assert touch_note_access(conn, "test/note.md") is True
        row = conn.execute("SELECT access_count FROM notes WHERE path=?", ("test/note.md",)).fetchone()
        assert row[0] == 2
        conn.close()

    def test_access_missing_path_returns_false(self, tmp_path, monkeypatch):
        conn = self._make_db(tmp_path, monkeypatch)
        assert touch_note_access(conn, "nonexistent/note.md") is False
        conn.close()

    def test_migration_idempotent(self, tmp_path, monkeypatch):
        """Running init_schema twice doesn't error (columns already exist)."""
        conn = self._make_db(tmp_path, monkeypatch)
        init_schema(conn)  # second call
        row = conn.execute("SELECT access_count FROM notes LIMIT 0").description
        assert any(col[0] == "access_count" for col in row)
        conn.close()

    def test_fresh_note_has_defaults(self, tmp_path, monkeypatch):
        conn = self._make_db(tmp_path, monkeypatch)
        conn.execute(
            "INSERT INTO notes (path, title, type, body) VALUES (?,?,?,?)",
            ("fresh/note.md", "Fresh", "note", "body"),
        )
        conn.commit()
        row = conn.execute("SELECT access_count, last_accessed_at FROM notes WHERE path=?", ("fresh/note.md",)).fetchone()
        assert row[0] == 0
        assert row[1] is None
        conn.close()
