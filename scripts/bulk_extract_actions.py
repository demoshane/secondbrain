"""Bulk action item extraction — run once to populate action_items from existing notes.

Usage:
    uv run python scripts/bulk_extract_actions.py

Iterates all notes in the brain, calls extract_action_items() on each.
Each call spawns `claude -p` — slow but correct. Skips notes that already
have action items in the DB to make it safe to re-run.
"""
import sys
from pathlib import Path

# Allow running from repo root without install
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.db import get_connection, init_schema
from engine.intelligence import extract_action_items
from engine.paths import BRAIN_ROOT


def main():
    conn = get_connection()
    init_schema(conn)

    notes = conn.execute("SELECT path FROM notes ORDER BY path").fetchall()
    total = len(notes)
    print(f"[bulk-extract] {total} notes to process")

    done = 0
    skipped = 0
    for (note_path,) in notes:
        p = Path(note_path)
        if not p.exists():
            skipped += 1
            continue
        existing = conn.execute(
            "SELECT COUNT(*) FROM action_items WHERE note_path=?", (note_path,)
        ).fetchone()[0]
        if existing > 0:
            skipped += 1
            continue
        print(f"[{done + 1}/{total}] {p.name}", flush=True)
        extract_action_items(p, conn)
        done += 1

    conn.close()
    count = done
    print(f"[bulk-extract] Done. Processed {count} notes, skipped {skipped}.")


if __name__ == "__main__":
    main()
