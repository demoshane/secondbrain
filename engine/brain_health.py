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
        LEFT JOIN relationships r ON n.path = r.target_path
        WHERE r.target_path IS NULL
          AND n.type NOT IN ('digest', 'memory')
        ORDER BY n.created_at DESC
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
    penalty = (orphan_ratio * 30) + (broken_ratio * 40) + (dup_ratio * 20)
    return max(0, round(100 - penalty * 100))
