"""Tests for engine/consolidate.py — scheduled consolidation job."""
import sqlite3
import pytest
from unittest.mock import patch
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


@pytest.fixture(autouse=True)
def _no_perf_benchmarks():
    """Prevent run_benchmarks() from writing to real brain during consolidate tests."""
    with patch("engine.perf.run_benchmarks", return_value={"results": []}):
        yield


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


# ---------------------------------------------------------------------------
# Phase 57: enrichment_sweep, stale_review, backlink_repair
# ---------------------------------------------------------------------------

def test_enrichment_sweep_queues_moderate_similarity(cons_conn):
    """enrichment_sweep queues pairs with similarity 0.80-0.92."""
    from engine.consolidate import enrichment_sweep
    from unittest.mock import MagicMock

    cons_conn.execute(
        "INSERT INTO notes (path, title, type, body, created_at, updated_at) VALUES (?,?,?,?,datetime('now'),datetime('now'))",
        ("a.md", "A", "note", "body A"),
    )
    cons_conn.execute(
        "INSERT INTO notes (path, title, type, body, created_at, updated_at) VALUES (?,?,?,?,datetime('now'),datetime('now'))",
        ("b.md", "B", "note", "body B"),
    )
    cons_conn.execute(
        "INSERT INTO note_embeddings (note_path, embedding) VALUES (?,?)",
        ("a.md", b"\x00" * 16),
    )
    cons_conn.commit()

    with patch("engine.intelligence.find_similar", return_value=[{"note_path": "b.md", "title": "B", "similarity": 0.85}]):
        result = enrichment_sweep(cons_conn)

    assert result["queued"] == 1
    row = cons_conn.execute("SELECT action, similarity FROM consolidation_queue WHERE status='pending'").fetchone()
    assert row[0] == "enrich"
    assert abs(row[1] - 0.85) < 0.01


def test_enrichment_sweep_skips_high_similarity(cons_conn):
    """enrichment_sweep skips pairs >= 0.92 (dup threshold)."""
    from engine.consolidate import enrichment_sweep

    cons_conn.execute("INSERT INTO note_embeddings (note_path, embedding) VALUES (?,?)", ("a.md", b"\x00" * 16))
    cons_conn.commit()

    with patch("engine.intelligence.find_similar", return_value=[{"note_path": "b.md", "title": "B", "similarity": 0.95}]):
        result = enrichment_sweep(cons_conn)

    assert result["queued"] == 0


def test_enrichment_sweep_skips_low_similarity(cons_conn):
    """enrichment_sweep doesn't queue pairs below 0.80 (find_similar threshold handles this)."""
    from engine.consolidate import enrichment_sweep

    cons_conn.execute("INSERT INTO note_embeddings (note_path, embedding) VALUES (?,?)", ("a.md", b"\x00" * 16))
    cons_conn.commit()

    with patch("engine.intelligence.find_similar", return_value=[]):
        result = enrichment_sweep(cons_conn)

    assert result["queued"] == 0


def test_enrichment_sweep_skips_dismissed(cons_conn):
    """enrichment_sweep skips pairs already dismissed."""
    import json as _json
    from engine.consolidate import enrichment_sweep

    pair = _json.dumps(["a.md", "b.md"])
    cons_conn.execute(
        "INSERT INTO consolidation_queue (action, source_paths, reason, detected_at, status) VALUES (?,?,?,datetime('now'),'dismissed')",
        ("enrich", pair, "test"),
    )
    cons_conn.execute("INSERT INTO note_embeddings (note_path, embedding) VALUES (?,?)", ("a.md", b"\x00" * 16))
    cons_conn.commit()

    with patch("engine.intelligence.find_similar", return_value=[{"note_path": "b.md", "title": "B", "similarity": 0.85}]):
        result = enrichment_sweep(cons_conn)

    assert result["queued"] == 0


def test_enrichment_sweep_skips_already_pending(cons_conn):
    """enrichment_sweep skips pairs already pending."""
    import json as _json
    from engine.consolidate import enrichment_sweep

    pair = _json.dumps(["a.md", "b.md"])
    cons_conn.execute(
        "INSERT INTO consolidation_queue (action, source_paths, reason, detected_at, status) VALUES (?,?,?,datetime('now'),'pending')",
        ("enrich", pair, "test"),
    )
    cons_conn.execute("INSERT INTO note_embeddings (note_path, embedding) VALUES (?,?)", ("a.md", b"\x00" * 16))
    cons_conn.commit()

    with patch("engine.intelligence.find_similar", return_value=[{"note_path": "b.md", "title": "B", "similarity": 0.85}]):
        result = enrichment_sweep(cons_conn)

    assert result["queued"] == 0


def test_enrichment_sweep_returns_counts(cons_conn):
    """enrichment_sweep returns scanned and queued counts."""
    from engine.consolidate import enrichment_sweep

    cons_conn.execute("INSERT INTO note_embeddings (note_path, embedding) VALUES (?,?)", ("a.md", b"\x00" * 16))
    cons_conn.execute("INSERT INTO note_embeddings (note_path, embedding) VALUES (?,?)", ("b.md", b"\x00" * 16))
    cons_conn.commit()

    with patch("engine.intelligence.find_similar", return_value=[]):
        result = enrichment_sweep(cons_conn)

    assert "queued" in result
    assert "scanned" in result
    assert result["scanned"] == 2


def test_stale_review_queues_old_low_access(cons_conn):
    """stale_review queues notes older than 90 days with low access."""
    from engine.consolidate import stale_review

    cons_conn.execute(
        "INSERT INTO notes (path, title, type, body, created_at, updated_at, access_count) VALUES (?,?,?,?,?,?,?)",
        ("old.md", "Old", "note", "old body", "2025-01-01T00:00:00Z", "2025-01-01T00:00:00Z", 0),
    )
    cons_conn.commit()

    result = stale_review(cons_conn)
    assert result["queued"] == 1


def test_stale_review_skips_high_access(cons_conn):
    """stale_review skips notes with access_count >= 3."""
    from engine.consolidate import stale_review

    cons_conn.execute(
        "INSERT INTO notes (path, title, type, body, created_at, updated_at, access_count) VALUES (?,?,?,?,?,?,?)",
        ("old.md", "Old", "note", "old body", "2025-01-01T00:00:00Z", "2025-01-01T00:00:00Z", 5),
    )
    cons_conn.commit()

    result = stale_review(cons_conn)
    assert result["queued"] == 0


def test_stale_review_skips_recent(cons_conn):
    """stale_review skips notes updated recently."""
    from engine.consolidate import stale_review

    cons_conn.execute(
        "INSERT INTO notes (path, title, type, body, created_at, updated_at, access_count) VALUES (?,?,?,?,?,datetime('now'),?)",
        ("recent.md", "Recent", "note", "body", "2025-01-01T00:00:00Z", 0),
    )
    cons_conn.commit()

    result = stale_review(cons_conn)
    assert result["queued"] == 0


def test_stale_review_handles_null_access_count(cons_conn):
    """stale_review treats NULL access_count as 0."""
    from engine.consolidate import stale_review

    cons_conn.execute(
        "INSERT INTO notes (path, title, type, body, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        ("old.md", "Old", "note", "body", "2025-01-01T00:00:00Z", "2025-01-01T00:00:00Z"),
    )
    cons_conn.commit()

    result = stale_review(cons_conn)
    assert result["queued"] == 1


def test_stale_review_skips_already_queued(cons_conn):
    """stale_review skips notes already queued as stale."""
    import json as _json
    from engine.consolidate import stale_review

    cons_conn.execute(
        "INSERT INTO notes (path, title, type, body, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        ("old.md", "Old", "note", "body", "2025-01-01T00:00:00Z", "2025-01-01T00:00:00Z"),
    )
    cons_conn.execute(
        "INSERT INTO consolidation_queue (action, source_paths, reason, detected_at, status) VALUES (?,?,?,datetime('now'),'pending')",
        ("stale", _json.dumps(["old.md"]), "test"),
    )
    cons_conn.commit()

    result = stale_review(cons_conn)
    assert result["queued"] == 0


def test_backlink_repair_replaces_wiki_link(cons_conn, tmp_path, monkeypatch):
    """backlink_repair fixes [[discard_path]] references using audit_log."""
    import engine.paths as _paths
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)
    from engine.consolidate import backlink_repair

    cons_conn.execute(
        "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?,?,?,datetime('now'))",
        ("merge", "keep.md", "merged:discard.md"),
    )
    note_file = tmp_path / "referrer.md"
    note_file.write_text("---\ntitle: Ref\n---\nSee [[discard.md]] here.", encoding="utf-8")
    cons_conn.execute(
        "INSERT INTO notes (path, title, type, body, created_at, updated_at) VALUES (?,?,?,?,datetime('now'),datetime('now'))",
        ("referrer.md", "Ref", "note", "See [[discard.md]] here."),
    )
    cons_conn.commit()

    result = backlink_repair(cons_conn)
    assert result["repaired_links"] == 1

    row = cons_conn.execute("SELECT body FROM notes WHERE path='referrer.md'").fetchone()
    assert "[[keep.md]]" in row[0]
    assert "[[discard.md]]" not in row[0]


def test_backlink_repair_scopes_to_7_days(cons_conn, tmp_path, monkeypatch):
    """backlink_repair ignores merges older than 7 days."""
    import engine.paths as _paths
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)
    from engine.consolidate import backlink_repair

    cons_conn.execute(
        "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?,?,?,datetime('now', '-30 days'))",
        ("merge", "keep.md", "merged:discard.md"),
    )
    cons_conn.execute(
        "INSERT INTO notes (path, title, type, body, created_at, updated_at) VALUES (?,?,?,?,datetime('now'),datetime('now'))",
        ("ref.md", "Ref", "note", "See [[discard.md]] here."),
    )
    cons_conn.commit()

    result = backlink_repair(cons_conn)
    assert result["repaired_links"] == 0


def test_backlink_repair_returns_counts(cons_conn, tmp_path, monkeypatch):
    """backlink_repair returns structured counts."""
    import engine.paths as _paths
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)
    from engine.consolidate import backlink_repair

    result = backlink_repair(cons_conn)
    assert "repaired_links" in result
    assert "repaired_synthesis_refs" in result
    assert "merges_checked" in result
    assert result["merges_checked"] == 0


def test_backlink_repair_no_merges_graceful(cons_conn, tmp_path, monkeypatch):
    """backlink_repair with empty audit_log returns zeros."""
    import engine.paths as _paths
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)
    from engine.consolidate import backlink_repair

    result = backlink_repair(cons_conn)
    assert result == {"repaired_links": 0, "repaired_synthesis_refs": 0, "merges_checked": 0}


def test_backlink_repair_synthesis_refs(cons_conn, tmp_path, monkeypatch):
    """backlink_repair repairs source_notes in synthesis frontmatter."""
    import engine.paths as _paths
    import frontmatter as _fm
    monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)
    from engine.consolidate import backlink_repair

    cons_conn.execute(
        "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?,?,?,datetime('now'))",
        ("merge", "keep.md", "merged:discard.md"),
    )
    synth_file = tmp_path / "synth.md"
    spost = _fm.Post("Synthesis body")
    spost["title"] = "Synth"
    spost["source_notes"] = ["discard.md", "other.md"]
    synth_file.write_text(_fm.dumps(spost), encoding="utf-8")
    cons_conn.execute(
        "INSERT INTO notes (path, title, type, body, created_at, updated_at) VALUES (?,?,?,?,datetime('now'),datetime('now'))",
        ("synth.md", "Synth", "synthesis", "Synthesis body"),
    )
    cons_conn.commit()

    result = backlink_repair(cons_conn)
    assert result["repaired_synthesis_refs"] == 1

    post = _fm.load(str(synth_file))
    assert "keep.md" in post.get("source_notes", [])
    assert "discard.md" not in post.get("source_notes", [])


def test_consolidate_main_full_integration(cons_conn, capsys):
    """consolidate_main includes enrichment_sweep, stale_review, backlink_repair."""
    from engine.consolidate import consolidate_main
    with patch("engine.intelligence.find_similar", return_value=[]):
        consolidate_main()
    import json
    result = json.loads(capsys.readouterr().out)
    assert "enrichment_sweep" in result
    assert "stale_review" in result
    assert "backlink_repair" in result
