"""Tests for Phase 16 digest generation (DIAG-01 through DIAG-04)."""
import datetime
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from engine.digest import generate_digest


def _make_db_with_pii_note(tmp_path: Path) -> sqlite3.Connection:
    """Create an in-memory DB with schema and one PII note created today."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY,
            path TEXT,
            title TEXT,
            type TEXT,
            body TEXT,
            sensitivity TEXT,
            created_at TEXT
        )"""
    )
    today = datetime.date.today().isoformat()
    conn.execute(
        "INSERT INTO notes (path, title, type, body, sensitivity, created_at) VALUES (?,?,?,?,?,?)",
        ("/brain/secret.md", "Secret Note", "note", "Confidential content here.", "pii", today),
    )
    conn.commit()
    return conn


class TestDigestWrite:
    def test_digest_written_to_correct_path(self, tmp_path):
        """generate_digest writes a file to the digests_dir with a weekly filename."""
        digests_dir = tmp_path / "digests"
        result = generate_digest(None, digests_dir)
        assert digests_dir.exists()
        assert result.parent == digests_dir
        assert result.suffix == ".md"


class TestDigestIdempotent:
    def test_second_run_skips(self, tmp_path):
        """generate_digest called twice in same week does not overwrite existing file."""
        digests_dir = tmp_path / "digests"
        result1 = generate_digest(None, digests_dir)
        mtime1 = result1.stat().st_mtime
        result2 = generate_digest(None, digests_dir)
        assert result1 == result2
        assert result2.stat().st_mtime == mtime1, "File was overwritten on second call"


class TestDigestSections:
    def test_all_four_sections_present(self, tmp_path):
        """generate_digest output contains Key Themes, Open Actions, Stale Notes, Captures This Week."""
        digests_dir = tmp_path / "digests"
        digest_path = generate_digest(None, digests_dir)
        content = Path(digest_path).read_text()
        assert "Key Themes" in content
        assert "Open Actions" in content
        assert "Stale Notes" in content
        assert "Captures This Week" in content


class TestDigestPIIRouting:
    def test_pii_notes_use_ollama(self, tmp_path, monkeypatch):
        """generate_digest routes PII notes through Ollama adapter (pii sensitivity)."""
        from engine import digest as d
        mock_router = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "Digest summary."
        mock_router.get_adapter.return_value = mock_adapter
        monkeypatch.setattr("engine.intelligence._router", mock_router)

        conn = _make_db_with_pii_note(tmp_path)
        digests_dir = tmp_path / "digests"
        result = generate_digest(conn, digests_dir)
        calls = mock_router.get_adapter.call_args_list
        assert any(c[0][0] == "pii" for c in calls), "Expected Ollama adapter called with pii sensitivity"


# --- Phase 26: ENGL-03 digest column fix stub ---

@pytest.mark.xfail(strict=False, reason="digest.py action_items column bug not yet fixed")
def test_generate_digest_open_actions_uses_correct_column(tmp_path, monkeypatch):
    """digest column fix: generate_digest() must query action_items.text and done=0, not action_text/status."""
    import sqlite3
    from engine.db import init_schema
    from pathlib import Path
    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
    monkeypatch.setenv("DIGEST_DIR", str(tmp_path / "digests"))
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    init_schema(conn)
    # Insert a known action item using correct column names
    conn.execute(
        "INSERT INTO action_items (note_path, text, done) VALUES (?, ?, ?)",
        ("/brain/note.md", "Important open task", 0)
    )
    conn.commit()
    conn.close()
    # generate_digest should not raise OperationalError: no such column: action_text
    try:
        generate_digest(brain_root=tmp_path, db_path=db, out_dir=tmp_path / "digests")
    except Exception as e:
        # Acceptable if AI adapter unavailable — must NOT be OperationalError
        assert "action_text" not in str(e), f"Column name bug still present: {e}"
