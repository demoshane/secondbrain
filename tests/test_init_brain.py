import json
import stat
import sys
import pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.init_brain import validate_drive_mount, create_brain_structure, generate_vscode_settings
from engine.paths import BRAIN_SUBDIRS


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
