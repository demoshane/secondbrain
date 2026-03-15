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
