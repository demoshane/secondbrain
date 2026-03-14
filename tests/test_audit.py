import pytest


def test_audit_log_create_entry(tmp_path, initialized_db):
    from engine.capture import write_note_atomic, build_post  # noqa: F401 — fails until Plan 01
    pytest.fail("not implemented")


def test_audit_log_search_entry(seeded_db):
    from engine.search import search_notes

    search_notes(seeded_db, "topic_1")
    rows = seeded_db.execute(
        "SELECT event_type, detail FROM audit_log WHERE event_type='search'"
    ).fetchall()
    assert len(rows) >= 1
    assert rows[-1][0] == "search"
    assert rows[-1][1] == "topic_1"


def test_detect_secrets_baseline_clean():
    pytest.fail("not implemented")
