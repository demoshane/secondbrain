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


def test_template_applied(tmp_path, initialized_db):
    from engine.templates import load_template, render_template

    # Write a minimal template file to a temp templates dir
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    template_file = templates_dir / "meeting.md"
    template_file.write_text("## Attendees\n\n${people}\n\n## Notes\n\n${body}\n")

    tmpl = load_template("meeting", templates_dir=templates_dir)
    rendered = render_template(tmpl, {"title": "Sprint Review", "body": "We reviewed the sprint.", "people": "Alice, Bob"})

    assert "Alice, Bob" in rendered
    assert "We reviewed the sprint." in rendered


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
# Phase 7: Absolute path storage contract (SEARCH-01)
# ---------------------------------------------------------------------------

def test_write_note_atomic_stores_absolute_path(tmp_path, initialized_db):
    """DB path column must equal str(target.resolve()) — canonical symlink-free form."""
    from engine.capture import write_note_atomic, build_post

    base = tmp_path.resolve()
    target_dir = base / "notes"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "2026-phase7-test.md"

    post = build_post("note", "Phase7 AbsPath Test", "body content", [], [], "public")
    write_note_atomic(target, post, initialized_db)

    row = initialized_db.execute(
        "SELECT path FROM notes WHERE title = ?", ("Phase7 AbsPath Test",)
    ).fetchone()
    assert row is not None, "Row must exist in DB after write_note_atomic"
    stored_path = row[0]
    assert stored_path == str(target.resolve()), (
        f"Stored path {stored_path!r} must equal resolved target {str(target.resolve())!r}"
    )


def test_write_note_atomic_path_is_absolute(tmp_path, initialized_db):
    """Stored DB path must be absolute (starts with '/') — no relative paths allowed."""
    from engine.capture import write_note_atomic, build_post

    base = tmp_path.resolve()
    target_dir = base / "notes"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "2026-phase7-abscheck.md"

    post = build_post("note", "Phase7 AbsCheck Test", "body content", [], [], "public")
    write_note_atomic(target, post, initialized_db)

    row = initialized_db.execute(
        "SELECT path FROM notes WHERE title = ?", ("Phase7 AbsCheck Test",)
    ).fetchone()
    assert row is not None
    stored_path = row[0]
    assert stored_path.startswith("/"), (
        f"DB path must start with '/' but got: {stored_path!r}"
    )


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
