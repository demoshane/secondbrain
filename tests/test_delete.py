"""Tests for Phase 22: Note deletion cascade + security hardening (GUIX-06).

TDD contract: all unit tests call the real delete_note() implementation.
Integration tests call the real DELETE /notes/<path> endpoint.
"""
from __future__ import annotations

import sqlite3
import sys
import urllib.parse
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.delete import delete_note  # noqa: E402
from engine.api import app  # noqa: E402


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def note_file(tmp_path, initialized_db):
    """Real .md file + full DB row set for unit tests."""
    note = tmp_path / "test-note.md"
    note.write_text(
        "---\ntitle: Delete Me\ntags: []\ntype: idea\n---\n\nSome content here.\n",
        encoding="utf-8",
    )
    path_str = str(note.resolve())
    brain_root = tmp_path

    # notes row
    initialized_db.execute(
        "INSERT OR IGNORE INTO notes (path, title, type, body, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
        (path_str, "Delete Me", "idea", "Some content here."),
    )
    # note_embeddings row
    initialized_db.execute(
        "INSERT OR IGNORE INTO note_embeddings (note_path, embedding, content_hash, stale)"
        " VALUES (?, ?, ?, 0)",
        (path_str, b"\x00" * 4, "hash_test"),
    )
    # relationships rows
    initialized_db.execute(
        "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type)"
        " VALUES (?, ?, ?)",
        (path_str, "/other/note.md", "link"),
    )
    initialized_db.execute(
        "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type)"
        " VALUES (?, ?, ?)",
        ("/other/note.md", path_str, "link"),
    )
    # action_items row
    initialized_db.execute(
        "INSERT OR IGNORE INTO action_items (note_path, text, done)"
        " VALUES (?, ?, 0)",
        (path_str, "Do the thing"),
    )
    # prior audit_log row
    initialized_db.execute(
        "INSERT INTO audit_log (event_type, note_path, detail, created_at)"
        " VALUES (?, ?, ?, datetime('now'))",
        ("index_note", path_str, "initial index"),
    )
    initialized_db.commit()

    return note, brain_root, path_str, initialized_db


# ---------------------------------------------------------------------------
# Unit tests: delete_note() cascade
# ---------------------------------------------------------------------------


def test_delete_note_removes_file(note_file):
    """File at abs_path no longer exists after delete_note()."""
    note, brain_root, path_str, conn = note_file
    delete_note(note, conn, brain_root)
    assert not note.exists(), "File should be removed from disk after delete_note()"


def test_delete_note_removes_db_row(note_file):
    """No row in `notes` table with that path after delete_note()."""
    note, brain_root, path_str, conn = note_file
    delete_note(note, conn, brain_root)
    row = conn.execute("SELECT path FROM notes WHERE path=?", (path_str,)).fetchone()
    assert row is None, f"notes row should be gone after delete_note(), got: {row}"


def test_delete_note_removes_embedding(note_file):
    """No row in `note_embeddings` with that note_path after delete_note()."""
    note, brain_root, path_str, conn = note_file
    delete_note(note, conn, brain_root)
    row = conn.execute(
        "SELECT note_path FROM note_embeddings WHERE note_path=?", (path_str,)
    ).fetchone()
    assert row is None, f"note_embeddings row should be gone, got: {row}"


def test_delete_note_removes_relationships(note_file):
    """No rows in `relationships` with source_path or target_path matching after delete_note()."""
    note, brain_root, path_str, conn = note_file
    delete_note(note, conn, brain_root)
    rows = conn.execute(
        "SELECT rowid FROM relationships WHERE source_path=? OR target_path=?",
        (path_str, path_str),
    ).fetchall()
    assert rows == [], f"relationships rows should be gone, got: {rows}"


def test_delete_note_removes_action_items(note_file):
    """No rows in `action_items` with that note_path after delete_note()."""
    note, brain_root, path_str, conn = note_file
    delete_note(note, conn, brain_root)
    rows = conn.execute(
        "SELECT id FROM action_items WHERE note_path=?", (path_str,)
    ).fetchall()
    assert rows == [], f"action_items rows should be gone, got: {rows}"


def test_delete_note_audit_log(note_file):
    """audit_log has a row with event_type='delete_note' after delete_note()."""
    note, brain_root, path_str, conn = note_file
    delete_note(note, conn, brain_root)
    row = conn.execute(
        "SELECT event_type, note_path, detail FROM audit_log"
        " WHERE event_type='delete_note'",
    ).fetchone()
    assert row is not None, "audit_log should have a delete_note entry"
    assert row[1] is None, "delete_note audit row should have note_path=NULL"
    assert path_str in row[2], "detail should contain the deleted path"


def test_fts5_clean_after_delete(note_file):
    """FTS5 search for the note title returns no hits after delete_note()."""
    note, brain_root, path_str, conn = note_file
    delete_note(note, conn, brain_root)
    rows = conn.execute(
        "SELECT rowid FROM notes_fts WHERE notes_fts MATCH ?", ("Delete Me",)
    ).fetchall()
    assert rows == [], f"FTS5 should return no hits after delete, got: {rows}"


# ---------------------------------------------------------------------------
# Integration tests: DELETE /notes/<path> endpoint
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_api_note(tmp_path, monkeypatch):
    """Real .md file + DB row for endpoint integration tests.

    Sets BRAIN_PATH to tmp_path so _resolve_note_path accepts the note's absolute path.
    """
    import os
    from engine.db import get_connection

    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))

    note = tmp_path / "api-note.md"
    note.write_text(
        "---\ntitle: API Note\ntags: []\ntype: idea\n---\n\nContent.\n",
        encoding="utf-8",
    )
    path_str = str(note.resolve())
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO notes (path, title, type, body, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
        (path_str, "API Note", "idea", "Content."),
    )
    conn.commit()
    conn.close()
    yield path_str
    # Cleanup: remove DB row if test didn't delete it
    conn = get_connection()
    conn.execute("DELETE FROM notes WHERE path=?", (path_str,))
    conn.commit()
    conn.close()
    if note.exists():
        note.unlink()


def test_delete_endpoint_200(client, tmp_api_note):
    """DELETE /notes/<encoded_path> returns 200 + {"deleted": True}."""
    response = client.delete(f"/notes/{tmp_api_note}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.data}"
    data = response.get_json()
    assert data.get("deleted") is True, f"Expected deleted=True, got: {data}"


def test_delete_endpoint_404(client, tmp_path, monkeypatch):
    """DELETE /notes/<nonexistent path inside brain_root> returns 404."""
    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
    # Construct a path that is inside brain_root but doesn't exist on disk
    ghost = tmp_path / "does-not-exist.md"
    response = client.delete(f"/notes/{ghost}")
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"


def test_delete_endpoint_path_traversal_403(client):
    """DELETE /notes/..%2F..%2Fetc%2Fpasswd returns 403."""
    response = client.delete("/notes/..%2F..%2Fetc%2Fpasswd")
    assert response.status_code == 403, f"Expected 403 for path traversal, got {response.status_code}"


def test_get_note_path_traversal_403(client):
    """GET /notes/..%2F..%2Fetc%2Fpasswd returns 403."""
    response = client.get("/notes/..%2F..%2Fetc%2Fpasswd")
    assert response.status_code == 403, f"Expected 403 for path traversal, got {response.status_code}"


def test_save_note_path_traversal_403(client):
    """PUT /notes/..%2F..%2Fetc%2Fpasswd returns 403."""
    response = client.put("/notes/..%2F..%2Fetc%2Fpasswd", json={"content": "evil"})
    assert response.status_code == 403, f"Expected 403 for path traversal, got {response.status_code}"


def test_delete_note_removes_source_file(initialized_db, tmp_path, monkeypatch):
    """delete_note() also removes the source file when note body contains 'File: <path>'."""
    # Set up brain_root/files/ with a source file
    files_dir = tmp_path / "files"
    files_dir.mkdir()
    source_file = files_dir / "photo.png"
    source_file.write_bytes(b"\x89PNG")

    # Create the note whose body references the source file
    note = tmp_path / "note" / "2026-01-01-photo.md"
    note.parent.mkdir()
    note.write_text(
        f"---\ntitle: Photo\ntype: note\n---\n\nFile: {source_file}\n",
        encoding="utf-8",
    )
    path_str = str(note.resolve())
    initialized_db.execute(
        "INSERT OR IGNORE INTO notes (path, title, type, body, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
        (path_str, "Photo", "note", f"File: {source_file}"),
    )
    initialized_db.commit()

    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
    delete_note(note, initialized_db, tmp_path)

    assert not note.exists(), "Note .md file should be deleted"
    assert not source_file.exists(), "Source file in files/ should also be deleted"


def test_delete_note_ignores_source_file_outside_files_dir(initialized_db, tmp_path, monkeypatch):
    """delete_note() does NOT delete files referenced outside brain_root/files/ (security guard)."""
    outside_file = tmp_path / "important.txt"
    outside_file.write_text("keep me")

    note = tmp_path / "note" / "2026-01-01-ref.md"
    note.parent.mkdir()
    note.write_text(
        f"---\ntitle: Ref\ntype: note\n---\n\nFile: {outside_file}\n",
        encoding="utf-8",
    )
    path_str = str(note.resolve())
    initialized_db.execute(
        "INSERT OR IGNORE INTO notes (path, title, type, body, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
        (path_str, "Ref", "note", f"File: {outside_file}"),
    )
    initialized_db.commit()

    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
    delete_note(note, initialized_db, tmp_path)

    assert not note.exists(), "Note .md file should be deleted"
    assert outside_file.exists(), "File outside files/ must NOT be deleted"
