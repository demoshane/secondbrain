import time

import pytest


def test_search_returns_match(seeded_db):
    from engine.search import search_notes

    results = search_notes(seeded_db, "topic_0")
    assert len(results) > 0
    for r in results:
        assert set(r.keys()) >= {"path", "type", "title", "created_at", "score"}
    # best-match first: most-negative score comes first
    assert results[0]["score"] <= results[-1]["score"]


def test_search_type_filter(seeded_db):
    from engine.search import search_notes

    seeded_db.execute(
        "INSERT INTO notes (path, type, title, body, tags, people) VALUES (?, ?, ?, ?, ?, ?)",
        ("notes/meeting_unique.md", "meeting", "Unique Meeting", "unique_meeting_keyword", "[]", "[]"),
    )
    seeded_db.commit()

    results = search_notes(seeded_db, "unique_meeting_keyword", note_type="meeting")
    assert len(results) == 1
    assert results[0]["type"] == "meeting"

    results_wrong_type = search_notes(seeded_db, "unique_meeting_keyword", note_type="note")
    assert results_wrong_type == []


def test_search_1000_notes_perf(seeded_db):
    from engine.search import search_notes

    start = time.monotonic()
    results = search_notes(seeded_db, "topic_0")
    elapsed = time.monotonic() - start
    assert elapsed < 2.0, f"Search took {elapsed:.2f}s, expected < 2s"
    assert len(results) > 0
