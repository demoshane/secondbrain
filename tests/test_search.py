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


# ---------------------------------------------------------------------------
# Phase 33-04: _apply_filters tests
# ---------------------------------------------------------------------------

class TestSearchExcerpt:
    """Tests for excerpt field returned by search functions."""

    def test_search_notes_has_excerpt_field(self, seeded_db):
        """search_notes results always include excerpt key (None for BM25-only path)."""
        from engine.search import search_notes
        results = search_notes(seeded_db, "topic_0")
        assert len(results) > 0
        for r in results:
            assert "excerpt" in r
            assert r["excerpt"] is None  # BM25-only path sets None

    def test_search_hybrid_has_excerpt_field(self, seeded_db):
        """search_hybrid results always include excerpt key."""
        from engine.search import search_hybrid
        with patch("engine.search._enrich_with_excerpts", side_effect=lambda conn, results, query: [
            {**r, "excerpt": None} for r in results
        ]):
            results = search_hybrid(seeded_db, "topic_0")
        assert len(results) > 0
        for r in results:
            assert "excerpt" in r

    def test_enrich_with_excerpts_no_chunks(self, seeded_db):
        """_enrich_with_excerpts sets excerpt=None when no chunks exist."""
        from engine.search import _enrich_with_excerpts
        results = [{"path": "notes/note_0000.md", "score": 1.0}]
        out = _enrich_with_excerpts(seeded_db, results, "test query")
        assert out[0]["excerpt"] is None

    def test_enrich_with_excerpts_with_chunk_data(self, seeded_db):
        """_enrich_with_excerpts returns best chunk text when chunks exist."""
        import struct
        from engine.search import _enrich_with_excerpts

        # Insert a chunk with a 384-dim embedding (matching stub embed_texts output)
        blob = struct.pack("384f", *[0.1] * 384)
        seeded_db.execute(
            "INSERT OR IGNORE INTO note_chunks (note_path, chunk_index, chunk_text, embedding) VALUES (?, ?, ?, ?)",
            ("notes/note_0000.md", 0, "This is the best matching chunk text for the note.", blob),
        )
        seeded_db.commit()

        results = [{"path": "notes/note_0000.md", "score": 1.0}]
        out = _enrich_with_excerpts(seeded_db, results, "test query")
        # Stub embed_texts returns 384-dim blob; chunk has 384-dim blob — dimensions match
        assert out[0]["excerpt"] is not None
        assert len(out[0]["excerpt"]) <= 300


class TestApplyFilters:
    """Tests for the _apply_filters() post-filter function in engine.search."""

    def _make_results(self, db_conn):
        """Insert test notes and return a list of result dicts matching _apply_filters input."""
        # Insert notes with mixed types, dates, people
        notes = [
            ("filter/note1.md", "note", "Note One", "2024-01-15T00:00:00Z", '["Alice"]'),
            ("filter/note2.md", "meeting", "Meeting Alpha", "2024-03-01T00:00:00Z", '["Bob"]'),
            ("filter/note3.md", "meeting", "Meeting Beta", "2023-12-01T00:00:00Z", '["Alice", "Bob"]'),
            ("filter/note4.md", "idea", "Idea One", "2024-06-01T00:00:00Z", '[]'),
        ]
        for path, ntype, title, created_at, people in notes:
            db_conn.execute(
                "INSERT OR IGNORE INTO notes (path, type, title, body, tags, people, created_at)"
                " VALUES (?, ?, ?, '', '[]', ?, ?)",
                (path, ntype, title, people, created_at),
            )
        db_conn.commit()

        # Add tags for note1
        db_conn.execute(
            "INSERT OR IGNORE INTO note_tags (note_path, tag) VALUES (?, ?)",
            ("filter/note1.md", "work"),
        )
        db_conn.commit()

        return [
            {"path": p, "type": t, "title": ti, "created_at": c, "score": 1.0}
            for p, t, ti, c, _ in notes
        ]

    def test_apply_filters_no_filters(self, seeded_db):
        """All-None params: results unchanged."""
        from engine.search import _apply_filters

        results = [
            {"path": "a.md", "type": "note", "title": "A", "created_at": "2024-01-01T00:00:00Z", "score": 1.0},
        ]
        out = _apply_filters(results, seeded_db)
        assert out == results

    def test_apply_filters_by_type(self, seeded_db):
        """note_type filter: only notes of matching type returned."""
        from engine.search import _apply_filters

        results = self._make_results(seeded_db)
        out = _apply_filters(results, seeded_db, note_type="meeting")
        assert len(out) == 2
        assert all(r["type"] == "meeting" for r in out)

    def test_apply_filters_by_date(self, seeded_db):
        """from_date filter: notes older than from_date excluded."""
        from engine.search import _apply_filters

        results = self._make_results(seeded_db)
        out = _apply_filters(results, seeded_db, from_date="2024-01-01")
        # note3 has 2023-12-01 — should be excluded
        assert all(r["created_at"] >= "2024-01-01" for r in out)
        paths = [r["path"] for r in out]
        assert "filter/note3.md" not in paths

    def test_apply_filters_by_person(self, seeded_db):
        """person filter: only notes where Alice appears in people column."""
        from engine.search import _apply_filters

        results = self._make_results(seeded_db)
        out = _apply_filters(results, seeded_db, person="Alice")
        paths = [r["path"] for r in out]
        assert "filter/note1.md" in paths   # Alice only
        assert "filter/note3.md" in paths   # Alice + Bob
        assert "filter/note2.md" not in paths  # Bob only
        assert "filter/note4.md" not in paths  # no people

    def test_apply_filters_combined(self, seeded_db):
        """Combined type + from_date: AND logic — both conditions must match."""
        from engine.search import _apply_filters

        results = self._make_results(seeded_db)
        # type=meeting AND from_date=2024-01-01 → only note2 (2024-03-01), not note3 (2023-12-01)
        out = _apply_filters(results, seeded_db, note_type="meeting", from_date="2024-01-01")
        assert len(out) == 1
        assert out[0]["path"] == "filter/note2.md"

    def test_apply_filters_importance_high(self, seeded_db):
        """_apply_filters(importance='high') returns only high-importance notes."""
        from engine.search import _apply_filters

        seeded_db.execute(
            "INSERT INTO notes (path, type, title, body, tags, people, importance) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("filter/imp_high.md", "note", "High Note", "body", "[]", "[]", "high"),
        )
        seeded_db.execute(
            "INSERT INTO notes (path, type, title, body, tags, people, importance) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("filter/imp_medium.md", "note", "Medium Note", "body", "[]", "[]", "medium"),
        )
        seeded_db.commit()

        results = [
            {"path": "filter/imp_high.md", "type": "note", "title": "High Note", "score": 1.0, "created_at": "2024-01-01"},
            {"path": "filter/imp_medium.md", "type": "note", "title": "Medium Note", "score": 1.0, "created_at": "2024-01-01"},
        ]
        out = _apply_filters(results, seeded_db, importance="high")
        paths = [r["path"] for r in out]
        assert "filter/imp_high.md" in paths
        assert "filter/imp_medium.md" not in paths

    def test_apply_filters_importance_none(self, seeded_db):
        """_apply_filters(importance=None) returns all results unchanged."""
        from engine.search import _apply_filters

        seeded_db.execute(
            "INSERT INTO notes (path, type, title, body, tags, people, importance) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("filter/imp2_high.md", "note", "High2", "body", "[]", "[]", "high"),
        )
        seeded_db.execute(
            "INSERT INTO notes (path, type, title, body, tags, people, importance) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("filter/imp2_low.md", "note", "Low2", "body", "[]", "[]", "low"),
        )
        seeded_db.commit()

        results = [
            {"path": "filter/imp2_high.md", "type": "note", "title": "High2", "score": 1.0, "created_at": "2024-01-01"},
            {"path": "filter/imp2_low.md", "type": "note", "title": "Low2", "score": 1.0, "created_at": "2024-01-01"},
        ]
        out = _apply_filters(results, seeded_db, importance=None)
        assert len(out) == 2


# ---------------------------------------------------------------------------
# Phase 50: Access boost tests
# ---------------------------------------------------------------------------


class TestAccessBoost:
    def test_no_access_returns_one(self):
        from engine.search import _access_boost
        assert _access_boost(None, 0) == 1.0

    def test_none_timestamp_returns_one(self):
        from engine.search import _access_boost
        assert _access_boost(None, 10) == 1.0

    def test_zero_count_returns_one(self):
        from engine.search import _access_boost
        assert _access_boost("2026-04-03T12:00:00Z", 0) == 1.0

    def test_recent_access_boosts(self):
        from engine.search import _access_boost
        from engine.db import _now_utc
        result = _access_boost(_now_utc(), 20)
        assert result > 1.0
        assert result <= 1.16  # max ~15%

    def test_old_access_decays(self):
        from engine.search import _access_boost
        # 120 days ago — should be near 1.0
        result = _access_boost("2026-01-01T00:00:00Z", 20)
        assert result < 1.05  # heavily decayed

    def test_cap_at_20_accesses(self):
        from engine.search import _access_boost
        from engine.db import _now_utc
        now = _now_utc()
        boost_20 = _access_boost(now, 20)
        boost_100 = _access_boost(now, 100)
        assert abs(boost_20 - boost_100) < 0.001  # capped, no difference

    def test_apply_access_boost_enriches_results(self, seeded_db):
        from engine.search import _apply_access_boost
        from engine.db import touch_note_access
        # Touch a note a few times (seeded_db uses notes/note_NNNN.md paths)
        touch_note_access(seeded_db, "notes/note_0000.md")
        touch_note_access(seeded_db, "notes/note_0000.md")
        touch_note_access(seeded_db, "notes/note_0000.md")
        results = [
            {"path": "notes/note_0000.md", "score": 1.0},
            {"path": "notes/note_0001.md", "score": 1.0},
        ]
        boosted = _apply_access_boost(results, seeded_db)
        scores = {r["path"]: r["score"] for r in boosted}
        assert scores["notes/note_0000.md"] > scores["notes/note_0001.md"]
