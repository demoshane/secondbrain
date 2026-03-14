#!/usr/bin/env python3
"""One-command native macOS setup: global CLI + launchd watcher + git hook installer.

Usage:
    python scripts/install_native.py            # install all three
    python scripts/install_native.py --cli      # global CLI only
    python scripts/install_native.py --launchd  # launchd agent only
    python scripts/install_native.py --hooks /path/to/repo1 /path/to/repo2
"""
import argparse
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / ".githooks"
PLIST_LABEL = "com.secondbrain.watch"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"


def find_uv() -> Path:
    """Locate uv binary via shutil.which, falling back to ~/.local/bin/uv."""
    raise NotImplementedError


def install_global_cli(repo_root: Path) -> None:
    """Install project as a global uv tool (editable).

    Runs: uv tool install --editable --force <repo_root>
    """
    raise NotImplementedError


def write_plist(sb_watch_bin: Path, repo_root: Path) -> Path:
    """Generate and write the launchd plist for sb-watch.

    Creates ~/Library/LaunchAgents/com.secondbrain.watch.plist using plistlib.dump.
    Returns the path to the written plist file.
    """
    raise NotImplementedError


def load_launchd_agent(plist_path: Path) -> None:
    """Load (or reload) the launchd agent idempotently.

    Runs launchctl bootout first (ignores error if not loaded),
    then launchctl bootstrap gui/<uid> <plist_path>.
    """
    raise NotImplementedError


def install_hook(repo_path: Path, hooks_dir: Path) -> None:
    """Point repo_path's git hooks at hooks_dir via git config core.hooksPath.

    Validates that repo_path is a valid git repository first.
    Raises ValueError if repo_path is not a git repo.
    Uses /usr/bin/git -C <path> (not bare git — scm_breeze compat).
    """
    raise NotImplementedError


def main() -> None:
    """Argparse dispatcher: --cli, --launchd, --hooks REPOS..., default=all three."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
