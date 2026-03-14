from __future__ import annotations

import argparse
import getpass
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import frontmatter


_ACCESS_DENIED = "Access denied: passphrase required for PII note."


def read_note(path: Path, conn: sqlite3.Connection) -> int:
    """Display note, gating PII notes behind passphrase. GDPR-04. Returns 0 on success, 1 on denial."""
    if not path.exists():
        print("Error: note not found.", file=sys.stderr)
        return 1

    try:
        post = frontmatter.load(str(path))
    except Exception as e:
        print(type(e).__name__, file=sys.stderr)
        return 1

    sensitivity = post.get("content_sensitivity", "public")

    if sensitivity == "pii":
        expected = os.environ.get("SB_PII_PASSPHRASE", "")
        if not expected:
            print(_ACCESS_DENIED)
            return 1

        entered = os.environ.get("SB_PII_PASSPHRASE_INPUT", "")
        if not entered:
            try:
                entered = getpass.getpass("Passphrase: ")
            except (EOFError, KeyboardInterrupt):
                print(_ACCESS_DENIED)
                return 1

        if entered != expected:
            print(_ACCESS_DENIED)
            return 1

    # Audit log — best-effort, never blocks read
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO audit_log (event_type, note_path, created_at) VALUES (?, ?, ?)",
            ("read", str(path), now),
        )
        conn.commit()
    except Exception:
        pass

    # Print frontmatter header + content
    title = post.get("title", "")
    note_type = post.get("type", "")
    print("---")
    if title:
        print(f"title: {title}")
    if note_type:
        print(f"type: {note_type}")
    if sensitivity:
        print(f"content_sensitivity: {sensitivity}")
    print("---")
    print(post.content)

    return 0


def main() -> None:
    """CLI entry point for sb-read."""
    parser = argparse.ArgumentParser(description="Display a note from the second brain.")
    parser.add_argument("path", type=Path, help="Path to the note file.")
    args = parser.parse_args()

    from engine.db import get_connection, init_schema

    conn = get_connection()
    init_schema(conn)
    code = read_note(args.path, conn)
    sys.exit(code)
