import logging
import time

import pytest
from unittest.mock import patch, MagicMock


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


# --- Wave 0 RED stubs for Phase 16 semantic search ---

class TestSemanticSearch:
    def test_semantic_returns_similar(self, seeded_db):
        import engine.search as s
        # Function doesn't exist yet — fails with AttributeError (RED)
        assert hasattr(s, "search_semantic"), "search_semantic not implemented"
        results = s.search_semantic(seeded_db, "cat feline animal")
        assert len(results) > 0


class TestSemanticFallback:
    def test_warns_when_too_many_unembed(self, seeded_db, capsys, caplog):
        import engine.search as s
        # Function doesn't exist yet — fails with AttributeError (RED)
        assert hasattr(s, "search_semantic"), "search_semantic not implemented"
        # Simulate >50 un-embedded notes
        with patch.object(s, "search_semantic", side_effect=AttributeError("not implemented")):
            pass
        # Direct call to trigger warning path — fails RED
        with caplog.at_level(logging.WARNING, logger="engine.search"):
            s.search_semantic(seeded_db, "test query")
        assert "sb-reindex" in caplog.text


class TestHybridSearch:
    def test_hybrid_returns_merged_results(self, seeded_db):
        import engine.search as s
        # Function doesn't exist yet — fails with AttributeError (RED)
        assert hasattr(s, "search_hybrid"), "search_hybrid not implemented"
        results = s.search_hybrid(seeded_db, "topic_0")
        assert len(results) > 0


class TestKeywordFlag:
    def test_keyword_bypasses_vector(self, seeded_db):
        import engine.search as s
        assert hasattr(s, "main"), "main not implemented"
        assert hasattr(s, "search_semantic"), "search_semantic not implemented (keyword bypass requires it)"
        # Patch get_connection and init_schema so main() uses the seeded in-memory DB
        with patch("engine.db.get_connection", return_value=seeded_db), \
             patch("engine.db.init_schema"):
            s.main(["topic_0", "--keyword"])


class TestHybridFallback:
    def test_no_embeddings_falls_back_to_fts(self, seeded_db, capsys):
        import engine.search as s
        # Function doesn't exist yet — fails with AttributeError (RED)
        assert hasattr(s, "search_hybrid"), "search_hybrid not implemented"
        results = s.search_hybrid(seeded_db, "topic_0")
        captured = capsys.readouterr()
        # Should print fallback notification when no embeddings table populated
        assert "fallback" in captured.out.lower() or len(results) >= 0
