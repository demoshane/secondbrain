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


def _resolve_digest(digests_dir: Path, selector: str) -> "Path | None":
    """Resolve a digest selector ('latest' or 'YYYY-WNN') to a Path, or None if not found."""
    files = sorted(digests_dir.glob("*.md"))
    if not files:
        return None
    if selector == "latest":
        return files[-1]
    target = digests_dir / f"{selector}.md"
    return target if target.exists() else None


def main(argv=None) -> None:
    """CLI entry point for sb-read."""
    parser = argparse.ArgumentParser(description="Display a note from the second brain.")
    parser.add_argument("path", type=Path, nargs="?", help="Path to the note file.")
    parser.add_argument("--digest", metavar="SELECTOR", help="Read digest: 'latest' or 'YYYY-WNN'")
    args = parser.parse_args(argv)

    if args.digest:
        from engine.paths import BRAIN_ROOT
        digests_dir = BRAIN_ROOT / ".meta" / "digests"
        digest_path = _resolve_digest(digests_dir, args.digest)
        if digest_path is None:
            print("No digests found.")
            sys.exit(0)
        # Read digest file directly — not PII-gated (type: digest, not content_sensitivity: pii)
        print(digest_path.read_text(encoding="utf-8"))
        sys.exit(0)

    from engine.db import get_connection, init_schema

    conn = get_connection()
    init_schema(conn)
    code = read_note(args.path, conn)
    sys.exit(code)
