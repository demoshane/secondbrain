"""sb-backup / sb-restore — Fernet-encrypted brain backup and restore.

Creates a tar.gz of all markdown notes + SQLite DB + optional hnswlib index,
encrypted with a per-machine Fernet key stored at ~/.config/second-brain/backup.key.
"""
from __future__ import annotations

import io
import secrets
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken  # noqa: F401 — re-exported for callers

from engine.paths import BRAIN_ROOT, DB_PATH

# ── Constants ────────────────────────────────────────────────────────────────

KEY_PATH = Path.home() / ".config" / "second-brain" / "backup.key"
HNSW_FILENAME = "brain.hnsw"
LABEL_MAP_FILENAME = "label_map.json"
DEFAULT_BACKUP_DIR = BRAIN_ROOT / ".backup"

# Two-step confirm token store: {token: expiry_epoch}
_pending_tokens: dict[str, float] = {}


# ── Key management ───────────────────────────────────────────────────────────

def _get_or_create_key() -> bytes:
    """Return the Fernet key, creating it on first use (chmod 600)."""
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        return KEY_PATH.read_bytes()
    key = Fernet.generate_key()
    KEY_PATH.write_bytes(key)
    KEY_PATH.chmod(0o600)
    return key


# ── Core operations ──────────────────────────────────────────────────────────

def backup_brain(brain_root: Path, db_path: Path, backup_dir: Path) -> Path:
    """Create a Fernet-encrypted tar.gz of brain notes, DB and optional index.

    Args:
        brain_root: Root of the brain (markdown notes live here).
        db_path: Absolute path to the SQLite database file.
        backup_dir: Directory where the .enc file is written (created if needed).

    Returns:
        Path to the created .enc file.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Build tar.gz in memory
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # Add all .md files
        for md_file in sorted(brain_root.rglob("*.md")):
            arcname = "notes/" + str(md_file.relative_to(brain_root))
            tar.add(str(md_file), arcname=arcname)

        # Add SQLite DB
        if db_path.exists():
            tar.add(str(db_path), arcname="brain.db")

        # Add hnswlib index if present
        hnsw_path = brain_root / ".meta" / HNSW_FILENAME
        if hnsw_path.exists():
            tar.add(str(hnsw_path), arcname=HNSW_FILENAME)

        # Add label map if present
        label_map_path = brain_root / ".meta" / LABEL_MAP_FILENAME
        if label_map_path.exists():
            tar.add(str(label_map_path), arcname=LABEL_MAP_FILENAME)

    raw_bytes = buf.getvalue()

    # Encrypt
    key = _get_or_create_key()
    f = Fernet(key)
    encrypted = f.encrypt(raw_bytes)

    # Write to disk
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    enc_path = backup_dir / f"brain-{timestamp}.enc"
    enc_path.write_bytes(encrypted)

    return enc_path


def restore_brain(enc_path: Path, target_root: Path, target_db: Path) -> dict:
    """Decrypt an .enc backup and restore notes + DB to target directories.

    Args:
        enc_path: Path to the .enc backup file.
        target_root: Directory where notes will be restored.
        target_db: Destination path for the SQLite DB.

    Returns:
        dict with keys: notes_restored (int), db_restored (bool), hnsw_restored (bool)

    Raises:
        InvalidToken: If the backup was encrypted with a different key.
    """
    key = _get_or_create_key()
    f = Fernet(key)
    raw_bytes = f.decrypt(enc_path.read_bytes())  # raises InvalidToken on bad key

    notes_restored = 0
    db_restored = False
    hnsw_restored = False

    buf = io.BytesIO(raw_bytes)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        for member in tar.getmembers():
            if member.name.startswith("notes/"):
                # Strip the "notes/" prefix and restore relative to target_root
                rel = member.name[len("notes/"):]
                if not rel:
                    continue
                dest = target_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                fobj = tar.extractfile(member)
                if fobj is not None:
                    dest.write_bytes(fobj.read())
                    notes_restored += 1
            elif member.name == "brain.db":
                target_db.parent.mkdir(parents=True, exist_ok=True)
                fobj = tar.extractfile(member)
                if fobj is not None:
                    target_db.write_bytes(fobj.read())
                    db_restored = True
            elif member.name == HNSW_FILENAME:
                dest = target_root / ".meta" / HNSW_FILENAME
                dest.parent.mkdir(parents=True, exist_ok=True)
                fobj = tar.extractfile(member)
                if fobj is not None:
                    dest.write_bytes(fobj.read())
                    hnsw_restored = True
            elif member.name == LABEL_MAP_FILENAME:
                dest = target_root / ".meta" / LABEL_MAP_FILENAME
                dest.parent.mkdir(parents=True, exist_ok=True)
                fobj = tar.extractfile(member)
                if fobj is not None:
                    dest.write_bytes(fobj.read())

    return {
        "notes_restored": notes_restored,
        "db_restored": db_restored,
        "hnsw_restored": hnsw_restored,
    }


def check_backup_health(backup_dir: Path, warn_days: int = 7) -> dict:
    """Return backup staleness info for sb-health.

    Args:
        backup_dir: Directory containing .enc backup files.
        warn_days: Age threshold in days above which backup is considered stale.

    Returns:
        dict with keys: last_backup (ISO str or None), stale (bool), age_days (int or None)
    """
    if not backup_dir.exists():
        return {"last_backup": None, "stale": True, "age_days": None}

    enc_files = sorted(backup_dir.glob("*.enc"), key=lambda p: p.stat().st_mtime)
    if not enc_files:
        return {"last_backup": None, "stale": True, "age_days": None}

    newest = enc_files[-1]
    mtime = newest.stat().st_mtime
    now = time.time()
    age_seconds = now - mtime
    age_days = int(age_seconds / 86400)

    last_backup = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    stale = age_days >= warn_days

    return {"last_backup": last_backup, "stale": stale, "age_days": age_days}


# ── CLI entry points ─────────────────────────────────────────────────────────

def backup_main() -> None:
    """sb-backup CLI entry point. Creates an encrypted brain backup."""
    enc_path = backup_brain(BRAIN_ROOT, DB_PATH, DEFAULT_BACKUP_DIR)
    print(f"Backup created: {enc_path}")
    print(f"Key: {KEY_PATH}")


def restore_main() -> None:
    """sb-restore CLI entry point. Two-step confirm_token pattern (destructive)."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="sb-restore",
        description="Restore brain from an encrypted backup (DESTRUCTIVE)",
    )
    parser.add_argument(
        "--enc-file",
        required=True,
        help="Path to the .enc backup file to restore from",
    )
    parser.add_argument(
        "--confirm",
        default="",
        help="Confirmation token (obtain from first run without --confirm)",
    )
    args = parser.parse_args()

    enc_path = Path(args.enc_file)
    if not enc_path.exists():
        print(f"Error: backup file not found: {enc_path}", file=sys.stderr)
        sys.exit(1)

    if not args.confirm:
        # Step 1: issue token and print warning
        tok = secrets.token_hex(8)
        _pending_tokens[tok] = time.time() + 60
        print("WARNING: This will overwrite your brain.")
        print(f"Confirm token: {tok}")
        print(f"Re-run with --confirm {tok} within 60 seconds to proceed.")
        sys.exit(0)

    # Step 2: verify token and execute
    tok = args.confirm
    expiry = _pending_tokens.pop(tok, None)
    if expiry is None or time.time() > expiry:
        print("Error: invalid or expired confirm token. Run without --confirm to get a new one.", file=sys.stderr)
        sys.exit(1)

    print(f"Restoring from {enc_path} ...")
    result = restore_brain(enc_path, BRAIN_ROOT, DB_PATH)
    print(f"  Notes restored: {result['notes_restored']}")
    print(f"  DB restored: {result['db_restored']}")
    print(f"  HNSW index restored: {result['hnsw_restored']}")
    print("Restore complete.")
