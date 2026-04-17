"""Tests for consolidation_queue table + enrich_note() function (Phase 57, Plan 01)."""
import datetime
import sqlite3
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

import frontmatter

from engine.db import init_schema


@pytest.fixture
def enrich_conn(tmp_path, monkeypatch):
    """Isolated DB + brain root for enrichment tests."""
    import engine.db as _db
    import engine.paths as _paths

    db_path = tmp_path / "enrich_test.db"
    monkeypatch.setattr(_db, "DB_PATH", db_path)
    monkeypatch.setattr(_paths, "DB_PATH", db_path)
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)
    conn = sqlite3.connect(str(db_path))
    init_schema(conn)
    yield conn
    conn.close()


def _create_note(tmp_path, rel_path, title, body, **fm_fields):
    """Helper: create a note on disk + insert into DB."""
    note_file = tmp_path / rel_path
    note_file.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(body)
    post["title"] = title
    for k, v in fm_fields.items():
        post[k] = v
    with open(note_file, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))
    return rel_path


def _insert_note_db(conn, rel_path, title, body):
    """Helper: insert note row into DB."""
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, body, type, created_at, updated_at) "
        "VALUES (?, ?, ?, 'note', datetime('now'), datetime('now'))",
        (rel_path, title, body),
    )
    conn.commit()


# --- consolidation_queue table tests ---

def test_consolidation_queue_created(enrich_conn):
    """init_schema creates consolidation_queue table."""
    row = enrich_conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='consolidation_queue'"
    ).fetchone()
    assert row is not None
    assert "consolidation_queue" in row[0]


def test_consolidation_queue_index(enrich_conn):
    """idx_cq_status index exists on consolidation_queue."""
    row = enrich_conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_cq_status'"
    ).fetchone()
    assert row is not None
    assert "status" in row[0]
    assert "action" in row[0]


# --- enrich_note() tests ---

def test_enrich_ai_path(enrich_conn, tmp_path, monkeypatch):
    """enrich_note with mock adapter updates note body via AI."""
    import engine.paths as _paths
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)

    rel = _create_note(tmp_path, "coding/test.md", "Test Note", "Original content")
    _insert_note_db(enrich_conn, rel, "Test Note", "Original content")

    mock_adapter = MagicMock()
    mock_adapter.generate.return_value = "Original content with new info integrated."

    with patch("engine.embeddings.embed_texts", return_value=[b"\x00" * 16]):
        from engine.intelligence import enrich_note
        result = enrich_note(rel, "new info here", enrich_conn, adapter=mock_adapter)

    assert result["enriched"] is True
    assert result["before_length"] == len("Original content")
    assert result["after_length"] == len("Original content with new info integrated.")

    # Verify disk
    post = frontmatter.load(str(tmp_path / rel))
    assert "new info integrated" in post.content

    # Verify DB
    row = enrich_conn.execute("SELECT body FROM notes WHERE path=?", (rel,)).fetchone()
    assert "new info integrated" in row[0]


def test_enrich_fallback(enrich_conn, tmp_path, monkeypatch):
    """enrich_note without adapter uses structured fallback."""
    import engine.paths as _paths
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)

    rel = _create_note(tmp_path, "coding/fallback.md", "Fallback", "Existing body")
    _insert_note_db(enrich_conn, rel, "Fallback", "Existing body")

    with patch("engine.embeddings.embed_texts", return_value=[b"\x00" * 16]), \
         patch("engine.intelligence._router") as mock_router:
        mock_router.get_adapter.side_effect = Exception("no adapter")
        from engine.intelligence import enrich_note
        result = enrich_note(rel, "appended info", enrich_conn, adapter=None)

    assert result["enriched"] is False
    today = datetime.date.today().isoformat()
    post = frontmatter.load(str(tmp_path / rel))
    assert f"## Update {today}" in post.content
    assert "appended info" in post.content


def test_enrich_reembed(enrich_conn, tmp_path, monkeypatch):
    """enrich_note re-embeds after update."""
    import engine.paths as _paths
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)

    rel = _create_note(tmp_path, "coding/embed.md", "Embed", "Body here")
    _insert_note_db(enrich_conn, rel, "Embed", "Body here")

    mock_embed = MagicMock(return_value=[b"\x00" * 16])
    with patch("engine.embeddings.embed_texts", mock_embed):
        from engine.intelligence import enrich_note
        enrich_note(rel, "new stuff", enrich_conn, adapter=None)

    mock_embed.assert_called_once()
    assert "new stuff" in mock_embed.call_args[0][0][0] or "Body here" in mock_embed.call_args[0][0][0]


def test_enrich_fts5_rebuild(enrich_conn, tmp_path, monkeypatch):
    """After enrich, FTS5 search finds the new content."""
    import engine.paths as _paths
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)

    rel = _create_note(tmp_path, "coding/fts.md", "FTS Test", "Old body")
    _insert_note_db(enrich_conn, rel, "FTS Test", "Old body")

    with patch("engine.embeddings.embed_texts", return_value=[b"\x00" * 16]):
        from engine.intelligence import enrich_note
        enrich_note(rel, "xylophone unique word", enrich_conn, adapter=None)

    row = enrich_conn.execute(
        "SELECT n.path FROM notes n JOIN notes_fts f ON n.id = f.rowid "
        "WHERE notes_fts MATCH 'xylophone'"
    ).fetchone()
    assert row is not None


def test_enrich_audit_log(enrich_conn, tmp_path, monkeypatch):
    """enrich_note writes audit_log with event_type='enriched'."""
    import engine.paths as _paths
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)

    rel = _create_note(tmp_path, "coding/audit.md", "Audit", "Content")
    _insert_note_db(enrich_conn, rel, "Audit", "Content")

    with patch("engine.embeddings.embed_texts", return_value=[b"\x00" * 16]):
        from engine.intelligence import enrich_note
        enrich_note(rel, "more content", enrich_conn, adapter=None)

    row = enrich_conn.execute(
        "SELECT detail FROM audit_log WHERE event_type='enriched' AND note_path=?", (rel,)
    ).fetchone()
    assert row is not None
    assert "before:" in row[0]
    assert "after:" in row[0]


def test_enrich_not_found(enrich_conn, tmp_path, monkeypatch):
    """enrich_note with nonexistent path raises ValueError."""
    import engine.paths as _paths
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)

    from engine.intelligence import enrich_note
    with pytest.raises(ValueError, match="not found"):
        enrich_note("nonexistent/path.md", "content", enrich_conn)


def test_enrich_preserves_frontmatter(enrich_conn, tmp_path, monkeypatch):
    """enrich_note preserves existing frontmatter fields."""
    import engine.paths as _paths
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)

    rel = _create_note(
        tmp_path, "coding/fm.md", "FM Test", "Body",
        people=["Alice"], tags=["project"], sensitivity="internal",
    )
    _insert_note_db(enrich_conn, rel, "FM Test", "Body")

    with patch("engine.embeddings.embed_texts", return_value=[b"\x00" * 16]):
        from engine.intelligence import enrich_note
        enrich_note(rel, "extra info", enrich_conn, adapter=None)

    post = frontmatter.load(str(tmp_path / rel))
    assert post.get("people") == ["Alice"]
    assert post.get("tags") == ["project"]
    assert post.get("sensitivity") == "internal"


def test_enrich_updates_timestamp(enrich_conn, tmp_path, monkeypatch):
    """enrich_note sets updated_at in frontmatter and DB."""
    import engine.paths as _paths
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)

    rel = _create_note(tmp_path, "coding/ts.md", "TS", "Body")
    _insert_note_db(enrich_conn, rel, "TS", "Body")

    with patch("engine.embeddings.embed_texts", return_value=[b"\x00" * 16]):
        from engine.intelligence import enrich_note
        enrich_note(rel, "new", enrich_conn, adapter=None)

    post = frontmatter.load(str(tmp_path / rel))
    assert "updated_at" in post.metadata

    row = enrich_conn.execute("SELECT updated_at FROM notes WHERE path=?", (rel,)).fetchone()
    assert row[0] is not None
    # Should be recent (within last minute)
    assert "T" in row[0]
