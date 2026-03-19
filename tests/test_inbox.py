"""Phase 27.9: Unit test scaffold for Inbox backend endpoints.

All tests are xfail(strict=False) — Wave 1 RED baseline.
Wave 1 (plan 27.9-01 Task 2) will build the endpoints and make these green.

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

    # Seed: one unassigned open action item
    conn.execute(
        "INSERT INTO action_items (note_path, text, done, assignee_path)"
        " VALUES (?, ?, ?, ?)",
        (str(brain / "ideas" / "some-idea.md"), "Do something important", 0, None),
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


@pytest.mark.xfail(strict=False, reason="Wave 1 not yet shipped")
def test_inbox_endpoint(client):
    """GET /inbox returns 200 with keys: unassigned_actions, unprocessed_notes, empty_notes, total_count."""
    c, _brain, _up, _ep = client
    raise AssertionError("endpoint not yet implemented")


@pytest.mark.xfail(strict=False, reason="Wave 1 not yet shipped")
def test_unprocessed_excludes_structured_types(client):
    """Notes with type 'meeting' or 'people' do NOT appear in unprocessed_notes."""
    c, brain, _up, _ep = client
    raise AssertionError("endpoint not yet implemented")


@pytest.mark.xfail(strict=False, reason="Wave 1 not yet shipped")
def test_unprocessed_excludes_old_notes(client):
    """A note created 15 days ago does NOT appear in unprocessed_notes."""
    c, brain, _up, _ep = client
    raise AssertionError("endpoint not yet implemented")


@pytest.mark.xfail(strict=False, reason="Wave 1 not yet shipped")
def test_dismiss_persists(client):
    """POST /inbox/dismiss then GET /inbox — dismissed item absent from response."""
    c, _brain, _up, empty_path = client
    raise AssertionError("endpoint not yet implemented")


@pytest.mark.xfail(strict=False, reason="Wave 1 not yet shipped")
def test_relationships_create(client):
    """POST /relationships returns 200 {"created": true}; row exists in relationships table."""
    c, brain, unprocessed_path, _ep = client
    raise AssertionError("endpoint not yet implemented")
