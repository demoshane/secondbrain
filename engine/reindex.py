"""Rebuild SQLite index from markdown source files.

Used after volume loss or fresh install (FOUND-07).
All path handling uses pathlib.Path — no os.path (FOUND-12).
Stores absolute paths in DB (SEARCH-01) so RAG reads can locate files directly.
"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

import frontmatter

from engine.db import get_connection, init_schema
from engine.paths import BRAIN_ROOT


def embed_pass(conn, provider: str, batch_size: int = 32, force: bool = False) -> dict:
    """Second pass: generate/update embeddings for stale or missing notes.

    Args:
        conn: Active sqlite3.Connection (WAL mode).
        provider: "sentence-transformers" or "ollama" from config.
        batch_size: Encoding batch size.
        force: If True, re-embed all notes regardless of hash (--full flag).

    Returns dict with keys: updated (int), unchanged (int).
    """
    import importlib
    import sys as _sys
    # Use sys.modules lookup so test mocks injected via sys.modules["engine.embeddings"]
    # are honoured; fall back to a fresh import if the module isn't loaded yet.
    if "engine.embeddings" not in _sys.modules:
        importlib.import_module("engine.embeddings")
    _embeddings = _sys.modules["engine.embeddings"]

    rows = conn.execute("SELECT path, body FROM notes").fetchall()
    existing = {
        r[0]: r[1]
        for r in conn.execute(
            "SELECT note_path, content_hash FROM note_embeddings"
        ).fetchall()
    }

    to_embed = []
    for path, body in rows:
        h = hashlib.sha256(body.encode()).hexdigest()
        if force or existing.get(path) != h:
            to_embed.append((path, body, h))

    unchanged = len(rows) - len(to_embed)

    if not to_embed:
        return {"updated": 0, "unchanged": unchanged}

    print(f"[sb-reindex] Embedding {len(to_embed)} new/stale notes...")

    paths, bodies, hashes = zip(*to_embed)
    blobs = _embeddings.embed_texts(list(bodies), provider=provider, batch_size=batch_size)
    now = datetime.datetime.utcnow().isoformat()

    for path, blob, h in zip(paths, blobs, hashes):
        conn.execute(
            """INSERT INTO note_embeddings (note_path, embedding, content_hash, stale, updated_at)
               VALUES (?, ?, ?, 0, ?)
               ON CONFLICT(note_path) DO UPDATE SET
                   embedding=excluded.embedding,
                   content_hash=excluded.content_hash,
                   stale=0,
                   updated_at=excluded.updated_at""",
            (path, blob, h, now),
        )
    conn.commit()
    return {"updated": len(to_embed), "unchanged": unchanged}


def reindex_brain(brain_root: Path, conn=None, full: bool = False) -> dict:
    """Walk all .md files under brain_root and upsert them into notes + FTS5.

    Args:
        brain_root: Path to brain root directory (BRAIN_ROOT in production)
        conn: Optional sqlite3.Connection (for testing with in-memory DB)
        full: If True, force re-embedding of all notes regardless of hash state.

    Returns dict with keys: indexed (int), errors (list of str),
                            embed_updated (int), embed_unchanged (int)
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

            note_path = str(md_path.resolve())

            tags = meta.get("tags", [])
            if isinstance(tags, list):
                tags_json = json.dumps(tags)
            else:
                tags_json = json.dumps([str(tags)])

            people = meta.get("people", [])
            if isinstance(people, list):
                people_json = json.dumps(people)
            else:
                people_json = json.dumps([str(people)])

            now = datetime.datetime.utcnow().isoformat()

            conn.execute(
                """
                INSERT INTO notes (path, type, title, body, tags, created_at, updated_at, sensitivity, people)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    type=excluded.type,
                    title=excluded.title,
                    body=excluded.body,
                    tags=excluded.tags,
                    updated_at=excluded.updated_at,
                    sensitivity=excluded.sensitivity,
                    people=excluded.people
                """,
                (
                    note_path,
                    meta.get("type", "note"),
                    meta.get("title", md_path.stem),
                    post.content,
                    tags_json,
                    meta.get("created_at", now),
                    now,
                    meta.get("content_sensitivity", "public"),
                    people_json,
                ),
            )
            indexed += 1
        except Exception as e:
            errors.append(f"{md_path}: {e}")

    # Rebuild FTS5 index to ensure consistency
    conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")
    conn.commit()

    # Build wiki-link relationships from note bodies
    from engine.links import update_wiki_link_relationships
    all_notes = conn.execute("SELECT path, body FROM notes").fetchall()
    for note_path, body in all_notes:
        update_wiki_link_relationships(conn, note_path, body)

    # --- Embedding second pass ---
    from engine.config_loader import load_config
    config = load_config(BRAIN_ROOT / ".meta" / "config.toml")
    embed_cfg = config.get("embeddings", {})
    provider = embed_cfg.get("provider", "sentence-transformers")
    batch_size = embed_cfg.get("batch_size", 32)

    # First-run download notice: print before model load if no embeddings exist yet
    has_embeddings = conn.execute("SELECT COUNT(*) FROM note_embeddings").fetchone()[0]
    if has_embeddings == 0 and not full:
        print("[sb-reindex] Downloading embedding model (~90MB, first-time only)...")

    embed_result = embed_pass(conn, provider=provider, batch_size=batch_size, force=full)

    if close_after:
        conn.close()

    return {
        "indexed": indexed,
        "errors": errors,
        "embed_updated": embed_result["updated"],
        "embed_unchanged": embed_result["unchanged"],
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Rebuild SQLite index from brain markdown files")
    ap.add_argument("--full", action="store_true", help="Force full embedding rebuild")
    args = ap.parse_args()

    print("[sb-reindex] Starting full index rebuild...")
    result = reindex_brain(BRAIN_ROOT, full=args.full)

    print(f"  [OK] Indexed {result['indexed']} notes")
    print(f"  [OK] {result['embed_updated']} embeddings updated, {result['embed_unchanged']} unchanged")
    if result["errors"]:
        print(f"  [WARN] {len(result['errors'])} errors:")
        for e in result["errors"]:
            print(f"    - {e}")
        sys.exit(1)
    print("[sb-reindex] Done.")
