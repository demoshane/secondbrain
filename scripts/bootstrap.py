"""
Bootstrap validator for Second Brain DevContainer.

Run on the HOST before opening the devcontainer, or inside the container
to verify the environment is correctly configured.

Usage: uv run python scripts/bootstrap.py --dev
"""
import argparse
import importlib.util
import platform
import sys
from pathlib import Path

# All checks registered via the @check decorator
_checks = []

# Detect container environment — /.dockerenv is absent in some DevContainer builds;
# fall back to checking the VS Code env var and the workspace mount point.
import os as _os
_IN_CONTAINER = (
    Path("/.dockerenv").exists()
    or _os.environ.get("REMOTE_CONTAINERS") == "true"
    or Path("/workspace").is_dir()
)


def check(label: str):
    """Register a check function."""
    def decorator(fn):
        _checks.append((label, fn))
        return fn
    return decorator


@check("Drive folder exists and is writable")
def check_drive():
    # Inside container the brain is bind-mounted at /workspace/brain
    drive_path = Path("/workspace/brain") if _IN_CONTAINER else Path.home() / "SecondBrain"
    if not drive_path.is_dir():
        hint = f"{drive_path} not found — brain bind-mount missing" if _IN_CONTAINER else f"{drive_path} not found — create ~/SecondBrain and sync Google Drive"
        return False, hint
    probe = drive_path / ".sb-probe"
    try:
        probe.write_text("probe")
        probe.unlink()
        return True, str(drive_path)
    except OSError as e:
        return False, f"Not writable: {e}"


@check(".env.host file present")
def check_env_host():
    # Inside container .env.host is bind-mounted at /workspace/.env.host
    env_path = Path("/workspace/.env.host") if _IN_CONTAINER else Path.home() / ".config" / "second-brain" / ".env.host"
    if env_path.exists():
        return True, str(env_path)
    hint = f"{env_path} not found — .env.host bind-mount missing" if _IN_CONTAINER else f"{env_path} not found — copy .env.host.example to {env_path}"
    return False, hint


@check("Python dependency: python-frontmatter")
def check_python_frontmatter():
    spec = importlib.util.find_spec("frontmatter")
    if spec is not None:
        return True, "installed"
    return False, "not installed — run: uv pip install python-frontmatter"


@check("Python version >= 3.12")
def check_python_version():
    v = sys.version_info
    if v >= (3, 12):
        return True, f"{v.major}.{v.minor}.{v.micro}"
    return False, f"Found {v.major}.{v.minor} — need >= 3.12"


def _check_windows_wsl2():
    """Print WSL2 warning if running on Windows."""
    if platform.system() == "Windows":
        print()
        print("  [WARN] Windows detected: ${localEnv:HOME} in devcontainer.json may resolve")
        print("         to the Windows path (C:\\Users\\...) instead of the WSL2 path.")
        print("         If the brain mount fails, see README for WSL2 workaround.")
        print()


def main():
    ap = argparse.ArgumentParser(
        description="Validate Second Brain DevContainer prerequisites"
    )
    ap.add_argument("--dev", action="store_true", help="Run development environment checks")
    args = ap.parse_args()

    if not args.dev:
        ap.print_help()
        sys.exit(0)

    if sys.prefix == sys.base_prefix:
        print("[WARN] Not running inside a virtual environment.")
        print("[WARN] Run via: uv run python scripts/bootstrap.py --dev")
        print("[WARN] python-frontmatter and other deps may be missing.")
        print()

    print("[bootstrap] Second Brain — environment check")
    print()

    _check_windows_wsl2()

    results = []
    for label, fn in _checks:
        ok, msg = fn()
        results.append((label, ok, msg))
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {label}: {msg}")

    print()
    all_pass = all(ok for _, ok, _ in results)
    if all_pass:
        print("[bootstrap] All checks passed. You can now open the DevContainer.")
        sys.exit(0)
    else:
        failed = sum(1 for _, ok, _ in results if not ok)
        print(f"[bootstrap] {failed} check(s) failed. Fix the issues above before opening the DevContainer.")
        sys.exit(1)


if __name__ == "__main__":
    main()
