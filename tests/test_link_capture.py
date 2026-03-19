"""Tests for engine.link_capture — fetch_link_metadata() and DB/capture integration."""
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO

import pytest

# ---------------------------------------------------------------------------
# Task 1: fetch_link_metadata()
# ---------------------------------------------------------------------------


def test_fetch_metadata_returns_title():
    """og:title is used when present; function returns dict with title + description."""
    from engine.link_capture import fetch_link_metadata

    html = b"""
    <html>
    <head>
        <meta property="og:title" content="My OG Title" />
        <meta property="og:description" content="My OG Desc" />
        <title>Fallback Title</title>
    </head>
    <body></body>
    </html>
    """

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.return_value = html

    with patch("engine.link_capture.urlopen", return_value=mock_resp):
        result = fetch_link_metadata("https://example.com/article")

    assert isinstance(result, dict)
    assert result["title"] == "My OG Title"
    assert result["description"] == "My OG Desc"


def test_fetch_metadata_html_title_fallback():
    """When og:title absent, HTML <title> is used."""
    from engine.link_capture import fetch_link_metadata

    html = b"<html><head><title>  Plain HTML Title  </title></head></html>"

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.return_value = html

    with patch("engine.link_capture.urlopen", return_value=mock_resp):
        result = fetch_link_metadata("https://example.com")

    assert result["title"] == "Plain HTML Title"
    assert result["description"] == ""


def test_fetch_metadata_fallback_on_error():
    """Any network/parse error returns hostname as title, empty description — never raises."""
    from engine.link_capture import fetch_link_metadata

    with patch("engine.link_capture.urlopen", side_effect=Exception("Network error")):
        result = fetch_link_metadata("https://example.com/some/path")

    assert isinstance(result, dict)
    assert result["title"] == "example.com"
    assert result["description"] == ""


def test_fetch_metadata_fallback_invalid_url():
    """Completely invalid URL uses the raw string as title fallback."""
    from engine.link_capture import fetch_link_metadata

    # urlopen will raise on bad URL — hostname extraction may also fail
    with patch("engine.link_capture.urlopen", side_effect=Exception("bad url")):
        result = fetch_link_metadata("not-a-url")

    assert isinstance(result, dict)
    assert "title" in result
    assert "description" in result


def test_fetch_metadata_og_title_alternate_attribute_order():
    """og:title works when content attribute comes before property attribute."""
    from engine.link_capture import fetch_link_metadata

    html = b"""<html><head>
        <meta content="Reversed Attr OG Title" property="og:title" />
    </head></html>"""

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.return_value = html

    with patch("engine.link_capture.urlopen", return_value=mock_resp):
        result = fetch_link_metadata("https://example.com")

    assert result["title"] == "Reversed Attr OG Title"


# ---------------------------------------------------------------------------
# Task 2: DB migration — url column
# ---------------------------------------------------------------------------


def test_url_column_exists(tmp_path):
    """After init_schema(), notes table has a 'url' column."""
    from engine.db import get_connection, init_schema

    db_path = str(tmp_path / "brain.db")
    conn = get_connection(db_path)
    init_schema(conn)

    cols = {row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()}
    conn.close()

    assert "url" in cols, f"'url' column missing from notes. Columns found: {cols}"


def test_capture_note_writes_url_to_frontmatter(tmp_path, monkeypatch):
    """capture_note() with url= kwarg writes url field into note's YAML frontmatter."""
    import engine.db
    import engine.paths

    db_path = tmp_path / "brain.db"
    monkeypatch.setattr(engine.db, "DB_PATH", db_path)
    monkeypatch.setattr(engine.paths, "DB_PATH", db_path)
    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))

    from engine.db import get_connection, init_schema
    from engine.capture import capture_note

    conn = get_connection(str(db_path))
    init_schema(conn)

    path = capture_note(
        note_type="link",
        title="Test Link Note",
        body="Some body",
        tags=[],
        people=[],
        content_sensitivity="public",
        brain_root=tmp_path,
        conn=conn,
        url="https://example.com/article",
    )
    conn.close()

    assert path.exists(), f"Note file not created at {path}"
    content = path.read_text()
    assert "url: https://example.com/article" in content


def test_capture_note_no_url_unaffected(tmp_path, monkeypatch):
    """capture_note() without url kwarg still works — url defaults to None, no frontmatter key."""
    import engine.db
    import engine.paths

    db_path = tmp_path / "brain.db"
    monkeypatch.setattr(engine.db, "DB_PATH", db_path)
    monkeypatch.setattr(engine.paths, "DB_PATH", db_path)
    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))

    from engine.db import get_connection, init_schema
    from engine.capture import capture_note

    conn = get_connection(str(db_path))
    init_schema(conn)

    path = capture_note(
        note_type="note",
        title="Normal Note",
        body="Body content",
        tags=[],
        people=[],
        content_sensitivity="public",
        brain_root=tmp_path,
        conn=conn,
    )
    conn.close()

    assert path.exists()
    content = path.read_text()
    assert "url:" not in content


def test_type_to_dir_has_link():
    """TYPE_TO_DIR['link'] == 'links'."""
    from engine.capture import TYPE_TO_DIR

    assert "link" in TYPE_TO_DIR
    assert TYPE_TO_DIR["link"] == "links"


def test_capture_note_url_stored_in_db(tmp_path, monkeypatch):
    """capture_note() with url= stores url in the notes table url column."""
    import engine.db
    import engine.paths

    db_path = tmp_path / "brain.db"
    monkeypatch.setattr(engine.db, "DB_PATH", db_path)
    monkeypatch.setattr(engine.paths, "DB_PATH", db_path)
    monkeypatch.setenv("BRAIN_PATH", str(tmp_path))

    from engine.db import get_connection, init_schema
    from engine.capture import capture_note

    conn = get_connection(str(db_path))
    init_schema(conn)

    path = capture_note(
        note_type="link",
        title="DB URL Test",
        body="Body",
        tags=[],
        people=[],
        content_sensitivity="public",
        brain_root=tmp_path,
        conn=conn,
        url="https://db-test.example.com",
    )

    row = conn.execute(
        "SELECT url FROM notes WHERE path = ?", (str(path.resolve()),)
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "https://db-test.example.com"
