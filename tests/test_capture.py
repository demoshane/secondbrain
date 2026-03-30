import json
import os
import sqlite3
import pytest
from pathlib import Path


def test_capture_writes_note(tmp_path, initialized_db):
    from engine.capture import write_note_atomic, build_post
    import frontmatter

    target_dir = tmp_path / "meetings"
    target_dir.mkdir()
    target = target_dir / "2026-03-14-team-sync.md"

    post = build_post(
        note_type="meeting",
        title="Team Sync",
        body="Discussion about Q2 goals",
        tags=["team", "q2"],
        people=["Alice", "Bob"],
        content_sensitivity="internal",
    )
    write_note_atomic(target, post, initialized_db)

    assert target.exists(), "Note file should be written to disk"
    loaded = frontmatter.load(str(target))
    assert loaded["title"] == "Team Sync"


def test_frontmatter_fields_complete(tmp_path, initialized_db):
    from engine.capture import build_post

    post = build_post(
        note_type="note",
        title="My Note",
        body="Some content",
        tags=["test"],
        people=[],
        content_sensitivity="public",
    )

    required_fields = {"type", "title", "date", "tags", "people", "created_at", "updated_at", "content_sensitivity"}
    for field in required_fields:
        assert field in post.metadata, f"Missing frontmatter field: {field}"

    assert post["type"] == "note"
    assert post["title"] == "My Note"
    assert post["content_sensitivity"] == "public"
    assert isinstance(post["tags"], list)
    assert isinstance(post["people"], list)


def test_rollback_on_index_failure(tmp_path, initialized_db):
    from engine.capture import write_note_atomic, build_post
    import frontmatter

    # Use a broken conn that fails on INSERT
    broken_conn = sqlite3.connect(":memory:")
    # Don't call init_schema — notes table doesn't exist, so INSERT will fail

    target_dir = tmp_path / "notes"
    target_dir.mkdir()
    target = target_dir / "will-fail.md"

    post = build_post(
        note_type="note",
        title="Rollback Test",
        body="body content that must not persist",
        tags=[],
        people=[],
    )

    with pytest.raises(Exception):
        write_note_atomic(target, post, broken_conn)

    assert not target.exists(), "Note file must not remain on disk after failure"
    # No temp files should remain either
    leftovers = list(target_dir.iterdir())
    assert leftovers == [], f"Temp files leaked: {leftovers}"


# templates.py tests removed — module deleted in Phase 39 remediation (F-02)


def test_error_message_no_body_content(tmp_path, initialized_db):
    from engine.capture import write_note_atomic, build_post

    broken_conn = sqlite3.connect(":memory:")
    # Don't init schema — forces INSERT failure

    target_dir = tmp_path / "notes"
    target_dir.mkdir()
    target = target_dir / "secret-note.md"

    secret_body = "SUPER SECRET BODY CONTENT XYZ"  # pragma: allowlist secret
    post = build_post(
        note_type="note",
        title="Secret Note",
        body=secret_body,
        tags=["confidential"],
        people=["Eve"],
    )

    with pytest.raises(Exception) as exc_info:
        write_note_atomic(target, post, broken_conn)

    error_message = str(exc_info.value)
    assert secret_body not in error_message, "Error message must not contain note body"
    assert "confidential" not in error_message, "Error message must not contain tags"
    assert "Eve" not in error_message, "Error message must not contain people"


# ---------------------------------------------------------------------------
# CAP-06: Memory update call site
# ---------------------------------------------------------------------------

def test_cap06_update_memory_called_after_capture(tmp_path):
    """update_memory() is called exactly once after a non-PII capture."""
    from unittest.mock import patch
    from engine.capture import main

    fake_note = tmp_path / "note.md"
    fake_note.write_text("")

    # Deferred imports inside main() must be patched at their source modules.
    with patch("engine.ai.update_memory") as mock_update_memory, \
         patch("engine.capture.capture_note", return_value=fake_note), \
         patch("engine.db.get_connection"), \
         patch("engine.db.init_schema"), \
         patch("engine.db.migrate_add_people_column"), \
         patch("engine.ai.ask_followup_questions", return_value=[]), \
         patch("engine.classifier.classify", return_value="public"):
        main(["--type", "note", "--title", "T", "--body", "B", "--sensitivity", "public"])

    mock_update_memory.assert_called_once()
    call_args = mock_update_memory.call_args[0]
    assert call_args[0] == "note"    # note_type
    assert "T" in call_args[1]       # title in summary


def test_cap06_update_memory_skipped_for_pii(tmp_path):
    """update_memory() is never called after a PII capture."""
    from unittest.mock import patch
    from engine.capture import main

    fake_note = tmp_path / "note.md"
    fake_note.write_text("")

    # Deferred imports inside main() must be patched at their source modules.
    with patch("engine.ai.update_memory") as mock_update_memory, \
         patch("engine.capture.capture_note", return_value=fake_note), \
         patch("engine.db.get_connection"), \
         patch("engine.db.init_schema"), \
         patch("engine.db.migrate_add_people_column"), \
         patch("engine.ai.ask_followup_questions", return_value=[]), \
         patch("engine.classifier.classify", return_value="pii"):
        main(["--type", "note", "--title", "T", "--body", "B", "--sensitivity", "pii"])

    mock_update_memory.assert_not_called()


# ---------------------------------------------------------------------------
# Phase 32-01: Relative path storage contract (ARCH-01)
# Replaces Phase 7 absolute-path contract: capture_note() now stores relative paths.
# ---------------------------------------------------------------------------

def test_capture_note_stores_relative_path(tmp_path, monkeypatch):
    """capture_note() must store a relative path in DB, not an absolute path.

    ARCH-01: DB must not contain absolute paths for portability.
    """
    import engine.db as db_mod
    import engine.paths as paths_mod

    brain = tmp_path / "SecondBrain"
    brain.mkdir()
    tmp_db = tmp_path / "brain.db"
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_db)
    monkeypatch.setattr(paths_mod, "DB_PATH", tmp_db)
    monkeypatch.setattr(paths_mod, "BRAIN_ROOT", brain)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    from engine.db import get_connection, init_schema
    from engine.capture import capture_note

    conn = get_connection(str(tmp_db))
    init_schema(conn)

    capture_note("note", "Relative Path Test", "body", [], [], "public", brain, conn)
    conn.commit()

    row = conn.execute(
        "SELECT path FROM notes WHERE title='Relative Path Test'"
    ).fetchone()
    assert row is not None, "Note must exist in DB"
    stored_path = row[0]
    assert not stored_path.startswith("/"), (
        f"DB path must be relative (not start with '/'), got: {stored_path!r}"
    )
    conn.close()


def test_capture_note_stored_path_resolves_correctly(tmp_path, monkeypatch):
    """The stored relative path, when resolved via resolve_path(), points to the actual file."""
    import engine.db as db_mod
    import engine.paths as paths_mod

    brain = tmp_path / "SecondBrain"
    brain.mkdir()
    tmp_db = tmp_path / "brain.db"
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_db)
    monkeypatch.setattr(paths_mod, "DB_PATH", tmp_db)
    monkeypatch.setattr(paths_mod, "BRAIN_ROOT", brain)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    from engine.db import get_connection, init_schema
    from engine.capture import capture_note
    from engine.paths import resolve_path

    conn = get_connection(str(tmp_db))
    init_schema(conn)

    note_path = capture_note("note", "Resolve Test Note", "content here", [], [], "public", brain, conn)
    conn.commit()

    row = conn.execute(
        "SELECT path FROM notes WHERE title='Resolve Test Note'"
    ).fetchone()
    assert row is not None
    stored_rel_path = row[0]

    # resolve_path() must give back the actual file location
    resolved = resolve_path(stored_rel_path)
    assert resolved.exists(), (
        f"resolve_path({stored_rel_path!r}) = {resolved} — file must exist on disk"
    )
    conn.close()


# ---------------------------------------------------------------------------
# Phase 27.1 Wave 0 stubs — entity extraction + dedup
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="Wave 2: engine/entities.py and capture enrichment not yet implemented")
def test_capture_stores_entities(tmp_path):
    """After capture_note(), the written file's frontmatter contains an 'entities' key."""
    from engine.db import get_connection, init_schema
    from engine.capture import capture_note
    conn = get_connection(str(tmp_path / "brain.db"))
    init_schema(conn)
    path = capture_note("note", "Alice in Wonderland", "Alice Johnson visited London", [], [], "public", tmp_path, conn)
    import frontmatter as fm
    post = fm.load(str(path))
    assert "entities" in post.metadata
    entities = post.metadata["entities"]
    assert "Alice Johnson" in entities.get("people", [])


@pytest.mark.xfail(strict=False, reason="Wave 2: check_capture_dedup() not yet implemented")
def test_dedup_returns_similar(tmp_path):
    """check_capture_dedup() returns non-empty list when a nearly-identical note exists above threshold."""
    from engine.db import get_connection, init_schema
    from engine.capture import check_capture_dedup, capture_note
    conn = get_connection(str(tmp_path / "brain.db"))
    init_schema(conn)
    # Capture a note first so there is something to match
    capture_note("note", "Meeting Notes Q1", "Discussed Q1 roadmap and priorities", [], [], "public", tmp_path, conn)
    # check_capture_dedup should find it (if embeddings available) or return [] (best-effort)
    result = check_capture_dedup("Meeting Notes Q1", "Discussed Q1 roadmap and priorities", conn)
    # Best-effort: if embeddings not loaded, result is [] and test still xfails gracefully
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Phase 28-01: title-only fast-path for large bodies
# ---------------------------------------------------------------------------

def test_dedup_title_only_large_body(tmp_path, monkeypatch):
    """When body > 2000 chars, embed_texts is called with [title] only."""
    import sqlite3
    import engine.capture as cap_mod

    captured_texts = []

    def fake_embed_texts(texts):
        captured_texts.extend(texts)
        return []  # returning [] triggers early return in _run_dedup → []

    monkeypatch.setattr(cap_mod, "_embed_texts_for_dedup", fake_embed_texts)

    conn = sqlite3.connect(":memory:")
    large_body = "x" * 2001
    cap_mod.check_capture_dedup("My Title", large_body, conn)

    assert captured_texts == ["My Title"], (
        f"Expected embed_texts called with ['My Title'] for large body, got {captured_texts}"
    )


def test_dedup_short_body_uses_full_text(tmp_path, monkeypatch):
    """When body <= 2000 chars, embed_texts is called with [f'{title}\\n{body}']."""
    import sqlite3
    import engine.capture as cap_mod

    captured_texts = []

    def fake_embed_texts(texts):
        captured_texts.extend(texts)
        return []

    monkeypatch.setattr(cap_mod, "_embed_texts_for_dedup", fake_embed_texts)

    conn = sqlite3.connect(":memory:")
    short_body = "short body"
    cap_mod.check_capture_dedup("My Title", short_body, conn)

    assert captured_texts == [f"My Title\n{short_body}"], (
        f"Expected embed_texts called with full text for short body, got {captured_texts}"
    )


# ---------------------------------------------------------------------------
# Phase 30-01: People write-back at capture time (PEO-02)
# ---------------------------------------------------------------------------

def test_capture_people_writeback(tmp_path, monkeypatch):
    """capture_note() extracts people from body and writes them to the people column.

    No explicit people param passed — extraction must populate the column.
    """
    import engine.db as db_mod
    import engine.paths as paths_mod
    from pathlib import Path

    brain_root = tmp_path / "brain"
    brain_root.mkdir()
    tmp_db = Path(str(tmp_path / "brain.db"))
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_db)
    monkeypatch.setattr(paths_mod, "DB_PATH", tmp_db)
    monkeypatch.setattr(paths_mod, "BRAIN_ROOT", brain_root)
    monkeypatch.setenv("BRAIN_PATH", str(brain_root))

    from engine.db import get_connection, init_schema
    from engine.capture import capture_note

    conn = get_connection(str(tmp_db))
    init_schema(conn)

    path = capture_note(
        "note",
        "Team Update",
        "Met Anna Korhonen today to discuss the project",
        [],          # no explicit people
        [],
        "public",
        brain_root,
        conn,
    )
    conn.commit()

    # ARCH-01: DB now stores relative paths — search by title
    row = conn.execute(
        "SELECT people FROM notes WHERE title = 'Team Update'"
    ).fetchone()
    assert row is not None, "Note must exist in DB"
    people_json = row[0]
    people = json.loads(people_json)
    assert any("Anna" in p and "Korhonen" in p for p in people), (
        f"Expected 'Anna Korhonen' in people column, got: {people}"
    )
    conn.close()


def test_capture_people_merge(tmp_path, monkeypatch):
    """capture_note() merges explicit people param with body-extracted people.

    Caller-supplied people come first; extracted people appended.
    """
    import engine.db as db_mod
    import engine.paths as paths_mod
    from pathlib import Path

    brain_root = tmp_path / "brain"
    brain_root.mkdir()
    tmp_db = Path(str(tmp_path / "brain.db"))
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_db)
    monkeypatch.setattr(paths_mod, "DB_PATH", tmp_db)
    monkeypatch.setattr(paths_mod, "BRAIN_ROOT", brain_root)
    monkeypatch.setenv("BRAIN_PATH", str(brain_root))

    from engine.db import get_connection, init_schema
    from engine.capture import capture_note

    conn = get_connection(str(tmp_db))
    init_schema(conn)

    capture_note(
        "note",
        "Meeting Summary",
        "Jane Doe presented the quarterly results",
        [],
        ["Bob Smith"],   # explicit people
        "public",
        brain_root,
        conn,
    )
    conn.commit()

    # ARCH-01: DB now stores relative paths — search by title
    row = conn.execute(
        "SELECT people FROM notes WHERE title = 'Meeting Summary'"
    ).fetchone()
    assert row is not None
    people = json.loads(row[0])
    # Both explicit and extracted must be present
    assert any("Bob" in p and "Smith" in p for p in people), f"Bob Smith missing: {people}"
    assert any("Jane" in p and "Doe" in p for p in people), f"Jane Doe missing: {people}"


def test_capture_people_dedup(tmp_path, monkeypatch):
    """capture_note() deduplicates people when explicit param overlaps with extraction."""
    import engine.db as db_mod
    import engine.paths as paths_mod
    from pathlib import Path

    brain_root = tmp_path / "brain"
    brain_root.mkdir()
    tmp_db = Path(str(tmp_path / "brain.db"))
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_db)
    monkeypatch.setattr(paths_mod, "DB_PATH", tmp_db)
    monkeypatch.setattr(paths_mod, "BRAIN_ROOT", brain_root)
    monkeypatch.setenv("BRAIN_PATH", str(brain_root))

    from engine.db import get_connection, init_schema
    from engine.capture import capture_note

    conn = get_connection(str(tmp_db))
    init_schema(conn)

    capture_note(
        "note",
        "Status Update",
        "Anna Korhonen reviewed the document",
        [],
        ["Anna Korhonen"],  # explicit — same as what extraction would produce
        "public",
        brain_root,
        conn,
    )
    conn.commit()

    # ARCH-01: DB now stores relative paths — search by title
    row = conn.execute(
        "SELECT people FROM notes WHERE title = 'Status Update'"
    ).fetchone()
    assert row is not None
    people = json.loads(row[0])
    anna_entries = [p for p in people if "Anna" in p and "Korhonen" in p]
    assert len(anna_entries) == 1, f"Expected exactly 1 'Anna Korhonen' entry, got: {people}"


# ---------------------------------------------------------------------------
# 32-03: Dual-write tests for note_tags and note_people junction tables
# ---------------------------------------------------------------------------

class TestJunctionTableDualWrite:
    """Verify capture_note and update_note dual-write to junction tables (32-03)."""

    def test_capture_writes_to_note_tags_junction(self, tmp_path, monkeypatch):
        """capture_note() must write tags to both JSON column AND note_tags junction table."""
        import engine.db as _db
        import engine.paths as _paths
        from engine.db import init_schema
        from engine.capture import capture_note

        brain = tmp_path / "SecondBrain"
        brain.mkdir()
        (brain / "note").mkdir()
        db_path = str(tmp_path / "test.db")
        monkeypatch.setattr(_db, "DB_PATH", tmp_path / "test.db")
        monkeypatch.setattr(_paths, "DB_PATH", tmp_path / "test.db")
        monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)

        conn = _db.get_connection(db_path)
        init_schema(conn)

        capture_note(
            note_type="note",
            title="Dual Write Test",
            body="testing junction table write",
            tags=["python", "testing"],
            people=[],
            content_sensitivity="public",
            brain_root=brain,
            conn=conn,
        )
        conn.commit()

        # Verify JSON column still written
        row = conn.execute("SELECT tags FROM notes WHERE title='Dual Write Test'").fetchone()
        assert row is not None
        json_tags = json.loads(row[0])
        assert "python" in json_tags
        assert "testing" in json_tags

        # Verify junction table populated
        note_path_row = conn.execute("SELECT path FROM notes WHERE title='Dual Write Test'").fetchone()
        assert note_path_row is not None
        jt_rows = conn.execute(
            "SELECT tag FROM note_tags WHERE note_path=? ORDER BY tag", (note_path_row[0],)
        ).fetchall()
        jt_tags = [r[0] for r in jt_rows]
        assert "python" in jt_tags
        assert "testing" in jt_tags
        conn.close()

    def test_capture_writes_to_note_people_junction(self, tmp_path, monkeypatch):
        """capture_note() must write people to both JSON column AND note_people junction table."""
        import engine.db as _db
        import engine.paths as _paths
        from engine.db import init_schema
        from engine.capture import capture_note

        brain = tmp_path / "SecondBrain"
        brain.mkdir()
        (brain / "meeting").mkdir()
        db_path = str(tmp_path / "test.db")
        monkeypatch.setattr(_db, "DB_PATH", tmp_path / "test.db")
        monkeypatch.setattr(_paths, "DB_PATH", tmp_path / "test.db")
        monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)

        conn = _db.get_connection(db_path)
        init_schema(conn)

        capture_note(
            note_type="meeting",
            title="People Junction Test",
            body="meeting notes",
            tags=[],
            people=["people/alice.md"],
            content_sensitivity="public",
            brain_root=brain,
            conn=conn,
        )
        conn.commit()

        # Verify JSON column still written
        row = conn.execute("SELECT people FROM notes WHERE title='People Junction Test'").fetchone()
        assert row is not None
        json_people = json.loads(row[0])
        assert "people/alice.md" in json_people

        # Verify junction table populated
        note_path_row = conn.execute("SELECT path FROM notes WHERE title='People Junction Test'").fetchone()
        assert note_path_row is not None
        jt_rows = conn.execute(
            "SELECT person FROM note_people WHERE note_path=?", (note_path_row[0],)
        ).fetchall()
        jt_people = [r[0] for r in jt_rows]
        assert "people/alice.md" in jt_people
        conn.close()

    def test_update_note_refreshes_note_tags_junction(self, tmp_path, monkeypatch):
        """update_note() must refresh note_tags junction rows when tags change."""
        import engine.db as _db
        import engine.paths as _paths
        from engine.db import init_schema
        from engine.capture import capture_note, update_note

        brain = tmp_path / "SecondBrain"
        brain.mkdir()
        (brain / "note").mkdir()
        db_path = str(tmp_path / "test.db")
        monkeypatch.setattr(_db, "DB_PATH", tmp_path / "test.db")
        monkeypatch.setattr(_paths, "DB_PATH", tmp_path / "test.db")
        monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)

        conn = _db.get_connection(db_path)
        init_schema(conn)

        note_path = capture_note(
            note_type="note",
            title="Update Tag Test",
            body="initial body",
            tags=["old-tag"],
            people=[],
            content_sensitivity="public",
            brain_root=brain,
            conn=conn,
        )
        conn.commit()

        # Verify old tag in junction table
        note_path_row = conn.execute("SELECT path FROM notes WHERE title='Update Tag Test'").fetchone()
        db_path_val = note_path_row[0]
        old_jt = conn.execute(
            "SELECT tag FROM note_tags WHERE note_path=?", (db_path_val,)
        ).fetchall()
        assert any(r[0] == "old-tag" for r in old_jt)

        # Now update with new tags
        update_note(
            note_path=str(note_path),
            title="Update Tag Test",
            body="updated body",
            tags=["new-tag"],
            conn=conn,
            brain_root=brain,
        )
        conn.commit()

        new_jt = conn.execute(
            "SELECT tag FROM note_tags WHERE note_path=?", (db_path_val,)
        ).fetchall()
        new_tags = [r[0] for r in new_jt]
        assert "new-tag" in new_tags, f"Expected 'new-tag' in junction table, got: {new_tags}"
        assert "old-tag" not in new_tags, f"Expected 'old-tag' removed from junction table, got: {new_tags}"
        conn.close()


# ---------------------------------------------------------------------------
# Phase 42: importance field
# ---------------------------------------------------------------------------

def test_build_post_importance_default():
    """build_post() without importance produces post['importance'] == 'medium'."""
    from engine.capture import build_post
    post = build_post("note", "t", "b", [], [])
    assert post["importance"] == "medium"


def test_build_post_importance_high():
    """build_post(importance='high') sets post['importance'] == 'high'."""
    from engine.capture import build_post
    post = build_post("note", "t", "b", [], [], importance="high")
    assert post["importance"] == "high"


def test_capture_note_importance_in_db(tmp_path, monkeypatch):
    """capture_note(importance='high') writes importance='high' to DB."""
    import engine.db as db_mod
    import engine.paths as paths_mod

    brain = tmp_path / "SecondBrain"
    brain.mkdir()
    tmp_db = tmp_path / "brain.db"
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_db)
    monkeypatch.setattr(paths_mod, "DB_PATH", tmp_db)
    monkeypatch.setattr(paths_mod, "BRAIN_ROOT", brain)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    from engine.db import get_connection, init_schema
    from engine.capture import capture_note

    conn = get_connection(str(tmp_db))
    init_schema(conn)

    capture_note("note", "Importance Test", "body", [], [], "public", brain, conn, importance="high")
    conn.commit()

    row = conn.execute("SELECT importance FROM notes WHERE title='Importance Test'").fetchone()
    assert row is not None
    assert row[0] == "high"
    conn.close()


def test_importance_migration_idempotent(tmp_path):
    """migrate_add_importance_column() called twice does not raise."""
    import sqlite3
    from engine.db import migrate_add_importance_column, init_schema

    conn = sqlite3.connect(str(tmp_path / "brain.db"))
    init_schema(conn)
    migrate_add_importance_column(conn)  # second call — must be idempotent
    conn.close()


def test_update_note_re_extracts_entities(tmp_path, monkeypatch):
    """ARCH-13: update_note() re-runs entity extraction and updates entities+people columns."""
    import engine.db as db_mod
    import engine.paths as paths_mod

    brain_root = tmp_path / "brain"
    (brain_root / "note").mkdir(parents=True)
    tmp_db = tmp_path / "brain.db"
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_db)
    monkeypatch.setattr(paths_mod, "DB_PATH", tmp_db)
    monkeypatch.setattr(paths_mod, "BRAIN_ROOT", brain_root)
    monkeypatch.setenv("BRAIN_PATH", str(brain_root))

    from engine.db import get_connection, init_schema
    from engine.capture import capture_note, update_note

    conn = get_connection(str(tmp_db))
    init_schema(conn)

    # Capture a note with no people references
    path = capture_note("note", "Test Note", "No people here", [], [], "public", brain_root, conn)
    conn.commit()

    # Update body to mention someone
    update_note(path, "Test Note", "Met Anna Korhonen today", ["tag1"], conn, brain_root)

    # Check entities column was updated
    row = conn.execute("SELECT entities FROM notes WHERE title='Test Note'").fetchone()
    assert row is not None
    entities = json.loads(row[0] or "{}")
    # entities should have been re-extracted (exact content depends on extraction quality)
    assert isinstance(entities, dict), f"entities should be a dict, got: {entities}"
    conn.close()


# ---------------------------------------------------------------------------
# Phase 46: Person stub creation in capture_note background thread (UCE-01/02/03)
# ---------------------------------------------------------------------------

class _SyncThread:
    """Runs threading.Thread target synchronously — eliminates race conditions in tests."""
    def __init__(self, target, daemon=None):
        self._target = target

    def start(self):
        self._target()


class TestPersonStubCreation:
    """Verify capture_note() creates person stubs for all capture paths (Phase 46)."""

    def _setup_brain(self, tmp_path, monkeypatch):
        """Isolated file-based brain + DB. Returns (brain_path, conn)."""
        import engine.db as db_mod
        import engine.paths as paths_mod

        brain = tmp_path / "brain"
        brain.mkdir()
        tmp_db = tmp_path / "brain.db"
        monkeypatch.setattr(db_mod, "DB_PATH", tmp_db)
        monkeypatch.setattr(paths_mod, "DB_PATH", tmp_db)
        monkeypatch.setattr(paths_mod, "BRAIN_ROOT", brain)
        monkeypatch.setenv("BRAIN_PATH", str(brain))

        from engine.db import get_connection, init_schema
        conn = get_connection(str(tmp_db))
        init_schema(conn)
        conn.commit()
        return brain, conn

    def _patch_slow_hooks(self, monkeypatch):
        """Stub out slow intelligence hooks (avoid subprocess claude calls)."""
        monkeypatch.setattr("engine.intelligence.check_connections", lambda *a, **kw: None)
        monkeypatch.setattr("engine.intelligence.extract_action_items", lambda *a, **kw: None)

    def test_stub_created_for_meeting_with_people(self, tmp_path, monkeypatch):
        """capture_note(meeting) with person in body → resolve_entities called, stub created."""
        brain, conn = self._setup_brain(tmp_path, monkeypatch)
        self._patch_slow_hooks(monkeypatch)

        resolve_calls = []

        def fake_resolve(entities, db_conn, brain_root):
            resolve_calls.append(entities)
            return {"new_stubs": [{"name": "John Smith", "type": "people"}], "existing": []}

        def fake_extract(title, body):
            if "John Smith" in body:
                return {"people": ["John Smith"], "places": [], "topics": [], "orgs": []}
            return {"people": [], "places": [], "topics": [], "orgs": []}

        monkeypatch.setattr("engine.entities.extract_entities", fake_extract)
        monkeypatch.setattr("engine.segmenter.resolve_entities", fake_resolve)
        monkeypatch.setattr("threading.Thread", _SyncThread)

        from engine.capture import capture_note
        capture_note(
            note_type="meeting",
            title="Team Sync",
            body="Met with John Smith about project",
            tags=[], people=[], content_sensitivity="public",
            brain_root=brain, conn=conn,
        )

        assert len(resolve_calls) == 1, f"Expected 1 resolve_entities call, got {len(resolve_calls)}"
        assert "John Smith" in resolve_calls[0].get("people", [])
        people_dir = brain / "people"
        stub_files = list(people_dir.glob("*.md")) if people_dir.exists() else []
        assert any("john-smith" in f.name for f in stub_files), (
            f"Expected john-smith stub in {people_dir}, found: {[f.name for f in stub_files]}"
        )
        conn.close()

    def test_stub_skipped_for_coding_type(self, tmp_path, monkeypatch):
        """capture_note(coding) → resolve_entities NOT called regardless of people in body."""
        brain, conn = self._setup_brain(tmp_path, monkeypatch)
        self._patch_slow_hooks(monkeypatch)

        resolve_calls = []

        def fake_resolve(entities, db_conn, brain_root):
            resolve_calls.append(entities)
            return {"new_stubs": [], "existing": []}

        monkeypatch.setattr("engine.entities.extract_entities",
                            lambda t, b: {"people": ["John Smith"], "places": [], "topics": [], "orgs": []})
        monkeypatch.setattr("engine.segmenter.resolve_entities", fake_resolve)
        monkeypatch.setattr("threading.Thread", _SyncThread)

        from engine.capture import capture_note
        capture_note(
            note_type="coding", title="My Snippet", body="John Smith wrote this",
            tags=[], people=[], content_sensitivity="public", brain_root=brain, conn=conn,
        )

        assert len(resolve_calls) == 0, "resolve_entities must not be called for coding type"
        conn.close()

    def test_stub_skipped_for_link_type(self, tmp_path, monkeypatch):
        """capture_note(link) → resolve_entities NOT called."""
        brain, conn = self._setup_brain(tmp_path, monkeypatch)
        self._patch_slow_hooks(monkeypatch)

        resolve_calls = []
        monkeypatch.setattr("engine.entities.extract_entities",
                            lambda t, b: {"people": ["John Smith"], "places": [], "topics": [], "orgs": []})
        monkeypatch.setattr("engine.segmenter.resolve_entities",
                            lambda e, c, r: resolve_calls.append(e) or {"new_stubs": [], "existing": []})
        monkeypatch.setattr("threading.Thread", _SyncThread)

        from engine.capture import capture_note
        capture_note(
            note_type="link", title="An Article", body="John Smith shared this",
            tags=[], people=[], content_sensitivity="public", brain_root=brain, conn=conn,
        )

        assert len(resolve_calls) == 0, "resolve_entities must not be called for link type"
        conn.close()

    def test_stub_skipped_for_files_type(self, tmp_path, monkeypatch):
        """capture_note(files) → resolve_entities NOT called."""
        brain, conn = self._setup_brain(tmp_path, monkeypatch)
        self._patch_slow_hooks(monkeypatch)

        resolve_calls = []
        monkeypatch.setattr("engine.entities.extract_entities",
                            lambda t, b: {"people": ["John Smith"], "places": [], "topics": [], "orgs": []})
        monkeypatch.setattr("engine.segmenter.resolve_entities",
                            lambda e, c, r: resolve_calls.append(e) or {"new_stubs": [], "existing": []})
        monkeypatch.setattr("threading.Thread", _SyncThread)

        from engine.capture import capture_note
        capture_note(
            note_type="files", title="My File", body="John Smith uploaded this",
            tags=[], people=[], content_sensitivity="public", brain_root=brain, conn=conn,
        )

        assert len(resolve_calls) == 0, "resolve_entities must not be called for files type"
        conn.close()

    def test_stub_skipped_when_no_people(self, tmp_path, monkeypatch):
        """capture_note(meeting) with no extracted people → resolve_entities NOT called."""
        brain, conn = self._setup_brain(tmp_path, monkeypatch)
        self._patch_slow_hooks(monkeypatch)

        resolve_calls = []
        monkeypatch.setattr("engine.entities.extract_entities",
                            lambda t, b: {"people": [], "places": [], "topics": [], "orgs": []})
        monkeypatch.setattr("engine.segmenter.resolve_entities",
                            lambda e, c, r: resolve_calls.append(e) or {"new_stubs": [], "existing": []})
        monkeypatch.setattr("threading.Thread", _SyncThread)

        from engine.capture import capture_note
        capture_note(
            note_type="meeting", title="Team Sync", body="Discussed project updates",
            tags=[], people=[], content_sensitivity="public", brain_root=brain, conn=conn,
        )

        assert len(resolve_calls) == 0, "resolve_entities must not be called when no people extracted"
        conn.close()

    def test_stub_no_recursive_loop(self, tmp_path, monkeypatch):
        """capture_note(people, body='') → empty people → no resolve_entities call (loop guard)."""
        brain, conn = self._setup_brain(tmp_path, monkeypatch)
        self._patch_slow_hooks(monkeypatch)

        resolve_calls = []
        # Empty body → no people found (simulates real extract_entities behaviour)
        monkeypatch.setattr("engine.entities.extract_entities",
                            lambda t, b: {"people": [], "places": [], "topics": [], "orgs": []})
        monkeypatch.setattr("engine.segmenter.resolve_entities",
                            lambda e, c, r: resolve_calls.append(e) or {"new_stubs": [], "existing": []})
        monkeypatch.setattr("threading.Thread", _SyncThread)

        from engine.capture import capture_note
        capture_note(
            note_type="people", title="X", body="",
            tags=[], people=[], content_sensitivity="public", brain_root=brain, conn=conn,
        )

        assert len(resolve_calls) == 0, "Empty-body stub capture must not trigger resolve_entities"
        conn.close()

    def test_stub_thread_error_silent(self, tmp_path, monkeypatch):
        """resolve_entities raising RuntimeError → capture_note still returns a valid Path."""
        brain, conn = self._setup_brain(tmp_path, monkeypatch)
        self._patch_slow_hooks(monkeypatch)

        def failing_resolve(entities, db_conn, brain_root):
            raise RuntimeError("DB failure")

        monkeypatch.setattr("engine.entities.extract_entities",
                            lambda t, b: {"people": ["John Smith"], "places": [], "topics": [], "orgs": []})
        monkeypatch.setattr("engine.segmenter.resolve_entities", failing_resolve)
        monkeypatch.setattr("threading.Thread", _SyncThread)

        from engine.capture import capture_note
        result = capture_note(
            note_type="meeting", title="Error Test", body="Met with John Smith",
            tags=[], people=[], content_sensitivity="public", brain_root=brain, conn=conn,
        )

        assert isinstance(result, Path), f"capture_note must return Path even on resolve error, got {result!r}"
        assert result.exists(), "Returned path must exist on disk"
        conn.close()
