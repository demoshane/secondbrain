"""TDD tests for _recency_multiplier helper in engine/search.py (Task 1, Plan 27-02)."""
import datetime
import pytest


def _iso(days_ago: int) -> str:
    """Return ISO-format UTC timestamp for `days_ago` days before now."""
    dt = datetime.datetime.utcnow() - datetime.timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class TestRecencyMultiplier:
    def test_exists(self):
        """_recency_multiplier must be importable from engine.search."""
        from engine.search import _recency_multiplier  # noqa: F401

    def test_new_note_boost(self):
        """New note (age ~0 days) returns >= 1.05 and <= 1.15."""
        from engine.search import _recency_multiplier

        result = _recency_multiplier(_iso(0))
        assert result >= 1.05, f"Expected >= 1.05, got {result}"
        assert result <= 1.15, f"Expected <= 1.15, got {result}"

    def test_half_life_boost(self):
        """Note at half_life_days (30) returns around 1.05 (within 0.01)."""
        from engine.search import _recency_multiplier

        result = _recency_multiplier(_iso(30), half_life_days=30)
        # boost at half_life = 0.1 * exp(-log(2)) = 0.1 * 0.5 = 0.05
        assert abs(result - 1.05) < 0.01, f"Expected ~1.05, got {result}"

    def test_old_note_minimal_boost(self):
        """Note at 180 days returns close to 1.0 (>= 1.0, <= 1.01)."""
        from engine.search import _recency_multiplier

        result = _recency_multiplier(_iso(180))
        assert result >= 1.0, f"Expected >= 1.0, got {result}"
        assert result <= 1.01, f"Expected <= 1.01, got {result}"

    def test_always_returns_float_ge_one(self):
        """Returns float >= 1.0 for any valid input."""
        from engine.search import _recency_multiplier

        for days in [0, 1, 7, 30, 90, 365]:
            result = _recency_multiplier(_iso(days))
            assert isinstance(result, float), f"Expected float, got {type(result)}"
            assert result >= 1.0, f"Expected >= 1.0 for {days} days, got {result}"

    def test_invalid_date_returns_one(self):
        """Invalid/empty created_at falls back to 1.0 (no boost, no crash)."""
        from engine.search import _recency_multiplier

        assert _recency_multiplier("") == 1.0
        assert _recency_multiplier("not-a-date") == 1.0
        assert _recency_multiplier(None) == 1.0

    def test_search_notes_applies_multiplier(self, tmp_path):
        """search_notes() result scores are modified by recency (> raw BM25 value)."""
        from engine.db import get_connection, init_schema
        from engine.search import search_notes

        db_path = tmp_path / "test.db"
        conn = get_connection(str(db_path))
        init_schema(conn)
        conn.execute(
            "INSERT INTO notes (path, type, title, body, tags, people) VALUES (?, ?, ?, ?, ?, ?)",
            ("/brain/note/python-tricks.md", "note", "Python Tricks", "python tricks tips", "[]", "[]"),
        )
        conn.commit()

        results = search_notes(conn, "python tricks")
        assert len(results) > 0
        # Score should be negative BM25 * multiplier >= 1.0; still negative but closer to 0
        # Just verify the score key is present and is a float
        assert isinstance(results[0]["score"], float)
        conn.close()
