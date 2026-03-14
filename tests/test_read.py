"""Tests for engine.read — GDPR-04 (PII passphrase gate).

All tests are xfail (strict=True): they must fail RED before implementation.
Deferred imports inside test bodies so pytest --collect-only works without engine.read existing.
"""
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture()
def pii_note(tmp_path: Path):
    """Temp note file with content_sensitivity: pii frontmatter."""
    note = tmp_path / "private-note.md"
    note.write_text(
        "---\ncontent_sensitivity: pii\ntitle: PII Note\n---\nSecret content.\n"
    )
    yield note


@pytest.fixture()
def public_note(tmp_path: Path):
    """Temp note file with content_sensitivity: public frontmatter."""
    note = tmp_path / "public-note.md"
    note.write_text(
        "---\ncontent_sensitivity: public\ntitle: Public Note\n---\nPublic content.\n"
    )
    yield note


def test_pii_note_denied_no_passphrase(pii_note: Path):
    """read_note returns 1 when SB_PII_PASSPHRASE unset and getpass raises EOFError."""
    import os
    from engine.read import read_note

    env = {k: v for k, v in os.environ.items() if k != "SB_PII_PASSPHRASE"}
    with patch.dict(os.environ, env, clear=True):
        with patch("getpass.getpass", side_effect=EOFError):
            result = read_note(pii_note, sqlite3.connect(":memory:"))

    assert result == 1


def test_pii_note_denied_wrong_passphrase(pii_note: Path):
    """read_note returns 1 when passphrase provided does not match SB_PII_PASSPHRASE."""
    import os
    from engine.read import read_note

    with patch.dict(os.environ, {"SB_PII_PASSPHRASE": "correct"}, clear=False):
        with patch("getpass.getpass", return_value="wrong"):
            result = read_note(pii_note, sqlite3.connect(":memory:"))

    assert result == 1


def test_pii_note_shown_correct_passphrase(pii_note: Path):
    """read_note returns 0 when passphrase matches SB_PII_PASSPHRASE."""
    import os
    from engine.read import read_note

    with patch.dict(os.environ, {"SB_PII_PASSPHRASE": "correct"}, clear=False):
        with patch("getpass.getpass", return_value="correct"):
            result = read_note(pii_note, sqlite3.connect(":memory:"))

    assert result == 0


def test_non_pii_note_no_gate(public_note: Path):
    """read_note returns 0 for a public note without requiring any passphrase."""
    import os
    from engine.read import read_note

    env = {k: v for k, v in os.environ.items() if k != "SB_PII_PASSPHRASE"}
    with patch.dict(os.environ, env, clear=True):
        result = read_note(public_note, sqlite3.connect(":memory:"))

    assert result == 0
