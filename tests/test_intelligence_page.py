"""Phase 27.7: xfail stubs for Intelligence page backend endpoints.

Tests auto-promote to PASS once Wave 2 ships the /intelligence and /brain-health endpoints.

Run: uv run pytest tests/test_intelligence_page.py -v
"""
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
    for d in ["meetings", "people", "ideas", "projects"]:
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
        yield c


@pytest.mark.xfail(strict=False, reason="stub — auto-promotes when Wave 2 ships")
def test_get_intelligence(client):
    """GET /intelligence returns 200 with nudges list."""
    r = client.get("/intelligence")
    assert r.status_code == 200
    data = r.get_json()
    assert "nudges" in data


@pytest.mark.xfail(strict=False, reason="stub — auto-promotes when Wave 2 ships")
def test_post_recap(client):
    """POST /intelligence/recap returns 200 with recap string."""
    r = client.post("/intelligence/recap")
    assert r.status_code == 200
    data = r.get_json()
    assert "recap" in data
    assert isinstance(data["recap"], str)


@pytest.mark.xfail(strict=False, reason="stub — auto-promotes when get_empty_notes fix ships")
def test_get_brain_health(client):
    """GET /brain-health returns 200 with all required health keys."""
    r = client.get("/brain-health")
    assert r.status_code == 200
    data = r.get_json()
    assert "score" in data
    assert "orphan_count" in data
    assert "empty_count" in data
    assert "broken_link_count" in data
    assert "duplicate_count" in data
