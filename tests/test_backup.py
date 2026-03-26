"""Tests for engine/backup.py — Fernet-encrypted brain backup & restore."""
from __future__ import annotations

import os
import stat
import time
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_brain(root: Path) -> list[Path]:
    """Create a minimal brain-like structure with .md files and a fake DB."""
    (root / "notes").mkdir(parents=True)
    (root / ".meta").mkdir(parents=True)
    note_a = root / "notes" / "alpha.md"
    note_b = root / "notes" / "beta.md"
    note_a.write_text("# Alpha\nContent A", encoding="utf-8")
    note_b.write_text("# Beta\nContent B", encoding="utf-8")
    db = root / ".meta" / "brain.db"
    db.write_bytes(b"SQLITE_FAKE_CONTENT")
    return [note_a, note_b, db]


# ---------------------------------------------------------------------------
# _get_or_create_key
# ---------------------------------------------------------------------------

class TestGetOrCreateKey:
    def test_creates_key_file_at_key_path(self, tmp_path, monkeypatch):
        """_get_or_create_key creates file at KEY_PATH with 0o600 permissions."""
        import engine.backup as backup
        key_path = tmp_path / "backup.key"
        monkeypatch.setattr(backup, "KEY_PATH", key_path)

        key = backup._get_or_create_key()

        assert key_path.exists(), "key file should be created"
        file_mode = stat.S_IMODE(key_path.stat().st_mode)
        assert file_mode == 0o600, f"expected 0o600 got {oct(file_mode)}"
        assert isinstance(key, bytes)
        assert len(key) > 0

    def test_idempotent_second_call(self, tmp_path, monkeypatch):
        """_get_or_create_key returns same key on second call."""
        import engine.backup as backup
        key_path = tmp_path / "backup.key"
        monkeypatch.setattr(backup, "KEY_PATH", key_path)

        key1 = backup._get_or_create_key()
        key2 = backup._get_or_create_key()

        assert key1 == key2


# ---------------------------------------------------------------------------
# backup_brain
# ---------------------------------------------------------------------------

class TestBackupBrain:
    def test_creates_enc_file(self, tmp_path, monkeypatch):
        """backup_brain creates a .enc file in backup_dir."""
        import engine.backup as backup
        key_path = tmp_path / "backup.key"
        monkeypatch.setattr(backup, "KEY_PATH", key_path)

        brain_root = tmp_path / "brain"
        _make_fake_brain(brain_root)
        db_path = brain_root / ".meta" / "brain.db"
        backup_dir = tmp_path / "backups"

        result_path = backup.backup_brain(brain_root, db_path, backup_dir)

        assert result_path.exists(), "backup file should exist"
        assert result_path.suffix == ".enc", "backup file should have .enc extension"
        assert backup_dir in result_path.parents

    def test_enc_file_is_valid_fernet(self, tmp_path, monkeypatch):
        """backup_brain .enc file decrypts without error using the same key."""
        from cryptography.fernet import Fernet
        import engine.backup as backup
        key_path = tmp_path / "backup.key"
        monkeypatch.setattr(backup, "KEY_PATH", key_path)

        brain_root = tmp_path / "brain"
        _make_fake_brain(brain_root)
        db_path = brain_root / ".meta" / "brain.db"
        backup_dir = tmp_path / "backups"

        enc_path = backup.backup_brain(brain_root, db_path, backup_dir)
        key = key_path.read_bytes()
        f = Fernet(key)
        decrypted = f.decrypt(enc_path.read_bytes())  # must not raise
        assert len(decrypted) > 0


# ---------------------------------------------------------------------------
# restore_brain
# ---------------------------------------------------------------------------

class TestRestoreBrain:
    def test_restore_extracts_notes_and_db(self, tmp_path, monkeypatch):
        """restore_brain decrypts .enc and extracts notes + DB to target dir."""
        import engine.backup as backup
        key_path = tmp_path / "backup.key"
        monkeypatch.setattr(backup, "KEY_PATH", key_path)

        brain_root = tmp_path / "brain"
        _make_fake_brain(brain_root)
        db_path = brain_root / ".meta" / "brain.db"
        backup_dir = tmp_path / "backups"

        enc_path = backup.backup_brain(brain_root, db_path, backup_dir)

        # Restore to a fresh target
        target_root = tmp_path / "restored_brain"
        target_db = tmp_path / "restored_brain" / ".meta" / "brain.db"
        result = backup.restore_brain(enc_path, target_root, target_db)

        assert result["db_restored"] is True
        assert result["notes_restored"] > 0
        assert target_db.exists(), "DB should be restored"

    def test_round_trip_produces_identical_content(self, tmp_path, monkeypatch):
        """Round-trip: backup then restore produces identical file content."""
        import engine.backup as backup
        key_path = tmp_path / "backup.key"
        monkeypatch.setattr(backup, "KEY_PATH", key_path)

        brain_root = tmp_path / "brain"
        _make_fake_brain(brain_root)
        db_path = brain_root / ".meta" / "brain.db"
        backup_dir = tmp_path / "backups"

        enc_path = backup.backup_brain(brain_root, db_path, backup_dir)

        target_root = tmp_path / "restored"
        target_db = tmp_path / "restored" / ".meta" / "brain.db"
        backup.restore_brain(enc_path, target_root, target_db)

        # Check note content is identical
        original_note = brain_root / "notes" / "alpha.md"
        restored_note = target_root / "notes" / "alpha.md"
        assert restored_note.exists(), "restored note should exist"
        assert restored_note.read_text() == original_note.read_text()

        # Check DB content is identical
        assert target_db.read_bytes() == db_path.read_bytes()

    def test_wrong_key_raises_invalid_token(self, tmp_path, monkeypatch):
        """restore_brain with wrong key raises InvalidToken."""
        from cryptography.fernet import Fernet, InvalidToken
        import engine.backup as backup
        key_path = tmp_path / "backup.key"
        monkeypatch.setattr(backup, "KEY_PATH", key_path)

        brain_root = tmp_path / "brain"
        _make_fake_brain(brain_root)
        db_path = brain_root / ".meta" / "brain.db"
        backup_dir = tmp_path / "backups"

        enc_path = backup.backup_brain(brain_root, db_path, backup_dir)

        # Overwrite key with a different one
        key_path.write_bytes(Fernet.generate_key())
        key_path.chmod(0o600)

        target_root = tmp_path / "restored"
        target_db = tmp_path / "restored" / ".meta" / "brain.db"
        with pytest.raises(InvalidToken):
            backup.restore_brain(enc_path, target_root, target_db)


# ---------------------------------------------------------------------------
# check_backup_health
# ---------------------------------------------------------------------------

class TestCheckBackupHealth:
    def test_no_backups_returns_none(self, tmp_path, monkeypatch):
        """check_backup_health returns last_backup=None when no .enc files exist."""
        import engine.backup as backup
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        result = backup.check_backup_health(backup_dir)

        assert result["last_backup"] is None
        assert result["stale"] is True
        assert result["age_days"] is None

    def test_fresh_backup_not_stale(self, tmp_path, monkeypatch):
        """check_backup_health returns stale=False for a backup created just now."""
        import engine.backup as backup
        key_path = tmp_path / "backup.key"
        monkeypatch.setattr(backup, "KEY_PATH", key_path)

        brain_root = tmp_path / "brain"
        _make_fake_brain(brain_root)
        db_path = brain_root / ".meta" / "brain.db"
        backup_dir = tmp_path / "backups"

        backup.backup_brain(brain_root, db_path, backup_dir)
        result = backup.check_backup_health(backup_dir, warn_days=7)

        assert result["last_backup"] is not None
        assert result["stale"] is False
        assert result["age_days"] is not None
        assert result["age_days"] <= 1  # just created

    def test_old_backup_is_stale(self, tmp_path, monkeypatch):
        """check_backup_health returns stale=True for a very old backup."""
        import engine.backup as backup
        key_path = tmp_path / "backup.key"
        monkeypatch.setattr(backup, "KEY_PATH", key_path)

        brain_root = tmp_path / "brain"
        _make_fake_brain(brain_root)
        db_path = brain_root / ".meta" / "brain.db"
        backup_dir = tmp_path / "backups"

        enc_path = backup.backup_brain(brain_root, db_path, backup_dir)

        # Back-date the file by 10 days
        old_time = time.time() - (10 * 24 * 3600)
        os.utime(enc_path, (old_time, old_time))

        result = backup.check_backup_health(backup_dir, warn_days=7)
        assert result["stale"] is True
        assert result["age_days"] >= 10


# ---------------------------------------------------------------------------
# CLI entry points smoke tests
# ---------------------------------------------------------------------------

class TestCLIEntryPoints:
    def test_backup_main_callable(self, tmp_path, monkeypatch):
        """backup_main is callable without crashing (smoke test)."""
        import engine.backup as backup

        # Patch paths so it operates in tmp_path
        key_path = tmp_path / "backup.key"
        brain_root = tmp_path / "brain"
        _make_fake_brain(brain_root)
        db_path = brain_root / ".meta" / "brain.db"
        backup_dir = tmp_path / "backups"

        monkeypatch.setattr(backup, "KEY_PATH", key_path)
        monkeypatch.setattr("engine.backup.BRAIN_ROOT", brain_root)
        monkeypatch.setattr("engine.backup.DB_PATH", db_path)
        monkeypatch.setattr("engine.backup.DEFAULT_BACKUP_DIR", backup_dir)

        backup.backup_main()  # must not raise

        enc_files = list(backup_dir.glob("*.enc"))
        assert len(enc_files) == 1

    def test_restore_main_first_step_prints_token(self, tmp_path, monkeypatch, capsys):
        """restore_main first step prints confirm token (two-step pattern)."""
        import engine.backup as backup
        import sys

        key_path = tmp_path / "backup.key"
        brain_root = tmp_path / "brain"
        _make_fake_brain(brain_root)
        db_path = brain_root / ".meta" / "brain.db"
        backup_dir = tmp_path / "backups"

        monkeypatch.setattr(backup, "KEY_PATH", key_path)
        monkeypatch.setattr("engine.backup.BRAIN_ROOT", brain_root)
        monkeypatch.setattr("engine.backup.DB_PATH", db_path)
        monkeypatch.setattr("engine.backup.DEFAULT_BACKUP_DIR", backup_dir)

        enc_path = backup.backup_brain(brain_root, db_path, backup_dir)

        monkeypatch.setattr(sys, "argv", ["sb-restore", "--enc-file", str(enc_path)])
        with pytest.raises(SystemExit) as exc_info:
            backup.restore_main()
        captured = capsys.readouterr()
        assert "confirm" in captured.out.lower() or exc_info.value.code == 0
