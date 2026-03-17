"""
Upload, attachment list, and batch capture tests — all endpoints implemented in Phase 25.
"""
import io
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.api import app  # noqa: E402
from engine.db import get_connection, init_schema  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client with an isolated in-tmp_path DB."""
    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))

    # Point the DB at tmp_path so init_schema builds a fresh DB there
    db_file = tmp_path / "brain.db"
    monkeypatch.setattr("engine.db.DB_PATH", db_file)
    monkeypatch.setattr("engine.paths.DB_PATH", db_file)

    # Initialise schema (creates attachments table etc.)
    conn = sqlite3.connect(str(db_file))
    init_schema(conn)
    conn.close()

    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestFileUpload:
    def test_upload_saves_file(self, client, tmp_path, monkeypatch):
        """POST /files/upload with a PDF — file is saved to the files/ dir."""
        monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
        pdf_bytes = b"%PDF-1.4 fake pdf content"
        data = {
            "file": (io.BytesIO(pdf_bytes), "document.pdf"),
            "note_path": "notes/test.md",
        }
        response = client.post(
            "/files/upload",
            data=data,
            content_type="multipart/form-data",
        )
        assert response.status_code == 200
        saved = list((tmp_path / "files").glob("*.pdf"))
        assert len(saved) == 1

    def test_upload_inserts_attachment_row(self, client, tmp_path, monkeypatch):
        """POST /files/upload — a row is inserted into the attachments table."""
        monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
        pdf_bytes = b"%PDF-1.4 fake pdf content"
        data = {
            "file": (io.BytesIO(pdf_bytes), "report.pdf"),
            "note_path": "notes/test.md",
        }
        client.post(
            "/files/upload",
            data=data,
            content_type="multipart/form-data",
        )
        db_file = tmp_path / "brain.db"
        conn = sqlite3.connect(str(db_file))
        rows = conn.execute(
            "SELECT * FROM attachments WHERE note_path = ?", ("notes/test.md",)
        ).fetchall()
        conn.close()
        assert len(rows) == 1

    def test_upload_rejects_executable(self, client, tmp_path, monkeypatch):
        """POST /files/upload with an .exe MIME type — returns 415."""
        monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
        data = {
            "file": (
                io.BytesIO(b"MZ fake executable"),
                "malware.exe",
                "application/x-msdownload",
            ),
            "note_path": "notes/test.md",
        }
        response = client.post(
            "/files/upload",
            data=data,
            content_type="multipart/form-data",
        )
        assert response.status_code == 415


class TestAttachmentsList:
    def test_list_attachments(self, client, tmp_path, monkeypatch):
        """GET /notes/attachments?path=... — returns list of attachment dicts."""
        monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
        response = client.get("/notes/attachments?path=notes/test.md")
        assert response.status_code == 200
        data = response.get_json()
        assert "attachments" in data
        assert isinstance(data["attachments"], list)


class TestBatchCapture:
    def test_batch_captures_unindexed(self, client, tmp_path, monkeypatch):
        """POST /batch-capture with an .md absent from DB — it appears in succeeded list."""
        monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
        note_file = tmp_path / "new-note.md"
        note_file.write_text(
            "---\ntitle: New Note\n---\n\nContent here.\n", encoding="utf-8"
        )
        response = client.post("/batch-capture", json={})
        assert response.status_code == 200
        result = response.get_json()
        succeeded_paths = [r.get("path", r) for r in result.get("succeeded", [])]
        assert any("new-note.md" in str(p) for p in succeeded_paths)

    def test_batch_skips_indexed(self, client, tmp_path, monkeypatch):
        """POST /batch-capture with an .md already in notes table — NOT in succeeded."""
        monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
        db_file = tmp_path / "brain.db"
        note_file = tmp_path / "existing-note.md"
        note_file.write_text(
            "---\ntitle: Existing Note\n---\n\nContent.\n", encoding="utf-8"
        )
        conn = sqlite3.connect(str(db_file))
        conn.execute(
            "INSERT INTO notes (path, title, type, body) VALUES (?, ?, ?, ?)",
            (str(note_file), "Existing Note", "note", "Content."),
        )
        conn.commit()
        conn.close()

        response = client.post("/batch-capture", json={})
        assert response.status_code == 200
        result = response.get_json()
        succeeded_paths = [r.get("path", r) for r in result.get("succeeded", [])]
        assert not any("existing-note.md" in str(p) for p in succeeded_paths)

    def test_batch_returns_structured_result(self, client, tmp_path, monkeypatch):
        """POST /batch-capture — response has 'succeeded' and 'failed' keys."""
        monkeypatch.setenv("BRAIN_PATH", str(tmp_path))
        response = client.post("/batch-capture", json={})
        assert response.status_code == 200
        result = response.get_json()
        assert "succeeded" in result
        assert "failed" in result
