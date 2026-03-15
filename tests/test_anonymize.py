"""GDPR-03 anonymize tests."""
import frontmatter as fm
import pytest


def _write_note(path, body, sensitivity="private"):
    """Write a minimal frontmatter note to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    post = fm.Post(body, title="Test Note", content_sensitivity=sensitivity)
    path.write_text(fm.dumps(post), encoding="utf-8")


def _seed_note(db, path, body, sensitivity="private"):
    """Insert or update a note row in the DB with an absolute path string."""
    existing = db.execute(
        "SELECT rowid FROM notes WHERE path=?", (str(path),)
    ).fetchone()
    if existing:
        db.execute(
            "UPDATE notes SET body=?, sensitivity=? WHERE path=?",
            (body, sensitivity, str(path)),
        )
    else:
        db.execute(
            "INSERT INTO notes (path, type, title, body, tags, people, sensitivity)"
            " VALUES (?, 'note', 'Test Note', ?, '[]', '[]', ?)",
            (str(path), body, sensitivity),
        )
    db.commit()


def test_anonymize_replaces_token_in_body(seeded_db, brain_root):
    from engine.anonymize import anonymize_note

    note_path = brain_root / "notes" / "anon_test_1.md"
    body = "Contact John Doe for details."
    _write_note(note_path, body)
    _seed_note(seeded_db, note_path, body)

    result = anonymize_note(note_path, ["John Doe"], seeded_db)

    updated = seeded_db.execute(
        "SELECT body FROM notes WHERE path=?", (str(note_path),)
    ).fetchone()[0]
    assert "[REDACTED]" in updated
    assert "John Doe" not in updated


def test_anonymize_case_insensitive(seeded_db, brain_root):
    from engine.anonymize import anonymize_note

    note_path = brain_root / "notes" / "anon_test_2.md"
    body = "Contact john doe today."
    _write_note(note_path, body)
    _seed_note(seeded_db, note_path, body)

    anonymize_note(note_path, ["John Doe"], seeded_db)

    updated = seeded_db.execute(
        "SELECT body FROM notes WHERE path=?", (str(note_path),)
    ).fetchone()[0]
    assert "[REDACTED]" in updated


def test_anonymize_updates_db_row(seeded_db, brain_root):
    from engine.anonymize import anonymize_note

    note_path = brain_root / "notes" / "anon_test_3.md"
    body = "Secret: Alice Smith."
    _write_note(note_path, body)
    _seed_note(seeded_db, note_path, body)

    anonymize_note(note_path, ["Alice Smith"], seeded_db)

    updated = seeded_db.execute(
        "SELECT body FROM notes WHERE path=?", (str(note_path),)
    ).fetchone()[0]
    assert "Alice Smith" not in updated


def test_anonymize_downgrades_sensitivity(seeded_db, brain_root):
    from engine.anonymize import anonymize_note

    note_path = brain_root / "notes" / "anon_test_4.md"
    body = "Contact Bob."
    _write_note(note_path, body, sensitivity="pii")
    _seed_note(seeded_db, note_path, body, sensitivity="pii")

    anonymize_note(note_path, ["Bob"], seeded_db, downgrade_sensitivity=True)

    sensitivity = seeded_db.execute(
        "SELECT sensitivity FROM notes WHERE path=?", (str(note_path),)
    ).fetchone()[0]
    assert sensitivity == "private"


def test_anonymize_audit_logged(seeded_db, brain_root):
    from engine.anonymize import anonymize_note

    note_path = brain_root / "notes" / "anon_test_5.md"
    body = "Data: Charlie."
    _write_note(note_path, body)
    _seed_note(seeded_db, note_path, body)

    anonymize_note(note_path, ["Charlie"], seeded_db)

    audit_row = seeded_db.execute(
        "SELECT id FROM audit_log WHERE event_type='anonymize' LIMIT 1"
    ).fetchone()
    assert audit_row is not None


def test_anonymize_noop_no_token_match(seeded_db, brain_root):
    from engine.anonymize import anonymize_note

    note_path = brain_root / "notes" / "anon_test_6.md"
    body = "Nothing sensitive here."
    _write_note(note_path, body)
    _seed_note(seeded_db, note_path, body)

    result = anonymize_note(note_path, ["NonExistentToken"], seeded_db)
    assert result.get("redacted_count", 0) == 0


def test_sb_anonymize_entry_point_registered():
    import importlib.metadata
    eps = {ep.name: ep for ep in importlib.metadata.entry_points(group="console_scripts")}
    assert "sb-anonymize" in eps, "sb-anonymize missing from [project.scripts] in pyproject.toml"
