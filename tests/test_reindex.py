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
