"""Tests for engine/consolidate.py — scheduled consolidation job."""
import sqlite3
import pytest
from engine.db import init_schema


@pytest.fixture
def cons_conn(tmp_path):
    import engine.db as _db
    import engine.paths as _paths
    db_path = tmp_path / "consolidate_test.db"
    _db.DB_PATH = db_path
    _paths.DB_PATH = db_path
    conn = sqlite3.connect(str(db_path))
    init_schema(conn)
    yield conn
    conn.close()


def test_consolidate_main_runs_clean(cons_conn, capsys):
    from engine.consolidate import consolidate_main
    consolidate_main()
    captured = capsys.readouterr()
    import json
    result = json.loads(captured.out)
    assert "archived_actions" in result
    assert "deleted_dangling" in result
    assert "snapshot" in result
    assert "cleaned_old_snapshots" in result


def test_consolidate_idempotent(cons_conn, capsys):
    from engine.consolidate import consolidate_main
    consolidate_main()
    consolidate_main()  # second run should not error
    # Snapshot should be skipped on second run (one-per-day guard)
    lines = capsys.readouterr().out.strip().split("\n")
    import json
    second = json.loads(lines[1])
    assert second["snapshot"]["skipped"] is True


def test_synthesize_clusters_empty(cons_conn):
    """synthesize_clusters returns 0 clusters on empty brain."""
    from engine.consolidate import synthesize_clusters
    result = synthesize_clusters(cons_conn)
    assert result["clusters_found"] == 0
    assert result["syntheses_created"] == 0


def test_synthesize_clusters_creates_note(cons_conn, tmp_path, monkeypatch):
    """synthesize_clusters creates a synthesis note for a qualifying cluster."""
    import datetime
    import engine.paths as _paths
    from engine.consolidate import synthesize_clusters
    from unittest.mock import MagicMock

    brain_root = tmp_path / "brain"
    (brain_root / "syntheses").mkdir(parents=True)
    monkeypatch.setattr(_paths, "BRAIN_ROOT", brain_root)

    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")
    for i in range(3):
        cons_conn.execute(
            "INSERT INTO notes (path, type, title, body, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (f"meetings/m{i}.md", "meeting", f"Meeting {i}", f"Discussion about ProjectX iteration {i}", now, now),
        )
        cons_conn.execute(
            "INSERT OR IGNORE INTO note_people (note_path, person) VALUES (?,?)",
            (f"meetings/m{i}.md", "person/alice.md"),
        )
    cons_conn.commit()

    # Mock the AI adapter to return a canned synthesis
    mock_adapter = MagicMock()
    mock_adapter.generate.return_value = "## Summary\nProjectX is progressing."
    mock_router = MagicMock()
    mock_router.get_adapter.return_value = mock_adapter
    monkeypatch.setattr("engine.intelligence._router", mock_router)

    result = synthesize_clusters(cons_conn)
    assert result["clusters_found"] >= 1
    assert result["syntheses_created"] >= 1

    # Verify synthesis note was written
    syntheses = list((brain_root / "syntheses").glob("*.md"))
    assert len(syntheses) >= 1
    content = syntheses[0].read_text(encoding="utf-8")
    assert "synthesis" in content.lower()


def test_synthesize_clusters_dedup(cons_conn, tmp_path, monkeypatch):
    """synthesize_clusters skips clusters that already have a recent synthesis."""
    import datetime
    import engine.paths as _paths
    from engine.consolidate import synthesize_clusters
    from unittest.mock import MagicMock

    brain_root = tmp_path / "brain"
    (brain_root / "syntheses").mkdir(parents=True)
    monkeypatch.setattr(_paths, "BRAIN_ROOT", brain_root)

    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")
    note_paths = []
    for i in range(3):
        path = f"meetings/m{i}.md"
        note_paths.append(path)
        cons_conn.execute(
            "INSERT INTO notes (path, type, title, body, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (path, "meeting", f"Meeting {i}", f"About ProjectX {i}", now, now),
        )
        cons_conn.execute(
            "INSERT OR IGNORE INTO note_people (note_path, person) VALUES (?,?)",
            (path, "person/alice.md"),
        )

    # Pre-insert an existing synthesis that covers these notes
    body_with_refs = "Synthesis\n" + "\n".join(note_paths)
    cons_conn.execute(
        "INSERT INTO notes (path, type, title, body, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        ("syntheses/existing.md", "synthesis", "Existing", body_with_refs, now, now),
    )
    cons_conn.commit()

    mock_adapter = MagicMock()
    mock_adapter.generate.return_value = "New synthesis"
    mock_router = MagicMock()
    mock_router.get_adapter.return_value = mock_adapter
    monkeypatch.setattr("engine.intelligence._router", mock_router)

    result = synthesize_clusters(cons_conn)
    assert result["skipped_existing"] >= 1


def test_consolidate_main_includes_synthesis(cons_conn, capsys):
    """consolidate_main output includes synthesis results."""
    from engine.consolidate import consolidate_main
    consolidate_main()
    import json
    result = json.loads(capsys.readouterr().out)
    assert "synthesis" in result
