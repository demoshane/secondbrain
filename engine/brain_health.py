"""Brain content health checks.

Distinct from engine/health.py which checks system components (Ollama, launchd).
This module checks brain data quality: orphans, broken links, duplicate notes.
"""
from __future__ import annotations

import sqlite3


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
