"""Phase 26 Wave 0: xfail stubs for ENGL-04 and ENGL-05 (brain health checks)."""
import pytest
import sqlite3
from pathlib import Path
from unittest.mock import patch

from engine.db import init_schema


@pytest.fixture
def conn(tmp_path):
    db = tmp_path / "test.db"
    c = sqlite3.connect(str(db))
    init_schema(c)
    yield c
    c.close()


@pytest.fixture
def client(tmp_path):
    """API test client with isolated SQLite DB."""
    import engine.db as _db
    import engine.paths as _paths
    tmp_db = tmp_path / "test.db"
    old_db_path = _db.DB_PATH
    old_paths_db = _paths.DB_PATH
    _db.DB_PATH = tmp_db
    _paths.DB_PATH = tmp_db
    # Init schema
    c = sqlite3.connect(str(tmp_db))
    init_schema(c)
    c.close()
    from engine.api import app
    app.config["TESTING"] = True
    with app.test_client() as tc:
        yield tc
    _db.DB_PATH = old_db_path
    _paths.DB_PATH = old_paths_db


@pytest.mark.xfail(strict=False, reason="engine/brain_health.py not yet implemented")
def test_get_orphan_notes_returns_notes_with_no_inbound_links(conn):
    # Insert a note with no relationships — should appear as orphan
    from engine.brain_health import get_orphan_notes
    conn.execute("INSERT INTO notes (path, title, type, body, sensitivity) VALUES (?, ?, ?, ?, ?)",
                 ("/brain/orphan.md", "Orphan Note", "note", "body", "public"))
    conn.commit()
    result = get_orphan_notes(conn)
    assert any(r["path"] == "/brain/orphan.md" for r in result)


@pytest.mark.xfail(strict=False, reason="engine/brain_health.py not yet implemented")
def test_get_orphan_notes_excludes_digest_and_memory_types(conn):
    from engine.brain_health import get_orphan_notes
    conn.execute("INSERT INTO notes (path, title, type, body, sensitivity) VALUES (?, ?, ?, ?, ?)",
                 ("/brain/digests/2026-W12.md", "Digest", "digest", "body", "public"))
    conn.commit()
    result = get_orphan_notes(conn)
    paths = [r["path"] for r in result]
    assert "/brain/digests/2026-W12.md" not in paths


@pytest.mark.xfail(strict=False, reason="engine/brain_health.py not yet implemented")
def test_get_duplicate_candidates_returns_pairs_above_threshold(conn):
    from engine.brain_health import get_duplicate_candidates
    # No embeddings in fixture — expect [] (no crash)
    result = get_duplicate_candidates(conn, threshold=0.92)
    assert isinstance(result, list)


@pytest.mark.xfail(strict=False, reason="engine/brain_health.py not yet implemented")
def test_compute_health_score_returns_100_for_clean_brain():
    from engine.brain_health import compute_health_score
    assert compute_health_score(total_notes=50, orphans=0, broken=0, duplicates=0) == 100


@pytest.mark.xfail(strict=False, reason="engine/brain_health.py not yet implemented")
def test_compute_health_score_reduces_for_orphans():
    from engine.brain_health import compute_health_score
    score_clean = compute_health_score(50, 0, 0, 0)
    score_orphans = compute_health_score(50, 25, 0, 0)  # 50% orphan ratio
    assert score_orphans < score_clean


@pytest.mark.xfail(strict=False, reason="engine/brain_health.py not yet implemented")
def test_compute_health_score_zero_notes_returns_100():
    from engine.brain_health import compute_health_score
    assert compute_health_score(total_notes=0, orphans=0, broken=0, duplicates=0) == 100


@pytest.mark.xfail(strict=False, reason="GET /brain-health not yet implemented")
def test_brain_health_api_returns_score_and_checks(client):
    # Uses local client fixture — isolated SQLite DB
    resp = client.get("/brain-health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "score" in data
    assert "orphans" in data
    assert "broken_links" in data
    assert "duplicate_candidates" in data
    assert isinstance(data["score"], int)
    assert 0 <= data["score"] <= 100
