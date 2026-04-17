"""Intelligence layer: session recap, action items, stale nudges, connection suggestions."""
import json
import datetime
import logging
import re
import subprocess
import time

logger = logging.getLogger(__name__)
from pathlib import Path

from engine.router import get_adapter as _get_adapter
from engine.db import get_connection, init_schema, migrate_add_action_items_table

STATE_PATH = Path.home() / ".meta" / "intelligence_state.json"
VAULT_GATE = 20  # minimum notes before any proactive offer fires

# Cooldown gate: prevent O(n) similarity scans more often than once per 30 minutes
_check_connections_last_run: float = 0.0
_CHECK_CONNECTIONS_COOLDOWN_SECS: int = 30 * 60

def _action_item_prompt() -> str:
    today = datetime.date.today().isoformat()
    return (
        f"Today's date is {today}. "
        "You are an assistant that extracts action items from notes. "
        "Output ONLY a newline-separated list of action items — one per line. "
        "Each line must be a concrete, specific commitment or to-do. "
        "Prefix each item with 'ME: ' if it is clearly a first-person action (the note author is responsible — uses 'I', 'my', 'I'll', 'I will', etc.). "
        "Items assigned to named other people should have no prefix. "
        "Items with unclear ownership should have no prefix. "
        "If a due date is mentioned or implied (e.g. 'by Friday', 'end of week', 'before the release'), "
        "append it as an ISO 8601 date after a pipe character: 'ME: Review contract | 2026-04-05'. "
        "Omit the pipe entirely if no due date is present. "
        "If there are no action items, output exactly: NONE"
    )

RECAP_SYSTEM_PROMPT = (
    "You are a personal assistant reviewing a week of notes. "
    "Write a 3-5 sentence summary covering: (1) what was worked on, "
    "(2) key decisions made, (3) open threads or risks. "
    "Be specific — mention note titles or topics by name. "
    "Output plain prose, no bullet points, no headers."
)

RECAP_ENTITY_SYSTEM_PROMPT = (
    "You are a knowledge assistant. Synthesise the following notes about a person or project "
    "into: (1) a 2-3 sentence narrative summary, and (2) a bullet list of open action items. "
    "Be concise. Format: narrative paragraph, then '## Open Actions' heading, then bullets."
)

PERSON_INSIGHT_SYSTEM_PROMPT = (
    "You are a personal knowledge assistant. The first line of the input is 'Person name: X'. "
    "Write a concise brain insight about THAT specific person: "
    "(1) who they are and their role/context, (2) recent interactions or meetings with them, "
    "(3) open action items involving them. Use 3-5 sentences, narrative style. Be specific — "
    "mention meeting titles, project names, and dates when available. "
    "Focus exclusively on the named person, not on other people mentioned in the notes."
)

WEEKLY_SYNTHESIS_SYSTEM_PROMPT = (
    "You are a personal knowledge assistant reviewing a full week of notes. "
    "Write a structured weekly synthesis covering: "
    "(1) Key themes and topics worked on this week, "
    "(2) Important decisions made or conclusions reached, "
    "(3) People you interacted with most and in what context, "
    "(4) Open threads, pending actions, or risks to watch. "
    "Use 2-3 short paragraphs. Be specific — mention note titles, people, "
    "and project names. Output plain prose with section headers."
)

ASK_BRAIN_SYSTEM_PROMPT = (
    "You are a personal knowledge assistant answering questions about the user's second brain notes. "
    "Answer based ONLY on the notes provided as context. "
    "If the question cannot be answered from the notes, say so clearly. "
    "Be concise and specific. Cite note titles when relevant. "
    "Output plain prose, no markdown headers unless the answer is long enough to warrant them."
)


class _RouterShim:
    """Thin wrapper so tests can patch `engine.intelligence._router`."""

    def get_adapter(self, sensitivity: str, config_path, feature: str = ""):
        return _get_adapter(sensitivity, config_path, feature=feature)


_router = _RouterShim()


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Summarization constants (38-06)
# ---------------------------------------------------------------------------

SUMMARY_THRESHOLD = 2000  # characters — notes longer than this get summarized
SUMMARY_MAX_INPUT = 8000  # characters — cap input to LLM to control cost


# ---------------------------------------------------------------------------
# Budget gate (INTL-10)
# ---------------------------------------------------------------------------

def budget_available(conn, feature: str = "default") -> bool:
    """True if vault has 20+ notes and this feature hasn't fired today.

    Each feature gets its own daily budget slot so they don't block each other.
    Migrates from legacy single-slot ``last_offer_date`` on first read.
    """
    note_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    if note_count < VAULT_GATE:
        return False
    state = _load_state()
    today = datetime.date.today().isoformat()
    budgets = state.get("daily_budgets", {})
    # Migrate legacy single-slot format
    if not budgets and "last_offer_date" in state:
        budgets = {"default": state["last_offer_date"]}
    return budgets.get(feature) != today


def consume_budget(feature: str = "default") -> None:
    """Record that this feature's daily slot has been used."""
    state = _load_state()
    budgets = state.get("daily_budgets", {})
    budgets[feature] = datetime.date.today().isoformat()
    state["daily_budgets"] = budgets
    _save_state(state)


# ---------------------------------------------------------------------------
# Git context detection (INTL-02)
# ---------------------------------------------------------------------------

def detect_git_context() -> str | None:
    """Return current git repo basename, or None if not in a git repo."""
    try:
        result = subprocess.run(
            ["/usr/bin/git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip()).name
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


# ---------------------------------------------------------------------------
# Action item extraction (INTL-03/04/05)
# ---------------------------------------------------------------------------

def extract_action_items(note_path: Path, body_or_conn=None, sensitivity: str = "public", conn=None) -> None:
    """Extract and store action items from note body. Best-effort — never raises.

    Supports two call signatures:
      extract_action_items(note_path, body, sensitivity, conn)  -- original
      extract_action_items(note_path, conn)                     -- reads note from disk
    """
    try:
        import frontmatter as _fm
        # Detect call style: if second arg is a connection (no body/sensitivity supplied)
        if conn is None and body_or_conn is not None and not isinstance(body_or_conn, str):
            # Called as extract_action_items(note_path, conn)
            conn = body_or_conn
            try:
                meta = _fm.load(str(note_path))
                body = meta.content
                sensitivity = meta.get("sensitivity", "public") or "public"
            except Exception:
                body = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
        else:
            body = body_or_conn if isinstance(body_or_conn, str) else ""

        from engine.paths import CONFIG_PATH
        from engine.config_loader import load_config as _load_config
        adapter = _router.get_adapter(sensitivity, CONFIG_PATH)
        raw = adapter.generate(user_content=body, system_prompt=_action_item_prompt())
        raw_lines = [line.strip() for line in raw.splitlines() if line.strip() and line.strip() != "NONE"]
        me_path = _load_config(CONFIG_PATH).get("user", {}).get("identity", "") or None
        for raw_line in raw_lines:
            # Parse ownership prefix: "ME: <text>" → assign to me, else no assignee
            if raw_line.upper().startswith("ME: "):
                assignee = me_path
                rest = raw_line[4:].strip()
            else:
                assignee = None
                rest = raw_line

            # Parse optional due date suffix: "<text> | YYYY-MM-DD"
            due_date = None
            if " | " in rest:
                text_part, date_part = rest.rsplit(" | ", 1)
                date_part = date_part.strip()
                if len(date_part) == 10 and date_part[4] == "-" and date_part[7] == "-":
                    due_date = date_part
                    rest = text_part.strip()
                # else: malformed suffix — keep rest as-is, no due date

            line = rest
            if not line:
                continue
            from engine.paths import store_path as _store_path
            rel_note_path = _store_path(note_path.resolve())
            existing = conn.execute(
                "SELECT COUNT(*) FROM action_items WHERE note_path=? AND text=?",
                (rel_note_path, line),
            ).fetchone()[0]
            if existing == 0:
                conn.execute(
                    "INSERT INTO action_items (note_path, text, done, assignee_path, due_date) VALUES (?, ?, 0, ?, ?)",
                    (rel_note_path, line, assignee, due_date),
                )
        conn.commit()
    except Exception:
        logger.warning("Action item extraction failed", exc_info=True)


def list_actions(conn, done: bool | None = False, assignee: str | None = None, note_path: str | None = None) -> list[dict]:
    """Return action items as a list of dicts.

    Args:
        conn: SQLite connection (must have row_factory=sqlite3.Row for dict() to work).
        done: True = completed only, False = open only (default), None = all items.
        assignee: If set, filter to items where assignee_path matches this value.
        note_path: If set, filter to items where note_path matches this value.
    """
    import sqlite3 as _sqlite3
    conn.row_factory = _sqlite3.Row
    sql = "SELECT id, text, note_path, created_at, assignee_path, done, due_date, description FROM action_items"
    params: list = []
    conditions = []
    if done is not None:
        conditions.append("done=?")
        params.append(1 if done else 0)
    if assignee is not None:
        conditions.append("assignee_path=?")
        params.append(assignee)
    if note_path is not None:
        conditions.append("note_path=?")
        params.append(note_path)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_overdue_actions(conn) -> list[dict]:
    """Return open action items whose due_date is in the past (due_date < today)."""
    import sqlite3 as _sqlite3
    conn.row_factory = _sqlite3.Row
    rows = conn.execute(
        "SELECT id, text, note_path, created_at, assignee_path, done, due_date, description "
        "FROM action_items "
        "WHERE due_date IS NOT NULL AND due_date < date('now') AND done=0 "
        "ORDER BY due_date",
    ).fetchall()
    return [dict(r) for r in rows]


def actions_main(argv=None) -> None:
    """Entry point for sb-actions CLI."""
    import argparse

    parser = argparse.ArgumentParser(prog="sb-actions", description="Manage action items")
    parser.add_argument("--done", type=int, metavar="ID", help="Mark item complete")
    args = parser.parse_args(argv)

    conn = get_connection()
    init_schema(conn)
    migrate_add_action_items_table(conn)

    if args.done is not None:
        conn.execute("UPDATE action_items SET done=1 WHERE id=?", (args.done,))
        conn.commit()
        print(f"Marked item {args.done} complete.")
        return

    rows = conn.execute(
        "SELECT id, text, note_path, created_at FROM action_items WHERE done=0 ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    if not rows:
        print("No open action items.")
        return

    print(f"{'ID':<4}  {'Action Item':<50}  {'Source':<30}  {'Date'}")
    print("-" * 100)
    for row_id, text, path, created_at in rows:
        short_path = Path(path).name if path else ""
        truncated = text[:48] + ".." if len(text) > 50 else text
        print(f"{row_id:<4}  {truncated:<50}  {short_path:<30}  {created_at[:10]}")


# ---------------------------------------------------------------------------
# Stale nudge (INTL-06/07/08)
# ---------------------------------------------------------------------------

def get_stale_notes(conn, days: int = 90, limit: int = 5, include_fresh: bool = False) -> list[dict]:
    """Return notes scored by relevance decay, excluding evergreen and snoozed.

    Uses graduated decay bands instead of a binary age threshold:
    - fresh (score > 0.8): only included when include_fresh=True
    - aging (0.4-0.8): candidate for review nudge
    - stale (< 0.4): should be surfaced in health checks

    Each result has: path, title, updated_at, decay_score, band, type, last_accessed_at.
    Person notes are excluded (always evergreen).
    """
    from engine.search import _relevance_decay

    rows = conn.execute(
        "SELECT path, title, type, created_at, updated_at, last_accessed_at, access_count "
        "FROM notes WHERE archived = 0 AND type NOT IN ('person') "
        "ORDER BY updated_at ASC LIMIT ?",
        (limit * 5,),
    ).fetchall()

    state = _load_state()
    snoozed = state.get("stale_snoozed", {})
    today = datetime.date.today().isoformat()

    results = []
    snoozed_updated = False
    for path, title, note_type, created_at, updated_at, last_accessed_at, access_count in rows:
        if len(results) >= limit:
            break
        if path in snoozed and snoozed[path] > today:
            continue
        from engine.paths import BRAIN_ROOT as _br
        p = _br / path
        if not p.exists():
            continue
        try:
            import frontmatter
            meta = frontmatter.load(str(p))
            if meta.get("evergreen"):
                continue
        except Exception:
            pass

        decay_score = _relevance_decay(created_at, note_type, last_accessed_at, access_count or 0)
        # Normalize: decay_score is 1.0-1.15, map to 0-1 band scale
        normalized = (decay_score - 1.0) / 0.15  # 0.0 = no boost, 1.0 = max boost

        if normalized > 0.8:
            band = "fresh"
        elif normalized > 0.4:
            band = "aging"
        else:
            band = "stale"

        if band == "fresh" and not include_fresh:
            continue

        results.append({
            "path": path,
            "title": title,
            "type": note_type,
            "updated_at": updated_at,
            "last_accessed_at": last_accessed_at,
            "decay_score": round(normalized, 3),
            "band": band,
        })
        snooze_until = (datetime.date.today() + datetime.timedelta(days=180)).isoformat()
        snoozed[path] = snooze_until
        snoozed_updated = True

    if snoozed_updated:
        state["stale_snoozed"] = snoozed
        _save_state(state)

    return results


def check_stale_nudge(conn) -> None:
    """Fire a stale note nudge if budget is available. Consumes budget on fire."""
    if not budget_available(conn, feature="stale_nudge"):
        return
    notes = get_stale_notes(conn)
    if not notes:
        return
    print("\nStale notes — consider reviewing:")
    for n in notes:
        title = n.get("title") or Path(n["path"]).stem
        print(f"  - {title}  ({n['updated_at'][:10]})")
    consume_budget(feature="stale_nudge")


# ---------------------------------------------------------------------------
# Temporal proximity (Phase 56)
# ---------------------------------------------------------------------------

def find_temporal_neighbors(
    conn,
    reference_time: str,
    window_minutes: int = 15,
    exclude_path: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Find notes created within window_minutes of reference_time.

    Args:
        conn: Open SQLite connection.
        reference_time: ISO 8601 timestamp (e.g. '2026-04-17T12:00:00Z').
        window_minutes: Time window in minutes (default 15).
        exclude_path: Note path to exclude from results (typically the just-captured note).
        limit: Max results (default 10).

    Returns:
        List of dicts: [{"path", "title", "type", "created_at", "delta_seconds"}]
        sorted by delta_seconds ascending (closest first).
    """
    window_seconds = window_minutes * 60
    rows = conn.execute(
        """
        SELECT path, title, type, created_at,
               ABS(CAST(
                   (julianday(created_at) - julianday(?)) * 86400
               AS INTEGER)) AS delta_seconds
        FROM notes
        WHERE ABS(
            (julianday(created_at) - julianday(?)) * 86400
        ) <= ?
          AND (path != ? OR ? IS NULL)
          AND type != 'synthesis'
        ORDER BY delta_seconds ASC
        LIMIT ?
        """,
        (reference_time, reference_time, window_seconds, exclude_path, exclude_path, limit),
    ).fetchall()
    return [
        {
            "path": r[0],
            "title": r[1],
            "type": r[2],
            "created_at": r[3],
            "delta_seconds": r[4],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Connection suggestions (INTL-09)
# ---------------------------------------------------------------------------

def find_similar(note_path: str, conn, threshold: float = 0.7, limit: int = 3) -> list[dict]:
    """Return up to limit notes with cosine similarity > threshold to note_path."""
    row = conn.execute(
        "SELECT embedding FROM note_embeddings WHERE note_path = ?", (note_path,)
    ).fetchone()
    if not row or not row[0]:
        return []
    query_blob = row[0]

    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except Exception:
        return []  # sqlite-vec not available — silently skip

    try:
        rows = conn.execute(
            """
            SELECT ne.note_path,
                   vec_distance_cosine(ne.embedding, ?) AS dist
            FROM note_embeddings ne
            WHERE ne.note_path != ?
              AND (1.0 - dist) >= ?
            ORDER BY dist
            LIMIT ?
            """,
            (query_blob, note_path, threshold, limit),
        ).fetchall()
        return [{"note_path": r[0], "similarity": 1.0 - r[1]} for r in rows]
    except Exception:
        logger.warning("find_similar query failed for %s", note_path, exc_info=True)
        return []


ENRICH_SYSTEM_PROMPT = (
    "You are a knowledge management assistant. "
    "Update the existing note by integrating new information. "
    "Preserve all existing facts. Add new information naturally. "
    "Don't duplicate content. Maintain the note's style and structure. "
    "Output only the updated note body — no preamble."
)


def enrich_note(existing_path: str, new_content: str, conn, adapter=None) -> dict:
    """Integrate new_content into an existing note using AI-assisted merge.

    Returns: {"path": str, "before_length": int, "after_length": int, "enriched": bool}
    """
    import frontmatter as _fm
    import tempfile
    import os as _os
    from engine.paths import BRAIN_ROOT, CONFIG_PATH, store_path as _store_path
    from engine.embeddings import embed_texts

    # Resolve path
    p = Path(existing_path)
    if not p.is_absolute():
        p = BRAIN_ROOT / existing_path
    if not p.exists():
        raise ValueError(f"Note not found: {existing_path!r}")

    post = _fm.load(str(p))
    existing_body = post.content or ""
    before_len = len(existing_body)

    # Try AI merge
    enriched = False
    if adapter is None:
        try:
            adapter = _router.get_adapter("public", CONFIG_PATH)
        except Exception:
            adapter = None

    merged_body = None
    if adapter and existing_body:
        try:
            merged_body = adapter.generate(
                user_content=f"EXISTING NOTE:\n{existing_body}\n\nNEW INFORMATION:\n{new_content}",
                system_prompt=ENRICH_SYSTEM_PROMPT,
            )
            enriched = True
        except Exception:
            merged_body = None

    if not merged_body:
        # Structured fallback — NOT raw --- concatenation
        today = datetime.date.today().isoformat()
        merged_body = existing_body + f"\n\n## Update {today}\n\n{new_content}"

    post.content = merged_body
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")
    post["updated_at"] = now
    after_len = len(merged_body)

    # Compute DB path
    try:
        db_path = _store_path(p.resolve())
    except ValueError:
        db_path = existing_path

    # Atomic write: tempfile in same dir, UPDATE DB, commit, os.replace
    tmp_fd, tmp_name = tempfile.mkstemp(dir=p.parent, suffix=".md")
    try:
        with _os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(_fm.dumps(post))
        tmp_fd = None  # fd now closed by context manager
        conn.execute(
            "UPDATE notes SET body=?, updated_at=? WHERE path=?",
            (merged_body, now, db_path),
        )
        conn.execute(
            "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?,?,?,datetime('now'))",
            ("enriched", db_path, f"before:{before_len},after:{after_len}"),
        )
        conn.commit()
        _os.replace(tmp_name, str(p))
    except Exception:
        if tmp_fd is not None:
            try:
                _os.close(tmp_fd)
            except OSError:
                pass
        Path(tmp_name).unlink(missing_ok=True)
        raise

    # Re-embed (best-effort)
    try:
        blobs = embed_texts([merged_body[:4000]])
        if blobs:
            conn.execute(
                "INSERT OR REPLACE INTO note_embeddings (note_path, embedding) VALUES (?,?)",
                (db_path, blobs[0]),
            )
    except Exception:
        pass

    # Rebuild FTS5
    conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")
    conn.commit()

    return {
        "path": existing_path,
        "before_length": before_len,
        "after_length": after_len,
        "enriched": enriched,
    }


def find_dormant_related(note_path: str, conn, limit: int = 3) -> list[dict]:
    """Return up to `limit` notes similar to note_path that haven't been updated in 30+ days.

    Uses find_similar with a wider threshold (0.5) to cast a broad net, then filters to
    notes whose updated_at is older than 30 days. Best-effort — returns [] on any error.

    Returns: [{"path": str, "title": str, "similarity": float, "last_updated": str}, ...]
    """
    try:
        cutoff = (
            datetime.datetime.now(datetime.UTC).replace(tzinfo=None) - datetime.timedelta(days=30)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        candidates = find_similar(note_path, conn, threshold=0.5, limit=20)
        if not candidates:
            return []

        results = []
        for candidate in candidates:
            if len(results) >= limit:
                break
            cpath = candidate["note_path"]
            row = conn.execute(
                "SELECT updated_at, title FROM notes WHERE path=?", (cpath,)
            ).fetchone()
            if not row:
                continue
            updated_at, title = row
            if updated_at and updated_at < cutoff:
                results.append({
                    "path": cpath,
                    "title": title or "",
                    "similarity": candidate["similarity"],
                    "last_updated": updated_at,
                })

        return results
    except Exception:
        return []


def surface_relevant(
    conn,
    context: str,
    max_results: int = 5,
    session_minutes: int = 30,
) -> list[dict]:
    """Find contextually relevant notes the user didn't ask for but should see.

    Pipeline:
    1. Semantic search against context text (wide net)
    2. Apply relevance decay (access + type-aware aging from Phase 51)
    3. Exclude notes already surfaced in current session (audit_log dedup)
    4. Flag dormant notes (not updated in 30+ days)
    5. Sort by combined score, take top max_results

    Returns: [{"path", "title", "snippet", "relevance_score", "reason"}]
    """
    from engine.search import search_semantic, _relevance_decay

    # Step 1: Semantic search with headroom
    try:
        candidates = search_semantic(conn, context, limit=max_results * 3)
    except Exception:
        return []

    if not candidates:
        return []

    # Step 2: Already has decay applied via search_semantic -> _apply_relevance_decay
    # (search_semantic calls _apply_relevance_decay internally)

    # Step 3: Session dedup — exclude notes seen recently
    cutoff_time = (
        datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        - datetime.timedelta(minutes=session_minutes)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        seen_rows = conn.execute(
            "SELECT DISTINCT note_path FROM audit_log "
            "WHERE event_type IN ('mcp_read', 'mcp_search', 'mcp_surface') "
            "AND created_at >= ? AND note_path IS NOT NULL",
            (cutoff_time,),
        ).fetchall()
        seen_paths = {r[0] for r in seen_rows}
    except Exception:
        seen_paths = set()

    candidates = [c for c in candidates if c["path"] not in seen_paths]

    # Step 4: Flag dormant notes and assign reasons
    dormant_cutoff = (
        datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        - datetime.timedelta(days=30)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    results = []
    for c in candidates[:max_results]:
        # Determine reason
        reason = "semantically_similar"
        try:
            row = conn.execute(
                "SELECT updated_at, access_count FROM notes WHERE path = ?",
                (c["path"],),
            ).fetchone()
            if row:
                updated_at = row[0]
                access_count = row[1] or 0
                if updated_at and updated_at < dormant_cutoff:
                    reason = "dormant_but_relevant"
                elif access_count >= 5:
                    reason = "frequently_accessed"
        except Exception:
            pass

        results.append({
            "path": c["path"],
            "title": c.get("title", ""),
            "snippet": c.get("excerpt", c.get("title", ""))[:200],
            "relevance_score": round(c.get("score", 0.0), 4),
            "reason": reason,
        })

    return results


def cluster_recent_notes(
    conn,
    window_days: int = 7,
    min_cluster_size: int = 3,
) -> list[dict]:
    """Identify clusters of related recent notes for synthesis.

    Groups notes created/updated in the last window_days by shared people
    (via note_people junction) and shared tags (via note_tags junction).
    Merges overlapping clusters and filters below min_cluster_size.

    Returns: [{"cluster_id": str, "topic": str, "notes": [paths],
               "shared_people": [...], "shared_tags": [...]}]
    """
    cutoff = (
        datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        - datetime.timedelta(days=window_days)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Get recent non-synthesis notes
    recent_rows = conn.execute(
        "SELECT path FROM notes WHERE "
        "(created_at >= ? OR updated_at >= ?) AND type != 'synthesis'",
        (cutoff, cutoff),
    ).fetchall()
    recent_paths = {r[0] for r in recent_rows}

    if not recent_paths:
        return []

    # Step 1: Group by shared people
    person_clusters: dict[str, set[str]] = {}
    for path in recent_paths:
        people_rows = conn.execute(
            "SELECT person FROM note_people WHERE note_path = ?", (path,)
        ).fetchall()
        for (person,) in people_rows:
            person_clusters.setdefault(person, set()).add(path)

    # Step 2: Group by shared tags (exclude generic tags)
    tag_clusters: dict[str, set[str]] = {}
    generic_tags = {"auto-synthesized", "auto-captured", "imported"}
    for path in recent_paths:
        tag_rows = conn.execute(
            "SELECT tag FROM note_tags WHERE note_path = ?", (path,)
        ).fetchall()
        for (tag,) in tag_rows:
            if tag.lower() not in generic_tags:
                tag_clusters.setdefault(tag, set()).add(path)

    # Step 3: Collect candidate clusters
    candidates: list[tuple[set[str], list[str], list[str]]] = []
    for person, notes in person_clusters.items():
        if len(notes) >= min_cluster_size:
            candidates.append((notes, [person], []))
    for tag, notes in tag_clusters.items():
        if len(notes) >= min_cluster_size:
            candidates.append((notes, [], [tag]))

    # Step 4: Merge overlapping clusters (>50% note overlap)
    merged: list[tuple[set[str], list[str], list[str]]] = []
    used = [False] * len(candidates)
    for i, (notes_i, people_i, tags_i) in enumerate(candidates):
        if used[i]:
            continue
        combined_notes = set(notes_i)
        combined_people = list(people_i)
        combined_tags = list(tags_i)
        for j in range(i + 1, len(candidates)):
            if used[j]:
                continue
            notes_j, people_j, tags_j = candidates[j]
            overlap = len(combined_notes & notes_j)
            smaller = min(len(combined_notes), len(notes_j))
            if smaller > 0 and overlap / smaller > 0.5:
                combined_notes |= notes_j
                combined_people.extend(p for p in people_j if p not in combined_people)
                combined_tags.extend(t for t in tags_j if t not in combined_tags)
                used[j] = True
        used[i] = True
        if len(combined_notes) >= min_cluster_size:
            merged.append((combined_notes, combined_people, combined_tags))

    # Step 5: Deduplicate — each note appears in at most one cluster (largest wins)
    merged.sort(key=lambda x: len(x[0]), reverse=True)
    assigned: set[str] = set()
    results: list[dict] = []
    for idx, (notes, people, tags) in enumerate(merged):
        unique = notes - assigned
        if len(unique) < min_cluster_size:
            continue
        assigned |= unique
        # Infer topic
        topic = tags[0] if tags else (
            people[0].rsplit("/", 1)[-1].replace(".md", "").replace("-", " ").title()
            if people else "Mixed"
        )
        results.append({
            "cluster_id": f"cluster-{idx}",
            "topic": topic,
            "notes": sorted(unique),
            "shared_people": people,
            "shared_tags": tags,
        })

    return results


def _append_related_link(note_path: Path, matched_stem: str) -> None:
    """Append Related: [[stem]] to new note — one-directional, best-effort."""
    try:
        existing = note_path.read_text(encoding="utf-8")
        link_line = f"\nRelated: [[{matched_stem}]]"
        if link_line.strip() not in existing:
            note_path.write_text(existing + link_line, encoding="utf-8")
    except OSError:
        pass


def check_connections(note_path: Path, conn, brain_root: Path) -> None:
    """Print connection suggestions when similar notes exist. Best-effort."""
    global _check_connections_last_run
    try:
        # Cooldown gate: skip O(n) similarity scan if run within the last 30 minutes
        now = time.monotonic()
        if (now - _check_connections_last_run) < _CHECK_CONNECTIONS_COOLDOWN_SECS:
            return
        if not budget_available(conn, feature="connections"):
            return
        # DB stores relative paths — convert absolute to relative for embedding lookup
        try:
            from engine.paths import store_path
            _db_path = store_path(note_path.resolve())
        except (ValueError, ImportError):
            _db_path = str(note_path.resolve())
        matches = find_similar(_db_path, conn)
        if not matches:
            _check_connections_last_run = time.monotonic()
            return
        logger.info("Related notes found for %s:", note_path.name)
        for m in matches:
            matched_path = Path(m["note_path"])
            logger.info("  - %s  (similarity: %.2f)", matched_path.name, m["similarity"])
            # Phase 17 revisit: skip append for pii-sensitivity notes
            _append_related_link(note_path, matched_path.stem)
        consume_budget(feature="connections")
        _check_connections_last_run = time.monotonic()
    except Exception:
        logger.warning("check_connections failed", exc_info=True)


# ---------------------------------------------------------------------------
# Entity recap (SRCH-03/04)
# ---------------------------------------------------------------------------

def recap_entity(name: str, conn) -> str | None:
    """Fetch notes about `name` (person or project), synthesise via PII-aware routing.

    Returns the printed summary string, or None if no notes found.
    Prints to stdout directly (same as recap_main pattern).
    """
    from engine.paths import CONFIG_PATH

    # 1. Fetch via search_hybrid (FTS + semantic merged)
    try:
        from engine.search import search_hybrid
        hybrid_results = search_hybrid(conn, name, limit=20)
    except Exception:
        hybrid_results = []

    # 2. Also fetch by explicit people/tags match via junction tables (F-03)
    try:
        tagged_by_people = conn.execute(
            "SELECT DISTINCT n.path, n.title, n.body, n.sensitivity FROM notes n "
            "JOIN note_people np ON np.note_path = n.path "
            "WHERE np.person LIKE ? ORDER BY n.updated_at DESC LIMIT 20",
            (f"%{name}%",),
        ).fetchall()
        tagged_by_tags = conn.execute(
            "SELECT DISTINCT n.path, n.title, n.body, n.sensitivity FROM notes n "
            "JOIN note_tags nt ON nt.note_path = n.path "
            "WHERE nt.tag = ? ORDER BY n.updated_at DESC LIMIT 20",
            (name,),
        ).fetchall()
        seen_tagged: set[str] = set()
        tagged = []
        for row in tagged_by_people + tagged_by_tags:
            if row[0] not in seen_tagged:
                seen_tagged.add(row[0])
                tagged.append(row)
        tagged = tagged[:20]
    except Exception:
        tagged = []

    # 3. Merge: tagged rows are authoritative (people/tags match).
    # hybrid_results are supplementary — only include if entity name appears in
    # their title (avoids false positives from stub/semantic fallback returning
    # unrelated notes when the entity name doesn't match anything).
    name_lower = name.lower()
    seen_paths: set[str] = set()
    merged_paths: list[str] = []

    # Authoritative: explicit people/tags match
    for row in tagged:
        p = row[0]
        if p and p not in seen_paths:
            seen_paths.add(p)
            merged_paths.append(p)

    # Supplementary: hybrid results where title/path suggests relevance
    for r in hybrid_results:
        p = r.get("path", "")
        title = (r.get("title") or "").lower()
        if p and p not in seen_paths and name_lower in title:
            seen_paths.add(p)
            merged_paths.append(p)

    merged_paths = merged_paths[:20]

    # 4. Empty state
    if not merged_paths:
        msg = f"No notes found about '{name}'. Capture a meeting or note to build context."
        logger.info(msg)
        return None

    # 5. Load full note bodies from DB (individual lookups avoid dynamic IN clause)
    rows = []
    seen_loaded = set()
    for _path in merged_paths:
        if _path in seen_loaded:
            continue
        _row = conn.execute(
            "SELECT path, title, body, sensitivity FROM notes WHERE path = ?", (_path,)
        ).fetchone()
        if _row:
            rows.append(_row)
            seen_loaded.add(_path)

    # If DB had tagged rows not returned by query (path mismatch), add them too
    existing_paths = {r[0] for r in rows}
    extra_rows = [r for r in tagged if r[0] in seen_paths and r[0] not in existing_paths]
    rows = list(rows) + extra_rows

    if not rows:
        msg = f"No notes found about '{name}'. Capture a meeting or note to build context."
        logger.info(msg)
        return None

    # 6. Split by sensitivity and truncate bodies to 500 chars
    pii_rows = [(r[1], r[2][:500]) for r in rows if r[3] == "pii"]
    public_rows = [(r[1], r[2][:500]) for r in rows if r[3] != "pii"]

    output_parts: list[str] = [f"# Recap: {name}\n"]

    # 7. PII synthesis via Ollama adapter
    if pii_rows:
        pii_text = "\n\n".join(f"Title: {title}\n{body}" for title, body in pii_rows)
        try:
            adapter = _router.get_adapter("pii", CONFIG_PATH)
            pii_summary = adapter.generate(
                user_content=f"Person/Project: {name}\n\nNotes:\n{pii_text}",
                system_prompt=RECAP_ENTITY_SYSTEM_PROMPT,
            )
        except Exception:
            pii_summary = "[Summary unavailable]"
        output_parts.append(pii_summary)

    # 8. Public synthesis via Claude adapter
    if public_rows:
        public_text = "\n\n".join(f"Title: {title}\n{body}" for title, body in public_rows)
        try:
            adapter = _router.get_adapter("public", CONFIG_PATH)
            public_summary = adapter.generate(
                user_content=f"Person/Project: {name}\n\nNotes:\n{public_text}",
                system_prompt=RECAP_ENTITY_SYSTEM_PROMPT,
            )
        except Exception:
            public_summary = "[Summary unavailable]"
        output_parts.append(public_summary)

    result = "\n\n".join(output_parts)
    print(result)
    return result


# ---------------------------------------------------------------------------
# Person insight (40-01)
# ---------------------------------------------------------------------------

def generate_person_insight(conn, person_path: str, force: bool = False) -> str:
    """Return a 24h-cached AI insight for a person note.

    Checks person_insights cache first. Regenerates via Ollama adapter when:
    - No cache entry exists
    - Cache is older than 24 hours
    - force=True

    Returns the insight string. Returns a fallback string on any exception.
    """
    import datetime
    try:
        import sqlite3 as _sqlite3
        orig_factory = conn.row_factory
        conn.row_factory = None  # use plain tuples for cache check

        cache_row = conn.execute(
            "SELECT insight, generated_at FROM person_insights WHERE person_path=?",
            (person_path,),
        ).fetchone()

        if cache_row and not force:
            insight_cached, generated_at_str = cache_row[0], cache_row[1]
            try:
                generated_at = datetime.datetime.fromisoformat(
                    generated_at_str.replace("Z", "+00:00")
                )
                age = datetime.datetime.now(datetime.timezone.utc) - generated_at
                if age < datetime.timedelta(hours=24):
                    conn.row_factory = orig_factory
                    return insight_cached
            except (ValueError, AttributeError):
                pass

        # Regenerate
        conn.row_factory = _sqlite3.Row

        person_row = conn.execute(
            "SELECT title, body FROM notes WHERE path=?", (person_path,)
        ).fetchone()
        person_title = person_row["title"] if person_row else ""
        person_body = (person_row["body"] or "")[:500] if person_row else ""

        related_rows = conn.execute(
            "SELECT n.title, n.body, n.type, substr(n.created_at,1,10) AS date "
            "FROM notes n JOIN note_people np ON np.note_path=n.path "
            "WHERE np.person LIKE ? ORDER BY n.updated_at DESC LIMIT 15",
            (f"%{person_title}%",),
        ).fetchall() if person_title else []

        open_action_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM action_items WHERE assignee_path=? AND done=0",
            (person_path,),
        ).fetchone()["cnt"]

        conn.row_factory = orig_factory

        parts = []
        if person_body:
            parts.append(f"Person profile:\n{person_body}")
        if related_rows:
            snippets = "\n\n".join(
                f"[{r['date']}] {r['title']} ({r['type']}): {(r['body'] or '')[:300]}"
                for r in related_rows
            )
            parts.append(f"Related notes:\n{snippets}")
        parts.append(f"Open action items assigned to this person: {open_action_count}")

        text = f"Person name: {person_title}\n\n" + "\n\n".join(parts) if parts else f"Person: {person_title}"

        from engine.paths import CONFIG_PATH
        adapter = _router.get_adapter("public", CONFIG_PATH)
        insight = adapter.generate(user_content=text, system_prompt=PERSON_INSIGHT_SYSTEM_PROMPT)

        conn.execute(
            "INSERT OR REPLACE INTO person_insights (person_path, insight, generated_at) "
            "VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))",
            (person_path, insight),
        )
        conn.commit()
        return insight

    except Exception as exc:
        logger.warning("generate_person_insight failed for %s: %s", person_path, exc)
        return f"Insight unavailable: {exc}"


# ---------------------------------------------------------------------------
# On-demand recap (GUIF-02 / ENGL-03)
# ---------------------------------------------------------------------------

def generate_recap_on_demand(conn, window_days: int | None = None) -> str:
    """Generate recap from recent notes within a configurable time window.

    Args:
        conn: Active sqlite3.Connection.
        window_days: How many days back to include. If None, reads from config
            ([recap].window_days, default 7). Hard cap of max_notes (default 50).

    Returns the summary string. Returns fallback string on error or empty DB.
    """
    try:
        from engine.config_loader import load_config
        from engine.paths import CONFIG_PATH as _cfg_path
        cfg = load_config(_cfg_path)
        recap_cfg = cfg.get("recap", {})
        if window_days is None:
            window_days = recap_cfg.get("window_days", 7)
        max_notes = recap_cfg.get("max_notes", 50)
        body_trunc = recap_cfg.get("body_truncation", 500)

        # Overdue actions — always prepend if any exist, regardless of recent notes
        overdue = get_overdue_actions(conn)
        overdue_section = ""
        if overdue:
            lines = ["## Overdue Actions"]
            for item in overdue:
                due = item["due_date"]
                lines.append(f"- {item['text']} (due {due})")
            overdue_section = "\n".join(lines) + "\n\n"

        # Use string arithmetic in SQL to avoid f-string interpolation into the query.
        # window_days and max_notes are ints (validated above); the interval is computed
        # entirely inside SQLite via arithmetic on a bound parameter — no injection risk.
        rows = conn.execute(
            "SELECT title, body, sensitivity FROM notes "
            "WHERE created_at >= datetime('now', (? || ' days')) "
            "ORDER BY created_at DESC LIMIT ?",
            (f"-{int(window_days)}", int(max_notes)),
        ).fetchall()
        if not rows:
            return overdue_section + f"No notes captured in the last {window_days} days."
        # Separate PII from public
        pii_parts = []
        public_parts = []
        for title, body, sensitivity in rows:
            snippet = f"## {title}\n{body[:body_trunc]}"
            if sensitivity == "pii":
                pii_parts.append(snippet)
            else:
                public_parts.append(snippet)
        from engine.paths import CONFIG_PATH
        parts = []
        if public_parts:
            adapter = _router.get_adapter("public", CONFIG_PATH)
            text = "\n\n".join(public_parts)
            result = adapter.generate(user_content=text, system_prompt=RECAP_SYSTEM_PROMPT)
            if result:
                parts.append(result)
        if pii_parts:
            adapter = _router.get_adapter("pii", CONFIG_PATH)
            text = "\n\n".join(pii_parts)
            result = adapter.generate(user_content=text, system_prompt=RECAP_SYSTEM_PROMPT)
            if result:
                parts.append(result)
        return overdue_section + ("\n\n".join(parts) if parts else "Recap generation unavailable (AI adapter not responding).")
    except Exception as exc:
        return f"Error generating recap: {exc}"


# ---------------------------------------------------------------------------
# Weekly synthesis (40-02)
# ---------------------------------------------------------------------------

def generate_weekly_synthesis(conn) -> str:
    """Generate an AI weekly synthesis from the last 7 days of notes.

    Always regenerates on call (no caching). Follows the same PII-aware adapter
    pattern as generate_recap_on_demand, but uses a 7-day window, up to 100 notes,
    and enriches the prompt with top people and recent action items.

    Returns synthesis string. Returns fallback string on empty DB or error.
    """
    try:
        from engine.paths import CONFIG_PATH
        window_days = 7
        max_notes = 100
        body_trunc = 300

        rows = conn.execute(
            "SELECT title, body, sensitivity FROM notes "
            "WHERE created_at >= datetime('now', (? || ' days')) "
            "ORDER BY created_at DESC LIMIT ?",
            (f"-{window_days}", max_notes),
        ).fetchall()

        if not rows:
            return f"No notes captured in the last {window_days} days."

        # Top people mentioned this week
        top_people = conn.execute(
            "SELECT np.person, COUNT(*) AS cnt FROM note_people np "
            "JOIN notes n ON n.path=np.note_path "
            "WHERE n.created_at >= datetime('now', '-7 days') "
            "GROUP BY np.person ORDER BY cnt DESC LIMIT 10",
        ).fetchall()

        # Recent action items created this week
        recent_actions = conn.execute(
            "SELECT text, note_path FROM action_items "
            "WHERE created_at >= datetime('now', '-7 days') "
            "ORDER BY created_at DESC LIMIT 20",
        ).fetchall()

        pii_parts = []
        public_parts = []
        for title, body, sensitivity in rows:
            snippet = f"## {title}\n{body[:body_trunc]}"
            if sensitivity == "pii":
                pii_parts.append(snippet)
            else:
                public_parts.append(snippet)

        # Build enrichment context
        enrichment_parts = []
        if top_people:
            people_list = ", ".join(f"{p[0]} ({p[1]}x)" for p in top_people)
            enrichment_parts.append(f"Top people this week: {people_list}")
        if recent_actions:
            actions_list = "; ".join(a[0] for a in recent_actions[:10])
            enrichment_parts.append(f"Recent action items: {actions_list}")
        enrichment = "\n".join(enrichment_parts)

        result_parts = []
        if public_parts:
            text = "\n\n".join(public_parts)
            if enrichment:
                text = enrichment + "\n\n" + text
            adapter = _router.get_adapter("public", CONFIG_PATH)
            result = adapter.generate(user_content=text, system_prompt=WEEKLY_SYNTHESIS_SYSTEM_PROMPT)
            if result:
                result_parts.append(result)
        if pii_parts:
            text = "\n\n".join(pii_parts)
            adapter = _router.get_adapter("pii", CONFIG_PATH)
            result = adapter.generate(user_content=text, system_prompt=WEEKLY_SYNTHESIS_SYSTEM_PROMPT)
            if result:
                result_parts.append(result)

        return "\n\n".join(result_parts) if result_parts else "Synthesis generation unavailable (AI adapter not responding)."

    except Exception as exc:
        return f"Error generating synthesis: {exc}"


# ---------------------------------------------------------------------------
# Summarization (38-06)
# ---------------------------------------------------------------------------

def summarize_note(conn, note_path: str, force: bool = False) -> str | None:
    """Generate and store a summary for a long note.

    Returns summary string if generated, None if note too short or already summarized.
    Uses existing LLM adapter pattern (router → ClaudeAdapter).

    Args:
        conn: Active SQLite connection.
        note_path: Path of the note to summarize.
        force: If True, regenerate even if a summary already exists.

    Returns:
        Summary string on success, None if note is too short or not found.
    """
    row = conn.execute(
        "SELECT body, summary FROM notes WHERE path=?", (note_path,)
    ).fetchone()
    if not row:
        return None

    body, existing_summary = row
    if not body or len(body) < SUMMARY_THRESHOLD:
        return None
    if existing_summary and not force:
        return existing_summary

    from engine.paths import CONFIG_PATH
    try:
        adapter = _router.get_adapter("public", CONFIG_PATH)
        prompt = (
            "Summarize the following note in 2-3 concise sentences. "
            "Focus on key facts, decisions, and action items.\n\n"
            + body[:SUMMARY_MAX_INPUT]
        )
        summary = adapter.generate(user_content=prompt)
        if summary:
            conn.execute(
                "UPDATE notes SET summary=? WHERE path=?",
                (summary.strip(), note_path),
            )
            conn.commit()
            return summary.strip()
    except Exception as e:
        logger.warning("Summarization failed for %s: %s", note_path, e)
    return None


def summarize_unsummarized(conn, limit: int = 10) -> int:
    """Batch summarize notes that are long but have no summary.

    Returns count of notes successfully summarized.

    Args:
        conn: Active SQLite connection.
        limit: Maximum number of notes to process in this batch.
    """
    rows = conn.execute(
        """SELECT path FROM notes
           WHERE (summary IS NULL OR summary = '')
             AND length(body) >= ?
           LIMIT ?""",
        (SUMMARY_THRESHOLD, limit),
    ).fetchall()
    count = 0
    for (path,) in rows:
        if summarize_note(conn, path):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Session recap (INTL-02)
# ---------------------------------------------------------------------------

def recap_main(argv=None) -> None:
    """Entry point for sb-recap CLI."""
    import argparse

    parser = argparse.ArgumentParser(prog="sb-recap", description="Summarise recent activity or recap a person/project")
    parser.add_argument("context", nargs="?", help="Entity name (person/project) or leave blank for session recap")
    parser.add_argument("--days", type=int, default=None, help="Recap window in days (overrides config [recap].window_days)")
    args = parser.parse_args(argv)

    conn = get_connection()
    init_schema(conn)

    if args.context:
        # Explicit argument → treat as entity recap (person or project)
        recap_entity(args.context, conn)
        conn.close()
        return

    # No argument → original session recap (auto-detect git context)
    context_name = detect_git_context()
    if not context_name:
        # No git context — fall back to general session recap with optional --days window
        result = generate_recap_on_demand(conn, window_days=args.days)
        conn.close()
        print(result)
        return

    rows = conn.execute(
        """
        SELECT title, body FROM notes
        WHERE tags LIKE '%' || ? || '%'
           OR people LIKE '%' || ? || '%'
           OR title LIKE '%' || ? || '%'
        ORDER BY updated_at DESC
        LIMIT 10
        """,
        (context_name, context_name, context_name),
    ).fetchall()

    # Fallback: no context match — show 5 most-recent notes instead
    if not rows:
        fallback_rows = conn.execute(
            "SELECT path, title, type, updated_at FROM notes ORDER BY updated_at DESC LIMIT 5"
        ).fetchall()
        conn.close()
        if not fallback_rows:
            print("No notes found yet. Capture your first note with: sb-capture")
            return
        print("Recent activity (no context match):")
        for path, title, note_type, updated_at in fallback_rows:
            date_str = updated_at[:10] if updated_at else "unknown"
            print(f"  [{note_type}] {title}  ({date_str})")
        return

    conn.close()

    note_snippets = "\n\n".join(
        f"Title: {title}\n{body[:200]}" for title, body in rows
    )
    try:
        from engine.paths import CONFIG_PATH
        adapter = _router.get_adapter("public", CONFIG_PATH)
        summary = adapter.generate(
            user_content=f"Context: {context_name}\n\nNotes:\n{note_snippets}",
            system_prompt=RECAP_SYSTEM_PROMPT,
        )
        print(summary)
    except Exception as exc:
        print(f"Could not generate recap: {exc}")


# ---------------------------------------------------------------------------
# Ask Brain (freeform Q&A over notes)
# ---------------------------------------------------------------------------

_MD_STRIP = re.compile(
    r'\[\[.*?\]\]'          # wikilinks [[...]]
    r'|#{1,6}\s+'           # ATX headers
    r'|\*{1,2}([^*]*)\*{1,2}'  # bold/italic — keep inner text
    r'|`[^`]*`'             # inline code
    r'|\[([^\]]*)\]\([^)]*\)'  # markdown links — keep label
)


def _plain_snippet(body: str, length: int) -> str:
    """Return a plain-text snippet from a markdown note body."""
    text = _MD_STRIP.sub(lambda m: m.group(1) or m.group(2) or "", body)
    text = " ".join(text.split())  # collapse whitespace
    return text[:length]


def _parse_temporal_from_date(question: str) -> tuple[str, str | None] | None:
    """Detect temporal intent and return (from_date, until_date) or None.

    until_date is set for bounded ranges (yesterday, last week, last N days).
    Open-ended ranges (today, this week, recent) leave until_date as None.
    Handles Finnish dd.M[.YYYY] format, English month names, and relative keywords.
    """
    q = question.lower()
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    # "since/after DD.M" or "since/after DD.M.YYYY" (Finnish format, most common)
    m = re.search(r'(?:since|after|from)\s+(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?', q)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        year = int(m.group(3)) if m.group(3) else today.year
        try:
            return datetime.date(year, month, day).isoformat(), None
        except ValueError:
            pass

    # "last N days"
    m = re.search(r'last\s+(\d+)\s+days?', q)
    if m:
        n = int(m.group(1))
        return (today - datetime.timedelta(days=n)).isoformat(), today.isoformat()

    # Keywords — bounded ranges include an until_date
    if 'today' in q:
        return today.isoformat(), tomorrow.isoformat()
    if 'yesterday' in q:
        yesterday = today - datetime.timedelta(days=1)
        return yesterday.isoformat(), today.isoformat()
    if 'this week' in q:
        week_start = today - datetime.timedelta(days=today.weekday())
        return week_start.isoformat(), None
    if 'last week' in q:
        this_monday = today - datetime.timedelta(days=today.weekday())
        last_monday = this_monday - datetime.timedelta(days=7)
        return last_monday.isoformat(), this_monday.isoformat()
    if any(w in q for w in ('recent', 'recently', 'latest', 'what happened', 'what\'s new', 'whats new')):
        return (today - datetime.timedelta(days=7)).isoformat(), None

    # "last monday/tuesday/..." or "since/after monday/..."
    _WEEKDAYS = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6,
    }
    for name, wd in _WEEKDAYS.items():
        if f'last {name}' in q or f'since {name}' in q or f'after {name}' in q:
            days_back = (today.weekday() - wd) % 7 or 7
            return (today - datetime.timedelta(days=days_back)).isoformat(), None

    return None


def ask_brain(question: str, conn, history: list[dict] | None = None) -> dict:
    """Answer a natural language question using the brain's notes as context.

    Args:
        history: Optional list of prior Q&A exchanges [{"question": str, "answer": str}, ...].
                 Last 5 kept. Prepended to prompt so the LLM has conversation context.

    Returns {"answer": str, "sources": [{"title": str, "path": str, "snippet": str}]}.
    """
    from engine.search import search_hybrid
    from engine.paths import CONFIG_PATH
    from engine.config_loader import load_config as _load_config

    # --- Enrich search query with conversation context for follow-ups ---
    # The user's follow-up may be vague ("what about their email?") — the search
    # needs key entities from prior exchanges, not full question text (which
    # dilutes the search with generic words like "who", "what", "discussed").
    # Strategy: pull source paths + titles from prior answers as search anchors.
    search_query = question
    if history:
        # Collect source titles and key nouns from prior Q&A
        prior_entities: list[str] = []
        for h in history[-3:]:
            # Extract proper nouns / capitalized words from prior questions
            # (simple heuristic: words starting with uppercase that aren't sentence-start)
            q_words = (h.get("question") or "").split()
            for i, w in enumerate(q_words):
                clean = w.strip("?.,!\"'()[]")
                if clean and clean[0].isupper() and i > 0 and len(clean) > 2:
                    prior_entities.append(clean)
            # Also grab first word if it looks like a name (not a question word)
            if q_words:
                first = q_words[0].strip("?.,!\"'()[]")
                if first and first[0].isupper() and first.lower() not in (
                    "who", "what", "when", "where", "why", "how", "tell",
                    "can", "could", "would", "should", "is", "are", "do", "does",
                    "did", "has", "have", "the", "a", "an", "my", "we",
                ):
                    prior_entities.append(first)
        if prior_entities:
            # Dedupe while preserving order
            seen: set[str] = set()
            unique = []
            for e in prior_entities:
                if e.lower() not in seen:
                    seen.add(e.lower())
                    unique.append(e)
            search_query = f"{' '.join(unique)} {question}"

    # --- Temporal injection: for "since X / today / this week" questions ---
    _temporal = _parse_temporal_from_date(question)
    temporal_results: list[dict] = []
    if _temporal:
        from_date, until_date = _temporal
        if until_date:
            rows = conn.execute(
                "SELECT path, title, type, created_at, body, sensitivity FROM notes "
                "WHERE date(created_at) >= ? AND date(created_at) < ? ORDER BY created_at DESC LIMIT 10",
                (from_date, until_date),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT path, title, type, created_at, body, sensitivity FROM notes "
                "WHERE date(created_at) >= ? ORDER BY created_at DESC LIMIT 10",
                (from_date,),
            ).fetchall()
        temporal_results = [
            {
                "path": r[0], "title": r[1], "type": r[2],
                "created_at": r[3], "body": r[4] or "", "sensitivity": r[5] or "public",
            }
            for r in rows
        ]

    try:
        semantic = search_hybrid(conn, search_query, limit=15, natural_language=True)
    except Exception:
        semantic = []

    # Fetch body for semantic results
    if semantic:
        paths = [r["path"] for r in semantic]
        placeholders = ",".join("?" * len(paths))
        body_rows = conn.execute(
            f"SELECT path, body, sensitivity FROM notes WHERE path IN ({placeholders})",
            paths,
        ).fetchall()
        body_map = {row[0]: (row[1] or "", row[2] or "public") for row in body_rows}
        for r in semantic:
            r["body"], r["sensitivity"] = body_map.get(r["path"], ("", "public"))

    # Merge: temporal first (deduped), then semantic fill
    if temporal_results:
        temporal_paths = {r["path"] for r in temporal_results}
        extra = [r for r in semantic if r["path"] not in temporal_paths]
        results = temporal_results + extra
    else:
        results = semantic

    # Pin prior source notes into follow-up context so they stay available.
    # Without this, a follow-up loses the notes the first answer was based on.
    if history:
        result_paths = {r["path"] for r in results}
        prior_paths: list[str] = []
        for h in history[-3:]:
            for sp in h.get("source_paths") or []:
                if sp and sp not in result_paths:
                    prior_paths.append(sp)
                    result_paths.add(sp)
        if prior_paths:
            ph = ",".join("?" * len(prior_paths))
            pinned_rows = conn.execute(
                f"SELECT path, title, type, created_at, body, sensitivity "
                f"FROM notes WHERE path IN ({ph})",
                prior_paths,
            ).fetchall()
            pinned = [
                {"path": r[0], "title": r[1], "type": r[2],
                 "created_at": r[3], "body": r[4] or "", "sensitivity": r[5] or "public"}
                for r in pinned_rows
            ]
            # Prepend pinned notes so they rank highest in context
            results = pinned + results

    if not results:
        return {
            "answer": "No relevant notes found to answer this question.",
            "sources": [],
        }

    # When all_local=true every sensitivity goes to OllamaAdapter anyway — splitting into
    # parallel tasks just doubles the slow local calls for no privacy benefit. Merge all
    # notes into a single "public" task (Rule 1 routes it to Ollama regardless).
    _all_local = _load_config(CONFIG_PATH).get("routing", {}).get("all_local", False)

    public_items = [
        (r.get("title", ""), r["body"][:4000], r.get("path", ""), r.get("created_at", "")[:10])
        for r in results if _all_local or r.get("sensitivity") != "pii"
    ]
    pii_items = [] if _all_local else [
        (r.get("title", ""), r["body"][:4000], r.get("path", ""), r.get("created_at", "")[:10])
        for r in results if r.get("sensitivity") == "pii"
    ]

    # Build tasks: public and PII calls run in parallel to halve wall-clock time.
    def _truncate(text: str, max_chars: int = 4000) -> str:
        return text if len(text) <= max_chars else text[:max_chars] + "…"

    # Build conversation history prefix (last 5 exchanges max)
    history_prefix = ""
    if history:
        recent = history[-5:]
        turns = "\n\n".join(
            f"Q: {h['question']}\nA: {h['answer']}" for h in recent
            if h.get("question") and h.get("answer")
        )
        if turns:
            history_prefix = f"Previous conversation:\n{turns}\n\n"

    tasks: list[tuple[str, str, str]] = []  # (key, sensitivity, prompt)
    if public_items:
        ctx = "\n\n".join(
            f"Note [{date}]: {title}\n{_truncate(body)}" if date else f"Note: {title}\n{_truncate(body)}"
            for title, body, _, date in public_items[:10]
        )
        tasks.append(("public", "public", f"{history_prefix}Question: {question}\n\nRelevant notes:\n{ctx}"))
    if pii_items:
        ctx = "\n\n".join(
            f"Note [{date}]: {title}\n{_truncate(body)}" if date else f"Note: {title}\n{_truncate(body)}"
            for title, body, _, date in pii_items[:5]
        )
        tasks.append(("pii", "pii", f"{history_prefix}Question: {question}\n\nRelevant notes:\n{ctx}"))

    def _call_adapter(sensitivity: str, prompt: str) -> tuple[str, str]:
        """Returns (answer_text, provider_name)."""
        try:
            feature = "ask_brain" if sensitivity == "public" else ""
            adapter = _router.get_adapter(sensitivity, CONFIG_PATH, feature=feature)
            result = adapter.generate(user_content=prompt, system_prompt=ASK_BRAIN_SYSTEM_PROMPT) or ""
            # Detect which provider was actually used
            from engine.adapters.fallback_adapter import FallbackAdapter
            from engine.adapters.groq_adapter import GroqAdapter
            if isinstance(adapter, FallbackAdapter):
                if adapter.used_fallback:
                    return result, "fallback"
                if isinstance(adapter._primary, GroqAdapter):
                    return result, "groq"
            return result, "default"
        except Exception as exc:
            import logging as _logging
            _logging.getLogger(__name__).warning("_call_adapter(%s) failed: %s", sensitivity, exc)
            return "", "error"

    answer_parts: list[str] = []
    providers: list[str] = []
    # Parallel timeout: Groq answers in ~1-2s; Ollama (PII path) can take 10-30s.
    # If PII times out, we fall through to a single public-only call (some context lost,
    # but better than dropping the entire answer). Timeout raised from 3s to 15s.
    _PARALLEL_TIMEOUT_S = 15.0
    if len(tasks) > 1:
        import concurrent.futures
        # Don't use context manager — its __exit__ calls shutdown(wait=True) which blocks
        # until ALL threads finish, including timed-out Ollama threads still running.
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks))
        future_map = {executor.submit(_call_adapter, sensitivity, prompt): (key, sensitivity)
                      for key, sensitivity, prompt in tasks}
        done, not_done = concurrent.futures.wait(future_map.keys(), timeout=_PARALLEL_TIMEOUT_S)
        for future in done:
            try:
                ans, provider = future.result()
                if ans:
                    answer_parts.append(ans)
                    providers.append(provider)
            except Exception as exc:
                logger.warning("ask_brain parallel task failed: %s", exc)
        for future in not_done:
            _, sensitivity = future_map[future]
            logger.warning("ask_brain: %s adapter timed out after %ss — dropped (PII not sent to cloud)", sensitivity, _PARALLEL_TIMEOUT_S)
            future.cancel()
        # wait=False: return immediately; timed-out Ollama threads finish in background.
        executor.shutdown(wait=False)
    elif tasks:
        _, sensitivity, prompt = tasks[0]
        ans, provider = _call_adapter(sensitivity, prompt)
        if ans:
            answer_parts.append(ans)
            providers.append(provider)

    # Determine overall provider: groq > fallback > default
    if "groq" in providers:
        overall_provider = "groq"
    elif "fallback" in providers:
        overall_provider = "fallback"
    else:
        overall_provider = "default"

    answer = "\n\n".join(answer_parts) or "Unable to generate an answer from the available notes."
    sources = [
        {
            "title": r.get("title", ""),
            "path": r.get("path", ""),
            "snippet": _plain_snippet(r["body"], 120),
        }
        for r in results[:5]
    ]
    return {"answer": answer, "sources": sources, "provider": overall_provider}
