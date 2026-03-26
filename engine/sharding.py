"""Filesystem sharding helpers for 100K+ note scale.

Provides utilities to move notes into type-based subdirectories with atomic
DB path updates across all tables that reference note paths.

Usage:
    from engine.sharding import get_shard_path, shard_note, shard_all_notes

    # Compute target path for a note
    target = get_shard_path(brain_root, note_type="meeting", filename="2026-q1.md")

    # Move a note into its correct shard (atomic)
    shard_note(conn, old_path="2026-q1.md", new_path="meetings/2026-q1.md")

    # Dry-run: list all moves needed without executing
    moves = shard_all_notes(conn, brain_root, dry_run=True)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# Shard map: note type → subdirectory name
# ---------------------------------------------------------------------------

SHARD_MAP: dict[str, str] = {
    "meeting": "meetings",
    "person": "people",
    "project": "projects",
    "strategy": "strategy",
    "idea": "ideas",
    "personal": "personal",
    "coding": "coding",
    "file": "files",
    "link": "links",
}

DEFAULT_SHARD = "notes"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_shard_path(brain_root: Path, note_type: str, filename: str) -> Path:
    """Return the target path for a note given its type and filename.

    Creates the target subdirectory if it does not exist.

    Args:
        brain_root: Root directory of the brain (e.g. ~/SecondBrain).
        note_type:  Note type string (e.g. "meeting", "person"). Unknown types
                    are mapped to DEFAULT_SHARD.
        filename:   Filename only (e.g. "2026-q1.md"). No path component.

    Returns:
        Full Path: brain_root / shard_subdir / filename.
    """
    shard_dir = SHARD_MAP.get(note_type, DEFAULT_SHARD)
    target_dir = brain_root / shard_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / filename


def shard_note(conn: sqlite3.Connection, old_path: str, new_path: str) -> None:
    """Move a note file and update all DB path references atomically.

    Moves the file on disk, then updates every table that stores a note_path
    (or source_path/target_path) in a single DB transaction. If the DB update
    fails, the file is moved back and the exception is re-raised.

    Tables updated:
        notes.path
        note_embeddings.note_path
        note_tags.note_path
        note_people.note_path
        action_items.note_path
        relationships.source_path
        relationships.target_path
        audit_log.note_path

    Args:
        conn:      Open SQLite connection with schema initialised.
        old_path:  Current path of the note (relative or absolute string).
        new_path:  Target path after sharding (relative or absolute string).

    Raises:
        FileNotFoundError: If the source file does not exist on disk.
        Exception:         Any SQLite error — file is moved back on failure.
    """
    old_file = Path(old_path)
    new_file = Path(new_path)

    if not old_file.exists():
        raise FileNotFoundError(f"shard_note: source file not found: {old_path!r}")

    # Create target directory if needed
    new_file.parent.mkdir(parents=True, exist_ok=True)

    # Move file first
    old_file.rename(new_file)

    try:
        # Disable FK enforcement during the cascade path-rename so that
        # updating notes.path does not violate child-table FK constraints.
        # Re-enabled in the finally block regardless of outcome.
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("BEGIN")
        conn.execute("UPDATE notes SET path=? WHERE path=?", (new_path, old_path))
        conn.execute(
            "UPDATE note_embeddings SET note_path=? WHERE note_path=?",
            (new_path, old_path),
        )
        conn.execute(
            "UPDATE note_tags SET note_path=? WHERE note_path=?",
            (new_path, old_path),
        )
        conn.execute(
            "UPDATE note_people SET note_path=? WHERE note_path=?",
            (new_path, old_path),
        )
        conn.execute(
            "UPDATE action_items SET note_path=? WHERE note_path=?",
            (new_path, old_path),
        )
        conn.execute(
            "UPDATE relationships SET source_path=? WHERE source_path=?",
            (new_path, old_path),
        )
        conn.execute(
            "UPDATE relationships SET target_path=? WHERE target_path=?",
            (new_path, old_path),
        )
        conn.execute(
            "UPDATE audit_log SET note_path=? WHERE note_path=?",
            (new_path, old_path),
        )
        conn.execute("COMMIT")
    except Exception:
        # DB failed — roll back and move file back to preserve consistency
        conn.execute("ROLLBACK")
        new_file.rename(old_file)
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def shard_all_notes(
    conn: sqlite3.Connection,
    brain_root: Path,
    dry_run: bool = True,
) -> list[dict]:
    """Compute (and optionally execute) moves for all notes that are not in their correct shard.

    For each note in the DB, computes the target shard path from the note's
    type. Notes already in the correct shard are skipped. Notes without a
    filename (edge case) are also skipped.

    Args:
        conn:       Open SQLite connection with schema initialised.
        brain_root: Root directory of the brain.
        dry_run:    If True, return the moves list without executing. If False,
                    execute shard_note() for each move.

    Returns:
        List of dicts with keys:
            old_path (str): Current path in DB.
            new_path (str): Target path after sharding.
            moved (bool):   True if the move was executed (dry_run=False only).
    """
    rows = conn.execute("SELECT path, type FROM notes").fetchall()
    moves: list[dict] = []

    for (note_path, note_type) in rows:
        p = Path(note_path)
        filename = p.name
        if not filename:
            continue  # skip notes without a filename (shouldn't happen)

        # Compute target path using shard map
        shard_dir = SHARD_MAP.get(note_type or "", DEFAULT_SHARD)

        if p.is_absolute():
            # Absolute path: target is brain_root / shard_dir / filename
            target_path = str(brain_root / shard_dir / filename)
        else:
            # Relative path: target is shard_dir/filename
            target_path = f"{shard_dir}/{filename}"

        if note_path == target_path:
            continue  # already in correct shard

        move = {"old_path": note_path, "new_path": target_path, "moved": False}

        if not dry_run:
            try:
                shard_note(conn, note_path, target_path)
                move["moved"] = True
            except Exception:
                # Skip notes whose file is missing or DB update fails
                pass

        moves.append(move)

    return moves
