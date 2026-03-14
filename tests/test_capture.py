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


@pytest.mark.xfail(strict=True, reason="CAP-06 not wired yet")
def test_cap06_update_memory_called_after_capture(tmp_path):
    from unittest.mock import patch, MagicMock
    from engine.capture import main

    fake_note = tmp_path / "note.md"
    fake_note.write_text("")

    with patch("engine.ai.update_memory") as mock_update_memory, \
         patch("engine.capture.capture_note", return_value=fake_note):
        main(["--type", "note", "--title", "T", "--body", "B", "--sensitivity", "public"])
        mock_update_memory.assert_called_once()


@pytest.mark.xfail(strict=True, reason="CAP-06 not wired yet")
def test_cap06_update_memory_skipped_for_pii(tmp_path):
    from unittest.mock import patch, MagicMock
    from engine.capture import main

    fake_note = tmp_path / "note.md"
    fake_note.write_text("")

    with patch("engine.ai.update_memory") as mock_update_memory, \
         patch("engine.capture.capture_note", return_value=fake_note):
        main(["--type", "note", "--title", "T", "--body", "B", "--sensitivity", "pii"])
        assert mock_update_memory.call_count == 0
