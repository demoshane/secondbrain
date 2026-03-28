"""Brain content health checks.

Distinct from engine/health.py which checks system components (Ollama, launchd).
This module checks brain data quality: orphans, broken links, duplicate notes.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from engine.paths import CONFIG_PATH

logger = logging.getLogger(__name__)
_ORPHAN_CHECK_CAP = 10000


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


def get_missing_file_notes(conn: sqlite3.Connection, cap: int = _ORPHAN_CHECK_CAP) -> list[dict]:
    """Return DB rows whose file no longer exists on disk (disk orphans)."""
    import os
    rows = conn.execute("SELECT path, title FROM notes WHERE archived = 0 LIMIT ?", (cap,)).fetchall()
    if len(rows) == cap:
        logger.warning("Orphan check truncated at %d rows — increase cap for full coverage", cap)
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


def get_archived_count(conn: sqlite3.Connection) -> int:
    """Return count of archived notes (archived = 1)."""
    return conn.execute("SELECT COUNT(*) FROM notes WHERE archived = 1").fetchone()[0]


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


def archive_old_audit_entries(conn: sqlite3.Connection, days: int = 90) -> int:
    """Move audit log entries older than `days` days into audit_log_archive.

    All inserts and deletes happen in a single transaction.
    Mirrors archive_old_action_items pattern (semgrep-safe: no dynamic IN-clause).
    Returns count of archived entries.
    """
    rows = conn.execute(
        """
        SELECT id, event_type, note_path, detail, created_at
        FROM audit_log
        WHERE created_at < datetime('now', ?)
        """,
        (f"-{days} days",),
    ).fetchall()

    if not rows:
        return 0

    with conn:
        conn.executemany(
            """
            INSERT INTO audit_log_archive (event_type, note_path, detail, created_at)
            VALUES (?, ?, ?, ?)
            """,
            [(r[1], r[2], r[3], r[4]) for r in rows],
        )
        # Delete each archived row individually using a parameterized statement
        # (avoids dynamic IN-clause construction flagged by SQL injection scanners)
        conn.executemany(
            "DELETE FROM audit_log WHERE id = ?",
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

    # Write merged body back to the keep file on disk
    keep_file = Path(keep_path)
    if not keep_file.is_absolute():
        from engine.paths import BRAIN_ROOT
        keep_file = BRAIN_ROOT / keep_path
    if keep_file.exists():
        original_text = keep_file.read_text(encoding="utf-8")
        # Replace body section: everything after the closing --- of frontmatter
        parts = original_text.split("---", 2)
        if len(parts) >= 3:
            keep_file.write_text(
                "---" + parts[1] + "---\n\n" + merged_body, encoding="utf-8"
            )
        else:
            keep_file.write_text(merged_body, encoding="utf-8")

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


def smart_merge_notes(
    keep_path: str,
    discard_path: str,
    conn: sqlite3.Connection,
) -> dict:
    """Merge two duplicate notes using AI to synthesise a deduplicated body.

    Calls the router's public-sensitivity adapter (Ollama by default) to produce
    a single coherent note from both bodies. Falls back to dumb concatenation if
    the LLM call fails for any reason.

    Returns same shape as merge_notes:
        {"keep": keep_path, "discarded": discard_path, "merged_tags": list[str], "smart": bool}
    """
    keep_row = conn.execute(
        "SELECT path, title, body FROM notes WHERE path = ?", (keep_path,)
    ).fetchone()
    if keep_row is None:
        raise ValueError(f"keep_path not found: {keep_path!r}")

    discard_row = conn.execute(
        "SELECT path, title, body FROM notes WHERE path = ?", (discard_path,)
    ).fetchone()
    if discard_row is None:
        raise ValueError(f"discard_path not found: {discard_path!r}")

    keep_body = keep_row[2] or ""
    discard_body = discard_row[2] or ""
    smart = False

    if keep_body or discard_body:
        try:
            import engine.router as _router

            adapter = _router.get_adapter("public", CONFIG_PATH)
            system_prompt = (
                "You are a knowledge management assistant. "
                "You are given two versions of a note that cover the same topic. "
                "Produce a single merged note that:\n"
                "- Removes exact duplicates and redundant sentences\n"
                "- Preserves all unique facts, decisions, and insights from both\n"
                "- Uses clear, concise prose\n"
                "- Does NOT add new information or commentary\n"
                "Output only the merged note body — no headings, no preamble."
            )
            user_content = (
                f"NOTE A (title: {keep_row[1]}):\n{keep_body}\n\n"
                f"NOTE B (title: {discard_row[1]}):\n{discard_body}"
            )
            merged_body = adapter.generate(
                user_content=user_content, system_prompt=system_prompt
            )
            smart = True
        except Exception:
            # Fallback: concat with separator
            if keep_body and discard_body:
                merged_body = keep_body + "\n\n---\n\n" + discard_body
            else:
                merged_body = keep_body or discard_body
    else:
        merged_body = ""

    # Reuse merge_notes but override the merged body by patching the DB directly
    # after the standard merge so relationships + cascade still run correctly.
    # We do this by calling merge_notes (which sets body to concat) then updating.
    result = merge_notes(keep_path, discard_path, conn)

    # Overwrite DB body with AI-synthesised version
    with conn:
        conn.execute(
            "UPDATE notes SET body=?, updated_at=datetime('now') WHERE path=?",
            (merged_body, keep_path),
        )
    conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")
    conn.commit()

    # Overwrite disk file with AI body
    keep_file = Path(keep_path)
    if not keep_file.is_absolute():
        from engine.paths import BRAIN_ROOT
        keep_file = BRAIN_ROOT / keep_path
    if keep_file.exists():
        original_text = keep_file.read_text(encoding="utf-8")
        parts = original_text.split("---", 2)
        if len(parts) >= 3:
            keep_file.write_text(
                "---" + parts[1] + "---\n\n" + merged_body, encoding="utf-8"
            )
        else:
            keep_file.write_text(merged_body, encoding="utf-8")

    result["smart"] = smart
    return result


def get_stub_notes(conn: sqlite3.Connection, word_limit: int = 50) -> list[dict]:
    """Return notes with body NULL, empty, or fewer than word_limit words.

    Uses LENGTH(body) < 400 as DB pre-filter, then Python word count for accuracy.
    Per D-04: surfaces thin content for enrichment or merge-first workflow.
    """
    rows = conn.execute(
        """
        SELECT path, title, body FROM notes
        WHERE body IS NULL OR TRIM(body) = '' OR LENGTH(body) < 400
        LIMIT 100
        """
    ).fetchall()
    stubs = []
    for path, title, body in rows:
        if body is None or body.strip() == "" or len(body.split()) < word_limit:
            stubs.append({"path": path, "title": title, "word_count": len((body or "").split())})
    return stubs[:50]


def repair_self_links(conn: sqlite3.Connection) -> int:
    """Delete relationships where source_path == target_path.

    These are artifacts from earlier bugs where a person profile was linked to itself.
    Returns count of deleted rows.
    """
    result = conn.execute(
        "DELETE FROM relationships WHERE source_path = target_path"
    )
    conn.commit()
    return result.rowcount


def repair_person_backlinks(brain_root: Path, conn: sqlite3.Connection) -> dict:
    """Remove stale [[...]] backlink lines from person files.

    For each backlink relationship whose target no longer exists on disk:
    - Remove the [[target_path]] line from the person (source) file
    - Delete the relationship row from DB

    Returns {"files_updated": int, "links_removed": int}
    """
    from collections import defaultdict

    rows = conn.execute(
        "SELECT source_path, target_path FROM relationships WHERE rel_type = 'backlink'"
    ).fetchall()

    stale = [(src, tgt) for src, tgt in rows if not Path(tgt).exists()]
    if not stale:
        return {"files_updated": 0, "links_removed": 0}

    by_source: dict[str, list[str]] = defaultdict(list)
    for src, tgt in stale:
        by_source[src].append(tgt)

    files_updated = 0
    links_removed = 0

    for source_path, stale_targets in by_source.items():
        person_file = Path(source_path)
        for tgt in stale_targets:
            conn.execute(
                "DELETE FROM relationships WHERE source_path=? AND target_path=?",
                (source_path, tgt),
            )
            links_removed += 1

        if not person_file.exists():
            continue

        text = person_file.read_text(encoding="utf-8")
        original = text
        for tgt in stale_targets:
            text = text.replace(f"\n- [[{tgt}]]", "")

        if text != original:
            person_file.write_text(text, encoding="utf-8")
            files_updated += 1

    conn.commit()
    return {"files_updated": files_updated, "links_removed": links_removed}


def delete_dangling_relationships(conn: sqlite3.Connection) -> int:
    """Delete relationships where source or target path not in notes table.

    Per D-07: removes stale graph edges pointing to deleted notes.
    Returns the count of deleted rows.
    """
    result = conn.execute(
        """
        DELETE FROM relationships
        WHERE source_path NOT IN (SELECT path FROM notes)
           OR target_path NOT IN (SELECT path FROM notes)
        """
    )
    conn.commit()
    return result.rowcount


def get_bidirectional_gaps(conn: sqlite3.Connection) -> list[dict]:
    """Return one-way relationships (A->B exists but B->A does not).

    Only includes pairs where both paths exist in notes table.
    Per D-07: flags asymmetric links for review — not auto-created.
    """
    rows = conn.execute(
        """
        SELECT r.source_path, r.target_path, r.rel_type
        FROM relationships r
        WHERE NOT EXISTS (
            SELECT 1 FROM relationships r2
            WHERE r2.source_path = r.target_path
              AND r2.target_path = r.source_path
        )
        AND r.source_path IN (SELECT path FROM notes)
        AND r.target_path IN (SELECT path FROM notes)
        ORDER BY r.source_path
        """
    ).fetchall()
    return [{"source": r[0], "target": r[1], "rel_type": r[2]} for r in rows]


def take_health_snapshot(conn: sqlite3.Connection) -> dict:
    """Take a health snapshot for today. Skips if one already exists for today (one-per-day guard)."""
    import datetime
    today = datetime.date.today().isoformat()
    existing = conn.execute(
        "SELECT id FROM health_snapshots WHERE date(snapped_at) = ?", (today,)
    ).fetchone()
    if existing:
        return {"skipped": True, "reason": "snapshot_exists_today"}

    total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    orphans = get_orphan_notes(conn)
    broken = get_missing_file_notes(conn)
    duplicates = get_duplicate_candidates(conn)
    stubs = get_stub_notes(conn)
    score = compute_health_score(total, len(orphans), len(broken), len(duplicates))

    conn.execute("""
        INSERT INTO health_snapshots (snapped_at, score, total_notes, orphan_count, broken_count, duplicate_count, stub_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (today, score, total, len(orphans), len(broken), len(duplicates), len(stubs)))
    conn.commit()
    return {"skipped": False, "score": score, "total_notes": total,
            "orphan_count": len(orphans), "broken_count": len(broken),
            "duplicate_count": len(duplicates), "stub_count": len(stubs)}


def cleanup_old_snapshots(conn: sqlite3.Connection, days: int = 90) -> int:
    """Delete health_snapshots older than `days` days. Returns deleted count."""
    result = conn.execute(
        "DELETE FROM health_snapshots WHERE snapped_at < date('now', ?)",
        (f"-{days} days",),
    )
    conn.commit()
    return result.rowcount


def check_drive_sync() -> dict:
    """3-tier Google Drive sync health check. Returns dict with status and message."""
    import subprocess

    app_path = Path("/Applications/Google Drive.app")
    drivefs_base = Path.home() / "Library" / "Application Support" / "Google" / "DriveFS"

    if not app_path.exists():
        return {
            "status": "not_installed",
            "message": (
                "Google Drive not installed. Install from https://www.google.com/drive/download/"
                " then add ~/SecondBrain in Preferences -> My Computer."
            ),
        }

    result = subprocess.run(["pgrep", "-x", "Google Drive"], capture_output=True)
    if result.returncode != 0:
        return {
            "status": "not_running",
            "message": "Google Drive installed but not running. Brain won't sync.",
        }

    db_matches = list(drivefs_base.glob("*/mirror_sqlite.db")) if drivefs_base.exists() else []
    if db_matches:
        return {
            "status": "ok",
            "message": "Drive running. Confirm ~/SecondBrain is added in Drive Preferences -> My Computer.",
        }
    return {
        "status": "not_configured",
        "message": "Drive running but no DriveFS account DB found. Open Drive preferences and sign in.",
    }


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
        "drive_sync": check_drive_sync(),
    }
