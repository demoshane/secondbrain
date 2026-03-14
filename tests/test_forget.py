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
