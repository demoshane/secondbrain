import json
import stat
import sys
import pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.init_brain import validate_drive_mount, create_brain_structure, generate_vscode_settings
from engine.paths import BRAIN_SUBDIRS

# Symbols imported below are not yet implemented — they will raise ImportError
# until plan 17-02 creates them. This establishes RED state for the scaffold.
from engine.init_brain import (  # noqa: E402
    detect_drive_macos,
    detect_drive_windows,
    assert_drive_or_exit,
    ollama_ensure,
    ollama_model_size_warning,
)


def test_creates_subdirs(brain_root):
    result = create_brain_structure(brain_root)
    for subdir in BRAIN_SUBDIRS:
        assert (brain_root / subdir).is_dir(), f"Missing subdir: {subdir}"
    assert set(result["created"]) == set(BRAIN_SUBDIRS)
    assert result["existed"] == []


def test_drive_validation_blocks_on_unwritable(brain_root):
    brain_root.chmod(0o555)  # read-only
    try:
        ok, msg = validate_drive_mount(brain_root)
        assert not ok
        assert "writable" in msg.lower() or "permission" in msg.lower() or "not writable" in msg.lower()
    finally:
        brain_root.chmod(0o755)  # restore for cleanup


def test_vscode_settings_generated(brain_root):
    path = generate_vscode_settings(brain_root)
    assert path.exists()
    data = json.loads(path.read_text())
    assert "files.exclude" in data
    assert "**/*.db" in data["files.exclude"]


def test_init_reports_created_vs_existed(brain_root):
    first = create_brain_structure(brain_root)
    assert set(first["created"]) == set(BRAIN_SUBDIRS)
    second = create_brain_structure(brain_root)
    assert set(second["existed"]) == set(BRAIN_SUBDIRS)
    assert second["created"] == []


class TestDriveDetection:
    def test_macos_found(self, tmp_path, monkeypatch):
        cloud_storage = tmp_path / "Library" / "CloudStorage"
        drive_dir = cloud_storage / "GoogleDrive-test@example.com" / "My Drive"
        drive_dir.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        result = detect_drive_macos()
        assert result is not None

    def test_macos_not_found(self, tmp_path, monkeypatch):
        cloud_storage = tmp_path / "Library" / "CloudStorage"
        cloud_storage.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        result = detect_drive_macos()
        assert result is None

    def test_windows_found(self, tmp_path, monkeypatch):
        gfs_dir = tmp_path / "GFS" / "My Drive"
        gfs_dir.mkdir(parents=True)
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        result = detect_drive_windows()
        assert result is not None

    def test_windows_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        result = detect_drive_windows()
        assert result is None


class TestDriveExitOnMissing:
    def test_exits_nonzero(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        with pytest.raises(SystemExit) as exc:
            assert_drive_or_exit(base_path=tmp_path)
        assert exc.value.code != 0

    def test_prints_error_message(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        with pytest.raises(SystemExit):
            assert_drive_or_exit(base_path=tmp_path)
        captured = capsys.readouterr()
        assert "Google Drive not found" in captured.err or "Google Drive not found" in captured.out


class TestOllamaEnsure:
    def test_no_binary_no_brew_returns_false(self, monkeypatch):
        import shutil
        monkeypatch.setattr(shutil, "which", lambda name: None)
        result = ollama_ensure()
        assert result is False

    def test_prints_download_url(self, monkeypatch, capsys):
        import shutil
        monkeypatch.setattr(shutil, "which", lambda name: None)
        ollama_ensure()
        captured = capsys.readouterr()
        assert "ollama.com/download" in captured.out or "ollama.com/download" in captured.err


class TestOllamaModelSizeWarning:
    def test_warning_printed(self, monkeypatch, capsys):
        import ollama
        monkeypatch.setattr(ollama, "list", lambda: type("R", (), {"models": []})())
        ollama_model_size_warning()
        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert "800 MB" in output or "nomic-embed-text" in output
