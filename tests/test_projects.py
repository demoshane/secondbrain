"""Phase 27.6: Unit tests for GET /projects and GET /projects/<path> endpoints.

Run: uv run pytest tests/test_projects.py -v
"""
import json
import urllib.parse
import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    """Flask test client with isolated brain dir and SQLite DB."""
    import engine.db as _db
    import engine.paths as _paths
    from engine.api import app as flask_app
    from engine.db import init_schema, get_connection
    from pathlib import Path

    brain = tmp_path / "brain"
    brain.mkdir()
    for d in ["projects", "people", "ideas"]:
        (brain / d).mkdir()

    tmp_db = Path(str(tmp_path / "test.db"))
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "BRAIN_ROOT", brain)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    conn = get_connection()
    init_schema(conn)
    conn.close()

    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c, brain


def seed_project(conn, brain):
    """Insert a test project note into SQLite using relative path (Phase 32+)."""
    abs_path = brain / "projects" / "alpha.md"
    rel_path = "projects/alpha.md"  # relative to brain root as stored by Phase 32
    now = "2026-03-01 09:00:00"
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?)",
        (rel_path, "Alpha Project", "projects", "Alpha project body text", now, now),
    )
    conn.commit()
    return str(abs_path)  # return absolute path for URL encoding


def test_list_projects_empty(client):
    """GET /projects returns 200 with {"projects": []} when no project notes exist."""
    c, brain = client
    resp = c.get("/projects")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "projects" in data
    assert data["projects"] == []


def test_list_projects(client):
    """GET /projects returns list with path, title, updated_at, open_actions when one project seeded."""
    from engine.db import get_connection
    c, brain = client
    conn = get_connection()
    seed_project(conn, brain)
    conn.close()

    resp = c.get("/projects")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "projects" in data
    assert len(data["projects"]) >= 1
    item = data["projects"][0]
    assert "path" in item
    assert "title" in item
    assert "updated_at" in item
    assert "open_actions" in item


def test_list_projects_open_actions_count(client):
    """open_actions = 1 when one undone action_item seeded for that project path."""
    from engine.db import get_connection
    c, brain = client
    conn = get_connection()
    note_path = seed_project(conn, brain)
    conn.execute(
        "INSERT INTO action_items (note_path, text, done) VALUES (?, ?, ?)",
        ("projects/alpha.md", "Do thing", 0),  # relative path matches Phase 32 storage
    )
    conn.commit()
    conn.close()

    resp = c.get("/projects")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data["projects"]) >= 1
    item = data["projects"][0]
    assert item["open_actions"] == 1


def test_project_detail(client):
    """GET /projects/<url-encoded-path> returns 200 with path, title, body, updated_at, open_actions."""
    from engine.db import get_connection
    c, brain = client
    conn = get_connection()
    note_path = seed_project(conn, brain)
    conn.close()

    enc = urllib.parse.quote(note_path.lstrip("/"), safe="")
    resp = c.get(f"/projects/{enc}")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "path" in data
    assert "title" in data
    assert "body" in data
    assert "updated_at" in data
    assert "open_actions" in data
    assert isinstance(data["open_actions"], int)


def test_project_detail_not_found(client):
    """GET /projects/<path> returns 404 when path is inside brain but not in DB."""
    c, brain = client
    # Build an absolute path inside the brain so _resolve_note_path doesn't raise ValueError
    missing = str(brain / "projects" / "missing.md")
    enc = urllib.parse.quote(missing.lstrip("/"), safe="")
    resp = c.get(f"/projects/{enc}")
    assert resp.status_code == 404


def test_project_detail_forbidden(client):
    """GET /projects/..%2F..%2Fetc%2Fpasswd returns 403 or 404 (path traversal guard)."""
    c, brain = client
    resp = c.get("/projects/..%2F..%2Fetc%2Fpasswd")
    assert resp.status_code in (403, 404)
