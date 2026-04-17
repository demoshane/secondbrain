"""Tests for Phase 56 Plan 03: capture nudges, recent_context, and session retrieval."""

import datetime
import json
import sqlite3
import time

import pytest
from pathlib import Path


@pytest.fixture
def brain_env(tmp_path, monkeypatch):
    """Set up isolated brain environment for MCP/capture testing."""
    import engine.paths as _paths
    import engine.db as _db
    import engine.mcp_server as _mcp

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
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    from engine.db import init_schema
    init_schema(conn)
    conn.close()

    return brain


def _get_conn(brain_env):
    from engine.db import get_connection
    return get_connection()


def _insert_note_directly(conn, brain, title, minutes_ago=0, capture_session=None):
    """Insert a note for setup."""
    from engine.paths import store_path

    ts = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=minutes_ago)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    slug = title.lower().replace(" ", "-")
    path = brain / "ideas" / f"{slug}.md"
    path.write_text(f"---\ntitle: {title}\ntype: note\n---\n\n{title}\n")

    try:
        rel_path = store_path(path.resolve())
    except ValueError:
        rel_path = str(path.resolve())

    conn.execute(
        "INSERT INTO notes (path, type, title, body, tags, people, created_at, updated_at, sensitivity, importance, capture_session)"
        " VALUES (?, 'note', ?, ?, '[]', '[]', ?, ?, 'public', 'medium', ?)",
        (rel_path, title, title, ts_str, ts_str, capture_session),
    )
    conn.commit()
    return rel_path


# ---------------------------------------------------------------------------
# sb_capture nudge tests
# ---------------------------------------------------------------------------


class TestSbCaptureNudges:
    def test_nudge_present_with_one_neighbor(self, brain_env):
        """Single neighbor → nudge with specific title."""
        conn = _get_conn(brain_env)
        try:
            _insert_note_directly(conn, brain_env, "Earlier Note", minutes_ago=3)
        finally:
            conn.close()

        from engine.mcp_server import sb_capture
        result = sb_capture(title="After Note", body="Follows the earlier one")
        assert result["status"] == "created"
        assert "recent_context" in result
        assert len(result["recent_context"]) >= 1
        assert "nudge" in result
        assert "Earlier Note" in result["nudge"]

    def test_nudge_present_with_multiple_neighbors(self, brain_env):
        """Multiple neighbors → nudge with count."""
        conn = _get_conn(brain_env)
        try:
            _insert_note_directly(conn, brain_env, "Neighbor A", minutes_ago=2)
            _insert_note_directly(conn, brain_env, "Neighbor B", minutes_ago=4)
        finally:
            conn.close()

        from engine.mcp_server import sb_capture
        result = sb_capture(title="Multi Neighbor", body="Has two neighbors nearby")
        assert "nudge" in result
        assert "2 recent captures" in result["nudge"]

    def test_no_nudge_when_isolated(self, brain_env):
        """No neighbors → no nudge field."""
        from engine.mcp_server import sb_capture
        result = sb_capture(title="Lonely Note", body="All alone in time")
        assert result["status"] == "created"
        assert "nudge" not in result
        assert result["recent_context"] == []

    def test_recent_context_has_correct_fields(self, brain_env):
        """recent_context entries have path, title, type, minutes_ago."""
        conn = _get_conn(brain_env)
        try:
            _insert_note_directly(conn, brain_env, "Context Source", minutes_ago=5)
        finally:
            conn.close()

        from engine.mcp_server import sb_capture
        result = sb_capture(title="Context Check", body="Checking context fields")
        ctx = result["recent_context"]
        assert len(ctx) >= 1
        entry = ctx[0]
        assert "path" in entry
        assert "title" in entry
        assert "type" in entry
        assert "minutes_ago" in entry
        assert isinstance(entry["minutes_ago"], int)
        assert entry["minutes_ago"] >= 1

    def test_nudge_escalates_over_captures(self, brain_env):
        """Nudge count grows as more notes are captured."""
        from engine.mcp_server import sb_capture

        r1 = sb_capture(title="Escalate A", body="First capture")
        assert "nudge" not in r1  # no prior notes

        r2 = sb_capture(title="Escalate B", body="Second capture")
        assert "nudge" in r2
        assert "Escalate A" in r2["nudge"]  # single neighbor

        r3 = sb_capture(title="Escalate C", body="Third capture")
        assert "nudge" in r3
        assert "2 recent captures" in r3["nudge"]


# ---------------------------------------------------------------------------
# sb_capture_batch nudge tests
# ---------------------------------------------------------------------------


class TestSbCaptureBatchNudges:
    def test_batch_returns_capture_session(self, brain_env):
        from engine.mcp_server import sb_capture_batch
        result = sb_capture_batch([
            {"title": "Batch X", "body": "x"},
            {"title": "Batch Y", "body": "y"},
        ])
        assert "capture_session" in result
        assert len(result["capture_session"]) > 0


# ---------------------------------------------------------------------------
# Capture session endpoint tests
# ---------------------------------------------------------------------------


class TestCaptureSessionEndpoint:
    @pytest.fixture
    def client(self, brain_env):
        """Flask test client pointing at isolated brain."""
        from engine.api import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c

    def test_session_retrieval(self, brain_env, client):
        """GET /capture-session/<id> returns session notes."""
        from engine.mcp_server import sb_capture

        r1 = sb_capture(title="Sess Ret A", body="First in session", session_id="ret-test-1")
        r2 = sb_capture(title="Sess Ret B", body="Second in session", session_id="ret-test-1")

        resp = client.get("/capture-session/ret-test-1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["session_id"] == "ret-test-1"
        assert data["count"] == 2
        titles = [n["title"] for n in data["notes"]]
        assert "Sess Ret A" in titles
        assert "Sess Ret B" in titles

    def test_session_404_unknown(self, client):
        """Unknown session returns 404."""
        resp = client.get("/capture-session/nonexistent-uuid")
        assert resp.status_code == 404

    def test_session_includes_relationships(self, brain_env, client):
        """Session endpoint includes co-captured relationships."""
        from engine.mcp_server import sb_capture

        sb_capture(title="Rel Sess A", body="a", session_id="rel-test-1")
        sb_capture(title="Rel Sess B", body="b", session_id="rel-test-1")

        resp = client.get("/capture-session/rel-test-1")
        data = resp.get_json()
        assert "relationships" in data
        # Should have co-captured relationships between the two
        assert len(data["relationships"]) >= 1


# ---------------------------------------------------------------------------
# Full lifecycle: conversation simulation
# ---------------------------------------------------------------------------


class TestConversationLifecycle:
    def test_three_captures_all_linked(self, brain_env):
        """3 separate sb_capture calls within window → all 3 co-captured."""
        from engine.mcp_server import sb_capture

        r1 = sb_capture(title="Conv A", body="First in conversation")
        r2 = sb_capture(title="Conv B", body="Second in conversation")
        r3 = sb_capture(title="Conv C", body="Third in conversation")

        assert r1["status"] == "created"
        assert len(r2["co_captured_with"]) >= 1
        assert len(r3["co_captured_with"]) >= 2

        # Verify all 3 are linked in DB
        conn = _get_conn(brain_env)
        try:
            rels = conn.execute(
                "SELECT source_path, target_path FROM relationships WHERE rel_type = 'co-captured'"
            ).fetchall()
            all_paths = set()
            for r in rels:
                all_paths.add(r[0])
                all_paths.add(r[1])
            # All 3 notes should appear in relationships
            assert len(all_paths) >= 3
        finally:
            conn.close()

    def test_session_grouping_across_time(self, brain_env):
        """session_id links notes even beyond temporal window."""
        conn = _get_conn(brain_env)
        try:
            # Note from 20 min ago with same session
            _insert_note_directly(conn, brain_env, "Old Session Note", minutes_ago=20, capture_session="long-session")
        finally:
            conn.close()

        from engine.mcp_server import sb_capture
        result = sb_capture(title="New Session Note", body="Same session, far apart", session_id="long-session")
        assert result["status"] == "created"
        # Should be linked via session_id even though outside 15-min window
        assert len(result["co_captured_with"]) >= 1

    def test_graph_integrity_after_lifecycle(self, brain_env):
        """All relationships point to existing notes after a multi-capture session."""
        from engine.mcp_server import sb_capture

        for i in range(5):
            sb_capture(title=f"Integrity {i}", body=f"Note number {i}")

        conn = _get_conn(brain_env)
        try:
            rels = conn.execute(
                "SELECT source_path, target_path FROM relationships WHERE rel_type = 'co-captured'"
            ).fetchall()
            for src, tgt in rels:
                src_exists = conn.execute("SELECT 1 FROM notes WHERE path = ?", (src,)).fetchone()
                tgt_exists = conn.execute("SELECT 1 FROM notes WHERE path = ?", (tgt,)).fetchone()
                assert src_exists, f"Dangling source: {src}"
                assert tgt_exists, f"Dangling target: {tgt}"
        finally:
            conn.close()
