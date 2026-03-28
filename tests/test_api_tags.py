"""Tests for Phase 23: Tags API extensions (GNAV-02, GNAV-03).

TDD contract — RED phase:
  - TestListNotesTags: GET /notes returns tags as a parsed list, not a raw JSON string
  - TestTagsOnlySave: PUT /notes/<path> with only tags in body updates file+DB
  - TestTagSearch: POST /search with tags param filters AND-style
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.api import app  # noqa: E402
from engine.db import get_connection  # noqa: E402


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def tmp_brain(tmp_path, monkeypatch):
    """Isolated brain: tmp file tree + tmp SQLite DB (never touches the real DB).

    Returns (tmp_path, note_work_path, note_other_path).
    """
    import engine.db as _db
    import engine.paths as _paths
    from engine.db import init_schema

    # Point DB_PATH at a tmp file so no real DB is touched
    tmp_db = tmp_path / "test_brain.db"
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)
    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))

    # Bootstrap schema in the tmp DB
    conn = get_connection()
    init_schema(conn)
    conn.commit()
    conn.close()

    # Note 1: tagged ["work", "idea"]
    note_work = tmp_path / "work-note.md"
    note_work.write_text(
        "---\ntitle: Work Note\ntags: [work, idea]\ntype: note\n---\n\nWork content.\n",
        encoding="utf-8",
    )
    path_work = "work-note.md"  # relative path (Phase 32+)

    # Note 2: tagged ["personal"]
    note_other = tmp_path / "personal-note.md"
    note_other.write_text(
        "---\ntitle: Personal Note\ntags: [personal]\ntype: idea\n---\n\nPersonal content.\n",
        encoding="utf-8",
    )
    path_other = "personal-note.md"  # relative path (Phase 32+)

    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
        (path_work, "Work Note", "note", "Work content.", '["work","idea"]'),
    )
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
        (path_other, "Personal Note", "idea", "Personal content.", '["personal"]'),
    )
    # Populate note_tags junction table (search uses this, not the JSON tags column)
    for tag in ("work", "idea"):
        conn.execute("INSERT OR IGNORE INTO note_tags (note_path, tag) VALUES (?, ?)", (path_work, tag))
    conn.execute("INSERT OR IGNORE INTO note_tags (note_path, tag) VALUES (?, ?)", (path_other, "personal"))
    conn.commit()
    conn.close()

    yield tmp_path, note_work, note_other, path_work, path_other
    # tmp_path is cleaned up automatically by pytest; monkeypatch reverts DB_PATH


# ---------------------------------------------------------------------------
# TestListNotesTags
# ---------------------------------------------------------------------------


class TestListNotesTags:
    """GET /notes returns each note's tags as a Python list, not a raw JSON string."""

    def test_tags_returned_as_list(self, client, tmp_brain):
        response = client.get("/notes")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.get_json()
        notes = data.get("notes", [])
        # Find the seeded note with tags
        tmp_path, note_work, note_other, path_work, path_other = tmp_brain
        matching = [n for n in notes if n["path"] == path_work]
        assert matching, f"Work note not found in /notes response; paths returned: {[n['path'] for n in notes]}"
        note = matching[0]
        tags = note.get("tags")
        assert isinstance(tags, list), (
            f"Expected tags to be a list, got {type(tags).__name__}: {tags!r}"
        )
        assert sorted(tags) == ["idea", "work"], (
            f"Expected ['idea', 'work'], got {tags!r}"
        )

    def test_all_notes_have_list_tags(self, client, tmp_brain):
        response = client.get("/notes")
        data = response.get_json()
        notes = data.get("notes", [])
        for note in notes:
            assert isinstance(note.get("tags"), list), (
                f"Note {note.get('path')} has tags={note.get('tags')!r} — expected list"
            )


# ---------------------------------------------------------------------------
# TestTagsOnlySave
# ---------------------------------------------------------------------------


class TestTagsOnlySave:
    """PUT /notes/<path> with only tags body updates frontmatter + DB without full reindex."""

    def test_tags_only_updates_file(self, client, tmp_brain):
        """After PUT with tags only, file frontmatter contains the new tags."""
        import frontmatter as _fm

        tmp_path, note_work, note_other, path_work, path_other = tmp_brain
        response = client.put(
            f"/notes/{path_work}",
            json={"tags": ["work", "idea", "urgent"]},
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.data}"
        )
        data = response.get_json()
        assert data.get("saved") is True, f"Expected saved=True, got: {data}"

        # Re-read file and check frontmatter
        post = _fm.loads(note_work.read_text(encoding="utf-8"))
        file_tags = post.metadata.get("tags", [])
        assert sorted(file_tags) == ["idea", "urgent", "work"], (
            f"Expected ['idea', 'urgent', 'work'] in frontmatter, got {file_tags!r}"
        )

    def test_tags_updates_db(self, client, tmp_brain):
        """After PUT with tags only, DB tags column reflects the new tags."""
        tmp_path, note_work, note_other, path_work, path_other = tmp_brain
        client.put(
            f"/notes/{path_work}",
            json={"tags": ["work", "urgent"]},
        )
        conn = get_connection()
        row = conn.execute(
            "SELECT tags FROM notes WHERE path=?", (path_work,)
        ).fetchone()
        conn.close()
        assert row is not None, "Note not found in DB after PUT"
        db_tags = json.loads(row[0])
        assert sorted(db_tags) == ["urgent", "work"], (
            f"Expected ['urgent', 'work'] in DB, got {db_tags!r}"
        )

    def test_content_unchanged(self, client, tmp_brain):
        """PUT with only tags does not alter the note body."""
        tmp_path, note_work, note_other, path_work, path_other = tmp_brain
        original_body = note_work.read_text(encoding="utf-8")

        import frontmatter as _fm
        original_post = _fm.loads(original_body)
        original_content = original_post.content

        client.put(
            f"/notes/{path_work}",
            json={"tags": ["new-tag"]},
        )

        updated_post = _fm.loads(note_work.read_text(encoding="utf-8"))
        assert updated_post.content == original_content, (
            f"Body changed after tags-only PUT.\nBefore: {original_content!r}\nAfter: {updated_post.content!r}"
        )


# ---------------------------------------------------------------------------
# TestTagSearch
# ---------------------------------------------------------------------------


class TestTagSearch:
    """POST /search with tags param filters results by tag (AND logic)."""

    def test_filter_returns_matching(self, client, tmp_brain):
        """POST /search with tags=["work"] returns only notes that have 'work' in tags."""
        tmp_path, note_work, note_other, path_work, path_other = tmp_brain
        response = client.post("/search", json={"query": "", "tags": ["work"]})
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.data}"
        )
        data = response.get_json()
        results = data.get("results", [])
        paths = [r["path"] for r in results]
        assert path_work in paths, (
            f"Work note ({path_work}) should be in results for tags=['work'], got: {paths}"
        )
        assert path_other not in paths, (
            f"Personal note ({path_other}) should NOT be in results for tags=['work'], got: {paths}"
        )

    def test_and_logic(self, client, tmp_brain):
        """POST /search with tags=["work"] excludes notes without 'work' even if query matches."""
        tmp_path, note_work, note_other, path_work, path_other = tmp_brain
        # Both notes are in the DB; tags filter should exclude the personal note
        response = client.post("/search", json={"query": "content", "tags": ["work"]})
        assert response.status_code == 200
        data = response.get_json()
        results = data.get("results", [])
        paths = [r["path"] for r in results]
        # personal note also has "content" in body but lacks "work" tag — must be excluded
        assert path_other not in paths, (
            f"Personal note should be excluded by AND tag filter, got paths: {paths}"
        )

    def test_no_tag_param(self, client, tmp_brain):
        """POST /search without tags param returns all matching results (backward compat)."""
        tmp_path, note_work, note_other, path_work, path_other = tmp_brain
        response = client.post("/search", json={"query": "content"})
        assert response.status_code == 200
        data = response.get_json()
        results = data.get("results", [])
        paths = [r["path"] for r in results]
        # Both notes have "content" in body — both should appear without tag filter
        assert path_work in paths, (
            f"Work note should appear in unfiltered search, got: {paths}"
        )
        assert path_other in paths, (
            f"Personal note should appear in unfiltered search, got: {paths}"
        )
