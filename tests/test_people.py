"""Phase 27.4 + 30-04: Unit tests for /people endpoint.

Tests cover:
  - Basic endpoint existence (from 27.4 stubs)
  - Enriched fields: org, last_interaction, mention_count (Phase 30-04)
  - Person type isolation: both 'person' and 'people' types appear; plain 'note' does not
"""
import json
import datetime
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


def test_list_people_endpoint(client):
    """GET /people returns 200 with a people key."""
    c, _ = client
    resp = c.get("/people")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "people" in data


def test_list_people_empty(client):
    """GET /people with no people notes returns {"people": []}."""
    c, _ = client
    resp = c.get("/people")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["people"] == []


def test_list_people_stats(client):
    """Note in people/ folder + 1 open action item -> open_actions=1, updated_at present."""
    from engine.db import get_connection

    c, brain = client

    note_path = str(brain / "people" / "alice.md")
    now = datetime.datetime.utcnow().isoformat()
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (note_path, "Alice", "people", "Alice is a colleague.", "[]", now, now),
    )
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


def test_list_people_enriched(client):
    """Enriched fields: org extracted from entities JSON, last_interaction from meeting people
    column, mention_count >= 1 for a person referenced in a non-person note."""
    from engine.db import get_connection

    c, brain = client

    person_path = str(brain / "people" / "bob.md")
    meeting_path = str(brain / "meetings" / "q1-review.md")
    now = datetime.datetime.utcnow().isoformat()
    entities_json = json.dumps({"orgs": ["Acme Corp"], "people": ["Bob"], "topics": []})

    conn = get_connection()
    # Person note with org in entities
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, entities, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (person_path, "Bob", "person", "Bob works at Acme Corp.", "[]", entities_json, now, now),
    )
    # Meeting note that references bob via people column
    people_json = json.dumps([person_path])
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, people, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (meeting_path, "Q1 Review", "meeting", "Met with Bob.", "[]", people_json, now, now),
    )
    # Populate note_people junction table (ARCH-15)
    conn.execute(
        "INSERT OR IGNORE INTO note_people (note_path, person) VALUES (?, ?)",
        (meeting_path, person_path),
    )
    conn.commit()
    conn.close()

    resp = c.get("/people")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    people = data["people"]
    assert len(people) == 1
    person = people[0]
    assert person["org"] == "Acme Corp"
    assert person["last_interaction"] is not None
    assert person["mention_count"] >= 1


def test_person_type_isolation(client):
    """Both type='person' and type='people' appear; plain type='note' does NOT."""
    from engine.db import get_connection

    c, brain = client

    now = datetime.datetime.utcnow().isoformat()
    person_path = str(brain / "people" / "carol.md")
    people_path = str(brain / "people" / "group.md")
    note_path = str(brain / "ideas" / "random.md")

    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (person_path, "Carol", "person", "Carol is a person.", "[]", now, now),
    )
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (people_path, "Engineering Group", "people", "A group note.", "[]", now, now),
    )
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (note_path, "Random Idea", "note", "Just an idea.", "[]", now, now),
    )
    conn.commit()
    conn.close()

    resp = c.get("/people")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    paths = [p["path"] for p in data["people"]]
    assert person_path in paths, "type='person' must appear"
    assert people_path in paths, "type='people' must appear"
    assert note_path not in paths, "type='note' must NOT appear"


def test_create_person_post_happy_path(client, monkeypatch):
    """POST /people with name returns 201 and a path to the created note."""
    from engine.db import get_connection
    import engine.capture as _capture

    c, brain = client

    # Patch capture_note to avoid real filesystem writes + intelligence hooks
    created = {}

    def _fake_capture(note_type, title, body, tags, people, content_sensitivity, brain_root, conn, **kw):
        p = brain / "people" / f"{title.lower().replace(' ', '-')}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"---\ntitle: {title}\ntype: {note_type}\n---\n", encoding="utf-8")
        path_str = str(p)
        conn.execute(
            "INSERT OR IGNORE INTO notes (path, title, type, body, tags, created_at, updated_at)"
            " VALUES (?,?,?,?,?,datetime('now'),datetime('now'))",
            (path_str, title, note_type, body, "[]"),
        )
        conn.commit()
        created["path"] = path_str
        return p

    monkeypatch.setattr(_capture, "capture_note", _fake_capture)

    resp = c.post("/people", json={"name": "Dana Koskinen", "role": "Engineer"})
    assert resp.status_code == 201, resp.data
    data = json.loads(resp.data)
    assert "path" in data
    assert data["path"]  # non-empty path


def test_create_person_missing_name(client):
    """POST /people without name returns 400."""
    c, _ = client
    resp = c.post("/people", json={})
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert "error" in data


def test_delete_person_clears_assignee(client):
    """DELETE /people/<path> NULLs assignee_path in action_items before deleting note."""
    from engine.db import get_connection
    import datetime

    c, brain = client

    # Create a person note file
    person_path_obj = brain / "people" / "erika.md"
    person_path_obj.parent.mkdir(parents=True, exist_ok=True)
    person_path_obj.write_text("---\ntitle: Erika\ntype: people\n---\n", encoding="utf-8")
    person_path_str = str(person_path_obj)

    now = datetime.datetime.utcnow().isoformat()
    conn = get_connection()
    # Insert person note into DB
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (person_path_str, "Erika", "people", "", "[]", now, now),
    )
    # Insert an action item assigned to this person
    conn.execute(
        "INSERT INTO action_items (note_path, text, done, assignee_path) VALUES (?,?,?,?)",
        (person_path_str, "Follow up", 0, person_path_str),
    )
    conn.commit()
    conn.close()

    # Encode the path — Flask test client handles URL encoding
    encoded = person_path_str.lstrip("/")
    resp = c.delete(f"/people/{encoded}")
    assert resp.status_code == 200, resp.data

    # Verify assignee_path was NULLed
    conn = get_connection()
    row = conn.execute(
        "SELECT assignee_path FROM action_items WHERE text = 'Follow up'"
    ).fetchone()
    conn.close()
    # Row should either be deleted (cascade) or have NULL assignee_path
    assert row is None or row[0] is None, f"Expected NULL assignee_path but got: {row}"
