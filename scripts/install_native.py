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
    found = shutil.which("uv")
    if found:
        return Path(found).resolve()
    fallback = Path.home() / ".local" / "bin" / "uv"
    if fallback.exists():
        return fallback
    raise FileNotFoundError(
        "uv not found in PATH or ~/.local/bin/uv — install uv first: https://docs.astral.sh/uv/"
    )


def install_global_cli(repo_root: Path) -> None:
    """Install project as a global uv tool (editable).

    Runs: uv tool install --editable --force <repo_root>
    """
    uv = find_uv()
    print(f"Installing global CLI from {repo_root} ...")
    subprocess.run(
        [str(uv), "tool", "install", "--editable", "--force", str(repo_root)],
        check=True,
    )
    if str(Path.home() / ".local" / "bin") not in os.environ.get("PATH", ""):
        print("~/.local/bin not in PATH — running uv tool update-shell ...")
        subprocess.run([str(uv), "tool", "update-shell"], check=True)
    print("Global CLI installed.")


def write_plist(sb_watch_bin: Path, repo_root: Path, plist_path: Path = None) -> Path:
    """Generate and write the launchd plist for sb-watch.

    Creates ~/Library/LaunchAgents/com.secondbrain.watch.plist using plistlib.dump.
    Returns the path to the written plist file.
    """
    target = plist_path if plist_path is not None else PLIST_PATH
    print(f"Writing plist to {target} ...")
    target.parent.mkdir(parents=True, exist_ok=True)
    log_dir = Path.home() / "Library" / "Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    plist = {
        "Label": PLIST_LABEL,
        "ProgramArguments": [str(sb_watch_bin)],
        "WorkingDirectory": str(Path.home() / "SecondBrain"),
        "EnvironmentVariables": {
            "PATH": f"{Path.home()}/.local/bin:/usr/local/bin:/usr/bin:/bin",
            "HOME": str(Path.home()),
        },
        "KeepAlive": True,
        "StandardOutPath": str(log_dir / "second-brain-watch.log"),
        "StandardErrorPath": str(log_dir / "second-brain-watch-error.log"),
    }
    with open(target, "wb") as f:
        plistlib.dump(plist, f)
    return target


def load_launchd_agent(plist_path: Path) -> None:
    """Load (or reload) the launchd agent idempotently.

    Runs launchctl bootout first (ignores error if not loaded),
    then launchctl bootstrap gui/<uid> <plist_path>.
    """
    uid = os.getuid()
    domain = f"gui/{uid}"
    # bootout: ignore failure (exit code 36 = already unloaded, harmless)
    subprocess.run(
        ["launchctl", "bootout", f"{domain}/{PLIST_LABEL}"],
        capture_output=True,
    )
    result = subprocess.run(
        ["launchctl", "bootstrap", domain, str(plist_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    print(f"Loaded launchd agent: {PLIST_LABEL}")


def install_hook(repo_path: Path, hooks_dir: Path) -> None:
    """Point repo_path's git hooks at hooks_dir via git config core.hooksPath.

    Validates that repo_path is a valid git repository first.
    Raises ValueError if repo_path is not a git repo.
    Uses /usr/bin/git -C <path> (not bare git — scm_breeze compat).
    """
    result = subprocess.run(
        ["/usr/bin/git", "-C", str(repo_path), "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"Not a git repo: {repo_path}")
    subprocess.run(
        ["/usr/bin/git", "-C", str(repo_path), "config", "core.hooksPath", str(hooks_dir)],
        check=True,
    )
    print(f"Installed hook: {repo_path}")


def main() -> None:
    """Argparse dispatcher: --cli, --launchd, --hooks REPOS..., default=all three."""
    parser = argparse.ArgumentParser(
        description="Install native macOS integrations for second-brain."
    )
    parser.add_argument("--cli", action="store_true", help="Install global CLI only")
    parser.add_argument("--launchd", action="store_true", help="Install launchd watcher agent")
    parser.add_argument("--hooks", nargs="+", metavar="REPO", help="Install git hook in REPO paths")
    args = parser.parse_args()

    run_all = not (args.cli or args.launchd or args.hooks)

    if args.cli or run_all:
        install_global_cli(REPO_ROOT)

    if args.launchd or run_all:
        install_global_cli(REPO_ROOT)
        sb_watch_bin = find_uv().parent / "sb-watch"
        plist_path = write_plist(sb_watch_bin, REPO_ROOT)
        load_launchd_agent(plist_path)

    if args.hooks:
        for repo in args.hooks:
            install_hook(Path(repo), HOOKS_DIR)
    elif run_all:
        print("No repos specified for --hooks. Run: python scripts/install_native.py --hooks /path/to/repo")


if __name__ == "__main__":
    main()
