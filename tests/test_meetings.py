"""Phase 27.5: Unit tests for GET /meetings and GET /meetings/<path> endpoints.

Tests are xfail(strict=False) — auto-promote to PASS once Task 2 ships the endpoints.

Run: uv run pytest tests/test_meetings.py -v
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
    for d in ["meetings", "people", "ideas"]:
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


def seed_meeting(conn, brain):
    """Insert a test meeting note into SQLite."""
    import datetime
    note_path = str(brain / "meetings" / "q1-kickoff.md")
    now = "2026-03-01 09:00:00"
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, people, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (note_path, "Q1 Kickoff", "meeting", "Q1 Kickoff notes", '["Alice"]', "[]", now, now),
    )
    conn.commit()
    return note_path


@pytest.mark.xfail(strict=False, reason="endpoint not yet implemented")
def test_list_meetings(client):
    """GET /meetings returns 200 with meetings list; each item has required keys."""
    from engine.db import get_connection
    c, brain = client
    conn = get_connection()
    seed_meeting(conn, brain)
    conn.close()

    resp = c.get("/meetings")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "meetings" in data
    assert len(data["meetings"]) >= 1
    item = data["meetings"][0]
    assert "path" in item
    assert "title" in item
    assert "meeting_date" in item
    assert "participant_count" in item
    assert "open_actions" in item


@pytest.mark.xfail(strict=False, reason="endpoint not yet implemented")
def test_meeting_detail(client):
    """GET /meetings/<path> returns 200 with full meeting detail."""
    from engine.db import get_connection
    c, brain = client
    conn = get_connection()
    note_path = seed_meeting(conn, brain)
    conn.close()

    # Encode the absolute path as a URL path segment (strip leading slash)
    enc = note_path.lstrip("/")
    resp = c.get(f"/meetings/{enc}")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "path" in data
    assert "title" in data
    assert "meeting_date" in data
    assert "participants" in data
    assert isinstance(data["participants"], list)
    assert "open_actions" in data


def test_participant_objects_with_person(client):
    """GET /meetings/<path> returns participants as [{name, path}] when person note exists."""
    from engine.db import get_connection
    c, brain = client
    conn = get_connection()

    now = "2026-03-01 09:00:00"
    person_rel = "people/alice.md"
    meeting_rel = "meetings/sync.md"

    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (person_rel, "Alice", "person", "", "[]", now, now),
    )
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, people, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (meeting_rel, "Sync", "meeting", "", '["Alice"]', "[]", now, now),
    )
    conn.commit()
    conn.close()

    abs_meeting = str(brain / meeting_rel)
    enc = abs_meeting.lstrip("/")
    resp = c.get(f"/meetings/{enc}")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert isinstance(data["participants"], list)
    assert len(data["participants"]) == 1
    p = data["participants"][0]
    assert p["name"] == "Alice"
    assert p["path"] == person_rel


def test_participant_objects_no_person(client):
    """GET /meetings/<path> returns participants with path=null when no person note exists."""
    from engine.db import get_connection
    c, brain = client
    conn = get_connection()

    now = "2026-03-01 09:00:00"
    meeting_rel = "meetings/mystery.md"
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, people, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (meeting_rel, "Mystery", "meeting", "", '["Unknown Person"]', "[]", now, now),
    )
    conn.commit()
    conn.close()

    abs_meeting = str(brain / meeting_rel)
    enc = abs_meeting.lstrip("/")
    resp = c.get(f"/meetings/{enc}")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data["participants"]) == 1
    p = data["participants"][0]
    assert p["name"] == "Unknown Person"
    assert p["path"] is None
    assert isinstance(data["open_actions"], int)
