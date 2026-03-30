"""Shared test data cleanup utility — used by perf tests and any future test suites."""
from __future__ import annotations


def cleanup_test_notes(prefix: str = "__perf_test__") -> int:
    """Delete all notes whose title starts with *prefix* from the DB and disk.

    Cascade order mirrors engine/delete.py:
    - note_embeddings, note_chunks, relationships (both directions),
      action_items, audit_log are cleared first.
    - Then notes row is deleted (FTS5 AFTER DELETE trigger fires automatically).
    - note_tags and note_people have FK CASCADE so they clean up automatically.
    - Physical .md files are removed from disk via BRAIN_ROOT.

    Returns:
        Number of notes deleted.
    """
    from engine.db import get_connection
    from engine.paths import BRAIN_ROOT

    conn = get_connection()
    try:
        escaped_prefix = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        rows = conn.execute(
            "SELECT path FROM notes WHERE title LIKE ? ESCAPE '\\'",
            (escaped_prefix + "%",),
        ).fetchall()

        paths = [r[0] for r in rows]

        for path_str in paths:
            conn.execute("DELETE FROM note_embeddings WHERE note_path=?", (path_str,))
            conn.execute("DELETE FROM note_chunks WHERE note_path=?", (path_str,))
            conn.execute(
                "DELETE FROM relationships WHERE source_path=? OR target_path=?",
                (path_str, path_str),
            )
            conn.execute("DELETE FROM action_items WHERE note_path=?", (path_str,))
            conn.execute("DELETE FROM audit_log WHERE note_path=?", (path_str,))
            conn.execute("DELETE FROM notes WHERE path=?", (path_str,))

            # Remove physical file
            abs_path = BRAIN_ROOT / path_str
            abs_path.unlink(missing_ok=True)

        conn.commit()
        return len(paths)
    finally:
        conn.close()
