"""Tests for scripts/install_native.py — Wave 0 stubs (RED phase).

All tests currently raise NotImplementedError until Wave 1 fills the function bodies.
Covers requirements: 4.1-CLI-01, 4.1-CLI-02, 4.1-LAUNCHD-01, 4.1-LAUNCHD-02,
4.1-LAUNCHD-03, 4.1-HOOK-01, 4.1-HOOK-02.
"""
import plistlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch
import subprocess

import pytest

# Make scripts/ importable without package install
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import install_native
from install_native import (
    REPO_ROOT,
    install_global_cli,
    install_hook,
    load_launchd_agent,
    write_plist,
)


# ---------------------------------------------------------------------------
# 4.1-CLI-01: uv tool install called with correct args
# ---------------------------------------------------------------------------

def test_global_cli_install():
    """install_global_cli calls uv tool install --editable --force <repo_root>."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        install_global_cli(REPO_ROOT)
        # Assert subprocess.run was called at least once
        assert mock_run.called
        # Find the call that contains "tool" and "install"
        found = False
        for c in mock_run.call_args_list:
            args = c[0][0] if c[0] else c[1].get("args", [])
            if "tool" in args and "install" in args:
                assert "--editable" in args
                assert "--force" in args
                assert str(REPO_ROOT) in args
                found = True
                break
        assert found, "uv tool install call not found"


# ---------------------------------------------------------------------------
# 4.1-CLI-02: uv tool update-shell called when bin dir not in PATH
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="implemented in Wave 1")
def test_update_shell_if_needed():
    """uv tool update-shell called when ~/.local/bin not in PATH."""
    with patch("subprocess.run") as mock_run, \
         patch("shutil.which", return_value=None):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        install_global_cli(REPO_ROOT)
        calls_flat = [
            c[0][0] if c[0] else c[1].get("args", [])
            for c in mock_run.call_args_list
        ]
        assert any(
            "update-shell" in args for args in calls_flat
        ), "uv tool update-shell not called"


# ---------------------------------------------------------------------------
# 4.1-LAUNCHD-01: plist written with correct keys
# ---------------------------------------------------------------------------

def test_plist_keys(tmp_path):
    """write_plist writes a plist with correct Label, ProgramArguments, KeepAlive, StandardOutPath."""
    fake_bin = Path("/fake/sb-watch")
    fake_repo = Path("/fake/repo")

    # Monkeypatch PLIST_PATH so the file is written into tmp_path
    fake_plist_path = tmp_path / "com.secondbrain.watch.plist"
    with patch.object(install_native, "PLIST_PATH", fake_plist_path):
        result_path = write_plist(fake_bin, fake_repo)

    assert result_path.exists(), "plist file not written"
    with open(result_path, "rb") as f:
        data = plistlib.load(f)

    assert data["Label"] == "com.secondbrain.watch"
    assert data["ProgramArguments"][0] == "/fake/sb-watch"
    assert data["KeepAlive"] is True
    assert "StandardOutPath" in data


# ---------------------------------------------------------------------------
# 4.1-LAUNCHD-02: launchctl bootstrap called for load
# ---------------------------------------------------------------------------

def test_launchctl_bootstrap():
    """load_launchd_agent calls launchctl bootstrap with the plist path."""
    fake_plist = Path("/fake/com.secondbrain.watch.plist")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        load_launchd_agent(fake_plist)
        calls_flat = [
            c[0][0] if c[0] else c[1].get("args", [])
            for c in mock_run.call_args_list
        ]
        assert any(
            "bootstrap" in args for args in calls_flat
        ), "launchctl bootstrap not called"


# ---------------------------------------------------------------------------
# 4.1-LAUNCHD-03: idempotent — bootout called before bootstrap each time
# ---------------------------------------------------------------------------

def test_idempotent_load():
    """load_launchd_agent calls bootout before bootstrap each time it runs."""
    fake_plist = Path("/fake/com.secondbrain.watch.plist")

    def run_twice():
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            load_launchd_agent(fake_plist)
            load_launchd_agent(fake_plist)
            return mock_run.call_args_list

    all_calls = run_twice()
    calls_flat = [
        c[0][0] if c[0] else c[1].get("args", [])
        for c in all_calls
    ]
    bootout_indices = [i for i, args in enumerate(calls_flat) if "bootout" in args]
    bootstrap_indices = [i for i, args in enumerate(calls_flat) if "bootstrap" in args]

    assert len(bootout_indices) >= 2, "bootout should be called at least twice (once per load)"
    # Each bootout should precede a bootstrap
    for b_out, b_in in zip(bootout_indices, bootstrap_indices):
        assert b_out < b_in, "bootout must come before bootstrap"


# ---------------------------------------------------------------------------
# 4.1-HOOK-01: git rev-parse validates repo; git config core.hooksPath written
# ---------------------------------------------------------------------------

def test_hook_install():
    """install_hook validates git repo and sets core.hooksPath."""
    fake_repo = Path("/fake/repo")
    fake_hooks = Path("/fake/.githooks")

    def mock_run(args, **kwargs):
        if "rev-parse" in args:
            return MagicMock(returncode=0, stdout=".git\n", stderr="")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=mock_run) as mock_sp:
        install_hook(fake_repo, fake_hooks)
        calls_flat = [
            c[0][0] if c[0] else c[1].get("args", [])
            for c in mock_sp.call_args_list
        ]
        assert any(
            "core.hooksPath" in args for args in calls_flat
        ), "core.hooksPath not set"


# ---------------------------------------------------------------------------
# 4.1-HOOK-02: invalid/non-git path raises ValueError
# ---------------------------------------------------------------------------

def test_hook_install_invalid_repo():
    """install_hook raises ValueError when path is not a git repo."""
    fake_repo = Path("/not/a/repo")
    fake_hooks = Path("/fake/.githooks")

    def mock_run(args, **kwargs):
        if "rev-parse" in args:
            return MagicMock(returncode=1, stdout="", stderr="not a git repo")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=mock_run):
        with pytest.raises(ValueError):
            install_hook(fake_repo, fake_hooks)


# ---------------------------------------------------------------------------
# Phase 35-03: write_consolidate_plist test
# ---------------------------------------------------------------------------

def test_write_consolidate_plist(tmp_path):
    from scripts.install_native import write_consolidate_plist
    import plistlib
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    plist_path = write_consolidate_plist(tmp_path, log_dir)
    assert plist_path.exists()
    with open(plist_path, "rb") as f:
        data = plistlib.load(f)
    assert data["Label"] == "com.secondbrain.consolidate"
    assert data["StartCalendarInterval"] == {"Hour": 3, "Minute": 0}
    assert "sb-consolidate" in data["ProgramArguments"]
