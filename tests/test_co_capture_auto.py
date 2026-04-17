"""Tests for Phase 56 Plan 02: automatic co-capture relationships via temporal proximity."""

import datetime
import sqlite3

import pytest
from pathlib import Path


@pytest.fixture
def brain_env(tmp_path, monkeypatch):
    """Set up isolated brain environment for MCP/capture testing."""
    import engine.paths as _paths
    import engine.db as _db
    import engine.mcp_server as _mcp
    import engine.capture as _cap

    brain = tmp_path / "brain"
    brain.mkdir()
    for d in ["ideas", "meetings", "projects", "people", "coding", "files", "personal", "strategy", "note"]:
        (brain / d).mkdir()

    db_path = brain / ".index" / "brain.db"
    db_path.parent.mkdir(parents=True)

    monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)
    monkeypatch.setattr(_paths, "DB_PATH", db_path)
    monkeypatch.setattr(_db, "DB_PATH", db_path)
    monkeypatch.setattr(_mcp, "BRAIN_ROOT", brain)
    # capture.py also imports store_path via _store_path — patch BRAIN_ROOT there too
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    from engine.db import init_schema
    init_schema(conn)
    conn.close()

    return brain


def _get_conn(brain_env):
    """Get a connection to the test DB."""
    from engine.db import get_connection
    return get_connection()


def _get_relationships(conn, rel_type="co-captured"):
    """Return all relationships of the given type."""
    rows = conn.execute(
        "SELECT source_path, target_path FROM relationships WHERE rel_type = ?",
        (rel_type,),
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def _insert_note_directly(conn, brain, title, note_type="note", minutes_ago=0, capture_session=None):
    """Insert a note directly (bypassing capture_note) for setup purposes."""
    from engine.paths import store_path

    ts = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=minutes_ago)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    slug = title.lower().replace(" ", "-")
    subdir = note_type + "s" if note_type != "note" else "ideas"
    path = brain / subdir / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\ntitle: {title}\ntype: {note_type}\n---\n\n{title} body\n")

    try:
        rel_path = store_path(path.resolve())
    except ValueError:
        rel_path = str(path.resolve())

    conn.execute(
        "INSERT INTO notes (path, type, title, body, tags, people, created_at, updated_at, sensitivity, importance, capture_session)"
        " VALUES (?, ?, ?, ?, '[]', '[]', ?, ?, 'public', 'medium', ?)",
        (rel_path, note_type, title, f"{title} body", ts_str, ts_str, capture_session),
    )
    conn.commit()
    return rel_path


# ---------------------------------------------------------------------------
# sb_capture auto co-capture tests
# ---------------------------------------------------------------------------


class TestSbCaptureAutoCoCaptured:
    def test_capture_with_temporal_neighbor(self, brain_env):
        """sb_capture auto-links with a recently captured note."""
        conn = _get_conn(brain_env)
        try:
            # Pre-existing note captured 2 minutes ago
            pre_path = _insert_note_directly(conn, brain_env, "Prior Note", minutes_ago=2)
        finally:
            conn.close()

        from engine.mcp_server import sb_capture
        result = sb_capture(title="New Note", body="Some body content here for dedup avoidance")
        assert result["status"] == "created"
        assert "co_captured_with" in result

        conn = _get_conn(brain_env)
        try:
            rels = _get_relationships(conn)
            # Should have at least one co-captured relationship
            all_paths = [r[0] for r in rels] + [r[1] for r in rels]
            assert pre_path in all_paths, f"Pre-existing note should be in co-captured relationships, got {rels}"
        finally:
            conn.close()

    def test_capture_no_neighbor_outside_window(self, brain_env):
        """No co-captured links when no notes within temporal window."""
        conn = _get_conn(brain_env)
        try:
            # Note from 30 minutes ago — outside 15-min window
            _insert_note_directly(conn, brain_env, "Old Note", minutes_ago=30)
        finally:
            conn.close()

        from engine.mcp_server import sb_capture
        result = sb_capture(title="Isolated Note", body="Content that stands alone in time")
        assert result["status"] == "created"
        assert result["co_captured_with"] == []

    def test_capture_with_session_id(self, brain_env):
        """Notes sharing a session_id are linked even if captured separately."""
        from engine.mcp_server import sb_capture

        r1 = sb_capture(title="Session Note A", body="First note in session", session_id="test-session-1")
        assert r1["status"] == "created"

        r2 = sb_capture(title="Session Note B", body="Second note in same session", session_id="test-session-1")
        assert r2["status"] == "created"
        assert len(r2["co_captured_with"]) >= 1

        conn = _get_conn(brain_env)
        try:
            rels = _get_relationships(conn)
            assert len(rels) >= 1, "Should have co-captured relationship between session notes"
        finally:
            conn.close()

    def test_capture_session_stored_in_db(self, brain_env):
        """session_id is persisted as capture_session in the notes table."""
        from engine.mcp_server import sb_capture

        sb_capture(title="Tracked Note", body="Note with session tracking", session_id="persist-test")

        conn = _get_conn(brain_env)
        try:
            row = conn.execute(
                "SELECT capture_session FROM notes WHERE title = 'Tracked Note'"
            ).fetchone()
            assert row is not None
            assert row[0] == "persist-test"
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# sb_capture_batch auto co-capture tests
# ---------------------------------------------------------------------------


class TestSbCaptureBatchAutoCoCaptured:
    def test_batch_intra_batch_linking(self, brain_env):
        """Notes in a batch are co-captured with each other."""
        from engine.mcp_server import sb_capture_batch

        result = sb_capture_batch([
            {"title": "Batch A", "body": "First in batch"},
            {"title": "Batch B", "body": "Second in batch"},
            {"title": "Batch C", "body": "Third in batch"},
        ])
        assert len(result["succeeded"]) == 3
        assert "capture_session" in result

        conn = _get_conn(brain_env)
        try:
            rels = _get_relationships(conn)
            # 3 notes → C(3,2) = 3 pairs minimum
            assert len(rels) >= 3, f"Expected at least 3 co-captured pairs, got {len(rels)}: {rels}"
        finally:
            conn.close()

    def test_batch_links_with_temporal_neighbors(self, brain_env):
        """Batch notes are also linked with pre-existing temporal neighbors."""
        conn = _get_conn(brain_env)
        try:
            pre_path = _insert_note_directly(conn, brain_env, "Pre Batch Note", minutes_ago=3)
        finally:
            conn.close()

        from engine.mcp_server import sb_capture_batch

        result = sb_capture_batch([
            {"title": "After Pre A", "body": "Batch after pre-existing"},
        ])
        assert len(result["succeeded"]) == 1

        conn = _get_conn(brain_env)
        try:
            rels = _get_relationships(conn)
            all_paths = [r[0] for r in rels] + [r[1] for r in rels]
            assert pre_path in all_paths, f"Pre-existing note should be linked, got {rels}"
        finally:
            conn.close()

    def test_batch_capture_session_stored(self, brain_env):
        """All batch notes share the same capture_session UUID."""
        from engine.mcp_server import sb_capture_batch

        result = sb_capture_batch([
            {"title": "Sess A", "body": "a"},
            {"title": "Sess B", "body": "b"},
        ])
        session_id = result["capture_session"]
        assert session_id  # non-empty

        conn = _get_conn(brain_env)
        try:
            rows = conn.execute(
                "SELECT capture_session FROM notes WHERE capture_session = ?",
                (session_id,),
            ).fetchall()
            assert len(rows) == 2
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Graph integrity tests
# ---------------------------------------------------------------------------


class TestCoCaptureGraphIntegrity:
    def test_no_fk_violations(self, brain_env):
        """All co-captured relationship paths exist in the notes table."""
        from engine.mcp_server import sb_capture

        sb_capture(title="Integrity A", body="First note for integrity check")
        sb_capture(title="Integrity B", body="Second note for integrity check")

        conn = _get_conn(brain_env)
        try:
            rels = _get_relationships(conn)
            for src, tgt in rels:
                src_exists = conn.execute("SELECT 1 FROM notes WHERE path = ?", (src,)).fetchone()
                tgt_exists = conn.execute("SELECT 1 FROM notes WHERE path = ?", (tgt,)).fetchone()
                assert src_exists, f"Source path {src} not in notes table"
                assert tgt_exists, f"Target path {tgt} not in notes table"
        finally:
            conn.close()

    def test_relationships_are_bidirectional(self, brain_env):
        """Co-captured relationships exist in both directions."""
        from engine.mcp_server import sb_capture

        sb_capture(title="BiDir A", body="Bidirectional test first")
        sb_capture(title="BiDir B", body="Bidirectional test second")

        conn = _get_conn(brain_env)
        try:
            rels = _get_relationships(conn)
            if rels:
                # Check at least one pair has both directions
                pairs = set()
                for src, tgt in rels:
                    pairs.add((src, tgt))
                # _auto_co_capture inserts both directions
                for src, tgt in list(pairs):
                    assert (tgt, src) in pairs, f"Missing reverse relationship for {src} → {tgt}"
        finally:
            conn.close()
