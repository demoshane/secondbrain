"""GDPR Article 20 data portability — sb-export CLI."""
import argparse
import datetime
import json
import sqlite3
import sys
from pathlib import Path


def export_brain(brain_root: Path, conn: sqlite3.Connection, output_path: Path, fmt: str = "json") -> int:
    """Export all notes to portable JSON. Returns count of exported rows.

    All notes including sensitivity='pii' are included — Article 20 covers
    all personal data the user has stored. Writes an audit_log row after
    every call. Creates parent directories if absent.
    """
    rows = conn.execute(
        "SELECT path, type, title, body, tags, people, created_at, updated_at, sensitivity"
        " FROM notes"
    ).fetchall()

    notes = [
        {
            "path": row[0],
            "type": row[1],
            "title": row[2],
            "body": row[3],
            "tags": row[4],
            "people": row[5],
            "created_at": row[6],
            "updated_at": row[7],
            "content_sensitivity": row[8],
        }
        for row in rows
    ]

    # GDPR Article 20: include archived action items for full data portability
    archive_rows = conn.execute(
        "SELECT note_path, text, done_at, created_at, archived_at, archived_reason"
        " FROM action_items_archive"
    ).fetchall()

    archived_items = [
        {
            "note_path": r[0],
            "text": r[1],
            "done_at": r[2],
            "created_at": r[3],
            "archived_at": r[4],
            "archived_reason": r[5],
        }
        for r in archive_rows
    ]

    export_data = {"notes": notes, "archived_action_items": archived_items}
    count = len(notes)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(export_data, indent=2, ensure_ascii=False), encoding="utf-8")

    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?, ?, ?, ?)",
        ("export", None, f"format:{fmt} count:{count}", now),
    )
    conn.commit()

    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Export all brain notes to a portable JSON file (GDPR Art. 20)")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path (default: ./sb-export-<YYYYMMDDTHHMMSS>.json)",
    )
    parser.add_argument(
        "--brain-root",
        type=Path,
        default=None,
        help="Brain root directory (default: BRAIN_ROOT from config)",
    )
    args = parser.parse_args()

    from engine.paths import BRAIN_ROOT
    from engine.db import get_connection, init_schema

    brain_root = args.brain_root if args.brain_root is not None else BRAIN_ROOT

    if args.output is None:
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        output_path = Path(f"sb-export-{timestamp}.json")
    else:
        output_path = args.output

    conn = get_connection()
    init_schema(conn)
    try:
        count = export_brain(brain_root, conn, output_path)
    finally:
        conn.close()

    print(f"Exported {count} notes to {output_path}")
    sys.exit(0)
