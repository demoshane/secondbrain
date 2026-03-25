"""Shared people service — ARCH-10: single source for people-with-metrics queries."""
import json
import sqlite3

from engine.db import PERSON_TYPES, PERSON_TYPES_PH


def list_people_with_metrics(conn: sqlite3.Connection) -> list[dict]:
    """Return all person notes with computed metrics.

    ARCH-11: matches people column entries by both path AND exact title
    (case-insensitive) to fix zero-metrics bug where name-string entries
    are invisible to path-only matching.

    Uses note_people junction table (ARCH-15) for indexed lookups.
    """
    old_factory = conn.row_factory
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(f"""
            SELECT n.path, n.title, n.entities, substr(n.updated_at, 1, 10) AS updated_at,
                (SELECT COUNT(*) FROM action_items a WHERE a.assignee_path=n.path AND a.done=0) AS open_actions,
                (SELECT MAX(m.created_at) FROM notes m
                    JOIN note_people np ON np.note_path = m.path
                    WHERE (np.person = n.path OR LOWER(np.person) = LOWER(n.title))
                    AND m.type='meeting') AS last_interaction,
                (SELECT COUNT(*) FROM notes m
                    JOIN note_people np ON np.note_path = m.path
                    WHERE (np.person = n.path OR LOWER(np.person) = LOWER(n.title))
                    AND m.type='meeting') AS total_meetings,
                (SELECT COUNT(*) FROM notes m
                    JOIN note_people np ON np.note_path = m.path
                    WHERE (np.person = n.path OR LOWER(np.person) = LOWER(n.title))
                    AND m.type NOT IN ({PERSON_TYPES_PH})) AS mention_count
            FROM notes n WHERE n.type IN ({PERSON_TYPES_PH}) ORDER BY n.title
        """, (*PERSON_TYPES, *PERSON_TYPES)).fetchall()
    finally:
        conn.row_factory = old_factory

    result = []
    for r in rows:
        try:
            ents = json.loads(r["entities"] or "{}")
        except (json.JSONDecodeError, TypeError):
            ents = {}
        org = (ents.get("orgs") or [""])[0]
        result.append({
            "path": r["path"],
            "title": r["title"],
            "updated_at": r["updated_at"],
            "open_actions": r["open_actions"],
            "org": org,
            "last_interaction": r["last_interaction"],
            "mention_count": r["mention_count"] or 0,
            "total_meetings": r["total_meetings"] or 0,
        })
    return result
