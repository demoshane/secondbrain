"""Note deletion utility — single shared implementation for GUI and CLI."""
from __future__ import annotations

import datetime
from pathlib import Path


def get_delete_impact(path_str: str, conn) -> dict:
    """Return counts of records that will be affected by deleting this note."""
    action_items = conn.execute(
        "SELECT COUNT(*) FROM action_items WHERE note_path=?", (path_str,)
    ).fetchone()[0]
    relationships = conn.execute(
        "SELECT COUNT(*) FROM relationships WHERE source_path=? OR target_path=?",
        (path_str, path_str),
    ).fetchone()[0]
    appears_in = conn.execute(
        "SELECT COUNT(*) FROM note_people WHERE person=?", (path_str,)
    ).fetchone()[0]
    return {"action_items": action_items, "relationships": relationships, "appears_in_people_of": appears_in}


def delete_note(abs_path: Path, conn, brain_root: Path) -> dict:
    """Delete a single note: file + DB cascade + audit log.

    Cascade order:
    1. suppress_next_delete(path_str)  — BEFORE unlink (watcher suppression)
    2. If note body has "File: <path>" under brain_root/files/, delete source file too
    3. abs_path.unlink(missing_ok=True)
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
    from engine.paths import store_path

    abs_path_str = str(abs_path.resolve())   # absolute — for watcher suppression
    path_str = store_path(abs_path)          # relative — preferred Phase 32+ format

    # Normalize path_str to match whatever format is actually stored in DB.
    # Pre-Phase-32 notes may have absolute paths; using the wrong format causes
    # DB queries to match 0 rows while the file is still deleted from disk.
    _row = conn.execute("SELECT path FROM notes WHERE path=?", (path_str,)).fetchone()
    if _row is None:
        _abs_row = conn.execute("SELECT path FROM notes WHERE path=?", (abs_path_str,)).fetchone()
        if _abs_row:
            path_str = _abs_row[0]

    # 1. Suppress watcher false-positive BEFORE unlink
    suppress_next_delete(abs_path_str)

    # 2a. If note body contains "File: <path>", delete the source file too
    try:
        for line in abs_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("File: "):
                source_file = Path(line[6:].strip())
                if source_file.is_file() and source_file.is_relative_to(brain_root / "files"):
                    suppress_next_delete(str(source_file.resolve()))
                    source_file.unlink(missing_ok=True)
                break
    except OSError:
        pass

    # 2b. Remove the note .md file from disk
    abs_path.unlink(missing_ok=True)

    # 3a. Capture note type BEFORE deleting (needed for person-specific cascade below)
    _type_row = conn.execute("SELECT type FROM notes WHERE path=?", (path_str,)).fetchone()
    _note_type = _type_row[0] if _type_row else None

    # 3b. Delete notes row (notes_ad AFTER DELETE trigger handles FTS5 automatically)
    conn.execute("DELETE FROM notes WHERE path=?", (path_str,))

    # 4. Delete note_embeddings row
    conn.execute("DELETE FROM note_embeddings WHERE note_path=?", (path_str,))

    # 5a. Remove [[backlink]] text from any note files that reference the deleted note.
    # backlinks are stored in note bodies as "\n- [[abs_path_str]]".
    # Query using both relative and absolute path to handle pre/post Phase-32 formats.
    _backlink_sources: set[str] = set()
    for _p in (path_str, abs_path_str):
        _rows = conn.execute(
            "SELECT source_path FROM relationships WHERE target_path=? AND rel_type='backlink'",
            (_p,),
        ).fetchall()
        _backlink_sources.update(r[0] for r in _rows)

    for _src in _backlink_sources:
        _src_file = Path(_src) if Path(_src).is_absolute() else brain_root / _src
        if not _src_file.exists():
            continue
        try:
            _text = _src_file.read_text(encoding="utf-8")
            _new = _text
            # Remove backlink lines for both path formats
            for _ref in (abs_path_str, path_str):
                _new = _new.replace(f"\n- [[{_ref}]]", "")
            if _new != _text:
                _src_file.write_text(_new, encoding="utf-8")
        except OSError:
            pass

    # 5b. Delete relationships (both directions, both path formats)
    for _p in (path_str, abs_path_str):
        conn.execute(
            "DELETE FROM relationships WHERE source_path=? OR target_path=?",
            (_p, _p),
        )

    # 6. Delete action_items rows (prevents orphan items in Actions panel)
    conn.execute("DELETE FROM action_items WHERE note_path=?", (path_str,))

    # 6a. Person-specific cascade: NULL assignee_path + clean note_people cross-refs
    if _note_type == "person":
        conn.execute("UPDATE action_items SET assignee_path=NULL WHERE assignee_path=?", (path_str,))
        conn.execute("DELETE FROM note_people WHERE person=?", (path_str,))

    # 7. Delete prior audit_log rows for this note (GDPR consistency)
    conn.execute("DELETE FROM audit_log WHERE note_path=?", (path_str,))

    # 8. Insert new audit log entry (note_path=NULL so it is never self-deleted)
    conn.execute(
        "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?, ?, ?, ?)",
        (
            "delete_note",
            None,
            path_str,
            datetime.datetime.now(datetime.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ),
    )

    # 9. Commit
    conn.commit()

    return {"deleted": True, "path": path_str}
