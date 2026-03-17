"""Regression test suite for search quality (ENGL-02).

All tests are marked xfail(strict=False) — they document the ranking contract
and will auto-promote to PASS once BM25 weight tuning ships in Wave 2.
"""
import pytest
from engine.db import get_connection, init_schema
from engine.search import search_notes


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

PRECISION_NOTES = [
    ("people", "Alice Johnson", "Project manager at Acme Corp."),
    ("people", "Bob Smith", "Engineer on the backend team."),
    ("meeting", "Q3 Planning Session", "Roadmap priorities for Q3."),
    ("meeting", "Design Review", "UI patterns reviewed."),
    ("note", "Python", "Short single-word title note."),
]

RECALL_NOTES = [
    ("note", "Random Note A", "The quarterly roadmap includes python and deployment."),
    ("note", "Random Note B", "Backend systems need resilience improvements."),
    ("note", "Team Update", "Alice is leading the new initiative."),
    ("note", "Architecture Note", "Service mesh patterns for microservices."),
    ("note", "Weekly Sync", "Alice and Bob discussed roadmap items."),
]


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def reg_conn(tmp_path_factory):
    """Isolated DB with precision and recall notes seeded."""
    db_path = tmp_path_factory.mktemp("reg_db") / "test.db"
    conn = get_connection(str(db_path))
    init_schema(conn)

    all_notes = PRECISION_NOTES + RECALL_NOTES
    for note_type, title, body in all_notes:
        path = f"/brain/{note_type}/{title.replace(' ', '-').lower()}.md"
        conn.execute(
            "INSERT INTO notes (path, type, title, body, tags, people) VALUES (?, ?, ?, ?, ?, ?)",
            (path, note_type, title, body, "[]", "[]"),
        )
    conn.commit()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Precision tests — exact match at top position
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="BM25 weights not yet applied")
def test_precision_person_full_name(reg_conn):
    """'Alice Johnson' should rank first for exact full-name query."""
    results = search_notes(reg_conn, "Alice Johnson")
    assert len(results) > 0
    assert results[0]["title"] == "Alice Johnson"


@pytest.mark.xfail(strict=False, reason="BM25 weights not yet applied")
def test_precision_partial_name(reg_conn):
    """'Alice' should surface 'Alice Johnson' in top 3."""
    results = search_notes(reg_conn, "Alice")
    titles = [r["title"] for r in results[:3]]
    assert "Alice Johnson" in titles


@pytest.mark.xfail(strict=False, reason="BM25 weights not yet applied")
def test_precision_meeting_title(reg_conn):
    """'Q3 Planning Session' should rank first for exact meeting title query."""
    results = search_notes(reg_conn, "Q3 Planning Session")
    assert len(results) > 0
    assert results[0]["title"] == "Q3 Planning Session"


@pytest.mark.xfail(strict=False, reason="BM25 weights not yet applied")
def test_precision_partial_meeting(reg_conn):
    """'Q3 Planning' should surface 'Q3 Planning Session' in top 3."""
    results = search_notes(reg_conn, "Q3 Planning")
    titles = [r["title"] for r in results[:3]]
    assert "Q3 Planning Session" in titles


@pytest.mark.xfail(strict=False, reason="BM25 weights not yet applied")
def test_precision_short_title(reg_conn):
    """'Python' should rank first for exact single-word title query."""
    results = search_notes(reg_conn, "Python")
    assert len(results) > 0
    assert results[0]["title"] == "Python"


# ---------------------------------------------------------------------------
# Recall tests — relevant note appears within top 5
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=False, reason="BM25 weights not yet applied")
def test_recall_body_topic(reg_conn):
    """'quarterly roadmap' should surface 'Random Note A' in top 5."""
    results = search_notes(reg_conn, "quarterly roadmap")
    titles = [r["title"] for r in results[:5]]
    assert "Random Note A" in titles


@pytest.mark.xfail(strict=False, reason="BM25 weights not yet applied")
def test_recall_semantic_synonym(reg_conn):
    """'resilience' should surface 'Random Note B' in top 5."""
    results = search_notes(reg_conn, "resilience")
    titles = [r["title"] for r in results[:5]]
    assert "Random Note B" in titles


@pytest.mark.xfail(strict=False, reason="BM25 weights not yet applied")
def test_recall_partial_name(reg_conn):
    """'Alice' should return at least one result with 'Alice' in title or body."""
    results = search_notes(reg_conn, "Alice")
    assert len(results) > 0
    matched = [
        r for r in results
        if "alice" in r["title"].lower() or "alice" in r.get("body", "").lower()
    ]
    assert len(matched) >= 1


@pytest.mark.xfail(strict=False, reason="BM25 weights not yet applied")
def test_recall_body_keyword(reg_conn):
    """'microservices' should surface 'Architecture Note' in top 5."""
    results = search_notes(reg_conn, "microservices")
    titles = [r["title"] for r in results[:5]]
    assert "Architecture Note" in titles


@pytest.mark.xfail(strict=False, reason="BM25 weights not yet applied")
def test_recall_mixed_content(reg_conn):
    """'Alice Bob' should surface 'Weekly Sync' in top 5."""
    results = search_notes(reg_conn, "Alice Bob")
    titles = [r["title"] for r in results[:5]]
    assert "Weekly Sync" in titles
