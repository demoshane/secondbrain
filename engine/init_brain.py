"""Brain initialization command."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from engine.paths import BRAIN_ROOT, BRAIN_SUBDIRS, INDEX_ROOT
from engine.db import get_connection, init_schema

CONSENT_NOTICE = (
    "Second Brain will store notes locally. Some notes may contain personal data.\n"
    "Do you consent to local storage of your notes? (yes/no): "
)
CONSENT_PATH_RELATIVE = Path(".meta") / "consent.json"


def check_consent(brain_root: Path) -> bool:
    """Return True if consent sentinel file exists at .meta/consent.json."""
    return (brain_root / CONSENT_PATH_RELATIVE).exists()


def write_consent_sentinel(brain_root: Path) -> None:
    """Write consent sentinel JSON to .meta/consent.json."""
    sentinel_path = brain_root / CONSENT_PATH_RELATIVE
    sentinel_path.parent.mkdir(parents=True, exist_ok=True)
    sentinel_path.write_text(
        json.dumps({"consented_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(tzinfo=None).isoformat(), "version": "1.0"}),
        encoding="utf-8",
    )


def prompt_consent(brain_root: Path, yes: bool = False) -> bool:
    """Prompt user for consent or auto-approve with yes=True.

    - If consent sentinel already exists: return True immediately (idempotent).
    - If yes=True: write sentinel and return True without prompting.
    - Otherwise: display CONSENT_NOTICE, read input, return True on 'yes',
      False on anything else or on EOFError/KeyboardInterrupt.
    """
    if check_consent(brain_root):
        return True
    if yes:
        write_consent_sentinel(brain_root)
        return True
    try:
        answer = input(CONSENT_NOTICE)
    except (EOFError, KeyboardInterrupt):
        print("\nConsent required. Aborting.")
        return False
    if answer.strip().lower() == "yes":
        write_consent_sentinel(brain_root)
        return True
    print("Consent required. Aborting.")
    return False


def validate_drive_mount(brain_root: Path) -> tuple[bool, str]:
    """Validate that the Drive-synced brain folder is mounted and writable.
    Must be called BEFORE creating any folders (FOUND-05 requirement).
    """
    if not brain_root.is_dir():
        return False, f"Brain root not found: {brain_root}"
    probe = brain_root / ".sb-write-probe"
    try:
        probe.write_text("probe")
        probe.unlink()
        return True, str(brain_root)
    except OSError as e:
        return False, f"Not writable: {e}"


def detect_drive_macos(home=None):
    """Return first GoogleDrive-*/My Drive path under ~/Library/CloudStorage, or None."""
    base = (home or Path.home()) / "Library" / "CloudStorage"
    for candidate in sorted(base.glob("GoogleDrive-*")):
        my_drive = candidate / "My Drive"
        if my_drive.is_dir():
            return my_drive
    return None


def detect_drive_windows(home=None):
    """Return Google Drive My Drive path on Windows, or None."""
    base = home or Path.home()
    candidate = base / "GFS" / "My Drive"
    if candidate.is_dir():
        return candidate
    for letter in "GHIJKLMNOPQRSTUVWXYZ":
        p = Path(f"{letter}:/My Drive")
        if p.is_dir():
            return p
    return None


def detect_drive_path(home=None):
    """Platform-dispatch Drive detection."""
    if sys.platform == "darwin":
        return detect_drive_macos(home)
    elif sys.platform == "win32":
        return detect_drive_windows(home)
    return None


def assert_drive_or_exit(home=None, base_path=None):
    """Detect Drive path; sys.exit(1) with readable message if not found.

    base_path: override used by tests to pass a tmp_path directly.
    """
    if base_path is not None:
        # Test isolation: treat base_path as the home directory
        path = detect_drive_macos(home=base_path) or detect_drive_windows(home=base_path)
    else:
        path = detect_drive_path(home)
    if path is None:
        print(
            "[sb-init] ERROR: Google Drive not found.\n"
            "  macOS: ensure Google Drive for Desktop is installed and signed in\n"
            "         (https://drive.google.com/drive/download).\n"
            "  Windows: ensure Google Drive for Desktop is installed\n"
            "           (https://drive.google.com/drive/download).",
            file=sys.stderr,
        )
        sys.exit(1)
    return path


def ollama_ensure(verbose=True):
    """Detect Ollama; install via package manager if missing. Return True if ready."""
    if not shutil.which("ollama"):
        if sys.platform == "darwin" and shutil.which("brew"):
            if verbose:
                print("[sb-init] Installing Ollama via Homebrew...")
            subprocess.run(["brew", "install", "ollama"], check=True)
        elif sys.platform == "win32" and shutil.which("winget"):
            if verbose:
                print("[sb-init] Installing Ollama via winget...")
            subprocess.run(["winget", "install", "Ollama.Ollama"], check=True)
        else:
            if verbose:
                print(
                    "[sb-init] ERROR: Ollama not found and no package manager available.\n"
                    "  Install manually from https://ollama.com/download",
                    file=sys.stderr,
                )
            return False
    # HTTP probe — binary may exist but service not running
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434", timeout=2)
    except Exception:
        if verbose:
            print(
                "[sb-init] Ollama binary found but service not running.\n"
                "  Start the Ollama app or run: ollama serve"
            )
    return True


def ollama_model_size_warning(model="nomic-embed-text"):
    """Print size warning if model not yet downloaded; then pull."""
    try:
        import ollama as _ollama
        result = _ollama.list()
        model_names = [m.model for m in result.models] if result.models else []
        if not any(model in name for name in model_names):
            print(
                f"[sb-init] Downloading {model} (~800 MB). "
                "This may take a few minutes on a slow connection."
            )
            subprocess.run(["ollama", "pull", model], check=True)
    except ImportError:
        # ollama SDK not installed — fall back to subprocess
        try:
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=10
            )
            if model not in result.stdout:
                print(
                    f"[sb-init] Downloading {model} (~800 MB). "
                    "This may take a few minutes on a slow connection."
                )
                subprocess.run(["ollama", "pull", model], check=True)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # Ollama not available — embeddings.py will handle at runtime
    except Exception:
        pass  # Ollama not available — embeddings.py will handle at runtime


def seed_templates(brain_root: Path) -> dict:
    """Copy repo skeleton templates to brain_root/.meta/templates/.
    Idempotent — existing files are never overwritten.
    """
    source_dir = Path(__file__).parent.parent / "brain" / ".meta" / "templates"
    dest_dir = brain_root / ".meta" / "templates"
    dest_dir.mkdir(parents=True, exist_ok=True)
    seeded = []
    existed = []
    for src in sorted(source_dir.glob("*.md")):
        dest = dest_dir / src.name
        if dest.exists():
            existed.append(src.name)
        else:
            shutil.copy2(src, dest)
            seeded.append(src.name)
    return {"seeded": seeded, "existed": existed}


def create_brain_structure(brain_root: Path, force: bool = False) -> dict:
    """Create brain subdirectories. Reports created vs. already existed.
    Idempotent — safe to call multiple times (FOUND-03).
    """
    created = []
    existed = []
    for subdir in BRAIN_SUBDIRS:
        p = brain_root / subdir
        if p.exists():
            existed.append(subdir)
        else:
            p.mkdir(parents=True, exist_ok=True)
            created.append(subdir)
    seed_templates(brain_root)
    return {"created": created, "existed": existed}


def generate_vscode_settings(brain_root: Path) -> Path:
    """Write .vscode/settings.json hiding binary files from VS Code explorer (FOUND-06)."""
    vscode_dir = brain_root / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    settings = {
        "files.exclude": {
            "**/*.db": True,
            "**/*.db-shm": True,
            "**/*.db-wal": True,
            "**/*.pdf": True,
            "**/*.docx": True,
            "**/*.xlsx": True,
            "**/*.pptx": True,
            "**/.sb-write-probe": True
        }
    }
    settings_path = vscode_dir / "settings.json"
    settings_path.write_text(json.dumps(settings, indent=2))
    return settings_path


def write_mcp_config(sb_mcp_bin: str | None = None, _cfg_path=None) -> None:
    """Write the second-brain MCP server entry to Claude Desktop config.

    Args:
        sb_mcp_bin: Path to the sb-mcp-server binary. If None, resolved via shutil.which.
        _cfg_path: Override config path (used in tests; if None, platform default is used).
    """
    import json
    import platform

    if sb_mcp_bin is None:
        sb_mcp_bin = shutil.which("sb-mcp-server")
    if sb_mcp_bin is None:
        # Fall back to venv-relative path (common when running via `uv run`)
        venv_candidate = Path(sys.executable).parent / "sb-mcp-server"
        if venv_candidate.exists():
            sb_mcp_bin = str(venv_candidate)
    if sb_mcp_bin is None:
        print(
            "  [MCP] sb-mcp-server not found in PATH — skipping Claude Desktop config.",
            file=sys.stderr,
        )
        return

    if _cfg_path is not None:
        cfg_path = Path(_cfg_path)
    else:
        system = platform.system()
        if system == "Darwin":
            cfg_path = (
                Path.home() / "Library" / "Application Support" / "Claude"
                / "claude_desktop_config.json"
            )
        elif system == "Windows":
            import os
            cfg_path = (
                Path(os.environ.get("APPDATA", "")) / "Claude"
                / "claude_desktop_config.json"
            )
        else:
            # Linux: Claude Desktop not available — skip silently
            return

    cfg: dict = {}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cfg = {}

    cfg.setdefault("mcpServers", {})["second-brain"] = {
        "command": sb_mcp_bin,
        "args": [],
    }
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"  [MCP] Wrote Claude Desktop config: {cfg_path}", file=sys.stderr)
    print("  [MCP] Restart Claude Desktop to activate the MCP server.", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Initialize the Second Brain folder structure and SQLite schema")
    ap.add_argument("--force", action="store_true", help="Recreate missing dirs (notes preserved)")
    ap.add_argument("--reset-db", action="store_true", help="Drop and recreate SQLite schema (DESTRUCTIVE)")
    ap.add_argument("--yes", action="store_true", help="Non-interactive: skip consent prompt (CI/DevContainer use)")
    ap.add_argument("--detect-drive", action="store_true",
                    help="Auto-detect Google Drive path instead of using configured BRAIN_ROOT")
    args = ap.parse_args()

    if not prompt_consent(BRAIN_ROOT, yes=args.yes):
        sys.exit(1)

    if args.detect_drive:
        detected = assert_drive_or_exit()
        print(f"[sb-init] Detected Google Drive at: {detected}")

    print("[sb-init] Validating Drive mount...")
    ok, msg = validate_drive_mount(BRAIN_ROOT)
    if not ok:
        print(f"  [FAIL] Drive mount: {msg}")
        print("[sb-init] Aborted — Drive mount must be active and writable before init.")
        sys.exit(1)
    print(f"  [PASS] Drive mount: {msg}")

    print("[sb-init] Creating brain structure...")
    result = create_brain_structure(BRAIN_ROOT, force=args.force)
    for d in result["created"]:
        print(f"  [CREATED] {d}/")
    for d in result["existed"]:
        print(f"  [EXISTS]  {d}/")

    print("[sb-init] Initializing SQLite schema...")
    conn = get_connection()
    init_schema(conn, reset=args.reset_db)
    conn.close()
    if args.reset_db:
        print("  [RESET] Schema dropped and recreated")
    else:
        print("  [OK] Schema initialized (idempotent)")

    print("[sb-init] Checking Ollama...")
    if ollama_ensure():
        ollama_model_size_warning()
        print("  [OK] Ollama ready")
    else:
        print("  [WARN] Ollama not ready — PII routing will be unavailable")

    print("[sb-init] Writing AI config...")
    config_path = BRAIN_ROOT / ".meta" / "config.toml"
    if not config_path.exists():
        config_path.write_text(
            '[routing]\n'
            'pii_model    = "ollama/llama3.2"\n'
            'private_model = "claude"\n'
            'public_model  = "claude"\n'
            '\n'
            '[ollama]\n'
            'host = "http://host.docker.internal:11434"\n'
            '\n'
            '[models]\n'
            '"ollama/llama3.2" = {adapter = "ollama", model = "llama3.2"}\n'
            '"claude"          = {adapter = "claude", model = ""}\n',
            encoding="utf-8",
        )
        print(f"  [CREATED] {config_path}")
    else:
        print(f"  [EXISTS]  {config_path}")

    print("[sb-init] Generating VS Code settings...")
    settings_path = generate_vscode_settings(BRAIN_ROOT)
    print(f"  [OK] {settings_path}")

    print("[sb-init] Writing Claude Desktop MCP config...")
    write_mcp_config()

    print("[sb-init] Done.")
