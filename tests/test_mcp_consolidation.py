"""Tests for sb_enrich + sb_consolidation_review MCP tools (Phase 57, Plan 05)."""
import json
import sqlite3
import pytest
from unittest.mock import patch, MagicMock

from engine.db import init_schema


# ---------------------------------------------------------------------------
# sb_enrich tests
# ---------------------------------------------------------------------------

def test_sb_enrich_success():
    """sb_enrich calls enrich_note and returns result."""
    mock_result = {"path": "coding/test.md", "before_length": 100, "after_length": 200, "enriched": True}
    with patch("engine.mcp_server._ensure_ready"), \
         patch("engine.mcp_server.get_connection") as mock_conn, \
         patch("engine.intelligence.enrich_note", return_value=mock_result), \
         patch("engine.mcp_server._log_mcp_audit"):
        from engine.mcp_server import sb_enrich
        result = sb_enrich("coding/test.md", "new info here")
        assert result["status"] == "enriched"
        assert result["path"] == "coding/test.md"
        assert result["before_length"] == 100
        assert result["after_length"] == 200
        assert result["enriched"] is True


def test_sb_enrich_not_found():
    """sb_enrich with bad path returns error dict."""
    with patch("engine.mcp_server._ensure_ready"), \
         patch("engine.mcp_server.get_connection"), \
         patch("engine.intelligence.enrich_note", side_effect=ValueError("Note not found: 'bad.md'")):
        from engine.mcp_server import sb_enrich
        result = sb_enrich("bad.md", "content")
        assert "error" in result
        assert "not found" in result["error"].lower()


def test_sb_enrich_exception_handling():
    """sb_enrich catches general exceptions gracefully."""
    with patch("engine.mcp_server._ensure_ready"), \
         patch("engine.mcp_server.get_connection"), \
         patch("engine.intelligence.enrich_note", side_effect=RuntimeError("AI down")):
        from engine.mcp_server import sb_enrich
        result = sb_enrich("some/path.md", "content")
        assert "error" in result


def test_sb_enrich_logs_audit():
    """sb_enrich logs MCP audit entry on success."""
    mock_result = {"path": "p.md", "before_length": 10, "after_length": 20, "enriched": True}
    with patch("engine.mcp_server._ensure_ready"), \
         patch("engine.mcp_server.get_connection"), \
         patch("engine.intelligence.enrich_note", return_value=mock_result), \
         patch("engine.mcp_server._log_mcp_audit") as mock_audit:
        from engine.mcp_server import sb_enrich
        sb_enrich("p.md", "content")
        mock_audit.assert_called_once_with("mcp_enrich", "p.md")


# ---------------------------------------------------------------------------
# sb_consolidation_review tests
# ---------------------------------------------------------------------------

class _NonClosingConn:
    """Wrapper that delegates everything to a real connection but ignores close()."""
    def __init__(self, real):
        self._real = real
    def close(self):
        pass  # ignore — fixture manages lifecycle
    def __getattr__(self, name):
        return getattr(self._real, name)


@pytest.fixture
def review_conn(tmp_path):
    """Isolated DB with consolidation_queue populated. Wrapped to survive MCP conn.close()."""
    import engine.db as _db
    import engine.paths as _paths
    db_path = tmp_path / "review_test.db"
    _db.DB_PATH = db_path
    _paths.DB_PATH = db_path
    conn = sqlite3.connect(str(db_path))
    init_schema(conn)
    conn.execute(
        "INSERT INTO consolidation_queue (action, source_paths, reason, similarity, detected_at, status) "
        "VALUES (?, ?, ?, ?, datetime('now'), 'pending')",
        ("enrich", json.dumps(["a.md", "b.md"]), "similarity", 0.85),
    )
    conn.execute(
        "INSERT INTO consolidation_queue (action, source_paths, reason, detected_at, status) "
        "VALUES (?, ?, ?, datetime('now'), 'pending')",
        ("stale", json.dumps(["c.md"]), "old note"),
    )
    conn.commit()
    yield _NonClosingConn(conn)
    conn.close()


def test_sb_consolidation_review_all(review_conn):
    """sb_consolidation_review with action='all' returns all pending items."""
    with patch("engine.mcp_server._ensure_ready"), \
         patch("engine.mcp_server.get_connection", return_value=review_conn):
        from engine.mcp_server import sb_consolidation_review
        result = sb_consolidation_review(action="all")
        assert result["count"] == 2
        assert len(result["items"]) == 2


def test_sb_consolidation_review_filter_enrich(review_conn):
    """sb_consolidation_review with action='enrich' returns only enrich items."""
    with patch("engine.mcp_server._ensure_ready"), \
         patch("engine.mcp_server.get_connection", return_value=review_conn):
        from engine.mcp_server import sb_consolidation_review
        result = sb_consolidation_review(action="enrich")
        assert result["count"] == 1
        assert result["items"][0]["action"] == "enrich"


def test_sb_consolidation_review_filter_stale(review_conn):
    """sb_consolidation_review with action='stale' returns only stale items."""
    with patch("engine.mcp_server._ensure_ready"), \
         patch("engine.mcp_server.get_connection", return_value=review_conn):
        from engine.mcp_server import sb_consolidation_review
        result = sb_consolidation_review(action="stale")
        assert result["count"] == 1
        assert result["items"][0]["action"] == "stale"


def test_sb_consolidation_review_item_format(review_conn):
    """Items have required keys: id, action, source_paths (list), target_path, reason, similarity, detected_at."""
    with patch("engine.mcp_server._ensure_ready"), \
         patch("engine.mcp_server.get_connection", return_value=review_conn):
        from engine.mcp_server import sb_consolidation_review
        result = sb_consolidation_review(action="enrich")
        item = result["items"][0]
        assert set(item.keys()) == {"id", "action", "source_paths", "target_path", "reason", "similarity", "detected_at"}
        assert isinstance(item["source_paths"], list)
        assert item["source_paths"] == ["a.md", "b.md"]


def test_sb_consolidation_review_limit(review_conn):
    """sb_consolidation_review respects limit parameter."""
    # Add more items
    for i in range(5):
        review_conn.execute(
            "INSERT INTO consolidation_queue (action, source_paths, reason, detected_at, status) "
            "VALUES (?, ?, ?, datetime('now'), 'pending')",
            ("enrich", json.dumps([f"x{i}.md"]), "test"),
        )
    review_conn.commit()

    with patch("engine.mcp_server._ensure_ready"), \
         patch("engine.mcp_server.get_connection", return_value=review_conn):
        from engine.mcp_server import sb_consolidation_review
        result = sb_consolidation_review(action="all", limit=2)
        assert result["count"] == 2


def test_sb_consolidation_review_empty(tmp_path):
    """Empty queue returns {"items": [], "count": 0}."""
    import engine.db as _db
    import engine.paths as _paths
    db_path = tmp_path / "empty_test.db"
    _db.DB_PATH = db_path
    _paths.DB_PATH = db_path
    conn = sqlite3.connect(str(db_path))
    init_schema(conn)

    with patch("engine.mcp_server._ensure_ready"), \
         patch("engine.mcp_server.get_connection", return_value=conn):
        from engine.mcp_server import sb_consolidation_review
        result = sb_consolidation_review()
        assert result == {"items": [], "count": 0}
    conn.close()


def test_sb_consolidation_review_dismiss(review_conn):
    """sb_consolidation_review with dismiss_id marks item as dismissed."""
    row = review_conn.execute("SELECT id FROM consolidation_queue WHERE status='pending' LIMIT 1").fetchone()
    item_id = row[0]

    with patch("engine.mcp_server._ensure_ready"), \
         patch("engine.mcp_server.get_connection", return_value=review_conn):
        from engine.mcp_server import sb_consolidation_review
        result = sb_consolidation_review(dismiss_id=item_id)
        assert result == {"dismissed": item_id}

    row = review_conn.execute("SELECT status, resolved_at FROM consolidation_queue WHERE id=?", (item_id,)).fetchone()
    assert row[0] == "dismissed"
    assert row[1] is not None
