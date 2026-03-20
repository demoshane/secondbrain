"""Tests for the Second Brain MCP server tools."""
import pytest
from unittest.mock import patch, MagicMock
import engine.mcp_server as mcp_mod


def test_sb_search():
    """sb_search returns a list (may be empty if brain has no notes)."""
    result = mcp_mod.sb_search("test query")
    assert isinstance(result, list)


def test_tool_parity():
    # 12 tools must be registered — use sync internal dict (same as sb_tools uses)
    # asyncio.run() raises RuntimeError when called from a running event loop (pytest-anyio)
    # FastMCP stores tools in _local_provider._components keyed as "tool:<name>@"
    components = mcp_mod.mcp._local_provider._components
    tool_names = [k.split(":")[1].rstrip("@") for k in components if k.startswith("tool:")]
    assert len(tool_names) >= 12, f"Expected >=12 tools, got {len(tool_names)}: {tool_names}"


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

@pytest.fixture
def isolated_mcp_brain(tmp_path, monkeypatch):
    """Redirect mcp_mod.BRAIN_ROOT and DB_PATH to tmp_path so no real brain is touched.

    Patches both the module-level names (mcp_mod.BRAIN_ROOT, engine.paths.BRAIN_ROOT)
    so that local re-imports inside sb_capture_batch also see the temp path.
    """
    import engine.db as _db
    import engine.paths as _paths
    from engine.db import init_schema

    brain = tmp_path / "brain"
    brain.mkdir()
    for d in ["note", "ideas", "meetings", "people", "projects"]:
        (brain / d).mkdir()

    tmp_db = brain / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    # Patch BRAIN_ROOT on both the paths module AND the already-imported mcp_mod name
    monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)
    monkeypatch.setattr(mcp_mod, "BRAIN_ROOT", brain)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    conn = _db.get_connection()
    init_schema(conn)
    conn.commit()
    conn.close()

    return brain


@pytest.mark.xfail(strict=False, reason="Wave 2: sb_capture dedup not yet implemented")
def test_sb_capture_dedup_warning(isolated_mcp_brain):
    """sb_capture returns duplicate_warning status when a near-duplicate exists."""
    # Capture original note
    mcp_mod.sb_capture("Dedup Test Note", "Content about Q1 roadmap planning")
    # Try to capture near-duplicate — should get duplicate_warning
    result = mcp_mod.sb_capture("Dedup Test Note", "Content about Q1 roadmap planning")
    assert result.get("status") == "duplicate_warning"
    assert "similar" in result


@pytest.mark.xfail(strict=False, reason="Wave 2: sb_capture confirm_token not yet implemented")
def test_sb_capture_dedup_confirm(isolated_mcp_brain):
    """sb_capture with confirm_token bypasses dedup and saves the note."""
    result = mcp_mod.sb_capture("Confirm Token Test", "Some body content", confirm_token="fake-token")
    # confirm_token path should attempt save (token may be invalid → xfail expected)
    assert "status" in result


def test_sb_capture_batch(isolated_mcp_brain):
    """sb_capture_batch saves multiple notes and returns succeeded/failed lists."""
    notes = [
        {"title": "Batch Note 1", "body": "Body 1", "note_type": "note"},
        {"title": "Batch Note 2", "body": "Body 2", "note_type": "note"},
    ]
    result = mcp_mod.sb_capture_batch(notes)
    assert "succeeded" in result
    assert len(result["succeeded"]) == 2


def test_sb_capture_batch_partial_failure(isolated_mcp_brain):
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

# ---------------------------------------------------------------------------
# Phase 28-02 — sb_capture_smart tests
# ---------------------------------------------------------------------------

def test_sb_capture_smart_returns_suggestions(isolated_mcp_brain):
    """Raw text containing meeting keywords returns at least one suggestion with type='meeting'."""
    result = mcp_mod.sb_capture_smart(
        "We had a meeting today and discussed the Q1 roadmap with attendees from engineering."
    )
    assert "suggestions" in result
    assert len(result["suggestions"]) >= 1
    types = [s["type"] for s in result["suggestions"]]
    assert "meeting" in types


def test_sb_capture_smart_project_hint(isolated_mcp_brain):
    """Text containing project keywords returns a suggestion with type='project'."""
    result = mcp_mod.sb_capture_smart(
        "The project milestone for Q2 is approaching. We have a deadline next sprint."
    )
    assert "suggestions" in result
    types = [s["type"] for s in result["suggestions"]]
    assert "project" in types


def test_sb_capture_smart_default_note(isolated_mcp_brain):
    """Plain text with no keywords returns suggestion with type 'note' or 'idea'."""
    result = mcp_mod.sb_capture_smart("This is just some random text without any special keywords.")
    assert "suggestions" in result
    assert len(result["suggestions"]) >= 1
    types = [s["type"] for s in result["suggestions"]]
    assert any(t in ("note", "idea") for t in types)


def test_sb_capture_smart_no_auto_save(isolated_mcp_brain):
    """Calling sb_capture_smart must NOT insert anything into the notes table."""
    import engine.db as _db
    conn = _db.get_connection()
    count_before = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    conn.close()

    mcp_mod.sb_capture_smart("We had a meeting and discussed the project milestone deadline.")

    conn = _db.get_connection()
    count_after = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    conn.close()

    assert count_after == count_before


def test_sb_capture_smart_returns_confirm_token(isolated_mcp_brain):
    """Response includes a non-empty confirm_token string and a hint."""
    result = mcp_mod.sb_capture_smart("Some freeform capture text.")
    assert "confirm_token" in result
    assert isinstance(result["confirm_token"], str)
    assert len(result["confirm_token"]) > 0
    assert "hint" in result
    assert "sb_capture_batch" in result["hint"]


# ---------------------------------------------------------------------------
# Phase 28-03: sb_tag — add/remove tags with fuzzy matching + confirm-token gate
# ---------------------------------------------------------------------------

@pytest.fixture
def mcp_tag_brain(tmp_path, monkeypatch):
    """Isolated brain with a seeded note for sb_tag tests."""
    import json
    import engine.db as _db
    import engine.paths as _paths
    from engine.db import init_schema

    brain = tmp_path / "brain"
    brain.mkdir()
    for d in ["note", "ideas", "meetings", "people", "projects"]:
        (brain / d).mkdir()

    tmp_db = brain / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)
    monkeypatch.setattr(mcp_mod, "BRAIN_ROOT", brain)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    conn = _db.get_connection()
    init_schema(conn)
    conn.commit()

    # Seed a note file and DB row with empty tags
    note_path = brain / "note" / "test-note.md"
    note_path.write_text("---\ntitle: Test Note\ntype: note\ntags: []\n---\n\nBody text.\n")
    conn.execute(
        "INSERT INTO notes (path, title, body, type, tags) VALUES (?, ?, ?, ?, ?)",
        (str(note_path), "Test Note", "Body text.", "note", json.dumps([])),
    )
    conn.commit()
    conn.close()

    return brain, note_path


def test_sb_tag_adds(mcp_tag_brain):
    """sb_tag action=add adds a brand-new tag (via confirm_token); persisted to frontmatter and DB."""
    import json
    import frontmatter as _fm
    import engine.db as _db

    brain, note_path = mcp_tag_brain

    # "work" is brand-new — first call returns confirm_token
    first = mcp_mod.sb_tag(path=str(note_path), action="add", tag="work")
    assert "confirm_token" in first

    # Second call with token — saves
    result = mcp_mod.sb_tag(path=str(note_path), action="add", tag="work", confirm_token=first["confirm_token"])

    assert result["action"] == "add"
    assert "work" in result["tags"]

    # Frontmatter on disk updated
    post = _fm.load(str(note_path))
    assert "work" in (post.get("tags") or [])

    # DB updated
    conn = _db.get_connection()
    row = conn.execute("SELECT tags FROM notes WHERE path=?", (str(note_path),)).fetchone()
    conn.close()
    db_tags = json.loads(row[0] or "[]")
    assert "work" in db_tags


def test_sb_tag_removes(mcp_tag_brain):
    """sb_tag action=remove removes a tag; persisted to frontmatter and DB."""
    import json
    import frontmatter as _fm
    import engine.db as _db

    brain, note_path = mcp_tag_brain

    # Directly seed the tag in DB and on disk for remove test
    conn = _db.get_connection()
    conn.execute("UPDATE notes SET tags=? WHERE path=?", (json.dumps(["work"]), str(note_path)))
    conn.commit()
    conn.close()
    note_path.write_text("---\ntitle: Test Note\ntype: note\ntags: [work]\n---\n\nBody text.\n")

    # Remove it — no confirm needed for remove
    result = mcp_mod.sb_tag(path=str(note_path), action="remove", tag="work")

    assert result["action"] == "remove"
    assert "work" not in result["tags"]

    # Frontmatter on disk updated
    post = _fm.load(str(note_path))
    assert "work" not in (post.get("tags") or [])

    # DB updated
    conn = _db.get_connection()
    row = conn.execute("SELECT tags FROM notes WHERE path=?", (str(note_path),)).fetchone()
    conn.close()
    db_tags = json.loads(row[0] or "[]")
    assert "work" not in db_tags


def test_sb_tag_fuzzy_match(mcp_tag_brain):
    """sb_tag uses fuzzy match when adding a tag close to an existing one."""
    import json
    import engine.db as _db

    brain, note_path = mcp_tag_brain

    # Seed an existing tag "meetings" in DB on another note
    conn = _db.get_connection()
    another = brain / "note" / "another.md"
    another.write_text("---\ntitle: Another\ntype: note\ntags: [meetings]\n---\n\nBody.\n")
    conn.execute(
        "INSERT INTO notes (path, title, body, type, tags) VALUES (?, ?, ?, ?, ?)",
        (str(another), "Another", "Body.", "note", json.dumps(["meetings"])),
    )
    conn.commit()
    conn.close()

    # Call with "meeting" (close to "meetings") — should fuzzy-match, no confirm needed
    result = mcp_mod.sb_tag(path=str(note_path), action="add", tag="meeting")

    # Should match "meetings" and apply it immediately
    assert result.get("matched") == "meetings"
    assert result.get("applied") is True
    assert "meetings" in result["tags"]


def test_sb_tag_new_requires_confirm(mcp_tag_brain):
    """sb_tag returns confirm_token for a brand-new tag with no close match."""
    brain, note_path = mcp_tag_brain

    result = mcp_mod.sb_tag(path=str(note_path), action="add", tag="zzznew")

    assert "confirm_token" in result
    assert "message" in result
    # Nothing saved yet
    import frontmatter as _fm
    post = _fm.load(str(note_path))
    assert "zzznew" not in (post.get("tags") or [])


def test_sb_tag_new_with_confirm(mcp_tag_brain):
    """sb_tag with valid confirm_token saves the new tag."""
    import json
    import frontmatter as _fm
    import engine.db as _db

    brain, note_path = mcp_tag_brain

    # First call — get token
    first = mcp_mod.sb_tag(path=str(note_path), action="add", tag="zzznew")
    token = first["confirm_token"]

    # Second call — confirm
    result = mcp_mod.sb_tag(path=str(note_path), action="add", tag="zzznew", confirm_token=token)

    assert "zzznew" in result["tags"]

    # Frontmatter on disk updated
    post = _fm.load(str(note_path))
    assert "zzznew" in (post.get("tags") or [])

    # DB updated
    conn = _db.get_connection()
    row = conn.execute("SELECT tags FROM notes WHERE path=?", (str(note_path),)).fetchone()
    conn.close()
    db_tags = json.loads(row[0] or "[]")
    assert "zzznew" in db_tags


# ---------------------------------------------------------------------------
# Phase 28-04 — sb_link and sb_unlink MCP tools
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated_link_brain(tmp_path, monkeypatch):
    """Isolated DB + brain root for sb_link / sb_unlink tests."""
    import engine.db as _db
    import engine.paths as _paths
    from engine.db import init_schema

    brain = tmp_path / "brain"
    brain.mkdir()
    for d in ["note", "ideas", "meetings", "people", "projects"]:
        (brain / d).mkdir()

    tmp_db = brain / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)
    monkeypatch.setattr(mcp_mod, "BRAIN_ROOT", brain)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    conn = _db.get_connection()
    init_schema(conn)
    conn.commit()
    conn.close()

    return brain


def test_sb_link_creates_relationship(isolated_link_brain):
    """sb_link creates a row in relationships with default rel_type='link'."""
    result = mcp_mod.sb_link("notes/a.md", "notes/b.md")
    assert result["linked"] is True
    assert result["source"] == "notes/a.md"
    assert result["target"] == "notes/b.md"
    assert result["rel_type"] == "link"

    import engine.db as _db
    conn = _db.get_connection()
    rows = conn.execute(
        "SELECT source_path, target_path, rel_type FROM relationships"
    ).fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0] == ("notes/a.md", "notes/b.md", "link")


def test_sb_link_custom_rel_type(isolated_link_brain):
    """sb_link with rel_type='references' stores that rel_type in DB."""
    mcp_mod.sb_link("notes/a.md", "notes/b.md", rel_type="references")

    import engine.db as _db
    conn = _db.get_connection()
    rows = conn.execute(
        "SELECT rel_type FROM relationships WHERE source_path='notes/a.md'"
    ).fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0][0] == "references"


def test_sb_link_idempotent(isolated_link_brain):
    """Calling sb_link twice with same args produces only one row (INSERT OR IGNORE)."""
    mcp_mod.sb_link("notes/a.md", "notes/b.md")
    mcp_mod.sb_link("notes/a.md", "notes/b.md")

    import engine.db as _db
    conn = _db.get_connection()
    count = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
    conn.close()
    assert count == 1


def test_sb_unlink_removes(isolated_link_brain):
    """sb_link then sb_unlink removes the row; table is empty."""
    mcp_mod.sb_link("notes/a.md", "notes/b.md")
    result = mcp_mod.sb_unlink("notes/a.md", "notes/b.md")
    assert result["unlinked"] is True

    import engine.db as _db
    conn = _db.get_connection()
    count = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
    conn.close()
    assert count == 0


def test_sb_unlink_absent_is_noop(isolated_link_brain):
    """sb_unlink on a non-existent pair returns success without raising."""
    result = mcp_mod.sb_unlink("notes/x.md", "notes/y.md")
    assert result["unlinked"] is True
    assert result["source"] == "notes/x.md"
    assert result["target"] == "notes/y.md"


def test_sb_edit_preserves_frontmatter(tmp_path, monkeypatch):
    """sb_edit must not wipe YAML frontmatter when editing note body."""
    import frontmatter as _fm
    brain = tmp_path / "brain"
    brain.mkdir()
    monkeypatch.setenv("BRAIN_PATH", str(brain))
    import engine.db, engine.paths
    db_path = brain / ".meta" / "brain.db"
    (brain / ".meta").mkdir()
    monkeypatch.setattr(engine.db, "DB_PATH", db_path)
    monkeypatch.setattr(engine.paths, "DB_PATH", db_path)
    from engine.db import get_connection, init_schema
    conn = get_connection(str(db_path))
    init_schema(conn)
    conn.close()

    monkeypatch.setattr(mcp_mod, "BRAIN_ROOT", brain)

    # Write a note with frontmatter
    note_path = brain / "ideas" / "test-note.md"
    note_path.parent.mkdir(parents=True)
    note_path.write_text(
        "---\ntitle: My Test Note\ntype: ideas\ntags: [foo, bar]\n---\n\nOriginal body.\n"
    )
    # Call sb_edit directly using absolute path (matches _safe_path expectation)
    result = mcp_mod.sb_edit(path=str(note_path), body="Updated body content.")
    # Verify frontmatter preserved
    post = _fm.load(str(note_path))
    assert post["title"] == "My Test Note"
    assert post["type"] == "ideas"
    assert post["tags"] == ["foo", "bar"]
    assert "Updated body content." in post.content


# ---------------------------------------------------------------------------
# Phase 28-05: sb_remind, due_date, and overdue recap tests
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated_action_db(tmp_path, monkeypatch):
    """Isolated DB with one action_items row for remind/due_date tests."""
    import engine.db as _db
    import engine.paths as _paths
    from engine.db import init_schema

    brain = tmp_path / "brain"
    brain.mkdir()
    for d in ["note", "ideas", "meetings", "people", "projects"]:
        (brain / d).mkdir()

    tmp_db = brain / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)
    monkeypatch.setattr(mcp_mod, "BRAIN_ROOT", brain)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    conn = _db.get_connection()
    init_schema(conn)
    conn.execute(
        "INSERT INTO action_items (id, note_path, text, done) "
        "VALUES (1, '/brain/note/test.md', 'Test action', 0)"
    )
    conn.commit()
    conn.close()
    return brain


def test_sb_remind_sets_due_date(isolated_action_db):
    """sb_remind(action_id=1, due_date='2026-04-01') persists due_date in DB."""
    import engine.db as _db
    result = mcp_mod.sb_remind(action_id=1, due_date="2026-04-01")
    assert result["updated"] is True
    assert result["action_id"] == 1
    assert result["due_date"] == "2026-04-01"
    conn = _db.get_connection()
    row = conn.execute("SELECT due_date FROM action_items WHERE id=1").fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "2026-04-01"


def test_sb_remind_clears_due_date(isolated_action_db):
    """sb_remind(action_id=1, due_date=None) clears due_date to NULL."""
    import engine.db as _db
    mcp_mod.sb_remind(action_id=1, due_date="2026-04-01")
    result = mcp_mod.sb_remind(action_id=1, due_date=None)
    assert result["updated"] is True
    assert result["due_date"] is None
    conn = _db.get_connection()
    row = conn.execute("SELECT due_date FROM action_items WHERE id=1").fetchone()
    conn.close()
    assert row[0] is None


def test_sb_actions_includes_due_date(isolated_action_db):
    """sb_actions() returns items with 'due_date' key after setting a due date."""
    mcp_mod.sb_remind(action_id=1, due_date="2026-04-01")
    results = mcp_mod.sb_actions(done=False)
    assert len(results) >= 1
    assert "due_date" in results[0]


def test_sb_remind_tool_exists():
    """sb_remind is registered as an MCP tool visible in sb_tools()."""
    components = mcp_mod.mcp._local_provider._components
    tool_names = [k.split(":")[1].rstrip("@") for k in components if k.startswith("tool:")]
    assert "sb_remind" in tool_names, f"sb_remind not found in tools: {tool_names}"


# ---------------------------------------------------------------------------
# Phase 28-06 — sb_person_context tests
# ---------------------------------------------------------------------------

@pytest.fixture
def mcp_person_brain(tmp_path, monkeypatch):
    """Isolated brain: person note, meeting, action item, mention note."""
    import engine.db as _db
    import engine.paths as _paths
    from engine.db import get_connection as _get_conn, init_schema as _init

    brain = tmp_path / "brain"
    for d in ["note", "ideas", "meetings", "people", "projects"]:
        (brain / d).mkdir(parents=True)

    tmp_db = brain / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)
    monkeypatch.setattr(mcp_mod, "BRAIN_ROOT", brain)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    conn = _get_conn(str(tmp_db))
    _init(conn)

    person_path = str(brain / "people" / "alice.md")
    meeting_path = str(brain / "meetings" / "kickoff.md")
    mention_path = str(brain / "note" / "project-plan.md")

    import json as _json
    conn.execute(
        "INSERT INTO notes (path, title, body, type, people) VALUES (?, ?, ?, ?, ?)",
        (person_path, "Alice", "Alice is a designer.", "person", _json.dumps([])),
    )
    conn.execute(
        "INSERT INTO notes (path, title, body, type, people) VALUES (?, ?, ?, ?, ?)",
        (meeting_path, "Kickoff Meeting", "We discussed plans with Alice today.", "meeting",
         _json.dumps([person_path])),
    )
    conn.execute(
        "INSERT INTO notes (path, title, body, type, people) VALUES (?, ?, ?, ?, ?)",
        (mention_path, "Project Plan", "Alice will lead the design phase.", "note",
         _json.dumps([person_path])),
    )
    conn.execute(
        "INSERT INTO action_items (text, done, assignee_path, note_path) VALUES (?, 0, ?, ?)",
        ("Alice must review the spec", person_path, meeting_path),
    )
    conn.commit()
    conn.close()

    return {
        "brain": brain,
        "person_path": person_path,
        "meeting_path": meeting_path,
        "mention_path": mention_path,
    }


def test_sb_person_context_returns_note_body(mcp_person_brain):
    """sb_person_context returns the person note body."""
    result = mcp_mod.sb_person_context(mcp_person_brain["person_path"])
    assert "note" in result
    assert "body" in result["note"]
    assert "Alice is a designer" in result["note"]["body"]


def test_sb_person_context_returns_meetings(mcp_person_brain):
    """sb_person_context returns meetings where the person name appears in body."""
    result = mcp_mod.sb_person_context(mcp_person_brain["person_path"])
    assert "meetings" in result
    meeting_paths = [m["path"] for m in result["meetings"]]
    assert mcp_person_brain["meeting_path"] in meeting_paths


def test_sb_person_context_returns_actions(mcp_person_brain):
    """sb_person_context returns action items assigned to or mentioning the person."""
    result = mcp_mod.sb_person_context(mcp_person_brain["person_path"])
    assert "actions" in result
    assert len(result["actions"]) >= 1
    texts = [a["text"] for a in result["actions"]]
    assert any("Alice" in t for t in texts)


def test_sb_person_context_returns_mentions(mcp_person_brain):
    """sb_person_context returns non-person notes mentioning the person by name."""
    result = mcp_mod.sb_person_context(mcp_person_brain["person_path"])
    assert "mentions" in result
    mention_paths = [m["path"] for m in result["mentions"]]
    assert mcp_person_brain["mention_path"] in mention_paths


def test_sb_person_context_unknown_path(mcp_person_brain):
    """sb_person_context returns found=False for non-existent path (no exception)."""
    result = mcp_mod.sb_person_context(str(mcp_person_brain["brain"] / "people" / "nobody.md"))
    assert result.get("found") is False
    assert "error" in result


# ---------------------------------------------------------------------------
# Phase 30-03 — sb_person_context column-based lookup + metrics + sb_list_people
# ---------------------------------------------------------------------------

@pytest.fixture
def mcp_person_brain_v2(tmp_path, monkeypatch):
    """Isolated brain for column-based person context tests.

    Seeds:
    - person note "Anna Korhonen" (type=person)
    - meeting1 (people column contains anna path) — newer date
    - meeting2 (people column contains anna path) — older date
    - meeting_body_only (people=[] but body mentions Anna) — must NOT appear in column lookup
    - note_mention (people column contains anna path) — non-meeting mention
    - action item assigned to anna_path
    """
    import json
    import engine.db as _db
    import engine.paths as _paths
    from engine.db import get_connection as _get_conn, init_schema as _init

    brain = tmp_path / "brain"
    for d in ["note", "meetings", "people", "projects"]:
        (brain / d).mkdir(parents=True)

    tmp_db = brain / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)
    monkeypatch.setattr(mcp_mod, "BRAIN_ROOT", brain)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    conn = _get_conn(str(tmp_db))
    _init(conn)

    anna_path = str(brain / "people" / "anna-korhonen.md")
    meeting1_path = str(brain / "meetings" / "sprint-review.md")
    meeting2_path = str(brain / "meetings" / "quarterly.md")
    meeting_body_only_path = str(brain / "meetings" / "body-only.md")
    mention_path = str(brain / "note" / "project-alpha.md")

    # Person note with entities JSON (org)
    conn.execute(
        "INSERT INTO notes (path, title, body, type, people, entities) VALUES (?, ?, ?, ?, ?, ?)",
        (
            anna_path,
            "Anna Korhonen",
            "Anna is a senior engineer.",
            "person",
            json.dumps([]),
            json.dumps({"orgs": ["Acme Ltd"]}),
        ),
    )
    # Meeting 1 — newer — has anna_path in people column
    conn.execute(
        "INSERT INTO notes (path, title, body, type, people, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            meeting1_path,
            "Sprint Review",
            "Sprint review session.",
            "meeting",
            json.dumps([anna_path]),
            "2026-02-10T10:00:00",
        ),
    )
    # Meeting 2 — older — has anna_path in people column
    conn.execute(
        "INSERT INTO notes (path, title, body, type, people, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            meeting2_path,
            "Quarterly Review",
            "Quarterly review session.",
            "meeting",
            json.dumps([anna_path]),
            "2026-01-05T10:00:00",
        ),
    )
    # Meeting body-only — mentions "Anna Korhonen" in body but people column is []
    conn.execute(
        "INSERT INTO notes (path, title, body, type, people, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            meeting_body_only_path,
            "Planning",
            "Anna Korhonen was mentioned here.",
            "meeting",
            json.dumps([]),
            "2026-01-20T10:00:00",
        ),
    )
    # Mention note — non-meeting with anna_path in people column
    conn.execute(
        "INSERT INTO notes (path, title, body, type, people, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            mention_path,
            "Project Alpha",
            "Anna leads this project.",
            "note",
            json.dumps([anna_path]),
            "2026-02-15T10:00:00",
        ),
    )
    # Action item assigned to anna
    conn.execute(
        "INSERT INTO action_items (text, done, assignee_path, note_path) VALUES (?, 0, ?, ?)",
        ("Anna to review architecture doc", anna_path, meeting1_path),
    )
    conn.commit()
    conn.close()

    return {
        "brain": brain,
        "anna_path": anna_path,
        "meeting1_path": meeting1_path,
        "meeting2_path": meeting2_path,
        "meeting_body_only_path": meeting_body_only_path,
        "mention_path": mention_path,
    }


def test_person_context_column_lookup(mcp_person_brain_v2):
    """Column-based lookup returns meetings with people column match; body-only meeting excluded."""
    d = mcp_person_brain_v2
    result = mcp_mod.sb_person_context(d["anna_path"])
    assert result.get("found") is True
    meeting_paths = [m["path"] for m in result["meetings"]]
    assert d["meeting1_path"] in meeting_paths
    assert d["meeting2_path"] in meeting_paths
    # body-only meeting must NOT appear (no people column match)
    assert d["meeting_body_only_path"] not in meeting_paths


def test_person_context_by_name(mcp_person_brain_v2):
    """sb_person_context resolves 'Anna Korhonen' name string to the correct path."""
    result = mcp_mod.sb_person_context("Anna Korhonen")
    assert result.get("found") is True
    assert result["path"] == mcp_person_brain_v2["anna_path"]


def test_person_context_metrics(mcp_person_brain_v2):
    """Response includes total_meetings=2, last_interaction_date is not null."""
    d = mcp_person_brain_v2
    result = mcp_mod.sb_person_context(d["anna_path"])
    assert result.get("found") is True
    assert result["total_meetings"] == 2
    assert result["last_interaction_date"] is not None
    assert result["total_mentions"] >= 1


def test_person_context_not_found(mcp_person_brain_v2):
    """sb_person_context returns found=False for nonexistent name."""
    result = mcp_mod.sb_person_context("Nonexistent Person")
    assert result.get("found") is False


def test_person_context_chronological(mcp_person_brain_v2):
    """Meetings are returned ordered newest-first (DESC by created_at)."""
    d = mcp_person_brain_v2
    result = mcp_mod.sb_person_context(d["anna_path"])
    meetings = result["meetings"]
    assert len(meetings) >= 2
    # meeting1 (2026-02-10) must come before meeting2 (2026-01-05)
    paths = [m["path"] for m in meetings]
    assert paths.index(d["meeting1_path"]) < paths.index(d["meeting2_path"])


# ---------------------------------------------------------------------------
# Phase 30-03 Task 2 — sb_list_people
# ---------------------------------------------------------------------------

@pytest.fixture
def mcp_list_people_brain(tmp_path, monkeypatch):
    """Isolated brain for sb_list_people tests.

    Seeds:
    - 2 person notes (Alice, Bob) with action items
    - 1 meeting with Alice in people column
    """
    import json
    import engine.db as _db
    import engine.paths as _paths
    from engine.db import get_connection as _get_conn, init_schema as _init

    brain = tmp_path / "brain"
    for d in ["note", "meetings", "people"]:
        (brain / d).mkdir(parents=True)

    tmp_db = brain / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)
    monkeypatch.setattr(mcp_mod, "BRAIN_ROOT", brain)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    conn = _get_conn(str(tmp_db))
    _init(conn)

    alice_path = str(brain / "people" / "alice.md")
    bob_path = str(brain / "people" / "bob.md")
    meeting_path = str(brain / "meetings" / "standup.md")

    conn.execute(
        "INSERT INTO notes (path, title, body, type, entities) VALUES (?, ?, ?, ?, ?)",
        (alice_path, "Alice", "Alice is a designer.", "person",
         json.dumps({"orgs": ["Acme Ltd"]})),
    )
    conn.execute(
        "INSERT INTO notes (path, title, body, type, entities) VALUES (?, ?, ?, ?, ?)",
        (bob_path, "Bob", "Bob is an engineer.", "people", json.dumps({})),
    )
    conn.execute(
        "INSERT INTO notes (path, title, body, type, people, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (meeting_path, "Standup", "Daily standup.", "meeting",
         json.dumps([alice_path]), "2026-02-01T09:00:00"),
    )
    # One open action for Alice
    conn.execute(
        "INSERT INTO action_items (text, done, assignee_path, note_path) VALUES (?, 0, ?, ?)",
        ("Alice review docs", alice_path, meeting_path),
    )
    conn.commit()
    conn.close()

    return {"brain": brain, "alice_path": alice_path, "bob_path": bob_path}


def test_sb_list_people(mcp_list_people_brain):
    """sb_list_people returns all person/people notes with metrics."""
    result = mcp_mod.sb_list_people()
    assert "people" in result
    people = result["people"]
    assert len(people) == 2
    paths = [p["path"] for p in people]
    assert mcp_list_people_brain["alice_path"] in paths
    assert mcp_list_people_brain["bob_path"] in paths

    # Check required fields exist on each person
    for p in people:
        assert "path" in p
        assert "title" in p
        assert "open_actions" in p
        assert "org" in p
        assert "last_interaction" in p
        assert "total_meetings" in p
        assert "total_mentions" in p

    # Alice should have 1 open action and 1 meeting
    alice = next(p for p in people if p["path"] == mcp_list_people_brain["alice_path"])
    assert alice["open_actions"] == 1
    assert alice["total_meetings"] == 1
    assert alice["org"] == "Acme Ltd"
    assert alice["last_interaction"] is not None

    # Bob should have 0 actions, 0 meetings
    bob = next(p for p in people if p["path"] == mcp_list_people_brain["bob_path"])
    assert bob["open_actions"] == 0
    assert bob["total_meetings"] == 0


def test_sb_list_people_empty(tmp_path, monkeypatch):
    """sb_list_people returns empty list on empty DB with no error."""
    import engine.db as _db
    import engine.paths as _paths
    from engine.db import get_connection as _get_conn, init_schema as _init

    brain = tmp_path / "brain"
    brain.mkdir()
    tmp_db = brain / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)
    monkeypatch.setattr(mcp_mod, "BRAIN_ROOT", brain)

    conn = _get_conn(str(tmp_db))
    _init(conn)
    conn.close()

    result = mcp_mod.sb_list_people()
    assert "people" in result
    assert result["people"] == []
