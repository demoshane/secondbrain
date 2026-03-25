"""Phase 26 Wave 0: xfail stubs for ENGL-04 and ENGL-05 (brain health checks)."""
import pytest
import sqlite3
from pathlib import Path
from unittest.mock import patch

from engine.db import init_schema


@pytest.fixture
def conn(tmp_path):
    db = tmp_path / "test.db"
    c = sqlite3.connect(str(db))
    init_schema(c)
    yield c
    c.close()


@pytest.fixture
def client(tmp_path):
    """API test client with isolated SQLite DB."""
    import engine.db as _db
    import engine.paths as _paths
    tmp_db = tmp_path / "test.db"
    old_db_path = _db.DB_PATH
    old_paths_db = _paths.DB_PATH
    _db.DB_PATH = tmp_db
    _paths.DB_PATH = tmp_db
    # Init schema
    c = sqlite3.connect(str(tmp_db))
    init_schema(c)
    c.close()
    from engine.api import app
    app.config["TESTING"] = True
    with app.test_client() as tc:
        yield tc
    _db.DB_PATH = old_db_path
    _paths.DB_PATH = old_paths_db


@pytest.mark.xfail(strict=False, reason="engine/brain_health.py not yet implemented")
def test_get_orphan_notes_returns_notes_with_no_inbound_links(conn):
    # Insert a note with no relationships — should appear as orphan
    from engine.brain_health import get_orphan_notes
    conn.execute("INSERT INTO notes (path, title, type, body, sensitivity) VALUES (?, ?, ?, ?, ?)",
                 ("/brain/orphan.md", "Orphan Note", "note", "body", "public"))
    conn.commit()
    result = get_orphan_notes(conn)
    assert any(r["path"] == "/brain/orphan.md" for r in result)


@pytest.mark.xfail(strict=False, reason="engine/brain_health.py not yet implemented")
def test_get_orphan_notes_excludes_digest_and_memory_types(conn):
    from engine.brain_health import get_orphan_notes
    conn.execute("INSERT INTO notes (path, title, type, body, sensitivity) VALUES (?, ?, ?, ?, ?)",
                 ("/brain/digests/2026-W12.md", "Digest", "digest", "body", "public"))
    conn.commit()
    result = get_orphan_notes(conn)
    paths = [r["path"] for r in result]
    assert "/brain/digests/2026-W12.md" not in paths


@pytest.mark.xfail(strict=False, reason="engine/brain_health.py not yet implemented")
def test_get_duplicate_candidates_returns_pairs_above_threshold(conn):
    from engine.brain_health import get_duplicate_candidates
    # No embeddings in fixture — expect [] (no crash)
    result = get_duplicate_candidates(conn, threshold=0.92)
    assert isinstance(result, list)


@pytest.mark.xfail(strict=False, reason="engine/brain_health.py not yet implemented")
def test_compute_health_score_returns_100_for_clean_brain():
    from engine.brain_health import compute_health_score
    assert compute_health_score(total_notes=50, orphans=0, broken=0, duplicates=0) == 100


@pytest.mark.xfail(strict=False, reason="engine/brain_health.py not yet implemented")
def test_compute_health_score_reduces_for_orphans():
    from engine.brain_health import compute_health_score
    score_clean = compute_health_score(50, 0, 0, 0)
    score_orphans = compute_health_score(50, 25, 0, 0)  # 50% orphan ratio
    assert score_orphans < score_clean


@pytest.mark.xfail(strict=False, reason="engine/brain_health.py not yet implemented")
def test_compute_health_score_zero_notes_returns_100():
    from engine.brain_health import compute_health_score
    assert compute_health_score(total_notes=0, orphans=0, broken=0, duplicates=0) == 100


@pytest.mark.xfail(strict=False, reason="GET /brain-health not yet implemented")
def test_brain_health_api_returns_score_and_checks(client):
    # Uses local client fixture — isolated SQLite DB
    resp = client.get("/brain-health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "score" in data
    assert "orphans" in data
    assert "broken_links" in data
    assert "duplicate_candidates" in data
    assert isinstance(data["score"], int)
    assert 0 <= data["score"] <= 100


# ---------------------------------------------------------------------------
# Orphan detection correctness spec (Phase 27.7)
# ---------------------------------------------------------------------------

def test_orphan_is_note_with_no_relationships(tmp_path):
    """QA-03: A note with no relationships (neither source nor target) is an orphan.

    Spec: get_orphan_notes() must include notes absent from both
    relationships.source_path and relationships.target_path.
    """
    from engine.db import init_schema, get_connection
    from engine.brain_health import get_orphan_notes
    import engine.db as _db
    import engine.paths as _paths

    db_path = tmp_path / "orphan_spec.db"
    _db.DB_PATH = db_path
    _paths.DB_PATH = db_path
    conn = get_connection()
    init_schema(conn)
    conn.execute(
        "INSERT INTO notes (path, title, type, body, sensitivity) VALUES (?,?,?,?,?)",
        ("ideas/orphan.md", "Orphan Note", "idea", "no links", "public"),
    )
    conn.commit()
    result = get_orphan_notes(conn)
    conn.close()
    assert any(r["path"] == "ideas/orphan.md" for r in result), \
        "Note with no relationships must be classified as orphan"


def test_note_with_outbound_link_is_not_orphan(tmp_path):
    """QA-03: A note that has an outbound link (source_path) is NOT an orphan.

    Spec: having any entry in relationships as source_path removes the note from orphan set.
    """
    from engine.db import init_schema, get_connection
    from engine.brain_health import get_orphan_notes
    import engine.db as _db
    import engine.paths as _paths

    db_path = tmp_path / "outbound_spec.db"
    _db.DB_PATH = db_path
    _paths.DB_PATH = db_path
    conn = get_connection()
    init_schema(conn)
    conn.execute(
        "INSERT INTO notes (path, title, type, body, sensitivity) VALUES (?,?,?,?,?)",
        ("ideas/linked.md", "Linked Note", "idea", "links out", "public"),
    )
    conn.execute(
        "INSERT INTO notes (path, title, type, body, sensitivity) VALUES (?,?,?,?,?)",
        ("ideas/target.md", "Target Note", "idea", "target", "public"),
    )
    conn.execute(
        "INSERT INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
        ("ideas/linked.md", "ideas/target.md", "reference"),
    )
    conn.commit()
    result = get_orphan_notes(conn)
    conn.close()
    assert not any(r["path"] == "ideas/linked.md" for r in result), \
        "Note with outbound link must NOT be an orphan"


def test_note_with_inbound_link_is_not_orphan(tmp_path):
    """QA-03: A note that has an inbound link (target_path) is NOT an orphan.

    Spec: having any entry in relationships as target_path removes the note from orphan set.
    """
    from engine.db import init_schema, get_connection
    from engine.brain_health import get_orphan_notes
    import engine.db as _db
    import engine.paths as _paths

    db_path = tmp_path / "inbound_spec.db"
    _db.DB_PATH = db_path
    _paths.DB_PATH = db_path
    conn = get_connection()
    init_schema(conn)
    conn.execute(
        "INSERT INTO notes (path, title, type, body, sensitivity) VALUES (?,?,?,?,?)",
        ("ideas/source.md", "Source Note", "idea", "links to target", "public"),
    )
    conn.execute(
        "INSERT INTO notes (path, title, type, body, sensitivity) VALUES (?,?,?,?,?)",
        ("ideas/pointed-to.md", "Pointed To Note", "idea", "has inbound", "public"),
    )
    conn.execute(
        "INSERT INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
        ("ideas/source.md", "ideas/pointed-to.md", "reference"),
    )
    conn.commit()
    result = get_orphan_notes(conn)
    conn.close()
    assert not any(r["path"] == "ideas/pointed-to.md" for r in result), \
        "Note with inbound link must NOT be an orphan"


# ---------------------------------------------------------------------------
# Phase 32-04: action_items archival
# ---------------------------------------------------------------------------

@pytest.fixture
def archive_conn(tmp_path):
    """Isolated SQLite DB with schema for archival tests."""
    import engine.db as _db
    import engine.paths as _paths
    db_path = tmp_path / "archive_test.db"
    _db.DB_PATH = db_path
    _paths.DB_PATH = db_path
    from engine.db import get_connection, init_schema
    conn = get_connection()
    init_schema(conn)
    yield conn
    conn.close()


def _insert_action_item(conn, note_path, text, done, done_at, created_at=None):
    """Helper: insert an action_item row with explicit done_at."""
    ca = created_at or "2025-01-01T00:00:00Z"
    conn.execute(
        "INSERT INTO action_items (note_path, text, done, done_at, created_at) VALUES (?,?,?,?,?)",
        (note_path, text, 1 if done else 0, done_at, ca),
    )
    conn.commit()


def test_archive_old_done_items_are_moved(archive_conn):
    """32-04: done items with done_at older than 90 days must be archived."""
    from engine.brain_health import archive_old_action_items
    _insert_action_item(archive_conn, "notes/a.md", "Old task", done=True, done_at="2020-01-01T00:00:00Z")
    count = archive_old_action_items(archive_conn, days=90)
    assert count == 1, f"Expected 1 archived, got {count}"
    # Must be in archive
    archived = archive_conn.execute("SELECT * FROM action_items_archive").fetchall()
    assert len(archived) == 1
    # Must be removed from action_items
    remaining = archive_conn.execute(
        "SELECT * FROM action_items WHERE note_path='notes/a.md'"
    ).fetchall()
    assert len(remaining) == 0


def test_archive_recent_done_items_not_archived(archive_conn):
    """32-04: done items with done_at less than 90 days ago must NOT be archived."""
    from engine.brain_health import archive_old_action_items
    import datetime
    recent = (datetime.datetime.utcnow() - datetime.timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _insert_action_item(archive_conn, "notes/b.md", "Recent task", done=True, done_at=recent)
    count = archive_old_action_items(archive_conn, days=90)
    assert count == 0, f"Expected 0 archived, got {count}"
    remaining = archive_conn.execute(
        "SELECT * FROM action_items WHERE note_path='notes/b.md'"
    ).fetchall()
    assert len(remaining) == 1


def test_archive_undone_items_not_archived(archive_conn):
    """32-04: non-done items must NOT be archived regardless of age."""
    from engine.brain_health import archive_old_action_items
    _insert_action_item(archive_conn, "notes/c.md", "Pending task", done=False, done_at=None)
    count = archive_old_action_items(archive_conn, days=90)
    assert count == 0, f"Expected 0 archived, got {count}"
    remaining = archive_conn.execute(
        "SELECT * FROM action_items WHERE note_path='notes/c.md'"
    ).fetchall()
    assert len(remaining) == 1


def test_archive_count_matches_archived(archive_conn):
    """32-04: return value of archive_old_action_items() must equal items moved."""
    from engine.brain_health import archive_old_action_items
    _insert_action_item(archive_conn, "notes/d.md", "Old 1", done=True, done_at="2019-01-01T00:00:00Z")
    _insert_action_item(archive_conn, "notes/e.md", "Old 2", done=True, done_at="2019-06-01T00:00:00Z")
    count = archive_old_action_items(archive_conn, days=90)
    assert count == 2
    archived = archive_conn.execute("SELECT * FROM action_items_archive").fetchall()
    assert len(archived) == 2


def test_health_report_includes_archived_count(archive_conn):
    """32-04: brain health report dict must include archived_action_items count."""
    from engine.brain_health import get_brain_health_report
    _insert_action_item(archive_conn, "notes/f.md", "Old task", done=True, done_at="2020-01-01T00:00:00Z")
    report = get_brain_health_report(archive_conn)
    assert "archived_action_items" in report, f"archived_action_items missing from {list(report.keys())}"
    assert report["archived_action_items"] >= 1


# ---------------------------------------------------------------------------
# Phase 35-01: merge_notes() tests (CONS-01)
# ---------------------------------------------------------------------------

@pytest.fixture
def merge_conn(tmp_path):
    """Isolated SQLite DB with schema + two markdown files on disk for merge testing."""
    import engine.db as _db
    import engine.paths as _paths
    db_path = tmp_path / "merge_test.db"
    _db.DB_PATH = db_path
    _paths.DB_PATH = db_path
    from engine.db import get_connection, init_schema
    conn = get_connection()
    init_schema(conn)
    # Create actual markdown files on disk
    keep_file = tmp_path / "keep.md"
    discard_file = tmp_path / "discard.md"
    keep_file.write_text("# Keep Note\n\nKeep body content.", encoding="utf-8")
    discard_file.write_text("# Discard Note\n\nDiscard body content.", encoding="utf-8")
    # Insert both notes into DB using their absolute paths
    conn.execute(
        "INSERT INTO notes (path, title, type, body, tags, sensitivity) VALUES (?,?,?,?,?,?)",
        (str(keep_file), "Keep Note", "note", "Keep body content.", '["alpha","beta"]', "public"),
    )
    conn.execute(
        "INSERT INTO notes (path, title, type, body, tags, sensitivity) VALUES (?,?,?,?,?,?)",
        (str(discard_file), "Discard Note", "note", "Discard body content.", '["beta","gamma"]', "public"),
    )
    conn.commit()
    yield conn, tmp_path, str(keep_file), str(discard_file)
    conn.close()


def test_merge_copies_body_tags_relationships(merge_conn):
    """35-01: merge_notes merges body with separator, unions tags, remaps relationships."""
    from engine.brain_health import merge_notes
    conn, tmp_path, keep_path, discard_path = merge_conn

    # Add a relationship from discard to another note
    other_file = tmp_path / "other.md"
    other_file.write_text("# Other\n\nOther body.", encoding="utf-8")
    conn.execute(
        "INSERT INTO notes (path, title, type, body, sensitivity) VALUES (?,?,?,?,?)",
        (str(other_file), "Other Note", "note", "Other body.", "public"),
    )
    conn.execute(
        "INSERT INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
        (discard_path, str(other_file), "reference"),
    )
    conn.commit()

    result = merge_notes(keep_path, discard_path, conn)

    assert result["keep"] == keep_path
    assert result["discarded"] == discard_path

    # Body: merged with separator
    row = conn.execute("SELECT body, tags FROM notes WHERE path=?", (keep_path,)).fetchone()
    assert "Keep body content." in row[0]
    assert "Discard body content." in row[0]
    assert "\n\n---\n\n" in row[0]

    # Tags: union of alpha, beta, gamma
    import json
    merged_tags = json.loads(row[1])
    assert set(merged_tags) == {"alpha", "beta", "gamma"}

    # Relationship remapped: discard->other should now be keep->other
    rels = conn.execute(
        "SELECT source_path FROM relationships WHERE target_path=?", (str(other_file),)
    ).fetchall()
    sources = [r[0] for r in rels]
    assert keep_path in sources
    assert discard_path not in sources


def test_merge_deletes_discard_note(merge_conn):
    """35-01: discard note is removed from notes, embeddings, action_items, note_people, note_tags tables."""
    from engine.brain_health import merge_notes
    conn, tmp_path, keep_path, discard_path = merge_conn

    # Add an action item and note_people row for the discard note
    conn.execute(
        "INSERT INTO action_items (note_path, text, done) VALUES (?,?,?)",
        (discard_path, "Do something", 0),
    )
    conn.execute(
        "INSERT INTO note_tags (note_path, tag) VALUES (?,?)",
        (discard_path, "gamma"),
    )
    conn.commit()

    merge_notes(keep_path, discard_path, conn)

    # Notes table: discard gone
    assert conn.execute("SELECT 1 FROM notes WHERE path=?", (discard_path,)).fetchone() is None
    # Action items: discard's items gone
    assert conn.execute("SELECT 1 FROM action_items WHERE note_path=?", (discard_path,)).fetchone() is None
    # Note tags: discard's tags gone
    assert conn.execute("SELECT 1 FROM note_tags WHERE note_path=?", (discard_path,)).fetchone() is None


def test_merge_fts5_rebuilt(merge_conn):
    """35-01: after merge, FTS5 search by discard title (title column only) returns no results."""
    from engine.brain_health import merge_notes
    conn, tmp_path, keep_path, discard_path = merge_conn

    # Record the discard note's rowid before merge
    discard_row = conn.execute("SELECT id FROM notes WHERE path=?", (discard_path,)).fetchone()
    assert discard_row is not None
    discard_rowid = discard_row[0]

    merge_notes(keep_path, discard_path, conn)

    # Discard note rowid must not exist in notes table anymore
    assert conn.execute("SELECT 1 FROM notes WHERE id=?", (discard_rowid,)).fetchone() is None

    # FTS5 search scoped to title column — discard title should not appear
    rows = conn.execute(
        "SELECT rowid FROM notes_fts WHERE notes_fts MATCH ?",
        ("title:\"Discard Note\"",),
    ).fetchall()
    assert len(rows) == 0, "Discard note title still in FTS5 after merge"

    # Keep note title should still be findable
    rows = conn.execute(
        "SELECT rowid FROM notes_fts WHERE notes_fts MATCH ?",
        ("title:\"Keep Note\"",),
    ).fetchall()
    assert len(rows) >= 1


def test_merge_discard_file_deleted(merge_conn):
    """35-01: discard markdown file is deleted from disk after merge."""
    from engine.brain_health import merge_notes
    from pathlib import Path
    conn, tmp_path, keep_path, discard_path = merge_conn

    assert Path(discard_path).exists(), "Discard file must exist before merge"
    merge_notes(keep_path, discard_path, conn)
    assert not Path(discard_path).exists(), "Discard file must be deleted after merge"


def test_merge_audit_logged(merge_conn):
    """35-01: audit_log has event_type='merge' entry after merge_notes."""
    from engine.brain_health import merge_notes
    conn, tmp_path, keep_path, discard_path = merge_conn

    merge_notes(keep_path, discard_path, conn)

    row = conn.execute(
        "SELECT note_path, detail FROM audit_log WHERE event_type='merge'",
    ).fetchone()
    assert row is not None, "No merge audit log entry found"
    assert row[0] == keep_path
    assert discard_path in row[1]


def test_merge_nonexistent_discard_raises(merge_conn):
    """35-01: merge_notes raises ValueError when discard_path not in DB."""
    from engine.brain_health import merge_notes
    conn, tmp_path, keep_path, discard_path = merge_conn

    with pytest.raises(ValueError, match="not found"):
        merge_notes(keep_path, "/nonexistent/path.md", conn)


# ---------------------------------------------------------------------------
# Phase 35-02: stub detection + connection cleanup (CONS-02, CONS-03)
# ---------------------------------------------------------------------------

@pytest.fixture
def stub_conn(tmp_path):
    """Isolated SQLite DB for stub and connection cleanup tests."""
    import engine.db as _db
    import engine.paths as _paths
    db_path = tmp_path / "stub_test.db"
    _db.DB_PATH = db_path
    _paths.DB_PATH = db_path
    from engine.db import get_connection, init_schema
    conn = get_connection()
    init_schema(conn)
    yield conn
    conn.close()


def _insert_note(conn, path, title, body):
    conn.execute(
        "INSERT INTO notes (path, title, type, body, sensitivity) VALUES (?,?,?,?,?)",
        (path, title, "note", body, "public"),
    )
    conn.commit()


def test_get_stub_notes_word_count(stub_conn):
    """35-02: get_stub_notes returns notes with < 50 words, excludes >= 50 words."""
    from engine.brain_health import get_stub_notes

    short_body = " ".join(["word"] * 10)   # 10 words — stub
    borderline = " ".join(["word"] * 49)   # 49 words — stub
    exact_50 = " ".join(["word"] * 50)     # 50 words — NOT stub
    long_body = " ".join(["word"] * 100)   # 100 words — NOT stub

    _insert_note(stub_conn, "a.md", "Short", short_body)
    _insert_note(stub_conn, "b.md", "Borderline", borderline)
    _insert_note(stub_conn, "c.md", "Exact50", exact_50)
    _insert_note(stub_conn, "d.md", "Long", long_body)

    result = get_stub_notes(stub_conn)
    paths = [r["path"] for r in result]

    assert "a.md" in paths, "10-word note must be a stub"
    assert "b.md" in paths, "49-word note must be a stub"
    assert "c.md" not in paths, "50-word note must NOT be a stub"
    assert "d.md" not in paths, "100-word note must NOT be a stub"


def test_get_stub_notes_includes_empty(stub_conn):
    """35-02: get_stub_notes includes notes with empty body (superset of get_empty_notes).

    Schema enforces NOT NULL DEFAULT '' so NULL is tested via empty string path.
    """
    from engine.brain_health import get_stub_notes
    stub_conn.execute(
        "INSERT INTO notes (path, title, type, body, sensitivity) VALUES (?,?,?,?,?)",
        ("empty_body.md", "Empty Body", "note", "", "public"),
    )
    stub_conn.commit()

    result = get_stub_notes(stub_conn)
    paths = [r["path"] for r in result]
    assert "empty_body.md" in paths, "Note with empty body must be included in stubs"


def test_delete_dangling_relationships(stub_conn):
    """35-02: delete_dangling_relationships removes relationship where source_path not in notes."""
    from engine.brain_health import delete_dangling_relationships
    _insert_note(stub_conn, "exists.md", "Exists", "body")
    stub_conn.execute(
        "INSERT INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
        ("ghost.md", "exists.md", "reference"),
    )
    stub_conn.commit()

    count = delete_dangling_relationships(stub_conn)
    assert count == 1, f"Expected 1 dangling deleted, got {count}"
    remaining = stub_conn.execute("SELECT * FROM relationships").fetchall()
    assert len(remaining) == 0


def test_delete_dangling_keeps_valid(stub_conn):
    """35-02: delete_dangling_relationships keeps relationships where both paths exist."""
    from engine.brain_health import delete_dangling_relationships
    _insert_note(stub_conn, "src.md", "Source", "body")
    _insert_note(stub_conn, "tgt.md", "Target", "body")
    stub_conn.execute(
        "INSERT INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
        ("src.md", "tgt.md", "reference"),
    )
    stub_conn.commit()

    count = delete_dangling_relationships(stub_conn)
    assert count == 0, f"Expected 0 deleted, got {count}"
    remaining = stub_conn.execute("SELECT * FROM relationships").fetchall()
    assert len(remaining) == 1


def test_bidirectional_gap_detection(stub_conn):
    """35-02: get_bidirectional_gaps returns A->B when B->A is missing, and nothing when both directions exist."""
    from engine.brain_health import get_bidirectional_gaps
    _insert_note(stub_conn, "A.md", "A", "body")
    _insert_note(stub_conn, "B.md", "B", "body")

    # Only A->B, no B->A
    stub_conn.execute(
        "INSERT INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
        ("A.md", "B.md", "reference"),
    )
    stub_conn.commit()

    gaps = get_bidirectional_gaps(stub_conn)
    assert any(g["source"] == "A.md" and g["target"] == "B.md" for g in gaps), \
        "A->B gap should be detected"

    # Add B->A
    stub_conn.execute(
        "INSERT INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
        ("B.md", "A.md", "reference"),
    )
    stub_conn.commit()

    gaps = get_bidirectional_gaps(stub_conn)
    assert not any(g["source"] == "A.md" and g["target"] == "B.md" for g in gaps), \
        "A->B should NOT be a gap when B->A also exists"


def test_bidirectional_gap_excludes_dangling(stub_conn):
    """35-02: dangling relationships (path not in notes) must NOT appear in bidirectional gaps."""
    from engine.brain_health import get_bidirectional_gaps
    # Insert only one note; the other path doesn't exist
    _insert_note(stub_conn, "real.md", "Real", "body")
    stub_conn.execute(
        "INSERT INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
        ("ghost.md", "real.md", "reference"),
    )
    stub_conn.commit()

    gaps = get_bidirectional_gaps(stub_conn)
    assert not any(g["source"] == "ghost.md" for g in gaps), \
        "Dangling source (ghost.md) must NOT appear in bidirectional gaps"


# ---------------------------------------------------------------------------
# Phase 35-03: health_snapshots migration + snapshot/cleanup (CONS-04, CONS-05)
# ---------------------------------------------------------------------------


def test_health_snapshots_migration(archive_conn):
    """35-03: init_schema creates health_snapshots table."""
    row = archive_conn.execute(
        "SELECT name FROM sqlite_master WHERE name='health_snapshots'"
    ).fetchone()
    assert row is not None, "health_snapshots table must exist after init_schema"


def test_take_health_snapshot(archive_conn):
    """35-03: take_health_snapshot inserts a row with snapped_at=today, score, counts."""
    from engine.brain_health import take_health_snapshot
    import datetime
    result = take_health_snapshot(archive_conn)
    assert result.get("skipped") is not True, "First snapshot must not be skipped"
    assert isinstance(result["score"], int)
    assert isinstance(result["total_notes"], int)
    assert isinstance(result["orphan_count"], int)
    assert isinstance(result["broken_count"], int)
    assert isinstance(result["duplicate_count"], int)
    assert isinstance(result["stub_count"], int)

    today = datetime.date.today().isoformat()
    row = archive_conn.execute(
        "SELECT snapped_at, score FROM health_snapshots WHERE date(snapped_at) = ?",
        (today,),
    ).fetchone()
    assert row is not None, "Snapshot row must exist in health_snapshots for today"
    assert isinstance(row[1], int)


def test_take_health_snapshot_skips_duplicate_day(archive_conn):
    """35-03: calling take_health_snapshot twice on same day inserts only 1 row."""
    from engine.brain_health import take_health_snapshot
    take_health_snapshot(archive_conn)
    result2 = take_health_snapshot(archive_conn)
    assert result2.get("skipped") is True, "Second snapshot same day must be skipped"
    assert result2.get("reason") == "snapshot_exists_today"
    count = archive_conn.execute("SELECT COUNT(*) FROM health_snapshots").fetchone()[0]
    assert count == 1, f"Expected 1 snapshot row, got {count}"


def test_cleanup_old_snapshots(archive_conn):
    """35-03: cleanup_old_snapshots deletes snapshots older than 90 days."""
    from engine.brain_health import cleanup_old_snapshots
    # Insert snapshot 100 days ago
    archive_conn.execute(
        "INSERT INTO health_snapshots (snapped_at, score, total_notes, orphan_count, broken_count, duplicate_count, stub_count)"
        " VALUES (date('now', '-100 days'), 80, 10, 1, 0, 0, 2)"
    )
    archive_conn.commit()
    deleted = cleanup_old_snapshots(archive_conn, days=90)
    assert deleted == 1, f"Expected 1 deleted, got {deleted}"
    count = archive_conn.execute("SELECT COUNT(*) FROM health_snapshots").fetchone()[0]
    assert count == 0


def test_cleanup_old_snapshots_keeps_recent(archive_conn):
    """35-03: cleanup_old_snapshots keeps snapshots within 90 days."""
    from engine.brain_health import cleanup_old_snapshots
    # Insert snapshot 30 days ago
    archive_conn.execute(
        "INSERT INTO health_snapshots (snapped_at, score, total_notes, orphan_count, broken_count, duplicate_count, stub_count)"
        " VALUES (date('now', '-30 days'), 90, 20, 0, 0, 0, 1)"
    )
    archive_conn.commit()
    deleted = cleanup_old_snapshots(archive_conn, days=90)
    assert deleted == 0, f"Expected 0 deleted, got {deleted}"
    count = archive_conn.execute("SELECT COUNT(*) FROM health_snapshots").fetchone()[0]
    assert count == 1
