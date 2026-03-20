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

    Sets BRAIN_PATH to tmp_path and patches DB_PATH to a temp DB so no real
    ~/SecondBrain data is touched.
    """
    import engine.db as _db
    import engine.paths as _paths
    from engine.db import init_schema

    tmp_db = tmp_path / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))

    conn = get_connection()
    init_schema(conn)
    conn.commit()
    conn.close()

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
    # tmp_path cleaned up by pytest; monkeypatch reverts DB_PATH


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
    @pytest.fixture(autouse=True)
    def _isolate_db(self, tmp_path, monkeypatch):
        import engine.db as _db
        import engine.paths as _paths
        from engine.db import init_schema
        tmp_db = tmp_path / "test.db"
        monkeypatch.setattr(_db, "DB_PATH", tmp_db)
        monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
        conn = get_connection()
        init_schema(conn)
        conn.commit()
        conn.close()

    def test_actions_returns_200(self, client):
        response = client.get("/actions")
        assert response.status_code == 200

    def test_actions_has_actions_key(self, client):
        response = client.get("/actions")
        assert "actions" in response.get_json()

    @pytest.mark.xfail(strict=False, reason="GPAG-02: done filter not yet implemented")
    def test_actions_filter_done_param(self, client):
        """GET /actions?done=1 returns only items with done=1."""
        response = client.get("/actions?done=1")
        assert response.status_code == 200
        data = response.get_json()
        assert "actions" in data
        for item in data["actions"]:
            assert item["done"] == 1

    @pytest.mark.xfail(strict=False, reason="GPAG-02: assignee filter not yet implemented")
    def test_actions_filter_assignee(self, client):
        """GET /actions?assignee=people/alice.md returns only items with that assignee_path."""
        from engine.db import get_connection
        conn = get_connection()
        conn.execute(
            "INSERT INTO action_items (note_path, body, done, assignee_path)"
            " VALUES (?, ?, 0, ?)",
            ("notes/test.md", "Test action for alice", "people/alice.md"),
        )
        conn.commit()
        conn.close()

        response = client.get("/actions?assignee=people/alice.md")
        assert response.status_code == 200
        data = response.get_json()
        assert "actions" in data
        paths = [item.get("assignee_path") for item in data["actions"]]
        assert "people/alice.md" in paths
        for item in data["actions"]:
            assert item.get("assignee_path") == "people/alice.md"

    @pytest.mark.xfail(strict=False, reason="GPAG-02: PUT /actions/<id> not yet implemented")
    def test_action_assign(self, client):
        """PUT /actions/<id> with assignee_path returns {"updated": True}."""
        from engine.db import get_connection
        conn = get_connection()
        cursor = conn.execute(
            "INSERT INTO action_items (note_path, body, done) VALUES (?, ?, 0)",
            ("notes/test-assign.md", "Action to assign"),
        )
        item_id = cursor.lastrowid
        conn.commit()
        conn.close()

        response = client.put(f"/actions/{item_id}", json={"assignee_path": "people/alice.md"})
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("updated") is True

    @pytest.mark.xfail(strict=False, reason="GPAG-02: my-actions filter not yet implemented")
    def test_my_actions(self, client):
        """GET /actions?assignee=people/alice.md&done=0 excludes done items."""
        from engine.db import get_connection
        conn = get_connection()
        conn.execute(
            "INSERT INTO action_items (note_path, body, done, assignee_path)"
            " VALUES (?, ?, 0, ?)",
            ("notes/my-actions-open.md", "Open action for alice", "people/alice.md"),
        )
        conn.execute(
            "INSERT INTO action_items (note_path, body, done, assignee_path)"
            " VALUES (?, ?, 1, ?)",
            ("notes/my-actions-done.md", "Done action for alice", "people/alice.md"),
        )
        conn.commit()
        conn.close()

        response = client.get("/actions?assignee=people/alice.md&done=0")
        assert response.status_code == 200
        data = response.get_json()
        assert "actions" in data
        for item in data["actions"]:
            assert item.get("done") == 0
            assert item.get("assignee_path") == "people/alice.md"


@pytest.fixture
def tmp_note_pair(tmp_path, monkeypatch):
    """Create temp .md files and insert them into SQLite for backlinks testing."""
    import engine.db as _db
    import engine.paths as _paths
    from engine.db import init_schema

    tmp_db = tmp_path / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))

    conn = get_connection()
    init_schema(conn)
    conn.commit()
    conn.close()

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
    # tmp_path cleaned up by pytest; monkeypatch reverts DB_PATH automatically


class TestCreateNote:
    @pytest.fixture(autouse=True)
    def _isolate_db(self, tmp_path, monkeypatch):
        import engine.db as _db
        import engine.paths as _paths
        from engine.db import init_schema
        tmp_db = tmp_path / "test.db"
        monkeypatch.setattr(_db, "DB_PATH", tmp_db)
        monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
        conn = get_connection()
        init_schema(conn)
        conn.commit()
        conn.close()

    def test_create_note_returns_201(self, client, tmp_path, monkeypatch):
        """POST /notes returns 201 and a path."""
        monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
        res = client.post("/notes", json={"title": "My Note", "type": "idea", "body": "", "brain_path": str(tmp_path)})
        assert res.status_code == 201
        data = res.get_json()
        assert "path" in data

    def test_create_note_indexed_in_sqlite(self, client, tmp_path, monkeypatch):
        """POST /notes immediately indexes the note into SQLite so GET /notes returns it."""
        monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
        res = client.post("/notes", json={"title": "Indexed Note", "type": "idea", "body": "", "brain_path": str(tmp_path)})
        assert res.status_code == 201
        note_path = res.get_json()["path"]
        conn = get_connection()
        row = conn.execute("SELECT title FROM notes WHERE path=?", (note_path,)).fetchone()
        conn.close()
        assert row is not None, "New note must be present in SQLite immediately after creation"
        assert row[0] == "Indexed Note"

    def test_create_note_file_exists_on_disk(self, client, tmp_path, monkeypatch):
        """POST /notes writes the markdown file to disk."""
        monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
        res = client.post("/notes", json={"title": "Disk Note", "type": "idea", "body": "hello", "brain_path": str(tmp_path)})
        note_path = res.get_json()["path"]
        assert Path(note_path).exists(), "Note file must exist on disk after creation"

    def test_create_note_slug_collision_resolved(self, client, tmp_path, monkeypatch):
        """Two notes with the same title get distinct paths (no overwrite)."""
        monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
        payload = {"title": "Dup Note", "type": "idea", "body": "", "brain_path": str(tmp_path)}
        r1 = client.post("/notes", json=payload)
        r2 = client.post("/notes", json=payload)
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.get_json()["path"] != r2.get_json()["path"], "Duplicate titles must produce distinct paths"


class TestUIPrefs:
    def test_get_prefs_empty(self, client, tmp_path, monkeypatch):
        """GET /ui/prefs returns {} when no prefs file exists."""
        monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
        res = client.get("/ui/prefs")
        assert res.status_code == 200
        assert res.get_json() == {}

    def test_put_and_get_prefs(self, client, tmp_path, monkeypatch):
        """PUT /ui/prefs persists data; GET /ui/prefs reads it back."""
        monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
        prefs = {"collapseState": {"recent": True, "projects": False}}
        put_res = client.put("/ui/prefs", json=prefs)
        assert put_res.status_code == 200
        get_res = client.get("/ui/prefs")
        assert get_res.get_json() == prefs


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


class TestNoteMetaPeopleColumn:
    """Regression tests: people comes only from people column, not body-mention scanning."""

    @pytest.fixture
    def meta_env(self, tmp_path, monkeypatch):
        """Isolated DB + BRAIN_PATH for note_meta people tests."""
        import engine.db as _db
        import engine.paths as _paths
        from engine.db import init_schema

        tmp_db = tmp_path / "test.db"
        monkeypatch.setattr(_db, "DB_PATH", tmp_db)
        monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
        monkeypatch.setenv("BRAIN_PATH", str(tmp_path))

        conn = get_connection()
        init_schema(conn)
        conn.commit()
        conn.close()
        return tmp_path

    def test_note_meta_no_body_fallback(self, client, meta_env):
        """Body mentions a person name, but people column is empty — person must NOT appear."""
        tmp_path = meta_env

        # Create a person note
        person_dir = tmp_path / "person"
        person_dir.mkdir()
        person_note = person_dir / "john-doe.md"
        person_note.write_text(
            "---\ntitle: John Doe\ntype: person\npeople: []\n---\nProfile of John Doe.\n",
            encoding="utf-8",
        )

        # Create a content note whose body mentions "John Doe" but people column is empty
        content_note = tmp_path / "meeting-notes.md"
        content_note.write_text(
            "---\ntitle: Meeting Notes\ntype: note\npeople: []\n---\nWe met with John Doe today.\n",
            encoding="utf-8",
        )

        # Insert both notes into SQLite
        conn = get_connection()
        conn.execute(
            "INSERT INTO notes (path, title, type, body, people, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            (str(person_note.resolve()), "John Doe", "person", "Profile of John Doe.", "[]"),
        )
        conn.execute(
            "INSERT INTO notes (path, title, type, body, people, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            (str(content_note.resolve()), "Meeting Notes", "note",
             "We met with John Doe today.", "[]"),
        )
        conn.commit()
        conn.close()

        response = client.get(f"/notes/{content_note.resolve()}/meta")
        assert response.status_code == 200
        data = response.get_json()
        people_titles = [p["title"] for p in data["people"]]
        assert "John Doe" not in people_titles, (
            f"Body-mention fallback must be gone — 'John Doe' should not appear when "
            f"people column is empty. Got: {people_titles}"
        )

    def test_note_meta_people_from_column(self, client, meta_env):
        """People column contains a person path — must resolve to {{path, title}}."""
        tmp_path = meta_env

        person_dir = tmp_path / "person"
        person_dir.mkdir()
        person_note = person_dir / "jane-smith.md"
        person_note.write_text(
            "---\ntitle: Jane Smith\ntype: person\n---\nProfile.\n",
            encoding="utf-8",
        )

        person_path = str(person_note.resolve())
        import json as _json
        content_note = tmp_path / "project-note.md"
        content_note.write_text(
            f"---\ntitle: Project Note\ntype: note\npeople:\n  - {person_path}\n---\nDetails.\n",
            encoding="utf-8",
        )

        conn = get_connection()
        conn.execute(
            "INSERT INTO notes (path, title, type, body, people, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            (person_path, "Jane Smith", "person", "Profile.", "[]"),
        )
        conn.execute(
            "INSERT INTO notes (path, title, type, body, people, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            (str(content_note.resolve()), "Project Note", "note", "Details.",
             _json.dumps([person_path])),
        )
        conn.commit()
        conn.close()

        response = client.get(f"/notes/{content_note.resolve()}/meta")
        assert response.status_code == 200
        data = response.get_json()
        people_paths = [p["path"] for p in data["people"]]
        people_titles = [p["title"] for p in data["people"]]
        assert person_path in people_paths, (
            f"Person from people column must appear. Got paths: {people_paths}"
        )
        assert "Jane Smith" in people_titles, (
            f"Person title must be resolved. Got titles: {people_titles}"
        )


class TestTabBar:
    @pytest.mark.xfail(strict=False, reason="GPAG-01: tab bar not yet implemented")
    def test_tab_bar_html(self, client):
        r = client.get("/ui")
        assert r.status_code == 200
        assert b'id="tab-bar"' in r.data
