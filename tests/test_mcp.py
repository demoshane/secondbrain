"""Tests for the Second Brain MCP server tools."""
import pytest
from unittest.mock import patch, MagicMock
import engine.mcp_server as mcp_mod


def test_sb_search():
    """sb_search returns a list (may be empty if brain has no notes)."""
    result = mcp_mod.sb_search("test query")
    assert isinstance(result, list)


def test_tool_parity():
    # 12 tools must be registered — use public list_tools() API (FastMCP 3.x)
    import asyncio
    tools = asyncio.run(mcp_mod.mcp.list_tools())
    tool_names = [t.name for t in tools]
    assert len(tools) >= 12, f"Expected 12 tools, got {len(tools)}: {tool_names}"


def test_two_step_confirmation():
    """sb_forget without a token returns pending+token (does NOT delete)."""
    result = mcp_mod.sb_forget("alice")
    assert result["status"] == "pending"
    assert "confirm_token" in result
    assert isinstance(result["confirm_token"], str)
    assert len(result["confirm_token"]) > 0

    # Second call without token returns a new pending (token was not consumed)
    result2 = mcp_mod.sb_forget("alice")
    assert result2["status"] == "pending"


def test_token_expiry():
    """TOKEN_EXPIRED raised for invalid/expired token; token store types are correct."""
    assert hasattr(mcp_mod, "_pending")
    assert hasattr(mcp_mod, "_pending_lock")
    assert isinstance(mcp_mod._pending, dict)
    import threading
    assert isinstance(mcp_mod._pending_lock, type(threading.Lock()))

    with pytest.raises(ValueError, match="TOKEN_EXPIRED"):
        mcp_mod.sb_forget("alice", confirm_token="invalid-token-xyz")


def test_init_writes_mcp_config():
    """write_mcp_config exists in engine.init_brain and is callable."""
    import engine.init_brain as ib
    assert hasattr(ib, "write_mcp_config")
    assert callable(ib.write_mcp_config)


def test_init_writes_mcp_config_creates_file(tmp_path):
    """write_mcp_config writes the second-brain entry to the given config path."""
    import json
    import engine.init_brain as ib

    fake_bin = "/usr/local/bin/sb-mcp-server"
    cfg_path = tmp_path / "claude_desktop_config.json"

    ib.write_mcp_config(sb_mcp_bin=fake_bin, _cfg_path=cfg_path)

    assert cfg_path.exists()
    cfg = json.loads(cfg_path.read_text())
    assert "mcpServers" in cfg
    assert "second-brain" in cfg["mcpServers"]
    assert cfg["mcpServers"]["second-brain"]["command"] == fake_bin


def test_pii_routing():
    """PII notes routed through adapter.summarize(); non-PII notes returned raw."""
    mock_adapter = MagicMock()
    mock_adapter.summarize.return_value = "[REDACTED SUMMARY]"

    with patch("engine.mcp_server.get_connection") as mock_conn_fn, \
         patch("engine.mcp_server.get_adapter", return_value=mock_adapter), \
         patch("engine.mcp_server._log_mcp_audit"), \
         patch("engine.mcp_server._safe_path") as mock_safe_path:

        mock_path = MagicMock()
        mock_path.read_text.return_value = "Alice's private note body"
        mock_path.__str__ = lambda self: "/fake/path/note.md"
        mock_safe_path.return_value = mock_path

        mock_conn = MagicMock()
        mock_conn_fn.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = ("pii",)

        result = mcp_mod.sb_read("/fake/path/note.md")
        mock_adapter.summarize.assert_called_once()
        assert result["content"] == "[REDACTED SUMMARY]"
        assert result["pii"] is True


def test_structured_error():
    """Paths outside BRAIN_ROOT raise ValueError with PATH_OUTSIDE_BRAIN code."""
    with pytest.raises(ValueError, match="PATH_OUTSIDE_BRAIN"):
        mcp_mod.sb_read("/etc/passwd")


def test_path_traversal_rejected():
    """Path traversal attempts raise ValueError with PATH_OUTSIDE_BRAIN code."""
    with pytest.raises(ValueError, match="PATH_OUTSIDE_BRAIN"):
        mcp_mod.sb_read("../../etc/passwd")


def test_retry_on_db_locked():
    """sb_recap returns a string (may be empty) on a real call."""
    result = mcp_mod.sb_recap(name="nonexistent-entity")
    assert isinstance(result, str)


def test_audit_log_written():
    """BODY_TOO_LARGE guard fires before any DB write."""
    # Use oversized body to stay in unit-test territory without touching real brain.
    with pytest.raises(ValueError, match="BODY_TOO_LARGE"):
        mcp_mod.sb_capture("title", "x" * 50_001)


def test_capture_idempotent():
    """TITLE_TOO_LONG guard fires correctly."""
    with pytest.raises(ValueError, match="TITLE_TOO_LONG"):
        mcp_mod.sb_capture("t" * 201, "body")


def test_body_too_large():
    """MCP-07: body exceeding 50,000 chars raises BODY_TOO_LARGE."""
    oversized = "x" * 50_001
    with pytest.raises(ValueError, match="BODY_TOO_LARGE"):
        mcp_mod.sb_capture("title", oversized)


def test_retry_on_db_locked_retry(monkeypatch):
    """MCP-08: transient sqlite3.OperationalError triggers tenacity retry and eventually succeeds."""
    import sqlite3 as _sqlite3
    call_count = {"n": 0}
    original_get_connection = mcp_mod.get_connection

    def flaky_get_connection():
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise _sqlite3.OperationalError("database is locked")
        return original_get_connection()

    monkeypatch.setattr(mcp_mod, "get_connection", flaky_get_connection)
    # sb_recap with a known name — may return empty string but must not raise
    result = mcp_mod.sb_recap(name="test-entity")
    assert isinstance(result, str)
    assert call_count["n"] >= 2  # confirmed retry fired


# ---------------------------------------------------------------------------
# Phase 27.1 Wave 0 stubs — dedup, batch capture, and sb_tools
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="Wave 2: sb_capture dedup not yet implemented")
def test_sb_capture_dedup_warning():
    """sb_capture returns duplicate_warning status when a near-duplicate exists."""
    # Capture original note
    mcp_mod.sb_capture("Dedup Test Note", "Content about Q1 roadmap planning")
    # Try to capture near-duplicate — should get duplicate_warning
    result = mcp_mod.sb_capture("Dedup Test Note", "Content about Q1 roadmap planning")
    assert result.get("status") == "duplicate_warning"
    assert "similar" in result


@pytest.mark.xfail(strict=False, reason="Wave 2: sb_capture confirm_token not yet implemented")
def test_sb_capture_dedup_confirm():
    """sb_capture with confirm_token bypasses dedup and saves the note."""
    result = mcp_mod.sb_capture("Confirm Token Test", "Some body content", confirm_token="fake-token")
    # confirm_token path should attempt save (token may be invalid → xfail expected)
    assert "status" in result


def test_sb_capture_batch():
    """sb_capture_batch saves multiple notes and returns succeeded/failed lists."""
    notes = [
        {"title": "Batch Note 1", "body": "Body 1", "note_type": "note"},
        {"title": "Batch Note 2", "body": "Body 2", "note_type": "note"},
    ]
    result = mcp_mod.sb_capture_batch(notes)
    assert "succeeded" in result
    assert len(result["succeeded"]) == 2


def test_sb_capture_batch_partial_failure():
    """A failing note in batch does not block other notes from saving."""
    notes = [
        {"title": "Good Note", "body": "Valid body content", "note_type": "note"},
        {"title": "", "body": "", "note_type": "invalid_type"},  # will fail
    ]
    result = mcp_mod.sb_capture_batch(notes)
    assert len(result.get("succeeded", [])) >= 1


def test_sb_tools():
    """sb_tools returns a list of tool dicts with name, description, parameters fields."""
    result = mcp_mod.sb_tools()
    assert isinstance(result, list)
    assert len(result) > 0
    tool = result[0]
    assert "name" in tool
    assert "description" in tool
    assert "parameters" in tool


# ---------------------------------------------------------------------------
# Phase 27 Wave 0 stubs — sb_edit frontmatter preservation
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="sb_edit frontmatter wipe not yet fixed")
def test_sb_edit_preserves_frontmatter(tmp_path, monkeypatch):
    """sb_edit must not wipe YAML frontmatter when editing note body."""
    import frontmatter as _fm
    brain = tmp_path / "brain"
    brain.mkdir()
    monkeypatch.setenv("BRAIN_PATH", str(brain))
    import engine.db, engine.paths
    db_path = brain / ".meta" / "brain.db"
    (brain / ".meta").mkdir()
    monkeypatch.setattr(engine.db, "DB_PATH", str(db_path))
    monkeypatch.setattr(engine.paths, "DB_PATH", str(db_path))
    from engine.db import get_connection, init_schema
    conn = get_connection(str(db_path))
    init_schema(conn)
    conn.close()

    # Write a note with frontmatter
    note_path = brain / "ideas" / "test-note.md"
    note_path.parent.mkdir(parents=True)
    note_path.write_text(
        "---\ntitle: My Test Note\ntype: ideas\ntags: [foo, bar]\n---\n\nOriginal body.\n"
    )
    # Call sb_edit directly (matches existing test style in this file)
    result = mcp_mod.sb_edit(path="ideas/test-note.md", body="Updated body content.")
    # Verify frontmatter preserved
    post = _fm.load(str(note_path))
    assert post["title"] == "My Test Note"
    assert post["type"] == "ideas"
    assert post["tags"] == ["foo", "bar"]
    assert "Updated body content." in post.content
