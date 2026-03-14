"""Brain initialization command."""
import argparse
import json
import shutil
import sys
from pathlib import Path
from engine.paths import BRAIN_ROOT, BRAIN_SUBDIRS, INDEX_ROOT
from engine.db import get_connection, init_schema


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


def main():
    ap = argparse.ArgumentParser(description="Initialize the Second Brain folder structure and SQLite schema")
    ap.add_argument("--force", action="store_true", help="Recreate missing dirs (notes preserved)")
    ap.add_argument("--reset-db", action="store_true", help="Drop and recreate SQLite schema (DESTRUCTIVE)")
    args = ap.parse_args()

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

    print("[sb-init] Done.")
