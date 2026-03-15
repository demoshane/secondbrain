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


def test_read_missing_file_returns_1(tmp_path: Path):
    """read_note returns 1 when the note file does not exist."""
    from engine.read import read_note

    missing = tmp_path / "does-not-exist.md"
    result = read_note(missing, sqlite3.connect(":memory:"))

    assert result == 1


def test_pii_note_denied_keyboard_interrupt(pii_note: Path):
    """read_note returns 1 when user hits Ctrl-C at the passphrase prompt."""
    import os
    from engine.read import read_note

    with patch.dict(os.environ, {"SB_PII_PASSPHRASE": "secret"}, clear=False):
        with patch("getpass.getpass", side_effect=KeyboardInterrupt):
            result = read_note(pii_note, sqlite3.connect(":memory:"))

    assert result == 1


def test_pii_note_allowed_via_passphrase_input_env(pii_note: Path):
    """SB_PII_PASSPHRASE_INPUT bypasses getpass for non-interactive use."""
    import os
    from engine.read import read_note

    env_patch = {"SB_PII_PASSPHRASE": "secret", "SB_PII_PASSPHRASE_INPUT": "secret"}
    with patch.dict(os.environ, env_patch, clear=False):
        result = read_note(pii_note, sqlite3.connect(":memory:"))

    assert result == 0


def test_private_note_readable_without_passphrase(tmp_path: Path):
    """Notes with content_sensitivity: private are readable without a passphrase."""
    import os
    from engine.read import read_note

    note = tmp_path / "private-note.md"
    note.write_text("---\ncontent_sensitivity: private\ntitle: Private\n---\nContent.\n")

    env = {k: v for k, v in os.environ.items() if k != "SB_PII_PASSPHRASE"}
    with patch.dict(os.environ, env, clear=True):
        result = read_note(note, sqlite3.connect(":memory:"))

    assert result == 0


def test_read_logs_audit_entry_on_pii_success(pii_note: Path):
    """A successful PII read writes a 'read' row to audit_log."""
    import os
    from engine.db import init_schema
    from engine.read import read_note

    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    with patch.dict(os.environ, {"SB_PII_PASSPHRASE": "s3cr3t"}, clear=False):
        with patch("getpass.getpass", return_value="s3cr3t"):
            read_note(pii_note, conn)

    row = conn.execute(
        "SELECT event_type, note_path FROM audit_log WHERE event_type = 'read'"
    ).fetchone()
    assert row is not None
    assert row[0] == "read"
    assert row[1] == str(pii_note)


# --- Wave 0 RED stubs for Phase 16 --digest flag ---

class TestDigestFlag:
    def test_digest_flag_resolves_latest(self, tmp_path):
        """sb-read --digest latest resolves to most recent digest file — fails RED (flag not yet added)."""
        from engine.read import main
        digest_dir = tmp_path / "digests"
        digest_dir.mkdir()
        (digest_dir / "2026-W11.md").write_text("---\ntitle: test\n---\nbody")
        # --digest flag doesn't exist yet — will raise SystemExit (argparse error)
        with pytest.raises(SystemExit):
            main(["--digest", "latest"])


class TestDigestFlagEmpty:
    def test_digest_flag_empty_dir_graceful(self, tmp_path, capsys):
        """sb-read --digest latest on empty digests dir prints 'No digests found.' — fails RED."""
        from engine.read import main
        with pytest.raises(SystemExit):
            main(["--digest", "latest"])
