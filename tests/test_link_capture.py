"""Tests for Phase 29 link capture — url column, metadata fetch, MCP tool, Flask API."""
import sqlite3
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _init_conn() -> sqlite3.Connection:
    from engine.db import init_schema
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    return conn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch, tmp_path):
    """Flask test client with isolated brain dir and SQLite DB."""
    import engine.db as _db
    import engine.paths as _paths
    from engine.api import app as flask_app
    from engine.db import init_schema, get_connection

    brain = tmp_path / "brain"
    brain.mkdir()
    for d in ["links", "note", "people"]:
        (brain / d).mkdir()

    tmp_db = Path(str(tmp_path / "test.db"))
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    conn = get_connection()
    init_schema(conn)
    conn.close()

    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c, brain


# ---------------------------------------------------------------------------
# Stubs — xfail(strict=False): auto-promote to PASS once Phase 29 ships
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="Phase 29 implementation not yet shipped")
def test_url_column_exists():
    """After init_schema on an in-memory DB, PRAGMA table_info(notes) includes a 'url' column."""
    conn = _init_conn()
    cols = [row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()]
    assert "url" in cols, f"'url' column missing from notes table; found: {cols}"


@pytest.mark.xfail(strict=False, reason="Phase 29 implementation not yet shipped")
def test_fetch_metadata_returns_title(monkeypatch):
    """fetch_link_metadata returns a dict with a non-empty 'title' key on success."""
    from engine import link_capture

    mock_html = (
        b"<html><head>"
        b'<meta property="og:title" content="Example OG Title">'
        b"<title>Example Title</title>"
        b"</head><body></body></html>"
    )

    import urllib.request

    class _FakeResp:
        def read(self, n=-1):
            return mock_html if n < 0 else mock_html[:n]

        def get_content_charset(self, default="utf-8"):
            return default

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: _FakeResp())

    result = link_capture.fetch_link_metadata("https://example.com")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "title" in result, f"'title' key missing from result: {result}"
    assert result["title"], f"title is empty; result={result}"


@pytest.mark.xfail(strict=False, reason="Phase 29 implementation not yet shipped")
def test_fetch_metadata_fallback_on_error(monkeypatch):
    """fetch_link_metadata returns domain-based fallback dict when HTTP fetch raises an error."""
    from engine import link_capture
    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: (_ for _ in ()).throw(OSError("Connection refused")))

    result = link_capture.fetch_link_metadata("https://unreachable.invalid/some/path")
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert result.get("title") == "unreachable.invalid", (
        f"Expected fallback title 'unreachable.invalid', got: {result.get('title')!r}"
    )
    assert result.get("description") == "", (
        f"Expected empty description on fallback, got: {result.get('description')!r}"
    )


@pytest.mark.xfail(strict=False, reason="Phase 29 implementation not yet shipped")
def test_sb_capture_link_registered():
    """sb_capture_link is present in the MCP server's registered tools."""
    import engine.mcp_server as mcp_mod
    components = mcp_mod.mcp._local_provider._components
    tool_names = [k.split(":")[1].rstrip("@") for k in components if k.startswith("tool:")]
    assert "sb_capture_link" in tool_names, (
        f"sb_capture_link not found in MCP tools: {tool_names}"
    )


@pytest.mark.xfail(strict=False, reason="Phase 29 implementation not yet shipped")
def test_links_api_returns_list(client):
    """GET /links returns HTTP 200 with JSON body containing a 'links' key."""
    c, _brain = client
    resp = c.get("/links")
    assert resp.status_code == 200, (
        f"Expected 200, got {resp.status_code}; body={resp.data[:200]}"
    )
    data = resp.get_json()
    assert data is not None, "Response body was not valid JSON"
    assert "links" in data, f"'links' key missing from response: {data}"
    assert isinstance(data["links"], list), (
        f"'links' value should be a list, got {type(data['links'])}"
    )


@pytest.mark.xfail(strict=False, reason="Phase 29 implementation not yet shipped")
def test_capture_link_duplicate_warn(monkeypatch, tmp_path):
    """Capturing the same URL twice returns status='duplicate_url_warning' on the second call."""
    import engine.db as _db
    import engine.paths as _paths
    from engine.db import init_schema, get_connection

    brain = tmp_path / "brain"
    brain.mkdir()
    (brain / "links").mkdir()

    tmp_db = Path(str(tmp_path / "dedup.db"))
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    conn = get_connection()
    init_schema(conn)
    conn.close()

    # Patch fetch so tests run offline
    from engine import link_capture
    monkeypatch.setattr(
        link_capture,
        "fetch_link_metadata",
        lambda url: {"title": "Test Page", "description": "A test page.", "domain": "example.com"},
    )

    import engine.mcp_server as mcp_mod
    monkeypatch.setattr(mcp_mod, "BRAIN_ROOT", brain)

    url = "https://example.com/test-duplicate"
    mcp_mod.sb_capture_link(url=url)
    result2 = mcp_mod.sb_capture_link(url=url)

    assert result2.get("status") == "duplicate_url_warning", (
        f"Expected 'duplicate_url_warning' on second capture, got: {result2}"
    )
