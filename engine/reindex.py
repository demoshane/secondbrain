"""Rebuild SQLite index from markdown source files.

Used after volume loss or fresh install (FOUND-07).
All path handling uses pathlib.Path — no os.path (FOUND-12).
"""
import datetime
import json
import sys
from pathlib import Path

import frontmatter

from engine.db import get_connection, init_schema
from engine.paths import BRAIN_ROOT


def reindex_brain(brain_root: Path, conn=None) -> dict:
    """Walk all .md files under brain_root and upsert them into notes + FTS5.

    Args:
        brain_root: Path to brain root directory (BRAIN_ROOT in production)
        conn: Optional sqlite3.Connection (for testing with in-memory DB)

    Returns dict with keys: indexed (int), errors (list of str)
    """
    close_after = conn is None
    if conn is None:
        conn = get_connection()

    init_schema(conn)

    indexed = 0
    errors = []

    for md_path in sorted(brain_root.rglob("*.md")):
        try:
            post = frontmatter.load(str(md_path))
            meta = post.metadata

            # Use relative path as the canonical identifier
            try:
                rel_path = str(md_path.relative_to(brain_root))
            except ValueError:
                rel_path = str(md_path)

            tags = meta.get("tags", [])
            if isinstance(tags, list):
                tags_json = json.dumps(tags)
            else:
                tags_json = json.dumps([str(tags)])

            now = datetime.datetime.utcnow().isoformat()

            conn.execute(
                """
                INSERT INTO notes (path, type, title, body, tags, created_at, updated_at, sensitivity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    type=excluded.type,
                    title=excluded.title,
                    body=excluded.body,
                    tags=excluded.tags,
                    updated_at=excluded.updated_at,
                    sensitivity=excluded.sensitivity
                """,
                (
                    rel_path,
                    meta.get("type", "note"),
                    meta.get("title", md_path.stem),
                    post.content,
                    tags_json,
                    meta.get("created_at", now),
                    now,
                    meta.get("content_sensitivity", "public"),
                ),
            )
            indexed += 1
        except Exception as e:
            errors.append(f"{md_path}: {e}")

    # Rebuild FTS5 index to ensure consistency
    conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")
    conn.commit()

    if close_after:
        conn.close()

    return {"indexed": indexed, "errors": errors}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Rebuild SQLite index from brain markdown files")
    ap.parse_args()

    print("[sb-reindex] Starting full index rebuild...")
    result = reindex_brain(BRAIN_ROOT)

    print(f"  [OK] Indexed {result['indexed']} notes")
    if result["errors"]:
        print(f"  [WARN] {len(result['errors'])} errors:")
        for e in result["errors"]:
            print(f"    - {e}")
        sys.exit(1)
    print("[sb-reindex] Done.")
