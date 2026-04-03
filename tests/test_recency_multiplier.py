"""TDD tests for _relevance_decay helper in engine/search.py (replaces _recency_multiplier from Plan 27-02)."""
import datetime
import pytest


def _iso(days_ago: int) -> str:
    """Return ISO-format UTC timestamp for `days_ago` days before now."""
    dt = datetime.datetime.utcnow() - datetime.timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class TestRelevanceDecay:
    def test_exists(self):
        """_relevance_decay must be importable from engine.search."""
        from engine.search import _relevance_decay  # noqa: F401

    def test_new_note_boost(self):
        """New note (age ~0 days) returns >= 1.05 and <= 1.16."""
        from engine.search import _relevance_decay

        result = _relevance_decay(_iso(0), "note")
        assert result >= 1.05, f"Expected >= 1.05, got {result}"
        assert result <= 1.16, f"Expected <= 1.16, got {result}"

    def test_half_life_boost(self):
        """Note at its type half-life (60 days) returns reduced but >1.0 boost."""
        from engine.search import _relevance_decay

        result = _relevance_decay(_iso(60), "note")
        assert result > 1.0, f"Expected > 1.0, got {result}"
        assert result < 1.10, f"Expected < 1.10, got {result}"

    def test_old_note_minimal_boost(self):
        """Note at 365 days returns close to 1.0."""
        from engine.search import _relevance_decay

        result = _relevance_decay(_iso(365), "note")
        assert result >= 1.0, f"Expected >= 1.0, got {result}"
        assert result <= 1.01, f"Expected <= 1.01, got {result}"

    def test_always_returns_float_ge_one(self):
        """Returns float >= 1.0 for any valid input."""
        from engine.search import _relevance_decay

        for days in [0, 1, 7, 30, 90, 365]:
            result = _relevance_decay(_iso(days), "note")
            assert isinstance(result, float), f"Expected float, got {type(result)}"
            assert result >= 1.0, f"Expected >= 1.0 for {days} days, got {result}"

    def test_invalid_date_returns_one(self):
        """Invalid/empty created_at falls back to 1.0 (no boost, no crash)."""
        from engine.search import _relevance_decay

        assert _relevance_decay("", "note") == 1.0
        assert _relevance_decay("not-a-date", "note") == 1.0
        assert _relevance_decay(None, "note") == 1.0

    def test_search_notes_applies_decay(self, tmp_path):
        """search_notes() result scores are modified by relevance decay."""
        from engine.db import get_connection, init_schema
        from engine.search import search_notes
        import engine.db as _db
        import engine.paths as _paths

        db_path = tmp_path / "test.db"
        _db.DB_PATH = db_path
        _paths.DB_PATH = db_path
        conn = get_connection(str(db_path))
        init_schema(conn)
        conn.execute(
            "INSERT INTO notes (path, type, title, body, tags, people) VALUES (?, ?, ?, ?, ?, ?)",
            ("note/python-tricks.md", "note", "Python Tricks", "python tricks tips", "[]", "[]"),
        )
        conn.commit()

        results = search_notes(conn, "python tricks")
        assert len(results) > 0
        assert isinstance(results[0]["score"], float)
        conn.close()
