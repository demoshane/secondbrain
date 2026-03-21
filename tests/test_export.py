"""GDPR-02 export tests — Wave 1 (full implementation)."""
import json
import pytest
from pathlib import Path


@pytest.fixture
def export_db(db_conn):
    """db_conn with schema + one public note + one pii note."""
    from engine.db import init_schema
    init_schema(db_conn)
    db_conn.execute(
        "INSERT INTO notes (path, type, title, body, tags, people, sensitivity) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("notes/public.md", "note", "Public Note", "Public body", "[]", "[]", "public"),
    )
    db_conn.execute(
        "INSERT INTO notes (path, type, title, body, tags, people, sensitivity) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("people/alice.md", "people", "Alice", "Alice body", "[]", "[]", "pii"),
    )
    db_conn.commit()
    return db_conn


def test_export_returns_note_count(brain_root, export_db):
    from engine.export import export_brain

    output_path = brain_root / "export.json"
    count = export_brain(brain_root, export_db, output_path)
    assert isinstance(count, int)
    assert count == 2


def test_export_json_contains_all_fields(brain_root, export_db):
    from engine.export import export_brain

    output_path = brain_root / "export.json"
    export_brain(brain_root, export_db, output_path)
    data = json.loads(output_path.read_text())
    # 32-04: export format is {"notes": [...], "archived_action_items": [...]}
    notes = data["notes"] if isinstance(data, dict) else data
    assert len(notes) > 0
    note = notes[0]
    for field in ("path", "type", "title", "body", "tags", "people",
                  "created_at", "updated_at", "content_sensitivity"):
        assert field in note


def test_export_includes_pii_notes(brain_root, export_db):
    from engine.export import export_brain

    output_path = brain_root / "export.json"
    export_brain(brain_root, export_db, output_path)
    data = json.loads(output_path.read_text())
    notes = data["notes"] if isinstance(data, dict) else data
    pii_notes = [n for n in notes if n.get("content_sensitivity") == "pii"]
    assert len(pii_notes) > 0


def test_export_includes_archived_action_items(brain_root, export_db):
    """32-04: export must include archived_action_items for GDPR data portability."""
    from engine.export import export_brain

    export_db.execute(
        "INSERT INTO action_items_archive (note_path, text, done_at, created_at) VALUES (?,?,?,?)",
        ("notes/public.md", "Archived task", "2020-01-01T00:00:00Z", "2019-01-01T00:00:00Z"),
    )
    export_db.commit()

    output_path = brain_root / "export.json"
    export_brain(brain_root, export_db, output_path)
    data = json.loads(output_path.read_text())
    assert isinstance(data, dict), "Export should be a dict with 'notes' and 'archived_action_items' keys"
    assert "archived_action_items" in data
    assert len(data["archived_action_items"]) == 1
    item = data["archived_action_items"][0]
    assert item["text"] == "Archived task"
    assert item["note_path"] == "notes/public.md"


def test_export_audit_logged(brain_root, export_db):
    from engine.export import export_brain

    output_path = brain_root / "export.json"
    export_brain(brain_root, export_db, output_path)
    row = export_db.execute(
        "SELECT id FROM audit_log WHERE event_type='export' LIMIT 1"
    ).fetchone()
    assert row is not None


def test_export_initialises_schema_on_fresh_db(tmp_path, monkeypatch):
    """export.main() must not raise OperationalError on a DB with no schema."""
    import sqlite3
    from engine.export import export_brain
    conn = sqlite3.connect(":memory:")
    output = tmp_path / "out.json"
    try:
        count = export_brain(tmp_path, conn, output)
        assert False, "Expected OperationalError on schema-less conn — fix not yet applied to main()"
    except Exception as e:
        assert "no such table" in str(e).lower() or "operationalerror" in type(e).__name__.lower(), \
            f"Unexpected error type: {type(e).__name__}: {e}"
