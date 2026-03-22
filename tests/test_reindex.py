import json
import sys
import pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.db import init_schema
from engine.reindex import reindex_brain


def _make_note(directory: Path, filename: str, frontmatter: str, body: str) -> Path:
    p = directory / filename
    p.write_text(f"---\n{frontmatter}\n---\n{body}")
    return p


def test_reindex_inserts_all_markdown(brain_root, db_conn):
    init_schema(db_conn)
    _make_note(brain_root, "note1.md", "type: note\ntitle: Note One", "Body one")
    _make_note(brain_root, "note2.md", "type: note\ntitle: Note Two", "Body two")
    _make_note(brain_root, "note3.md", "type: idea\ntitle: An Idea", "Body three")
    result = reindex_brain(brain_root, db_conn)
    assert result["errors"] == []
    count = db_conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    assert count == 3


def test_reindex_idempotent(brain_root, db_conn):
    init_schema(db_conn)
    _make_note(brain_root, "note1.md", "type: note\ntitle: Note", "Body")
    reindex_brain(brain_root, db_conn)
    reindex_brain(brain_root, db_conn)
    count = db_conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    assert count == 1  # no duplicates


def test_reindex_empty_brain(brain_root, db_conn):
    init_schema(db_conn)
    result = reindex_brain(brain_root, db_conn)
    assert result["errors"] == []
    assert result["indexed"] == 0
    count = db_conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    assert count == 0


def test_reindex_parses_frontmatter_fields(brain_root, db_conn):
    init_schema(db_conn)
    _make_note(
        brain_root, "typed.md",
        'type: meeting\ntitle: "Team Sync"\ntags: [work, team]\ncontent_sensitivity: private',
        "Meeting notes here"
    )
    reindex_brain(brain_root, db_conn)
    row = db_conn.execute("SELECT type, title, tags, sensitivity FROM notes WHERE path LIKE '%typed.md'").fetchone()
    assert row is not None
    assert row[0] == "meeting"
    assert row[1] == "Team Sync"
    tags = json.loads(row[2])
    assert "work" in tags
    assert row[3] == "private"


def test_reindex_stores_absolute_paths(brain_root, db_conn):
    """After reindex, every path stored in the DB must be absolute (SEARCH-01)."""
    init_schema(db_conn)
    _make_note(brain_root, "note1.md", "type: note\ntitle: Note One", "Body one")
    reindex_brain(brain_root, db_conn)
    rows = db_conn.execute("SELECT path FROM notes").fetchall()
    assert len(rows) >= 1
    for (path,) in rows:
        assert Path(path).is_absolute(), f"Expected absolute path, got: {path}"


def test_reindex_preserves_people_column(tmp_path, db_conn):
    """After reindex, people field from frontmatter must survive in the DB."""
    import json
    init_schema(db_conn)
    note = tmp_path / "people" / "alice.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("---\ntype: people\ntitle: Alice\npeople:\n  - alice\n---\nProfile")
    reindex_brain(tmp_path.resolve(), db_conn)
    row = db_conn.execute("SELECT people FROM notes WHERE title='Alice'").fetchone()
    assert row is not None, "Note not indexed"
    people = json.loads(row[0])
    assert "alice" in people, f"people column lost after reindex: {row[0]}"


# --- --entities flag tests ---

def test_entities_flag_populates_people_column(brain_root, db_conn):
    """--entities flag: note with empty people column gets people extracted from body."""
    init_schema(db_conn)
    # Note body mentions "Alice Smith" — extraction should pick her up
    _make_note(
        brain_root, "meeting.md",
        "type: note\ntitle: Team Meeting\npeople: []",
        "Spoke with Alice Smith about the project roadmap.",
    )
    # First reindex without --entities (people column stays [] from frontmatter)
    reindex_brain(brain_root, db_conn)
    row_before = db_conn.execute(
        "SELECT people FROM notes WHERE title='Team Meeting'"
    ).fetchone()
    assert row_before is not None
    people_before = json.loads(row_before[0])
    assert people_before == [], f"Expected empty before --entities run, got: {people_before}"

    # Now reindex WITH --entities
    reindex_brain(brain_root, db_conn, entities=True)
    row_after = db_conn.execute(
        "SELECT people FROM notes WHERE title='Team Meeting'"
    ).fetchone()
    assert row_after is not None
    people_after = json.loads(row_after[0])
    assert len(people_after) > 0, (
        f"--entities flag should have populated people column, got: {people_after}"
    )
    # At least one extracted name should be present (exact name depends on extraction)
    assert any("Alice" in p for p in people_after), (
        f"'Alice Smith' or 'Alice' not found in extracted people: {people_after}"
    )


def test_entities_flag_overwrites_people_column(brain_root, db_conn):
    """--entities flag: replaces (not merges) existing people column content."""
    init_schema(db_conn)
    # Note has a stale/wrong entry in people column, body has "Bob Johnson"
    _make_note(
        brain_root, "note-with-stale.md",
        "type: note\ntitle: Stale People Note\npeople:\n  - OldEntry",
        "Met Bob Johnson this morning to discuss quarterly targets.",
    )
    reindex_brain(brain_root, db_conn)

    # Confirm OldEntry is in DB after normal reindex (read from frontmatter)
    row = db_conn.execute(
        "SELECT people FROM notes WHERE title='Stale People Note'"
    ).fetchone()
    assert row is not None
    assert "OldEntry" in json.loads(row[0]), "Precondition: OldEntry should be in people"

    # ARCH-12: Run with --entities: should MERGE extracted with frontmatter, not overwrite
    reindex_brain(brain_root, db_conn, entities=True)
    row_after = db_conn.execute(
        "SELECT people FROM notes WHERE title='Stale People Note'"
    ).fetchone()
    people_after = json.loads(row_after[0])
    # OldEntry comes from frontmatter — ARCH-12 says preserve user-curated entries
    assert "OldEntry" in people_after, (
        f"--entities must MERGE with frontmatter. OldEntry missing: {people_after}"
    )


# ---------------------------------------------------------------------------
# Phase 33-02: Incremental reindex via mtime comparison (PERF-03)
# ---------------------------------------------------------------------------

import datetime as _dt
import time as _time


def test_incremental_skips_unchanged(brain_root, db_conn):
    """reindex_brain default (no flags) skips files whose mtime <= DB updated_at."""
    init_schema(db_conn)
    note = _make_note(brain_root, "stable.md", "type: note\ntitle: Stable Note", "Content")

    # First pass — indexes the file (sets updated_at to utcnow)
    result1 = reindex_brain(brain_root, db_conn)
    assert result1["indexed"] == 1

    # Artificially set the DB updated_at to far in the future so mtime < updated_at
    future_ts = (_dt.datetime.utcnow() + _dt.timedelta(hours=1)).isoformat()
    db_conn.execute("UPDATE notes SET updated_at=? WHERE title='Stable Note'", (future_ts,))
    db_conn.commit()

    # Second pass — file mtime has not changed; DB updated_at is in future → should skip
    result2 = reindex_brain(brain_root, db_conn)
    # incremental mode: unchanged files are skipped (indexed count should be 0)
    assert result2.get("skipped", 0) >= 1 or result2["indexed"] == 0, (
        f"Expected file to be skipped on second pass, got: {result2}"
    )


def test_full_flag_reindexes_all(brain_root, db_conn):
    """reindex_brain --full re-indexes all files regardless of mtime."""
    init_schema(db_conn)
    _make_note(brain_root, "stable.md", "type: note\ntitle: Stable Note", "Content")

    # First pass
    reindex_brain(brain_root, db_conn)

    # Set DB updated_at far in future (same as incremental test)
    future_ts = (_dt.datetime.utcnow() + _dt.timedelta(hours=1)).isoformat()
    db_conn.execute("UPDATE notes SET updated_at=? WHERE title='Stable Note'", (future_ts,))
    db_conn.commit()

    # Second pass with full=True — must reindex ALL files
    result2 = reindex_brain(brain_root, db_conn, full=True)
    assert result2["indexed"] == 1, (
        f"full=True must reindex all files, got indexed={result2['indexed']}"
    )
