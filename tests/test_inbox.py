"""Phase 27.9: Unit tests for Inbox backend endpoints.

Run: uv run pytest tests/test_inbox.py -v
"""
import datetime
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
    for d in ["ideas", "people", "meetings", "coding"]:
        (brain / d).mkdir()

    tmp_db = Path(str(tmp_path / "test.db"))
    monkeypatch.setattr(_db, "DB_PATH", tmp_db)
    monkeypatch.setattr(_paths, "DB_PATH", tmp_db)
    monkeypatch.setenv("BRAIN_PATH", str(brain))

    conn = get_connection()
    init_schema(conn)

    now = datetime.datetime.utcnow().isoformat()

    # Seed: parent note for action item (FK constraint requires note to exist)
    action_note_path = str(brain / "ideas" / "some-idea.md")
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (action_note_path, "Some Idea", "ideas", "Action source.", "[]", now, now),
    )
    # Seed: one unassigned open action item
    conn.execute(
        "INSERT INTO action_items (note_path, text, done, assignee_path)"
        " VALUES (?, ?, ?, ?)",
        (action_note_path, "Do something important", 0, None),
    )

    # Seed: one unprocessed note (type='ideas', recent, no tags, no relationships)
    unprocessed_path = str(brain / "ideas" / "unprocessed-note.md")
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (unprocessed_path, "Unprocessed Idea", "ideas", "Some idea content.", "[]", now, now),
    )

    # Seed: one empty note
    empty_path = str(brain / "ideas" / "empty-note.md")
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (empty_path, "Empty Note", "ideas", "", "[]", now, now),
    )

    conn.commit()
    conn.close()

    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c, brain, unprocessed_path, empty_path


def test_inbox_endpoint(client):
    """GET /inbox returns 200 with keys: unassigned_actions, unprocessed_notes, empty_notes, total_count."""
    c, _brain, _up, _ep = client
    resp = c.get("/inbox")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "unassigned_actions" in data
    assert "unprocessed_notes" in data
    assert "empty_notes" in data
    assert "total_count" in data
    assert isinstance(data["unassigned_actions"], list)
    assert isinstance(data["unprocessed_notes"], list)
    assert isinstance(data["empty_notes"], list)
    assert isinstance(data["total_count"], int)


def test_unprocessed_excludes_structured_types(client):
    """Notes with type 'meeting' or 'people' do NOT appear in unprocessed_notes."""
    from engine.db import get_connection
    c, brain, _up, _ep = client

    now = datetime.datetime.utcnow().isoformat()
    conn = get_connection()
    meeting_path = str(brain / "meetings" / "weekly.md")
    people_path = str(brain / "people" / "alice.md")
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (meeting_path, "Weekly Meeting", "meeting", "Discussion notes.", "[]", now, now),
    )
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (people_path, "Alice", "people", "Alice info.", "[]", now, now),
    )
    conn.commit()
    conn.close()

    resp = c.get("/inbox")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    paths = [n["path"] for n in data["unprocessed_notes"]]
    assert meeting_path not in paths
    assert people_path not in paths


def test_unprocessed_excludes_old_notes(client):
    """A note created 15 days ago does NOT appear in unprocessed_notes."""
    from engine.db import get_connection
    c, brain, _up, _ep = client

    old_ts = (datetime.datetime.utcnow() - datetime.timedelta(days=15)).isoformat()
    old_path = str(brain / "ideas" / "old-note.md")
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (old_path, "Old Note", "ideas", "Old content.", "[]", old_ts, old_ts),
    )
    conn.commit()
    conn.close()

    resp = c.get("/inbox")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    paths = [n["path"] for n in data["unprocessed_notes"]]
    assert old_path not in paths


def test_dismiss_persists(client):
    """POST /inbox/dismiss then GET /inbox — dismissed item absent from response."""
    c, _brain, _up, empty_path = client

    # Empty note should appear before dismiss
    resp = c.get("/inbox")
    data = json.loads(resp.data)
    empty_paths = [n["path"] for n in data["empty_notes"]]
    assert empty_path in empty_paths

    # Dismiss it
    resp2 = c.post(
        "/inbox/dismiss",
        data=json.dumps({"path": empty_path, "item_type": "note"}),
        content_type="application/json",
    )
    assert resp2.status_code == 200
    assert json.loads(resp2.data) == {"dismissed": True}

    # Should not appear after dismiss
    resp3 = c.get("/inbox")
    data3 = json.loads(resp3.data)
    empty_paths3 = [n["path"] for n in data3["empty_notes"]]
    assert empty_path not in empty_paths3


def test_relationships_create(client):
    """POST /relationships returns 200 {"created": true}; row exists in relationships table."""
    from engine.db import get_connection
    c, brain, unprocessed_path, _ep = client

    target_path = str(brain / "ideas" / "target-note.md")
    now = datetime.datetime.utcnow().isoformat()
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, title, type, body, tags, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (target_path, "Target Note", "ideas", "", "[]", now, now),
    )
    conn.commit()
    conn.close()
    resp = c.post(
        "/relationships",
        data=json.dumps({"source_path": unprocessed_path, "target_path": target_path}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert json.loads(resp.data) == {"created": True}

    conn = get_connection()
    row = conn.execute(
        "SELECT source_path, target_path, rel_type FROM relationships WHERE source_path=? AND target_path=?",
        (unprocessed_path, target_path),
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[2] == "connection"
