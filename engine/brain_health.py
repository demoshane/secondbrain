"""Brain content health checks.

Distinct from engine/health.py which checks system components (Ollama, launchd).
This module checks brain data quality: orphans, broken links, duplicate notes.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from engine.db import _json_list
import sqlite3
from pathlib import Path

import frontmatter as _fm

from engine.paths import CONFIG_PATH

logger = logging.getLogger(__name__)
_ORPHAN_CHECK_CAP = 10000


_ORPHAN_BODY_MIN_LENGTH = 100  # Notes with body >= this are findable via search


def get_orphan_notes(conn: sqlite3.Connection) -> list[dict]:
    """Return notes that are truly unfindable — too little content AND no metadata paths.

    A note is findable (not orphaned) if ANY of these hold:
    - Has relationships/links (reachable from other notes)
    - Has people tags (shows up in people views)
    - Has tags (shows up in filtered views)
    - Has enough body text for search to surface it (>= 100 chars)
    - Is a person or digest or memory type (structurally standalone)
    """
    rows = conn.execute(
        """
        SELECT n.path, n.title FROM notes n
        WHERE n.type NOT IN ('digest', 'memory', 'person')
          AND n.path NOT IN (
              SELECT source_path FROM relationships
              UNION
              SELECT target_path FROM relationships
          )
          AND (n.people IS NULL OR n.people = '[]' OR n.people = 'null')
          AND (n.tags IS NULL OR n.tags = '[]' OR n.tags = 'null')
          AND (n.body IS NULL OR LENGTH(TRIM(n.body)) < ?)
        ORDER BY n.created_at DESC
        """,
        (_ORPHAN_BODY_MIN_LENGTH,),
    ).fetchall()
    return [{"path": row[0], "title": row[1]} for row in rows]


def get_missing_file_notes(conn: sqlite3.Connection, cap: int = _ORPHAN_CHECK_CAP) -> list[dict]:
    """Return DB rows whose file no longer exists on disk (disk orphans)."""
    from engine.paths import BRAIN_ROOT as _br
    rows = conn.execute("SELECT path, title FROM notes WHERE archived = 0 LIMIT ?", (cap,)).fetchall()
    if len(rows) == cap:
        logger.warning("Orphan check truncated at %d rows — increase cap for full coverage", cap)
    return [{"path": r[0], "title": r[1]} for r in rows if not (_br / r[0]).exists()]


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


_DUPLICATE_CHECK_CAP = 100


def get_duplicate_candidates(
    conn: sqlite3.Connection, threshold: float = 0.92
) -> list[dict]:
    """Return pairs of notes with cosine similarity above threshold.

    Returns [] silently if sqlite-vec is unavailable or embeddings table is empty.
    Threshold 0.92 chosen to surface likely duplicates, not merely related notes.
    Capped at _DUPLICATE_CHECK_CAP notes to avoid O(N²) scan on large brains.
    """
    try:
        from engine.intelligence import find_similar

        paths_rows = conn.execute(
            "SELECT note_path FROM note_embeddings ORDER BY rowid DESC LIMIT ?",
            (_DUPLICATE_CHECK_CAP,),
        ).fetchall()
        paths = [r[0] for r in paths_rows]

        # Load dismissed duplicate pairs with their similarity at dismissal time.
        # Resurface if current similarity differs by more than 5% from when dismissed.
        dismissed: dict[tuple[str, str], float] = {}
        try:
            dismissed_rows = conn.execute(
                "SELECT path, detail FROM dismissed_inbox_items WHERE item_type='duplicate'"
            ).fetchall()
            for r in dismissed_rows:
                parts = r[0].split("||")
                if len(parts) == 2:
                    try:
                        sim = float(r[1]) if r[1] else 0.0
                    except (ValueError, TypeError):
                        sim = 0.0
                    dismissed[tuple(sorted(parts))] = sim
        except Exception:
            pass

        # Build a set of ALL person-type note paths to skip person-vs-person pairs.
        # Person stubs often have empty/minimal bodies → near-identical embeddings
        # that produce false-positive duplicates (different people, same template).
        # Query ALL persons, not just those in the scan window — find_similar can
        # return matches outside the cap'd paths list.
        person_rows = conn.execute(
            "SELECT path FROM notes WHERE type IN ('person')"
        ).fetchall()
        person_paths = {r[0] for r in person_rows}

        seen: set[tuple[str, str]] = set()
        pairs: list[dict] = []
        for path in paths:
            try:
                matches = find_similar(path, conn, threshold=threshold, limit=5)
            except Exception:
                continue
            for m in matches:
                # Skip person-vs-person pairs (false positives from stub templates)
                if path in person_paths and m["note_path"] in person_paths:
                    continue
                key = tuple(sorted([path, m["note_path"]]))
                if key in dismissed:
                    # Resurface if similarity shifted by >5% since dismissal
                    if abs(m["similarity"] - dismissed[key]) <= 0.05:
                        continue
                if key not in seen:
                    seen.add(key)
                    pairs.append(
                        {
                            "a": path,
                            "b": m["note_path"],
                            "similarity": m["similarity"],
                        }
                    )

        # Enrich with titles for UI display
        if pairs:
            all_paths = list({p["a"] for p in pairs} | {p["b"] for p in pairs})
            ph = ",".join("?" for _ in all_paths)
            title_rows = conn.execute(
                f"SELECT path, title FROM notes WHERE path IN ({ph})", all_paths  # noqa: S608
            ).fetchall()
            title_map = {r[0]: r[1] for r in title_rows}
            for p in pairs:
                p["a_title"] = title_map.get(p["a"], p["a"].split("/")[-1].replace(".md", ""))
                p["b_title"] = title_map.get(p["b"], p["b"].split("/")[-1].replace(".md", ""))

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

    # Phase 57: Frontmatter merge — union people/tags, keep earlier created_at
    from engine.paths import BRAIN_ROOT
    keep_file = Path(keep_path)
    if not keep_file.is_absolute():
        keep_file = BRAIN_ROOT / keep_path
    discard_file = Path(discard_path)
    if not discard_file.is_absolute():
        discard_file = BRAIN_ROOT / discard_path

    keep_post = _fm.load(str(keep_file)) if keep_file.exists() else None
    discard_post = _fm.load(str(discard_file)) if discard_file.exists() else None

    if keep_post and discard_post:
        for field in ("people", "tags"):
            keep_val = keep_post.get(field, []) or []
            discard_val = discard_post.get(field, []) or []
            if isinstance(keep_val, str):
                keep_val = [keep_val]
            if isinstance(discard_val, str):
                discard_val = [discard_val]
            merged_fm = sorted(set(keep_val + discard_val))
            if merged_fm:
                keep_post[field] = merged_fm

        d_created = discard_post.get("created_at", "")
        k_created = keep_post.get("created_at", "")
        if d_created and (not k_created or str(d_created) < str(k_created)):
            keep_post["created_at"] = d_created

        import datetime as _dt
        keep_post["updated_at"] = _dt.datetime.now(_dt.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Phase 57: AI-assisted body merge (fall back to --- separator)
    ai_merged = False
    try:
        from engine.intelligence import enrich_note
        enrich_result = enrich_note(keep_path, discard_body, conn)
        ai_merged = True
        merged_body = None  # enrich_note already wrote to disk + DB
    except Exception:
        # Fallback: current --- separator approach
        if keep_body and discard_body:
            merged_body = keep_body + "\n\n---\n\n" + discard_body
        elif discard_body:
            merged_body = discard_body
        else:
            merged_body = keep_body

    keep_tags = _json_list(keep_row[3])
    discard_tags = _json_list(discard_row[3])
    merged_tags = sorted(set(keep_tags + discard_tags))
    merged_tags_json = json.dumps(merged_tags)

    with conn:
        # Update keep note — if AI merge handled body, only update tags
        if ai_merged:
            conn.execute(
                "UPDATE notes SET tags=?, updated_at=datetime('now') WHERE path=?",
                (merged_tags_json, keep_path),
            )
        else:
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

    # Write merged body + frontmatter back to keep file on disk
    # (skip body write if AI merge already handled it via enrich_note)
    if keep_file.exists():
        post = _fm.load(str(keep_file))
        if not ai_merged and merged_body is not None:
            post.content = merged_body
        # Always write back frontmatter updates (people/tags union, created_at)
        if keep_post:
            for field in ("people", "tags", "created_at", "updated_at"):
                if field in keep_post.metadata:
                    post[field] = keep_post[field]
        fd, tmp = tempfile.mkstemp(dir=keep_file.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(_fm.dumps(post))
            os.replace(tmp, keep_file)
        except Exception:
            Path(tmp).unlink(missing_ok=True)
            raise

    # Delete discard file from disk (after DB commit per ARCH-08)
    discard_file.unlink(missing_ok=True)

    # Phase 57: Backlink repair — replace [[discard_path]] with [[keep_path]] in all notes
    rows = conn.execute(
        "SELECT path, body FROM notes WHERE body LIKE ?",
        (f"%[[{discard_path}]]%",),
    ).fetchall()
    for note_path, body in rows:
        if body and f"[[{discard_path}]]" in body:
            new_body = body.replace(f"[[{discard_path}]]", f"[[{keep_path}]]")
            conn.execute("UPDATE notes SET body=? WHERE path=?", (new_body, note_path))
            note_file_path = BRAIN_ROOT / note_path
            if note_file_path.exists():
                try:
                    npost = _fm.load(str(note_file_path))
                    npost.content = new_body
                    with open(note_file_path, "w", encoding="utf-8") as fh:
                        fh.write(_fm.dumps(npost))
                except Exception:
                    pass

    # Phase 57: Repair source_notes in synthesis note frontmatter
    synth_rows = conn.execute(
        "SELECT path FROM notes WHERE type='synthesis'"
    ).fetchall()
    for (synth_path,) in synth_rows:
        synth_file = BRAIN_ROOT / synth_path
        if synth_file.exists():
            try:
                spost = _fm.load(str(synth_file))
                sources = spost.get("source_notes", []) or []
                if discard_path in sources:
                    spost["source_notes"] = [keep_path if s == discard_path else s for s in sources]
                    with open(synth_file, "w", encoding="utf-8") as fh:
                        fh.write(_fm.dumps(spost))
            except Exception:
                pass

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

    # Overwrite disk file with AI body (atomic, frontmatter-safe)
    keep_file = Path(keep_path)
    if not keep_file.is_absolute():
        from engine.paths import BRAIN_ROOT
        keep_file = BRAIN_ROOT / keep_path
    if keep_file.exists():
        post = _fm.load(str(keep_file))
        post.content = merged_body
        fd, tmp = tempfile.mkstemp(dir=keep_file.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(_fm.dumps(post))
            os.replace(tmp, keep_file)
        except Exception:
            Path(tmp).unlink(missing_ok=True)
            raise

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

    # DB stores relative paths — resolve against BRAIN_ROOT for disk access
    from engine.paths import BRAIN_ROOT as _br
    stale = [(src, tgt) for src, tgt in rows if not (_br / tgt).exists()]
    if not stale:
        return {"files_updated": 0, "links_removed": 0}

    by_source: dict[str, list[str]] = defaultdict(list)
    for src, tgt in stale:
        by_source[src].append(tgt)

    files_updated = 0
    links_removed = 0

    for source_path, stale_targets in by_source.items():
        person_file = _br / source_path
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

    # Phase 57: consolidation queue stats
    try:
        cq_rows = conn.execute(
            "SELECT action, COUNT(*) FROM consolidation_queue WHERE status='pending' GROUP BY action"
        ).fetchall()
        consolidation_pending = {row[0]: row[1] for row in cq_rows}
        consolidation_total = sum(consolidation_pending.values())
    except Exception:
        consolidation_pending = {}
        consolidation_total = 0

    return {
        "score": score,
        "total_notes": total_notes,
        "orphans": orphans,
        "broken_links": broken,
        "duplicate_candidates": duplicates,
        "empty_notes": empty,
        "archived_action_items": archived_count,
        "drive_sync": check_drive_sync(),
        "consolidation_queue": {
            "pending_total": consolidation_total,
            "by_action": consolidation_pending,
        },
    }
