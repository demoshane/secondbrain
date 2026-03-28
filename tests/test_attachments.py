"""Tests for engine/attachments.py — COV-06."""
import pytest
from pathlib import Path
from unittest.mock import patch
import engine.db as _db
import engine.paths as _paths


@pytest.fixture
def attachment_brain(tmp_path, monkeypatch):
    """Isolated DB for attachment tests."""
    from engine.db import init_schema, get_connection

    tmp_db = tmp_path / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)

    conn = get_connection()
    init_schema(conn)
    conn.close()
    return tmp_path


def test_save_attachment_returns_dict(attachment_brain):
    """save_attachment inserts a row and returns a dict with expected keys."""
    from engine.attachments import save_attachment

    result = save_attachment(
        note_path="notes/test-note.md",
        file_path="/tmp/uploaded_file.pdf",
        filename="uploaded_file.pdf",
        size=1024,
    )

    assert isinstance(result, dict)
    assert result["note_path"] == "notes/test-note.md"
    assert result["filename"] == "uploaded_file.pdf"
    assert result["size"] == 1024
    assert "id" in result
    assert "uploaded_at" in result


def test_list_attachments_returns_saved(attachment_brain):
    """list_attachments returns previously saved attachments for a note_path."""
    from engine.attachments import save_attachment, list_attachments

    note_path = "notes/my-note.md"
    save_attachment(note_path, "/tmp/file1.png", "file1.png", 512)
    save_attachment(note_path, "/tmp/file2.png", "file2.png", 768)

    results = list_attachments(note_path)
    assert len(results) == 2
    filenames = {r["filename"] for r in results}
    assert filenames == {"file1.png", "file2.png"}


def test_list_attachments_empty_for_unknown_note(attachment_brain):
    """list_attachments returns empty list when note has no attachments."""
    from engine.attachments import list_attachments

    results = list_attachments("notes/no-attachments.md")
    assert results == []


def test_suppress_next_create_marks_path():
    """suppress_next_create adds path; is_upload_suppressed returns True immediately."""
    from engine.attachments import suppress_next_create, is_upload_suppressed

    path = "/tmp/test_suppress_path.pdf"
    suppress_next_create(path, window=10.0)
    assert is_upload_suppressed(path) is True


def test_is_upload_suppressed_false_for_unknown():
    """is_upload_suppressed returns False for paths not in suppress set."""
    from engine.attachments import is_upload_suppressed

    assert is_upload_suppressed("/tmp/not_suppressed_ever.txt") is False


def test_save_attachment_multiple_notes_isolated(attachment_brain):
    """Attachments for different notes are stored independently."""
    from engine.attachments import save_attachment, list_attachments

    save_attachment("notes/note-a.md", "/tmp/a.pdf", "a.pdf", 100)
    save_attachment("notes/note-b.md", "/tmp/b.pdf", "b.pdf", 200)

    assert len(list_attachments("notes/note-a.md")) == 1
    assert len(list_attachments("notes/note-b.md")) == 1
    assert list_attachments("notes/note-a.md")[0]["filename"] == "a.pdf"
