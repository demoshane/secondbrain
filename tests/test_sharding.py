"""Tests for engine/sharding.py — filesystem sharding helpers.

Phase 38-02: Validates that notes can be moved into type-based subdirectories
with full atomic DB path cascade.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from engine.db import init_schema


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def shard_conn(tmp_path):
    """Isolated SQLite DB + brain root directory for sharding tests."""
    import engine.db as _db
    import engine.paths as _paths

    db_path = tmp_path / "shard_test.db"
    _db.DB_PATH = db_path
    _paths.DB_PATH = db_path
    _paths.BRAIN_ROOT = tmp_path / "brain"

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    yield conn, tmp_path / "brain"
    conn.close()


def _make_note_file(brain_root: Path, rel_path: str, content: str = "# Test Note\n\nBody.") -> Path:
    """Create a .md file at brain_root/rel_path with given content."""
    full = brain_root / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return full


def _insert_note(conn: sqlite3.Connection, path: str, note_type: str = "note") -> None:
    """Insert a minimal note row into notes table."""
    conn.execute(
        "INSERT INTO notes (path, title, type, body, sensitivity) VALUES (?,?,?,?,?)",
        (path, "Test Note", note_type, "body", "public"),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# get_shard_path tests
# ---------------------------------------------------------------------------


def test_get_shard_path_meeting_type(tmp_path):
    """get_shard_path for type='meeting' returns meetings/ subdirectory."""
    from engine.sharding import get_shard_path

    brain_root = tmp_path / "brain"
    result = get_shard_path(brain_root, "meeting", "my-note.md")
    assert result == brain_root / "meetings" / "my-note.md"


def test_get_shard_path_person_type(tmp_path):
    """get_shard_path for type='person' returns people/ subdirectory."""
    from engine.sharding import get_shard_path

    brain_root = tmp_path / "brain"
    result = get_shard_path(brain_root, "person", "alice.md")
    assert result == brain_root / "people" / "alice.md"


def test_get_shard_path_unknown_type_uses_default(tmp_path):
    """get_shard_path for unknown type returns DEFAULT_SHARD subdirectory."""
    from engine.sharding import get_shard_path, DEFAULT_SHARD

    brain_root = tmp_path / "brain"
    result = get_shard_path(brain_root, "unknown_type", "note.md")
    assert result == brain_root / DEFAULT_SHARD / "note.md"


def test_get_shard_path_creates_subdirectory(tmp_path):
    """get_shard_path creates the target subdirectory if it does not exist."""
    from engine.sharding import get_shard_path

    brain_root = tmp_path / "brain"
    result = get_shard_path(brain_root, "meeting", "test.md")
    assert result.parent.exists(), "get_shard_path must create the subdirectory"


# ---------------------------------------------------------------------------
# shard_note tests
# ---------------------------------------------------------------------------


def test_shard_note_moves_file_and_updates_notes_path(shard_conn):
    """shard_note moves file on disk and updates notes.path in DB."""
    from engine.sharding import shard_note

    conn, brain_root = shard_conn
    old_abs = str(brain_root / "note-to-shard.md")
    new_abs = str(brain_root / "meetings" / "note-to-shard.md")

    old_file = _make_note_file(brain_root, "note-to-shard.md")
    _insert_note(conn, old_abs, "meeting")

    shard_note(conn, old_abs, new_abs)

    # File moved
    assert not old_file.exists(), "Old file must not exist after shard"
    assert Path(new_abs).exists(), "New file must exist after shard"

    # DB updated
    row = conn.execute("SELECT path FROM notes WHERE path=?", (new_abs,)).fetchone()
    assert row is not None, "notes.path must be updated to new_abs"
    old_row = conn.execute("SELECT path FROM notes WHERE path=?", (old_abs,)).fetchone()
    assert old_row is None, "Old path must not remain in notes table"


def test_shard_note_updates_note_embeddings(shard_conn):
    """shard_note updates note_path in note_embeddings."""
    from engine.sharding import shard_note

    conn, brain_root = shard_conn
    old_abs = str(brain_root / "embed-note.md")
    new_abs = str(brain_root / "ideas" / "embed-note.md")

    _make_note_file(brain_root, "embed-note.md")
    _insert_note(conn, old_abs)
    conn.execute(
        "INSERT INTO note_embeddings (note_path, embedding, content_hash, stale) VALUES (?,?,?,?)",
        (old_abs, b"\x00" * 4, "hash1", 0),
    )
    conn.commit()

    shard_note(conn, old_abs, new_abs)

    row = conn.execute("SELECT note_path FROM note_embeddings WHERE note_path=?", (new_abs,)).fetchone()
    assert row is not None, "note_embeddings.note_path must be updated"
    assert conn.execute("SELECT 1 FROM note_embeddings WHERE note_path=?", (old_abs,)).fetchone() is None


def test_shard_note_updates_note_tags(shard_conn):
    """shard_note updates note_path in note_tags."""
    from engine.sharding import shard_note

    conn, brain_root = shard_conn
    old_abs = str(brain_root / "tag-note.md")
    new_abs = str(brain_root / "projects" / "tag-note.md")

    _make_note_file(brain_root, "tag-note.md")
    _insert_note(conn, old_abs)
    conn.execute("INSERT INTO note_tags (note_path, tag) VALUES (?,?)", (old_abs, "work"))
    conn.commit()

    shard_note(conn, old_abs, new_abs)

    row = conn.execute("SELECT note_path FROM note_tags WHERE note_path=?", (new_abs,)).fetchone()
    assert row is not None, "note_tags.note_path must be updated"


def test_shard_note_updates_note_people(shard_conn):
    """shard_note updates note_path in note_people."""
    from engine.sharding import shard_note

    conn, brain_root = shard_conn
    old_abs = str(brain_root / "people-note.md")
    new_abs = str(brain_root / "meetings" / "people-note.md")

    _make_note_file(brain_root, "people-note.md")
    _insert_note(conn, old_abs)
    conn.execute("INSERT INTO note_people (note_path, person) VALUES (?,?)", (old_abs, "Alice"))
    conn.commit()

    shard_note(conn, old_abs, new_abs)

    row = conn.execute("SELECT note_path FROM note_people WHERE note_path=?", (new_abs,)).fetchone()
    assert row is not None, "note_people.note_path must be updated"


def test_shard_note_updates_action_items(shard_conn):
    """shard_note updates note_path in action_items."""
    from engine.sharding import shard_note

    conn, brain_root = shard_conn
    old_abs = str(brain_root / "action-note.md")
    new_abs = str(brain_root / "ideas" / "action-note.md")

    _make_note_file(brain_root, "action-note.md")
    _insert_note(conn, old_abs)
    conn.execute(
        "INSERT INTO action_items (note_path, text, done) VALUES (?,?,?)",
        (old_abs, "Do something", 0),
    )
    conn.commit()

    shard_note(conn, old_abs, new_abs)

    row = conn.execute("SELECT note_path FROM action_items WHERE note_path=?", (new_abs,)).fetchone()
    assert row is not None, "action_items.note_path must be updated"


def test_shard_note_updates_relationships(shard_conn):
    """shard_note updates source_path and target_path in relationships."""
    from engine.sharding import shard_note

    conn, brain_root = shard_conn
    old_abs = str(brain_root / "rel-source.md")
    new_abs = str(brain_root / "coding" / "rel-source.md")
    other_abs = str(brain_root / "target.md")

    _make_note_file(brain_root, "rel-source.md")
    _make_note_file(brain_root, "target.md")
    _insert_note(conn, old_abs)
    _insert_note(conn, other_abs)
    # old_abs is source
    conn.execute(
        "INSERT INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
        (old_abs, other_abs, "reference"),
    )
    # old_abs is target
    conn.execute(
        "INSERT INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
        (other_abs, old_abs, "reference"),
    )
    conn.commit()

    shard_note(conn, old_abs, new_abs)

    src_row = conn.execute(
        "SELECT source_path FROM relationships WHERE source_path=?", (new_abs,)
    ).fetchone()
    assert src_row is not None, "relationships.source_path must be updated"

    tgt_row = conn.execute(
        "SELECT target_path FROM relationships WHERE target_path=?", (new_abs,)
    ).fetchone()
    assert tgt_row is not None, "relationships.target_path must be updated"


def test_shard_note_after_move_no_missing_files(shard_conn):
    """After shard_note, get_missing_file_notes returns empty list for moved note."""
    from engine.sharding import shard_note
    from engine.brain_health import get_missing_file_notes

    conn, brain_root = shard_conn
    old_abs = str(brain_root / "orphan-check.md")
    new_abs = str(brain_root / "strategy" / "orphan-check.md")

    _make_note_file(brain_root, "orphan-check.md")
    _insert_note(conn, old_abs)

    shard_note(conn, old_abs, new_abs)

    missing = get_missing_file_notes(conn)
    missing_paths = [m["path"] for m in missing]
    assert new_abs not in missing_paths, "Moved note must not appear in missing files list"
    assert old_abs not in missing_paths, "Old path must not appear in missing files list either"


def test_shard_note_nonexistent_file_raises(shard_conn):
    """shard_note raises FileNotFoundError when the source file does not exist."""
    from engine.sharding import shard_note

    conn, brain_root = shard_conn
    old_abs = str(brain_root / "nonexistent.md")
    new_abs = str(brain_root / "ideas" / "nonexistent.md")

    _insert_note(conn, old_abs)
    # Do NOT create the file on disk

    with pytest.raises(FileNotFoundError):
        shard_note(conn, old_abs, new_abs)


# ---------------------------------------------------------------------------
# shard_all_notes tests
# ---------------------------------------------------------------------------


def test_shard_all_notes_dry_run_no_moves(shard_conn):
    """shard_all_notes(dry_run=True) returns moves list without moving any files."""
    from engine.sharding import shard_all_notes

    conn, brain_root = shard_conn
    note_file = _make_note_file(brain_root, "note-in-root.md")
    note_abs = str(note_file)
    _insert_note(conn, note_abs, "meeting")

    moves = shard_all_notes(conn, brain_root, dry_run=True)
    # Should detect a move is needed (note is not in meetings/)
    assert isinstance(moves, list)
    assert any(m["old_path"] == note_abs for m in moves), \
        "Dry run should detect note is not in correct shard"
    # The file should still be in original location (dry run = no actual moves)
    assert note_file.exists(), "Dry run must not move files"
    assert not any(m.get("moved") for m in moves), "No moves should be executed in dry run"


def test_shard_all_notes_execute_moves(shard_conn):
    """shard_all_notes(dry_run=False) actually moves files."""
    from engine.sharding import shard_all_notes

    conn, brain_root = shard_conn
    # Create a note that is already in the correct shard (meetings/)
    note_file = _make_note_file(brain_root, "meetings/already-sharded.md")
    note_abs = str(note_file)
    _insert_note(conn, note_abs, "meeting")

    moves = shard_all_notes(conn, brain_root, dry_run=False)
    # No moves needed — note is already in correct shard (meetings/ matches SHARD_MAP["meeting"])
    assert isinstance(moves, list)
    assert not any(m["old_path"] == note_abs for m in moves), \
        "Note already in correct shard should not appear in moves"
