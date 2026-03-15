"""GDPR-03 anonymize stubs — Wave 0 (xfail until implemented)."""
import pytest


@pytest.mark.xfail(strict=False, reason="Wave 0 stub — implementation pending")
def test_anonymize_replaces_token_in_body(seeded_db, brain_root):
    from engine.anonymize import anonymize_note
    from pathlib import Path

    # Insert a note with a known token in body
    seeded_db.execute(
        "UPDATE notes SET body='Contact John Doe for details.' WHERE rowid=1"
    )
    seeded_db.commit()
    row = seeded_db.execute("SELECT path FROM notes LIMIT 1").fetchone()
    path = brain_root / row[0]

    result = anonymize_note(path, ["John Doe"], seeded_db)
    updated = seeded_db.execute(
        "SELECT body FROM notes WHERE path=?", (row[0],)
    ).fetchone()[0]
    assert "[REDACTED]" in updated
    assert "John Doe" not in updated


@pytest.mark.xfail(strict=False, reason="Wave 0 stub — implementation pending")
def test_anonymize_case_insensitive(seeded_db, brain_root):
    from engine.anonymize import anonymize_note

    seeded_db.execute(
        "UPDATE notes SET body='Contact john doe today.' WHERE rowid=1"
    )
    seeded_db.commit()
    row = seeded_db.execute("SELECT path FROM notes LIMIT 1").fetchone()
    path = brain_root / row[0]

    anonymize_note(path, ["John Doe"], seeded_db)
    updated = seeded_db.execute(
        "SELECT body FROM notes WHERE path=?", (row[0],)
    ).fetchone()[0]
    assert "[REDACTED]" in updated


@pytest.mark.xfail(strict=False, reason="Wave 0 stub — implementation pending")
def test_anonymize_updates_db_row(seeded_db, brain_root):
    from engine.anonymize import anonymize_note

    seeded_db.execute(
        "UPDATE notes SET body='Secret: Alice Smith.' WHERE rowid=1"
    )
    seeded_db.commit()
    row = seeded_db.execute("SELECT path FROM notes LIMIT 1").fetchone()
    path = brain_root / row[0]

    anonymize_note(path, ["Alice Smith"], seeded_db)
    updated = seeded_db.execute(
        "SELECT body FROM notes WHERE path=?", (row[0],)
    ).fetchone()[0]
    assert "Alice Smith" not in updated


@pytest.mark.xfail(strict=False, reason="Wave 0 stub — implementation pending")
def test_anonymize_downgrades_sensitivity(seeded_db, brain_root):
    from engine.anonymize import anonymize_note

    seeded_db.execute(
        "UPDATE notes SET body='Contact Bob.', sensitivity='pii' WHERE rowid=1"
    )
    seeded_db.commit()
    row = seeded_db.execute("SELECT path FROM notes LIMIT 1").fetchone()
    path = brain_root / row[0]

    anonymize_note(path, ["Bob"], seeded_db, downgrade_sensitivity=True)
    sensitivity = seeded_db.execute(
        "SELECT sensitivity FROM notes WHERE path=?", (row[0],)
    ).fetchone()[0]
    assert sensitivity == "private"


@pytest.mark.xfail(strict=False, reason="Wave 0 stub — implementation pending")
def test_anonymize_audit_logged(seeded_db, brain_root):
    from engine.anonymize import anonymize_note

    seeded_db.execute(
        "UPDATE notes SET body='Data: Charlie.' WHERE rowid=1"
    )
    seeded_db.commit()
    row = seeded_db.execute("SELECT path FROM notes LIMIT 1").fetchone()
    path = brain_root / row[0]

    anonymize_note(path, ["Charlie"], seeded_db)
    audit_row = seeded_db.execute(
        "SELECT id FROM audit_log WHERE event_type='anonymize' LIMIT 1"
    ).fetchone()
    assert audit_row is not None


@pytest.mark.xfail(strict=False, reason="Wave 0 stub — implementation pending")
def test_anonymize_noop_no_token_match(seeded_db, brain_root):
    from engine.anonymize import anonymize_note

    seeded_db.execute(
        "UPDATE notes SET body='Nothing sensitive here.' WHERE rowid=1"
    )
    seeded_db.commit()
    row = seeded_db.execute("SELECT path FROM notes LIMIT 1").fetchone()
    path = brain_root / row[0]

    result = anonymize_note(path, ["NonExistentToken"], seeded_db)
    assert result.get("redacted_count", 0) == 0
