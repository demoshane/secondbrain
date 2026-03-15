"""GDPR-02 export stubs — Wave 0 (xfail until implemented)."""
import pytest


@pytest.mark.xfail(strict=False, reason="Wave 0 stub — implementation pending")
def test_export_returns_note_count(brain_root, db_conn):
    from engine.export import export_brain
    from pathlib import Path

    output_path = brain_root / "export.json"
    count = export_brain(brain_root, db_conn, output_path)
    assert isinstance(count, int)


@pytest.mark.xfail(strict=False, reason="Wave 0 stub — implementation pending")
def test_export_json_contains_all_fields(brain_root, db_conn):
    import json
    from engine.export import export_brain
    from pathlib import Path

    output_path = brain_root / "export.json"
    export_brain(brain_root, db_conn, output_path)
    data = json.loads(output_path.read_text())
    assert len(data) > 0
    note = data[0]
    for field in ("path", "type", "title", "body", "tags", "people",
                   "created_at", "updated_at", "content_sensitivity"):
        assert field in note


@pytest.mark.xfail(strict=False, reason="Wave 0 stub — implementation pending")
def test_export_includes_pii_notes(brain_root, db_conn):
    from engine.export import export_brain
    import json

    output_path = brain_root / "export.json"
    export_brain(brain_root, db_conn, output_path)
    data = json.loads(output_path.read_text())
    pii_notes = [n for n in data if n.get("content_sensitivity") == "pii"]
    assert len(pii_notes) > 0


@pytest.mark.xfail(strict=False, reason="Wave 0 stub — implementation pending")
def test_export_audit_logged(brain_root, db_conn):
    from engine.export import export_brain

    output_path = brain_root / "export.json"
    export_brain(brain_root, db_conn, output_path)
    row = db_conn.execute(
        "SELECT id FROM audit_log WHERE event_type='export' LIMIT 1"
    ).fetchone()
    assert row is not None
