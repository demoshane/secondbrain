import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.api import app  # noqa: E402 — raises ImportError until 17-01


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_body(self, client):
        response = client.get("/health")
        assert response.get_json()["status"] == "ok"


class TestNotesList:
    def test_notes_returns_200(self, client):
        response = client.get("/notes")
        assert response.status_code == 200

    def test_notes_has_notes_key(self, client):
        response = client.get("/notes")
        assert "notes" in response.get_json()


class TestSearch:
    def test_search_returns_200(self, client):
        response = client.post("/search", json={"query": "hello"})
        assert response.status_code == 200

    def test_search_has_results_key(self, client):
        response = client.post("/search", json={"query": "hello"})
        assert "results" in response.get_json()


class TestReadNote:
    def test_read_missing_note_404(self, client):
        response = client.get("/notes/nonexistent%2Fpath.md")
        assert response.status_code == 404


class TestActionItems:
    def test_actions_returns_200(self, client):
        response = client.get("/actions")
        assert response.status_code == 200

    def test_actions_has_actions_key(self, client):
        response = client.get("/actions")
        assert "actions" in response.get_json()
