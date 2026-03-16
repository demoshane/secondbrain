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
def tmp_note(tmp_path):
    """Create a real temporary .md file with valid frontmatter; yield its absolute path."""
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
    def test_read_missing_note_404(self, client):
        response = client.get("/notes/nonexistent%2Fpath.md")
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
