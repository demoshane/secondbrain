"""Tests for _json_list and _now_utc helpers in engine/db.py."""
import re

from engine.db import _json_list, _now_utc


class TestJsonList:
    def test_none_returns_empty(self):
        assert _json_list(None) == []

    def test_empty_string_returns_empty(self):
        assert _json_list("") == []

    def test_empty_json_array_returns_empty(self):
        assert _json_list("[]") == []

    def test_json_string_parses(self):
        assert _json_list('["a", "b"]') == ["a", "b"]

    def test_already_list_returned_as_is(self):
        lst = ["x", "y"]
        assert _json_list(lst) is lst

    def test_nested_values(self):
        assert _json_list('[1, 2, 3]') == [1, 2, 3]


class TestNowUtc:
    def test_returns_string(self):
        assert isinstance(_now_utc(), str)

    def test_matches_expected_format(self):
        result = _now_utc()
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", result), (
            f"Unexpected format: {result!r}"
        )

    def test_two_calls_are_close(self):
        t1 = _now_utc()
        t2 = _now_utc()
        # Both should share the same date prefix (won't cross midnight in a test run)
        assert t1[:10] == t2[:10]
