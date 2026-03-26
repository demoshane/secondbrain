"""Tests for the summarization layer (Plan 38-06, Task 2)."""
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from engine.db import init_schema, migrate_add_summary_column


@pytest.fixture
def conn(tmp_path, monkeypatch):
    """In-memory SQLite connection with full schema including summary column."""
    import engine.db as _db
    import engine.paths as _paths
    monkeypatch.setattr(_db, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(_paths, "DB_PATH", tmp_path / "test.db")
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    init_schema(c)
    yield c
    c.close()


def _insert_note(conn, path, body, summary=None):
    conn.execute(
        "INSERT INTO notes (path, type, title, body, summary) VALUES (?, 'note', ?, ?, ?)",
        (path, Path(path).stem, body, summary),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Migration tests
# ---------------------------------------------------------------------------

class TestSummaryMigration:
    def test_migrate_adds_summary_column(self, tmp_path):
        """migrate_add_summary_column creates the summary TEXT column."""
        c = sqlite3.connect(str(tmp_path / "test.db"))
        c.execute("""
            CREATE TABLE notes (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                body TEXT NOT NULL DEFAULT ''
            )
        """)
        cols_before = {row[1] for row in c.execute("PRAGMA table_info(notes)").fetchall()}
        assert "summary" not in cols_before

        migrate_add_summary_column(c)

        cols_after = {row[1] for row in c.execute("PRAGMA table_info(notes)").fetchall()}
        assert "summary" in cols_after

    def test_migrate_summary_idempotent(self, conn):
        """migrate_add_summary_column is idempotent — no error on second call."""
        migrate_add_summary_column(conn)  # already run by init_schema
        migrate_add_summary_column(conn)  # second call must not raise


# ---------------------------------------------------------------------------
# summarize_note() tests
# ---------------------------------------------------------------------------

class TestSummarizeNote:
    def test_short_note_returns_none(self, conn):
        """Notes below SUMMARY_THRESHOLD (2000 chars) return None without LLM call."""
        from engine.intelligence import summarize_note
        short_body = "Short note body."
        _insert_note(conn, "test/short.md", short_body)
        result = summarize_note(conn, "test/short.md")
        assert result is None

    def test_long_note_calls_llm_and_returns_summary(self, conn):
        """Notes above threshold call LLM and return a summary string."""
        from engine.intelligence import summarize_note, SUMMARY_THRESHOLD
        long_body = "x " * (SUMMARY_THRESHOLD + 10)  # above threshold by chars
        # Ensure it's definitely > SUMMARY_THRESHOLD characters
        assert len(long_body) > SUMMARY_THRESHOLD
        _insert_note(conn, "test/long.md", long_body)

        with patch("engine.adapters.claude_adapter.ClaudeAdapter.generate", return_value="Test summary text."):
            with patch("engine.intelligence.summarize_note.__wrapped__" if hasattr(summarize_note, "__wrapped__") else "engine.adapters.claude_adapter.ClaudeAdapter.generate", return_value="Test summary text.") as _mock:
                # Use router-level patch to intercept the adapter call
                mock_adapter = MagicMock()
                mock_adapter.generate.return_value = "Test summary text."
                with patch("engine.router.get_adapter", return_value=mock_adapter):
                    # summarize_note uses call_claude directly — patch at that level
                    pass

        # Direct patch on call_claude
        with patch("engine.adapters.claude_adapter.ClaudeAdapter.generate", return_value="Test summary text."):
            result = summarize_note(conn, "test/long.md")

        assert result == "Test summary text."

    def test_long_note_writes_summary_to_db(self, conn):
        """summarize_note writes summary to notes.summary column."""
        from engine.intelligence import summarize_note, SUMMARY_THRESHOLD
        long_body = "y " * (SUMMARY_THRESHOLD + 10)
        assert len(long_body) > SUMMARY_THRESHOLD
        _insert_note(conn, "test/writeback.md", long_body)

        with patch("engine.adapters.claude_adapter.ClaudeAdapter.generate", return_value="Stored summary."):
            result = summarize_note(conn, "test/writeback.md")

        stored = conn.execute("SELECT summary FROM notes WHERE path=?", ("test/writeback.md",)).fetchone()[0]
        assert stored == "Stored summary."

    def test_existing_summary_skips_llm(self, conn):
        """Notes with existing summary skip LLM call unless force=True."""
        from engine.intelligence import summarize_note, SUMMARY_THRESHOLD
        long_body = "z " * (SUMMARY_THRESHOLD + 10)
        _insert_note(conn, "test/cached.md", long_body, summary="Existing summary.")

        with patch("engine.adapters.claude_adapter.ClaudeAdapter.generate") as mock_gen:
            result = summarize_note(conn, "test/cached.md")
            mock_gen.assert_not_called()

        assert result == "Existing summary."

    def test_existing_summary_force_calls_llm(self, conn):
        """force=True bypasses existing summary and calls LLM again."""
        from engine.intelligence import summarize_note, SUMMARY_THRESHOLD
        long_body = "w " * (SUMMARY_THRESHOLD + 10)
        _insert_note(conn, "test/force.md", long_body, summary="Old summary.")

        with patch("engine.adapters.claude_adapter.ClaudeAdapter.generate", return_value="New summary."):
            result = summarize_note(conn, "test/force.md", force=True)

        assert result == "New summary."

    def test_missing_note_returns_none(self, conn):
        """summarize_note returns None if note_path not in DB."""
        from engine.intelligence import summarize_note
        result = summarize_note(conn, "nonexistent/note.md")
        assert result is None


# ---------------------------------------------------------------------------
# summarize_unsummarized() tests
# ---------------------------------------------------------------------------

class TestSummarizeUnsummarized:
    def test_batch_summarize_returns_count(self, conn):
        """summarize_unsummarized returns count of notes it successfully summarized."""
        from engine.intelligence import summarize_unsummarized, SUMMARY_THRESHOLD
        long_body = "q " * (SUMMARY_THRESHOLD + 10)
        _insert_note(conn, "batch/one.md", long_body)
        _insert_note(conn, "batch/two.md", long_body)
        _insert_note(conn, "batch/short.md", "short body")

        with patch("engine.adapters.claude_adapter.ClaudeAdapter.generate", return_value="Batch summary."):
            count = summarize_unsummarized(conn, limit=10)

        assert count == 2

    def test_already_summarized_not_reprocessed(self, conn):
        """summarize_unsummarized skips notes that already have a summary."""
        from engine.intelligence import summarize_unsummarized, SUMMARY_THRESHOLD
        long_body = "p " * (SUMMARY_THRESHOLD + 10)
        _insert_note(conn, "skip/one.md", long_body, summary="Already done.")

        with patch("engine.adapters.claude_adapter.ClaudeAdapter.generate") as mock_gen:
            count = summarize_unsummarized(conn, limit=10)
            mock_gen.assert_not_called()

        assert count == 0
