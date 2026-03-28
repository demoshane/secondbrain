"""Tests for POST /summarise-url endpoint (Phase 41.3-07)."""
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.api import app
from engine.db import get_connection, init_schema


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client with isolated DB."""
    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
    db_file = tmp_path / "brain.db"
    monkeypatch.setattr("engine.db.DB_PATH", db_file)
    monkeypatch.setattr("engine.paths.DB_PATH", db_file)
    conn = sqlite3.connect(str(db_file))
    init_schema(conn)
    conn.close()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestSummariseUrl:
    def test_missing_url_returns_400(self, client):
        """POST /summarise-url with no url → 400."""
        res = client.post(
            "/summarise-url",
            json={"content": "some text here"},
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_missing_content_returns_400(self, client):
        """POST /summarise-url with no content → 400."""
        res = client.post(
            "/summarise-url",
            json={"url": "https://example.com"},
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_empty_url_returns_400(self, client):
        """POST /summarise-url with empty url → 400."""
        res = client.post(
            "/summarise-url",
            json={"url": "", "content": "some text"},
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_empty_content_returns_400(self, client):
        """POST /summarise-url with empty content → 400."""
        res = client.post(
            "/summarise-url",
            json={"url": "https://example.com", "content": ""},
            content_type="application/json",
        )
        assert res.status_code == 400

    def test_valid_request_returns_summary(self, client):
        """POST /summarise-url with valid input calls LLM and returns {summary}."""
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "This is a test summary."

        with patch("engine.intelligence._router") as mock_router:
            mock_router.get_adapter.return_value = mock_adapter
            res = client.post(
                "/summarise-url",
                json={
                    "url": "https://example.com/article",
                    "content": "Long article text that needs summarising.",
                },
                content_type="application/json",
            )

        assert res.status_code == 200
        data = res.get_json()
        assert "summary" in data
        assert data["summary"] == "This is a test summary."

    def test_content_truncated_to_8000_chars(self, client):
        """Content longer than 8000 chars is truncated server-side before LLM call."""
        long_content = "x" * 10000
        mock_adapter = MagicMock()
        mock_adapter.generate.return_value = "Truncated summary."

        with patch("engine.intelligence._router") as mock_router:
            mock_router.get_adapter.return_value = mock_adapter
            res = client.post(
                "/summarise-url",
                json={"url": "https://example.com", "content": long_content},
                content_type="application/json",
            )

        assert res.status_code == 200
        # Verify the adapter was called with truncated content (≤8000 chars)
        call_kwargs = mock_adapter.generate.call_args
        user_content = call_kwargs[1].get("user_content") or call_kwargs[0][0]
        assert len(user_content) <= 8100  # allow for prompt wrapper overhead
