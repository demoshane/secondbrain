"""RED scaffold for Phase 18 GUI Hub API extensions.

All tests fail until Wave 1 implements the endpoints.
"""
import json
import os
import pytest
from engine.api import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestGuiShell:
    def test_get_ui_returns_200(self, client):
        r = client.get("/ui")
        assert r.status_code == 200


class TestSaveNote:
    def test_put_note_saves_content(self, client, tmp_path):
        p = tmp_path / "test.md"
        p.write_text("# Hello")
        # Absolute path starts with '/' — join without doubling the slash
        r = client.put(
            f"/notes{p}",
            json={"content": "# Updated"},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("saved") is True
        assert p.read_text() == "# Updated"


class TestCreateNote:
    def test_post_note_creates_file(self, client, tmp_path):
        r = client.post(
            "/notes",
            json={"title": "Test Note", "type": "idea", "body": "content", "brain_path": str(tmp_path)},
        )
        assert r.status_code == 201
        data = r.get_json()
        assert "path" in data


class TestNoteMeta:
    def test_get_note_meta_returns_structure(self, client, tmp_path):
        p = tmp_path / "note.md"
        p.write_text("# Note")
        # Absolute path starts with '/' — join without doubling the slash
        r = client.get(f"/notes{p}/meta")
        assert r.status_code == 200
        data = r.get_json()
        assert "backlinks" in data
        assert "related" in data


class TestFilesList:
    def test_get_files_returns_list(self, client):
        r = client.get("/files")
        assert r.status_code == 200
        data = r.get_json()
        assert "files" in data


class TestFilesMove:
    def test_post_files_move(self, client, tmp_path):
        src = tmp_path / "a.pdf"
        src.write_bytes(b"data")
        dst = tmp_path / "sub" / "a.pdf"
        r = client.post(
            "/files/move",
            json={"src": str(src), "dst": str(dst)},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("moved") is True


class TestActionDone:
    def test_post_action_done(self, client):
        r = client.post("/actions/1/done")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("done") is True


class TestIntelligence:
    def test_get_intelligence_returns_structure(self, client):
        r = client.get("/intelligence")
        assert r.status_code == 200
        data = r.get_json()
        assert "recap" in data
        assert "nudges" in data
