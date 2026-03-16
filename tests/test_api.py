import pytest
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.api import app  # noqa: E402 — raises ImportError until 17-01
from engine.db import get_connection


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def tmp_note(tmp_path, monkeypatch):
    """Create a real temporary .md file with valid frontmatter; yield its absolute path.

    Sets BRAIN_PATH to tmp_path so _resolve_note_path accepts the note's absolute path.
    """
    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
    note = tmp_path / "test-note.md"
    note.write_text(
        "---\ntitle: Original Title\ntags: [test]\ntype: idea\n---\n\nBody content here.\n",
        encoding="utf-8",
    )
    # Insert into SQLite so note_meta / save_note can find it
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO notes (path, title, type, created_at, updated_at, body)"
        " VALUES (?, ?, ?, datetime('now'), datetime('now'), ?)",
        (str(note.resolve()), "Original Title", "idea", "Body content here."),
    )
    conn.commit()
    conn.close()
    yield str(note.resolve())
    # Cleanup
    conn = get_connection()
    conn.execute("DELETE FROM notes WHERE path=?", (str(note.resolve()),))
    conn.commit()
    conn.close()


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_body(self, client):
        response = client.get("/health")
        assert response.get_json()["status"] == "ok"


class TestNotesList:
    def test_notes_returns_200(self, client):
        response = client.get("/notes")
        assert response.status_code == 200

    def test_notes_has_notes_key(self, client):
        response = client.get("/notes")
        assert "notes" in response.get_json()


class TestSearch:
    def test_search_returns_200(self, client):
        response = client.post("/search", json={"query": "hello"})
        assert response.status_code == 200

    def test_search_has_results_key(self, client):
        response = client.post("/search", json={"query": "hello"})
        assert "results" in response.get_json()


class TestReadNote:
    def test_read_missing_note_404(self, client, tmp_path, monkeypatch):
        """A path inside brain_root that doesn't exist returns 404."""
        monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
        ghost = tmp_path / "nonexistent.md"
        response = client.get(f"/notes/{ghost}")
        assert response.status_code == 404

    def test_read_note_returns_body_key(self, client, tmp_note):
        """GET without ?raw returns 'body' key with no YAML frontmatter block."""
        response = client.get(f"/notes/{tmp_note}")
        assert response.status_code == 200
        data = response.get_json()
        assert "body" in data, f"Expected 'body' key, got: {list(data.keys())}"
        assert "---" not in data["body"], "Frontmatter block should be stripped from body"

    def test_read_note_raw_param(self, client, tmp_note):
        """GET with ?raw=true returns 'content' key with full raw file including frontmatter."""
        response = client.get(f"/notes/{tmp_note}?raw=true")
        assert response.status_code == 200
        data = response.get_json()
        assert "content" in data, f"Expected 'content' key, got: {list(data.keys())}"
        assert "---" in data["content"], "Raw content should include frontmatter"


class TestSaveNote:
    def test_save_note_returns_saved(self, client, tmp_note):
        """PUT returns saved=True."""
        full_content = "---\ntitle: Saved Title\ntags: [test]\ntype: idea\n---\n\nUpdated body.\n"
        response = client.put(
            f"/notes/{tmp_note}",
            json={"content": full_content},
        )
        assert response.status_code == 200
        assert response.get_json()["saved"] is True

    def test_save_note_updates_sqlite_title(self, client, tmp_note):
        """After PUT, SQLite notes.title matches the title from saved frontmatter."""
        full_content = "---\ntitle: New Title\ntags: [test]\ntype: idea\n---\n\nUpdated body.\n"
        client.put(f"/notes/{tmp_note}", json={"content": full_content})
        conn = get_connection()
        row = conn.execute("SELECT title FROM notes WHERE path=?", (tmp_note,)).fetchone()
        conn.close()
        assert row is not None, "Note row not found in SQLite"
        assert row[0] == "New Title", f"Expected 'New Title', got: {row[0]}"

    def test_save_note_preserves_frontmatter(self, client, tmp_note):
        """After PUT with full frontmatter, re-reading the file still shows frontmatter."""
        full_content = "---\ntitle: Preserved\ntags: [keep]\ntype: idea\n---\n\nContent preserved.\n"
        client.put(f"/notes/{tmp_note}", json={"content": full_content})
        disk_content = Path(tmp_note).read_text(encoding="utf-8")
        assert disk_content.startswith("---"), "File should still start with frontmatter after save"


class TestActionItems:
    def test_actions_returns_200(self, client):
        response = client.get("/actions")
        assert response.status_code == 200

    def test_actions_has_actions_key(self, client):
        response = client.get("/actions")
        assert "actions" in response.get_json()


@pytest.fixture
def tmp_note_pair(tmp_path, monkeypatch):
    """Create temp .md files and insert them into SQLite for backlinks testing."""
    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
    note_a = tmp_path / "note_a.md"
    note_a.write_text(
        "---\ntitle: Alice Smith\n---\n\nProject lead for Q1.",
        encoding="utf-8",
    )
    note_b = tmp_path / "note_b.md"
    note_b.write_text(
        "---\ntitle: Project Notes\n---\n\nMet with Alice Smith today to discuss the roadmap.",
        encoding="utf-8",
    )
    note_c = tmp_path / "note_c_alice.md"
    note_c.write_text(
        "---\ntitle: Alice Path Note\n---\n\nThis note body mentions nobody relevant.",
        encoding="utf-8",
    )
    note_unique = tmp_path / "note_unique.md"
    note_unique.write_text(
        "---\ntitle: Zzz Unique Title Xyz\n---\n\nNo mention of anyone.",
        encoding="utf-8",
    )
    note_lower = tmp_path / "note_lower.md"
    note_lower.write_text(
        "---\ntitle: Lower Case Note\n---\n\nMet with alice smith yesterday.",
        encoding="utf-8",
    )

    notes_data = [
        (str(note_a), "Alice Smith", "Project lead for Q1."),
        (str(note_b), "Project Notes", "Met with Alice Smith today to discuss the roadmap."),
        (str(note_c), "Alice Path Note", "This note body mentions nobody relevant."),
        (str(note_unique), "Zzz Unique Title Xyz", "No mention of anyone."),
        (str(note_lower), "Lower Case Note", "Met with alice smith yesterday."),
    ]
    conn = get_connection()
    for path, title, body in notes_data:
        conn.execute(
            "INSERT OR REPLACE INTO notes (path, title, body, type, created_at, updated_at)"
            " VALUES (?, ?, ?, 'note', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
            (path, title, body),
        )
    conn.commit()
    conn.close()

    yield {
        "note_a": note_a,
        "note_b": note_b,
        "note_c": note_c,
        "note_unique": note_unique,
        "note_lower": note_lower,
    }

    conn = get_connection()
    for path, _, _ in notes_data:
        conn.execute("DELETE FROM notes WHERE path=?", (path,))
    conn.commit()
    conn.close()


class TestNoteMeta:
    def test_backlinks_content_match(self, client, tmp_note_pair):
        """note_b body mentions 'Alice Smith' — must appear in note_a's backlinks."""
        note_a = tmp_note_pair["note_a"]
        note_b = tmp_note_pair["note_b"]
        response = client.get(f"/notes/{note_a}/meta")
        assert response.status_code == 200
        data = response.get_json()
        backlink_paths = [bl["path"] for bl in data["backlinks"]]
        assert str(note_b) in backlink_paths, (
            f"Expected note_b ({note_b}) in backlinks, got: {backlink_paths}"
        )

    def test_backlinks_no_false_positive(self, client, tmp_note_pair):
        """note_c filename contains 'alice' but body doesn't mention 'Alice Smith'."""
        note_a = tmp_note_pair["note_a"]
        note_c = tmp_note_pair["note_c"]
        response = client.get(f"/notes/{note_a}/meta")
        assert response.status_code == 200
        data = response.get_json()
        backlink_paths = [bl["path"] for bl in data["backlinks"]]
        assert str(note_c) not in backlink_paths, (
            f"note_c ({note_c}) should NOT be in backlinks (filename match only)"
        )

    def test_backlinks_empty_when_no_mentions(self, client, tmp_note_pair):
        """'Zzz Unique Title Xyz' is not mentioned in any other note body."""
        note_unique = tmp_note_pair["note_unique"]
        response = client.get(f"/notes/{note_unique}/meta")
        assert response.status_code == 200
        data = response.get_json()
        assert data["backlinks"] == [], (
            f"Expected empty backlinks list, got: {data['backlinks']}"
        )

    def test_backlinks_case_insensitive(self, client, tmp_note_pair):
        """note_lower body has 'alice smith' (lowercase) — must still appear in backlinks."""
        note_a = tmp_note_pair["note_a"]
        note_lower = tmp_note_pair["note_lower"]
        response = client.get(f"/notes/{note_a}/meta")
        assert response.status_code == 200
        data = response.get_json()
        backlink_paths = [bl["path"] for bl in data["backlinks"]]
        assert str(note_lower) in backlink_paths, (
            f"Expected note_lower ({note_lower}) in backlinks (case-insensitive), got: {backlink_paths}"
        )
