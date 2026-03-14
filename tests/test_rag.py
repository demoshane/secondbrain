"""Tests for engine/rag.py — RAG-lite FTS5 context retrieval (SEARCH-04)."""
import sqlite3

import pytest

from engine.db import init_schema
from engine.rag import augment_prompt, retrieve_context


def _make_db(tmp_path):
    """Return an in-memory SQLite connection with schema initialised."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    return conn


def _seed_note(conn, tmp_path, title: str, body: str, path_name: str = "note.md"):
    """Insert one note into the DB and write the file to tmp_path."""
    note_path = tmp_path / path_name
    note_path.write_text(body, encoding="utf-8")
    conn.execute(
        "INSERT INTO notes (path, title, body) VALUES (?, ?, ?)",
        (str(note_path), title, body),
    )
    conn.commit()
    return note_path


def test_retrieve_context_returns_block(tmp_path):
    """retrieve_context returns a formatted string with RETRIEVED CONTEXT header and note title."""
    conn = _make_db(tmp_path)
    _seed_note(conn, tmp_path, title="My Test Note", body="This is about python testing.", path_name="note.md")

    result = retrieve_context("python", conn)

    assert "RETRIEVED CONTEXT" in result
    assert "My Test Note" in result


def test_augment_prompt_in_user_content(tmp_path):
    """augment_prompt returns string with query and context; context appears before query."""
    conn = _make_db(tmp_path)
    _seed_note(conn, tmp_path, title="AI Article", body="Artificial intelligence overview content.", path_name="ai.md")

    result = augment_prompt("artificial intelligence", conn)

    assert "artificial intelligence" in result
    assert "RETRIEVED CONTEXT" in result
    # Context must be prepended — header comes before query
    assert result.index("RETRIEVED CONTEXT") < result.index("artificial intelligence")


def test_retrieve_context_empty(tmp_path):
    """retrieve_context returns empty string when FTS5 finds no matching notes."""
    conn = _make_db(tmp_path)
    # No notes seeded

    result = retrieve_context("xyzzy_no_match", conn)

    assert result == ""


def test_note_body_truncated(tmp_path):
    """retrieve_context truncates each note's body to 500 chars."""
    conn = _make_db(tmp_path)
    # Use a real word repeated so FTS5 can match it, padded to >500 chars total
    word = "verbosity "
    long_body = word * 110  # ~1100 chars, contains the word 'verbosity' many times
    _seed_note(conn, tmp_path, title="Long Note", body=long_body, path_name="long.md")

    result = retrieve_context("verbosity", conn)

    assert "Long Note" in result
    # The body in the context block must be <= 500 chars.
    # Extract the body portion: after the note header line "[Long Note] (...)"
    header_marker = "[Long Note]"
    header_pos = result.index(header_marker)
    # Body starts after the newline following the header line
    body_start = result.index("\n", header_pos) + 1
    footer_pos = result.index("=== END RETRIEVED CONTEXT ===")
    # Trim trailing newline before footer
    body_in_result = result[body_start:footer_pos].rstrip("\n")
    assert len(body_in_result) <= 500
