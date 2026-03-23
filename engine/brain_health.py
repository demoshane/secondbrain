"""Brain content health checks.

Distinct from engine/health.py which checks system components (Ollama, launchd).
This module checks brain data quality: orphans, broken links, duplicate notes.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def get_orphan_notes(conn: sqlite3.Connection) -> list[dict]:
    """Return notes with no inbound relationship links.

    Excludes digest and memory note types (they are structurally linkless by design).
    """
    rows = conn.execute(
        """
        SELECT n.path, n.title FROM notes n
        WHERE n.type NOT IN ('digest', 'memory')
          AND n.path NOT IN (
              SELECT source_path FROM relationships
              UNION
              SELECT target_path FROM relationships
          )
          AND (n.people IS NULL OR n.people = '[]' OR n.people = 'null')
          AND (n.tags IS NULL OR n.tags = '[]' OR n.tags = 'null')
        ORDER BY n.created_at DESC
        """
    ).fetchall()
    return [{"path": row[0], "title": row[1]} for row in rows]


def get_missing_file_notes(conn: sqlite3.Connection) -> list[dict]:
    """Return DB rows whose file no longer exists on disk (disk orphans)."""
    import os
    rows = conn.execute("SELECT path, title FROM notes LIMIT 500").fetchall()
    return [{"path": r[0], "title": r[1]} for r in rows if not os.path.exists(r[0])]


def get_empty_notes(conn: sqlite3.Connection) -> list[dict]:
    """Return notes with no meaningful body content.

    Empty = body IS NULL, empty string, or only whitespace.
    Returns at most 20 results, consistent with orphan cap.
    """
    rows = conn.execute(
        """
        SELECT path, title FROM notes
        WHERE (body IS NULL OR TRIM(body) = '')
        LIMIT 20
        """
    ).fetchall()
    return [{"path": row[0], "title": row[1]} for row in rows]


def get_duplicate_candidates(
    conn: sqlite3.Connection, threshold: float = 0.92
) -> list[dict]:
    """Return pairs of notes with cosine similarity above threshold.

    Returns [] silently if sqlite-vec is unavailable or embeddings table is empty.
    Threshold 0.92 chosen to surface likely duplicates, not merely related notes.
    """
    try:
        from engine.intelligence import find_similar

        paths_rows = conn.execute(
            "SELECT note_path FROM note_embeddings"
        ).fetchall()
        paths = [r[0] for r in paths_rows]
        seen: set[tuple[str, str]] = set()
        pairs: list[dict] = []
        for path in paths:
            try:
                matches = find_similar(path, conn, threshold=threshold, limit=5)
            except Exception:
                continue
            for m in matches:
                key = tuple(sorted([path, m["note_path"]]))
                if key not in seen:
                    seen.add(key)
                    pairs.append(
                        {
                            "a": path,
                            "b": m["note_path"],
                            "similarity": m["similarity"],
                        }
                    )
        return pairs
    except Exception:
        return []


def compute_health_score(
    total_notes: int,
    orphans: int,
    broken: int,
    duplicates: int,
) -> int:
    """Compute a 0-100 brain health score.

    100 = perfect (no issues). Lower = more issues.
    Penalty weights: broken links 40%, orphans 30%, duplicates 20%.
    """
    if total_notes == 0:
        return 100
    orphan_ratio = orphans / total_notes
    broken_ratio = broken / max(total_notes, 1)
    dup_ratio = duplicates / max(total_notes, 1)
    # Each ratio is in [0,1]; weights are points deducted (max penalty = 90pts).
    # Do NOT multiply by 100 — ratios scaled by weights already yield a 0-100 score.
    penalty = (orphan_ratio * 30) + (broken_ratio * 40) + (dup_ratio * 20)
    return max(0, round(100 - penalty))


def archive_old_action_items(conn: sqlite3.Connection, days: int = 90) -> int:
    """Move done action items older than `days` days into action_items_archive.

    All inserts and deletes happen in a single transaction.
    Returns count of archived items.
    """
    rows = conn.execute(
        """
        SELECT id, note_path, text, done_at, created_at
        FROM action_items
        WHERE done = 1
          AND done_at IS NOT NULL
          AND done_at < datetime('now', ?)
        """,
        (f"-{days} days",),
    ).fetchall()

    if not rows:
        return 0

    with conn:
        conn.executemany(
            """
            INSERT INTO action_items_archive (note_path, text, done_at, created_at, archived_reason)
            VALUES (?, ?, ?, ?, 'auto_90day')
            """,
            [(r[1], r[2], r[3], r[4]) for r in rows],
        )
        # Delete each archived row individually using a parameterized statement
        # (avoids dynamic IN-clause construction flagged by SQL injection scanners)
        conn.executemany(
            "DELETE FROM action_items WHERE id = ?",
            [(r[0],) for r in rows],
        )

    return len(rows)


def merge_notes(
    keep_path: str, discard_path: str, conn: sqlite3.Connection
) -> dict:
    """Merge a duplicate note (discard) into a keep note.

    Per D-02: merges body (separator-joined), tags (set-union), and remaps
    relationships from discard to keep. Then cascade-deletes discard from all
    tables, rebuilds FTS5, deletes disk file, and writes an audit log entry.

    Args:
        keep_path:    Path of the note to keep (merge target).
        discard_path: Path of the note to delete after merging its content.
        conn:         Open SQLite connection.

    Returns:
        {"keep": keep_path, "discarded": discard_path, "merged_tags": list[str]}

    Raises:
        ValueError: If keep_path or discard_path is not found in the notes table.
    """
    keep_row = conn.execute(
        "SELECT path, title, body, tags FROM notes WHERE path = ?", (keep_path,)
    ).fetchone()
    if keep_row is None:
        raise ValueError(f"keep_path not found: {keep_path!r}")

    discard_row = conn.execute(
        "SELECT path, title, body, tags FROM notes WHERE path = ?", (discard_path,)
    ).fetchone()
    if discard_row is None:
        raise ValueError(f"discard_path not found: {discard_path!r}")

    keep_body = keep_row[2] or ""
    discard_body = discard_row[2] or ""
    if keep_body and discard_body:
        merged_body = keep_body + "\n\n---\n\n" + discard_body
    elif discard_body:
        merged_body = discard_body
    else:
        merged_body = keep_body

    keep_tags = json.loads(keep_row[3] or "[]")
    discard_tags = json.loads(discard_row[3] or "[]")
    merged_tags = sorted(set(keep_tags + discard_tags))
    merged_tags_json = json.dumps(merged_tags)

    with conn:
        # Update keep note body, tags, updated_at
        conn.execute(
            "UPDATE notes SET body=?, tags=?, updated_at=datetime('now') WHERE path=?",
            (merged_body, merged_tags_json, keep_path),
        )

        # Remap relationships: discard→X becomes keep→X (skip duplicates)
        conn.execute(
            """
            UPDATE relationships SET source_path=?
            WHERE source_path=?
              AND target_path NOT IN (
                  SELECT target_path FROM relationships WHERE source_path=?
              )
            """,
            (keep_path, discard_path, keep_path),
        )
        # Remap relationships: X→discard becomes X→keep (skip duplicates)
        conn.execute(
            """
            UPDATE relationships SET target_path=?
            WHERE target_path=?
              AND source_path NOT IN (
                  SELECT source_path FROM relationships WHERE target_path=?
              )
            """,
            (keep_path, discard_path, keep_path),
        )
        # Delete any remaining relationships involving discard
        conn.execute(
            "DELETE FROM relationships WHERE source_path=? OR target_path=?",
            (discard_path, discard_path),
        )

        # Cascade-delete discard from satellite tables
        conn.execute("DELETE FROM note_embeddings WHERE note_path=?", (discard_path,))
        conn.execute("DELETE FROM action_items WHERE note_path=?", (discard_path,))
        conn.execute("DELETE FROM note_people WHERE note_path=?", (discard_path,))
        conn.execute("DELETE FROM note_tags WHERE note_path=?", (discard_path,))

        # Delete the discard note itself (triggers FTS5 delete trigger)
        conn.execute("DELETE FROM notes WHERE path=?", (discard_path,))

    # Rebuild FTS5 outside the transaction to ensure it reads committed state
    conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")
    conn.commit()

    # Delete discard file from disk (after DB commit per ARCH-08)
    discard_file = Path(discard_path)
    if not discard_file.is_absolute():
        from engine.paths import BRAIN_ROOT
        discard_file = BRAIN_ROOT / discard_path
    discard_file.unlink(missing_ok=True)

    # Write audit log entry
    conn.execute(
        "INSERT INTO audit_log (event_type, note_path, detail, created_at)"
        " VALUES ('merge', ?, ?, datetime('now'))",
        (keep_path, f"merged:{discard_path}"),
    )
    conn.commit()

    return {"keep": keep_path, "discarded": discard_path, "merged_tags": merged_tags}


def get_brain_health_report(conn: sqlite3.Connection) -> dict:
    """Run all health checks and return a summary dict.

    Also triggers archival of old done action items as a side effect.
    """
    orphans = get_orphan_notes(conn)
    broken = get_missing_file_notes(conn)
    duplicates = get_duplicate_candidates(conn)
    empty = get_empty_notes(conn)
    total_notes = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    archived_count = archive_old_action_items(conn)

    score = compute_health_score(
        total_notes=total_notes,
        orphans=len(orphans),
        broken=len(broken),
        duplicates=len(duplicates),
    )

    return {
        "score": score,
        "total_notes": total_notes,
        "orphans": orphans,
        "broken_links": broken,
        "duplicate_candidates": duplicates,
        "empty_notes": empty,
        "archived_action_items": archived_count,
    }
