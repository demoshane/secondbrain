"""Tests for engine.forget — GDPR-01 (person erasure) and GDPR-02 (meeting cleanup).

All tests are xfail (strict=True): they must fail RED before implementation.
Deferred imports inside test bodies so pytest --collect-only works without engine.forget existing.
"""
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture()
def brain_tmp(tmp_path: Path):
    """Temp brain root with people/ and meetings/ subdirs and in-memory SQLite."""
    from engine.db import init_schema

    (tmp_path / "people").mkdir()
    (tmp_path / "meetings").mkdir()
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    yield tmp_path, conn
    conn.close()


def test_forget_deletes_person_file(brain_tmp):
    """forget_person removes the person's file from people/."""
    from engine.forget import forget_person

    brain_root, conn = brain_tmp
    person_file = brain_root / "people" / "alice-smith.md"
    person_file.write_text("---\nname: Alice Smith\n---\n")

    forget_person("alice-smith", brain_root, conn)

    assert not person_file.exists()


def test_forget_deletes_sole_reference_meeting(brain_tmp):
    """Meeting whose only attendee is the forgotten person is deleted."""
    from engine.forget import forget_person

    brain_root, conn = brain_tmp
    sole_meeting = brain_root / "meetings" / "2024-01-01-alice-solo.md"
    sole_meeting.write_text("---\npeople: [alice-smith]\n---\n")
    multi_meeting = brain_root / "meetings" / "2024-01-02-alice-bob.md"
    multi_meeting.write_text("---\npeople: [alice-smith, bob-jones]\n---\n")

    forget_person("alice-smith", brain_root, conn)

    assert not sole_meeting.exists()


def test_forget_spares_shared_meeting(brain_tmp):
    """Meeting with multiple attendees survives after one attendee is forgotten."""
    from engine.forget import forget_person

    brain_root, conn = brain_tmp
    sole_meeting = brain_root / "meetings" / "2024-01-01-alice-solo.md"
    sole_meeting.write_text("---\npeople: [alice-smith]\n---\n")
    multi_meeting = brain_root / "meetings" / "2024-01-02-alice-bob.md"
    multi_meeting.write_text("---\npeople: [alice-smith, bob-jones]\n---\n")

    forget_person("alice-smith", brain_root, conn)

    assert multi_meeting.exists()


def test_forget_cleans_backlinks(brain_tmp):
    """Lines containing the slug are removed from note bodies after forget."""
    from engine.forget import forget_person

    brain_root, conn = brain_tmp
    note = brain_root / "meetings" / "2024-01-03-notes.md"
    note.write_text(
        "---\npeople: [bob-jones]\n---\nMet with alice-smith today.\nBob was present.\n"
    )

    forget_person("alice-smith", brain_root, conn)

    content = note.read_text()
    assert "alice-smith" not in content


def test_search_zero_after_forget(brain_tmp):
    """engine.search.search_notes returns empty list after person is forgotten."""
    from engine.forget import forget_person
    import engine.search as search_mod

    brain_root, conn = brain_tmp

    forget_person("alice-smith", brain_root, conn)

    results = search_mod.search_notes(conn, "alice-smith")
    assert results == []


def test_fts5_rebuild_after_forget(brain_tmp):
    """forget_person issues an FTS5 'rebuild' SQL command to keep index consistent."""
    from engine.forget import forget_person
    from engine.db import init_schema

    # Use a spy subclass — sqlite3.Connection.execute is read-only in Python 3.14+
    class SpyConnection(sqlite3.Connection):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._executed_sql: list[str] = []

        def execute(self, sql, *args, **kwargs):
            self._executed_sql.append(sql)
            return super().execute(sql, *args, **kwargs)

    brain_root, _conn = brain_tmp
    spy_conn = SpyConnection(":memory:")
    init_schema(spy_conn)

    forget_person("alice-smith", brain_root, spy_conn)

    assert any("rebuild" in sql.lower() for sql in spy_conn._executed_sql)
    spy_conn.close()


def test_forget_removes_notes_row_from_db(brain_tmp):
    """forget_person deletes the person's row from the notes table."""
    from engine.forget import forget_person

    brain_root, conn = brain_tmp
    person_path = str(brain_root / "people" / "alice-smith.md")
    conn.execute(
        "INSERT INTO notes (path, type, title, body, tags) VALUES (?, ?, ?, ?, ?)",
        (person_path, "person", "Alice Smith", "", "[]"),
    )
    conn.commit()

    forget_person("alice-smith", brain_root, conn)

    row = conn.execute("SELECT 1 FROM notes WHERE path = ?", (person_path,)).fetchone()
    assert row is None


def test_forget_removes_relationships_from_db(brain_tmp):
    """forget_person deletes relationships where the person is source or target."""
    from engine.forget import forget_person

    brain_root, conn = brain_tmp
    person_path = str(brain_root / "people" / "alice-smith.md")
    other_path = str(brain_root / "notes" / "other.md")
    # Insert parent notes rows first to satisfy FK constraints on relationships
    conn.execute(
        "INSERT OR IGNORE INTO notes (path, title, type, body, created_at, updated_at)"
        " VALUES (?, 'Alice Smith', 'person', '', datetime('now'), datetime('now'))",
        (person_path,),
    )
    conn.execute(
        "INSERT OR IGNORE INTO notes (path, title, type, body, created_at, updated_at)"
        " VALUES (?, 'Other Note', 'note', '', datetime('now'), datetime('now'))",
        (other_path,),
    )
    conn.execute(
        "INSERT INTO relationships (source_path, target_path) VALUES (?, ?)",
        (person_path, other_path),
    )
    conn.execute(
        "INSERT INTO relationships (source_path, target_path) VALUES (?, ?)",
        (other_path, person_path),
    )
    conn.commit()

    forget_person("alice-smith", brain_root, conn)

    rows = conn.execute(
        "SELECT 1 FROM relationships WHERE source_path = ? OR target_path = ?",
        (person_path, person_path),
    ).fetchall()
    assert rows == []


def test_forget_removes_prior_audit_log_entries(brain_tmp):
    """forget_person deletes prior audit_log rows referencing the person's path."""
    from engine.forget import forget_person

    brain_root, conn = brain_tmp
    person_path = str(brain_root / "people" / "alice-smith.md")
    conn.execute(
        "INSERT INTO audit_log (event_type, note_path) VALUES (?, ?)",
        ("read", person_path),
    )
    conn.commit()

    forget_person("alice-smith", brain_root, conn)

    row = conn.execute(
        "SELECT 1 FROM audit_log WHERE note_path = ?", (person_path,)
    ).fetchone()
    assert row is None


def test_forget_logs_erasure_event_in_audit_log(brain_tmp):
    """forget_person writes a 'forget' audit event with detail 'person:<slug>'."""
    from engine.forget import forget_person

    brain_root, conn = brain_tmp

    forget_person("alice-smith", brain_root, conn)

    row = conn.execute(
        "SELECT detail FROM audit_log WHERE event_type = 'forget'"
    ).fetchone()
    assert row is not None
    assert row[0] == "person:alice-smith"


def test_forget_nonexistent_person_is_noop(brain_tmp):
    """forget_person on an unknown slug returns empty lists and does not raise."""
    from engine.forget import forget_person

    brain_root, conn = brain_tmp

    result = forget_person("nobody-here", brain_root, conn)

    assert result["deleted_files"] == []
    assert result["cleaned_backlinks"] == []
    assert result["errors"] == []


# ---------------------------------------------------------------------------
# Phase 7: Forget after capture — path consistency (GDPR-01)
# ---------------------------------------------------------------------------

def test_forget_removes_row_stored_by_capture(tmp_path):
    """forget_person must delete the DB row for a note stored by capture_note (no reindex)."""
    import sqlite3
    from engine.db import init_schema
    from engine.capture import write_note_atomic, build_post
    from engine.forget import forget_person

    brain_root = tmp_path.resolve() / "brain"
    (brain_root / "people").mkdir(parents=True)
    (brain_root / "meetings").mkdir(parents=True)

    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(notes)").fetchall()}
    if "people" not in cols:
        conn.execute("ALTER TABLE notes ADD COLUMN people TEXT NOT NULL DEFAULT '[]'")
    conn.commit()

    target = brain_root / "people" / "carol-danvers.md"
    post = build_post("people", "Carol Danvers", "profile body", [], [], "public")
    write_note_atomic(target, post, conn)

    forget_person("carol-danvers", brain_root, conn)

    row = conn.execute(
        "SELECT 1 FROM notes WHERE title = ?", ("Carol Danvers",)
    ).fetchone()
    assert row is None, "forget_person must delete the row that capture stored"
    conn.close()


# ---------------------------------------------------------------------------
# Phase 37-04: forget_person NULLs assignee_path
# ---------------------------------------------------------------------------

def test_forget_person_nulls_assignee_path(brain_tmp):
    """forget_person NULLs assignee_path for all erased person paths."""
    from engine.forget import forget_person

    brain_root, conn = brain_tmp
    slug = "dave-smith"
    person_file = brain_root / "people" / f"{slug}.md"
    person_file.write_text("---\ntitle: Dave Smith\ntype: person\n---\n")

    person_path = str(person_file)
    conn.execute(
        "INSERT OR IGNORE INTO notes (path, title, type, body, created_at, updated_at)"
        " VALUES (?, 'Dave Smith', 'person', '', datetime('now'), datetime('now'))",
        (person_path,),
    )
    # Insert parent note for 'other.md' to satisfy FK on action_items.note_path
    conn.execute(
        "INSERT OR IGNORE INTO notes (path, title, type, body, created_at, updated_at)"
        " VALUES ('other.md', 'Other Note', 'note', '', datetime('now'), datetime('now'))"
    )
    conn.execute(
        "INSERT INTO action_items (note_path, text, assignee_path) VALUES ('other.md', 'Task', ?)",
        (person_path,),
    )
    conn.commit()

    forget_person(slug, brain_root, conn)

    row = conn.execute(
        "SELECT assignee_path FROM action_items WHERE note_path='other.md'"
    ).fetchone()
    assert row is not None
    assert row[0] is None, "forget_person should NULL assignee_path for erased person"
