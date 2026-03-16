"""Note deletion utility — single shared implementation for GUI and CLI."""
from __future__ import annotations

import datetime
from pathlib import Path


def delete_note(abs_path: Path, conn, brain_root: Path) -> dict:
    """Delete a single note: file + DB cascade + audit log.

    Cascade order:
    1. suppress_next_delete(path_str)  — BEFORE unlink (watcher suppression)
    2. abs_path.unlink(missing_ok=True)
    3. DELETE FROM notes WHERE path=?         (notes_ad trigger handles FTS5 automatically)
    4. DELETE FROM note_embeddings WHERE note_path=?
    5. DELETE FROM relationships WHERE source_path=? OR target_path=?
    6. DELETE FROM action_items WHERE note_path=?
    7. DELETE FROM audit_log WHERE note_path=?
    8. INSERT INTO audit_log (event_type="delete_note", note_path=NULL, detail=path_str)
    9. conn.commit()

    Returns: {"deleted": True, "path": path_str}
    Error messages: type(e).__name__ only — no file content (GDPR-05).
    """
    from engine.watcher import suppress_next_delete  # lazy import — avoids circular imports

    path_str = str(abs_path.resolve())

    # 1. Suppress watcher false-positive BEFORE unlink
    suppress_next_delete(path_str)

    # 2. Remove file from disk
    abs_path.unlink(missing_ok=True)

    # 3. Delete notes row (notes_ad AFTER DELETE trigger handles FTS5 automatically)
    conn.execute("DELETE FROM notes WHERE path=?", (path_str,))

    # 4. Delete note_embeddings row
    conn.execute("DELETE FROM note_embeddings WHERE note_path=?", (path_str,))

    # 5. Delete relationships (both directions)
    conn.execute(
        "DELETE FROM relationships WHERE source_path=? OR target_path=?",
        (path_str, path_str),
    )

    # 6. Delete action_items rows (prevents orphan items in Actions panel)
    conn.execute("DELETE FROM action_items WHERE note_path=?", (path_str,))

    # 7. Delete prior audit_log rows for this note (GDPR consistency)
    conn.execute("DELETE FROM audit_log WHERE note_path=?", (path_str,))

    # 8. Insert new audit log entry (note_path=NULL so it is never self-deleted)
    conn.execute(
        "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?, ?, ?, ?)",
        (
            "delete_note",
            None,
            path_str,
            datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        ),
    )

    # 9. Commit
    conn.commit()

    return {"deleted": True, "path": path_str}
