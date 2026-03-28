"""Tests for engine/merge_cli.py — COV-07."""
import pytest
import json
from pathlib import Path
import engine.db as _db
import engine.paths as _paths


@pytest.fixture
def merge_brain(tmp_path, monkeypatch):
    """Isolated DB with two duplicate note rows for merge tests."""
    from engine.db import init_schema, get_connection

    tmp_db = tmp_path / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)

    conn = get_connection()
    init_schema(conn)

    # Insert two test notes
    for path, title, body, tags in [
        ("notes/note-a.md", "Note A", "Body of A", '["tagA"]'),
        ("notes/note-b.md", "Note B", "Body of B", '["tagB"]'),
    ]:
        conn.execute(
            "INSERT INTO notes (path, title, body, tags) VALUES (?, ?, ?, ?)",
            (path, title, body, tags),
        )
    conn.commit()
    conn.close()
    return tmp_path


def test_merge_notes_keeps_target(merge_brain):
    """merge_notes merges bodies and returns keep/discarded paths."""
    from engine.db import get_connection
    from engine.brain_health import merge_notes

    conn = get_connection()
    result = merge_notes("notes/note-a.md", "notes/note-b.md", conn)
    conn.close()

    assert result["keep"] == "notes/note-a.md"
    assert result["discarded"] == "notes/note-b.md"


def test_merge_notes_merges_tags(merge_brain):
    """merge_notes produces a union of both notes' tags."""
    from engine.db import get_connection
    from engine.brain_health import merge_notes

    conn = get_connection()
    result = merge_notes("notes/note-a.md", "notes/note-b.md", conn)
    conn.close()

    assert "tagA" in result["merged_tags"]
    assert "tagB" in result["merged_tags"]


def test_merge_notes_raises_for_missing_keep(merge_brain):
    """merge_notes raises ValueError when keep_path is not in DB."""
    from engine.db import get_connection
    from engine.brain_health import merge_notes

    conn = get_connection()
    with pytest.raises(ValueError, match="keep_path not found"):
        merge_notes("notes/nonexistent.md", "notes/note-b.md", conn)
    conn.close()


def test_merge_notes_raises_for_missing_discard(merge_brain):
    """merge_notes raises ValueError when discard_path is not in DB."""
    from engine.db import get_connection
    from engine.brain_health import merge_notes

    conn = get_connection()
    with pytest.raises(ValueError, match="discard_path not found"):
        merge_notes("notes/note-a.md", "notes/nonexistent.md", conn)
    conn.close()


def test_merge_duplicates_main_no_candidates(merge_brain, monkeypatch, capsys):
    """merge_duplicates_main prints 'No duplicate candidates' when none found."""
    from engine.merge_cli import merge_duplicates_main
    from engine import brain_health

    monkeypatch.setattr(brain_health, "get_duplicate_candidates", lambda conn: [])

    merge_duplicates_main()

    captured = capsys.readouterr()
    assert "No duplicate candidates" in captured.out
