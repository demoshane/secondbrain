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


# --- Wiring tests: ask_followup_questions integrates with augment_prompt ---

def test_ask_followup_questions_with_conn_injects_context(tmp_path):
    """When conn is provided, ask_followup_questions passes augmented content to adapter."""
    from unittest.mock import patch, MagicMock
    from engine.ai import ask_followup_questions
    from engine.paths import CONFIG_PATH

    conn = _make_db(tmp_path)
    _seed_note(
        conn, tmp_path,
        title="Python Testing Patterns",
        body="pytest fixtures and parametrize patterns for python testing.",
        path_name="pytest.md",
    )

    captured_user_content = {}

    def fake_generate(user_content, system_prompt):
        captured_user_content["value"] = user_content
        return "1. What testing framework?\n2. What coverage target?"

    mock_adapter = MagicMock()
    mock_adapter.generate.side_effect = fake_generate

    with patch("engine.router.get_adapter", return_value=mock_adapter):
        result = ask_followup_questions("coding", "python testing", "public", CONFIG_PATH, conn=conn)

    # Result should be a list of questions (not the fallback)
    assert isinstance(result, list)
    assert len(result) >= 2
    # The user_content passed to adapter should contain RETRIEVED CONTEXT (FTS5 match found)
    assert "RETRIEVED CONTEXT" in captured_user_content.get("value", ""), (
        f"Expected RETRIEVED CONTEXT in user_content but got: {captured_user_content.get('value', '')!r}"
    )


def test_ask_followup_questions_without_conn_uses_raw_title(tmp_path):
    """When conn=None, ask_followup_questions passes raw title to adapter (no augmentation)."""
    from unittest.mock import patch, MagicMock
    from engine.ai import ask_followup_questions
    from engine.paths import CONFIG_PATH

    captured_user_content = {}

    def fake_generate(user_content, system_prompt):
        captured_user_content["value"] = user_content
        return "1. What is the key insight?\n2. How does this connect to current work?"

    mock_adapter = MagicMock()
    mock_adapter.generate.side_effect = fake_generate

    with patch("engine.router.get_adapter", return_value=mock_adapter):
        result = ask_followup_questions("note", "my raw title", "public", CONFIG_PATH, conn=None)

    assert isinstance(result, list)
    assert len(result) >= 2
    # Without conn, user_content must be exactly the raw title
    assert captured_user_content.get("value") == "my raw title"
    assert "RETRIEVED CONTEXT" not in captured_user_content.get("value", "")


# ---------------------------------------------------------------------------
# Phase 7: RAG path resolution after capture (SEARCH-04)
# ---------------------------------------------------------------------------

def test_retrieve_context_reads_captured_note(tmp_path):
    """retrieve_context must read file content — not fall back to '[note file not readable]'."""
    import sqlite3
    from engine.db import init_schema
    from engine.capture import write_note_atomic, build_post
    from engine.rag import retrieve_context

    brain_root = tmp_path.resolve() / "brain"
    notes_dir = brain_root / "notes"
    notes_dir.mkdir(parents=True)

    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(notes)").fetchall()}
    if "people" not in cols:
        conn.execute("ALTER TABLE notes ADD COLUMN people TEXT NOT NULL DEFAULT '[]'")
    conn.commit()

    target = notes_dir / "2026-phase7-rag-test.md"
    post = build_post("note", "Phase7 RAG Test", "unique rag path resolution content", [], [], "public")
    write_note_atomic(target, post, conn)

    context = retrieve_context("rag path resolution", conn)
    assert "[note file not readable]" not in context, (
        f"RAG must read file directly; got fallback. context={context!r}"
    )
    conn.close()
