"""Phase 27.4: Unit test scaffold for /api/people endpoint.

All tests are xfail(strict=False) — Wave 0 RED baseline.
Wave 1 (plan 27.4-02) will build the endpoint and make these green.

Run: uv run pytest tests/test_people.py -v
"""
import json
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
    for d in ["people", "ideas", "meetings"]:
        (brain / d).mkdir()

    tmp_db = Path(str(tmp_path / "test.db"))
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    conn = get_connection()
    init_schema(conn)
    conn.close()

    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c, brain


@pytest.mark.xfail(strict=False, reason="endpoint not yet implemented")
def test_list_people_endpoint(client):
    """GET /people returns 200 with a people key."""
    c, _ = client
    resp = c.get("/people")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "people" in data


@pytest.mark.xfail(strict=False, reason="endpoint not yet implemented")
def test_list_people_empty(client):
    """GET /people with no people notes returns {"people": []}."""
    c, _ = client
    resp = c.get("/people")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["people"] == []


@pytest.mark.xfail(strict=False, reason="endpoint not yet implemented")
def test_list_people_stats(client):
    """Note in people/ folder + 1 open action item -> open_actions=1, updated_at present."""
    import datetime
    from engine.db import get_connection

    c, brain = client

    # Insert a person note
    note_path = str(brain / "people" / "alice.md")
    now = datetime.datetime.utcnow().isoformat()
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (note_path, "Alice", "people", "Alice is a colleague.", "[]", now, now),
    )
    # Insert an open action item assigned to that person note
    conn.execute(
        "INSERT INTO action_items (note_path, text, done, assignee_path)"
        " VALUES (?,?,?,?)",
        (note_path, "Follow up with Alice", 0, note_path),
    )
    conn.commit()
    conn.close()

    resp = c.get("/people")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "people" in data
    assert len(data["people"]) == 1
    person = data["people"][0]
    assert person["open_actions"] == 1
    assert person["updated_at"] is not None
