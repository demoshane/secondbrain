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
    "You are a personal knowledge assistant. Given notes about a person, write a concise "
    "brain insight: (1) who they are and their role/context, (2) recent interactions or meetings, "
    "(3) open action items involving them. Use 3-5 sentences, narrative style. Be specific — "
    "mention meeting titles, project names, and dates when available."
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

def budget_available(conn) -> bool:
    """True if vault has 20+ notes and no offer has been made today."""
    note_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    if note_count < VAULT_GATE:
        return False
    state = _load_state()
    today = datetime.date.today().isoformat()
    return state.get("last_offer_date") != today


def consume_budget() -> None:
    """Record that today's offer slot has been used."""
    state = _load_state()
    state["last_offer_date"] = datetime.date.today().isoformat()
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

def get_stale_notes(conn, days: int = 90, limit: int = 5) -> list[dict]:
    """Return up to limit notes not updated in `days` days, excluding evergreen and snoozed."""
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat() + "T00:00:00Z"
    rows = conn.execute(
        "SELECT path, title, updated_at FROM notes WHERE updated_at < ? ORDER BY updated_at ASC LIMIT ?",
        (cutoff, limit * 3),
    ).fetchall()

    state = _load_state()
    snoozed = state.get("stale_snoozed", {})
    today = datetime.date.today().isoformat()

    results = []
    snoozed_updated = False
    for path, title, updated_at in rows:
        if len(results) >= limit:
            break
        # Check snooze: skip if recheck date is in the future
        if path in snoozed and snoozed[path] > today:
            continue
        # Check file existence — skip deleted files
        p = Path(path)
        if not p.exists():
            continue
        # Check evergreen frontmatter
        try:
            import frontmatter
            meta = frontmatter.load(str(p))
            if meta.get("evergreen"):
                continue
        except Exception:
            pass
        results.append({"path": path, "title": title, "updated_at": updated_at})
        # INTL-08: snooze this note for 180 days now that it has been nudged
        snooze_until = (datetime.date.today() + datetime.timedelta(days=180)).isoformat()
        snoozed[path] = snooze_until
        snoozed_updated = True

    if snoozed_updated:
        state["stale_snoozed"] = snoozed
        _save_state(state)

    return results


def check_stale_nudge(conn) -> None:
    """Fire a stale note nudge if budget is available. Consumes budget on fire."""
    if not budget_available(conn):
        return
    notes = get_stale_notes(conn)
    if not notes:
        return
    print("\nStale notes — consider reviewing:")
    for n in notes:
        title = n.get("title") or Path(n["path"]).stem
        print(f"  - {title}  ({n['updated_at'][:10]})")
    consume_budget()


# ---------------------------------------------------------------------------
# Connection suggestions (INTL-09)
# ---------------------------------------------------------------------------

def find_similar(note_path: str, conn, threshold: float = 0.8, limit: int = 3) -> list[dict]:
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
        return []


def find_dormant_related(note_path: str, conn, limit: int = 3) -> list[dict]:
    """Return up to `limit` notes similar to note_path that haven't been updated in 30+ days.

    Uses find_similar with a wider threshold (0.5) to cast a broad net, then filters to
    notes whose updated_at is older than 30 days. Best-effort — returns [] on any error.

    Returns: [{"path": str, "title": str, "similarity": float, "last_updated": str}, ...]
    """
    try:
        cutoff = (
            datetime.datetime.utcnow() - datetime.timedelta(days=30)
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
        if not budget_available(conn):
            return
        matches = find_similar(str(note_path.resolve()), conn)
        if not matches:
            _check_connections_last_run = time.monotonic()
            return
        logger.info("Related notes found for %s:", note_path.name)
        for m in matches:
            matched_path = Path(m["note_path"])
            logger.info("  - %s  (similarity: %.2f)", matched_path.name, m["similarity"])
            # Phase 17 revisit: skip append for pii-sensitivity notes
            _append_related_link(note_path, matched_path.stem)
        consume_budget()
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
        print(msg)
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
        print(msg)
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

        text = "\n\n".join(parts) or f"Person: {person_title}"

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


def _parse_temporal_from_date(question: str) -> str | None:
    """Detect temporal intent and return an ISO date string (from_date) if found.

    Handles Finnish dd.M[.YYYY] format, English month names, and relative keywords.
    Returns None when no temporal pattern is detected.
    """
    q = question.lower()
    today = datetime.date.today()

    # "since/after DD.M" or "since/after DD.M.YYYY" (Finnish format, most common)
    m = re.search(r'(?:since|after|from)\s+(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?', q)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        year = int(m.group(3)) if m.group(3) else today.year
        try:
            return datetime.date(year, month, day).isoformat()
        except ValueError:
            pass

    # "last N days"
    m = re.search(r'last\s+(\d+)\s+days?', q)
    if m:
        return (today - datetime.timedelta(days=int(m.group(1)))).isoformat()

    # Keywords
    if 'today' in q:
        return today.isoformat()
    if 'yesterday' in q:
        return (today - datetime.timedelta(days=1)).isoformat()
    if 'this week' in q:
        return (today - datetime.timedelta(days=today.weekday())).isoformat()
    if 'last week' in q:
        return (today - datetime.timedelta(days=today.weekday() + 7)).isoformat()
    if any(w in q for w in ('recent', 'recently', 'latest', 'what happened', 'what\'s new', 'whats new')):
        return (today - datetime.timedelta(days=7)).isoformat()

    # "last monday/tuesday/..." or "since/after monday/..."
    _WEEKDAYS = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6,
    }
    for name, wd in _WEEKDAYS.items():
        if f'last {name}' in q or f'since {name}' in q or f'after {name}' in q:
            days_back = (today.weekday() - wd) % 7 or 7
            return (today - datetime.timedelta(days=days_back)).isoformat()

    return None


def ask_brain(question: str, conn) -> dict:
    """Answer a natural language question using the brain's notes as context.

    Returns {"answer": str, "sources": [{"title": str, "path": str, "snippet": str}]}.
    """
    from engine.search import search_hybrid
    from engine.paths import CONFIG_PATH

    # --- Temporal injection: for "since X / today / this week" questions ---
    from_date = _parse_temporal_from_date(question)
    temporal_results: list[dict] = []
    if from_date:
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
        semantic = search_hybrid(conn, question, limit=15, natural_language=True)
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

    if not results:
        return {
            "answer": "No relevant notes found to answer this question.",
            "sources": [],
        }

    public_items = [
        (r.get("title", ""), r["body"][:800], r.get("path", ""), r.get("created_at", "")[:10])
        for r in results if r.get("sensitivity") != "pii"
    ]
    pii_items = [
        (r.get("title", ""), r["body"][:800], r.get("path", ""), r.get("created_at", "")[:10])
        for r in results if r.get("sensitivity") == "pii"
    ]

    # Build tasks: public and PII calls run in parallel to halve wall-clock time.
    def _truncate(text: str, max_chars: int = 600) -> str:
        return text if len(text) <= max_chars else text[:max_chars] + "…"

    tasks: list[tuple[str, str, str]] = []  # (key, sensitivity, prompt)
    if public_items:
        ctx = "\n\n".join(
            f"Note [{date}]: {title}\n{_truncate(body)}" if date else f"Note: {title}\n{_truncate(body)}"
            for title, body, _, date in public_items[:10]
        )
        tasks.append(("public", "public", f"Question: {question}\n\nRelevant notes:\n{ctx}"))
    if pii_items:
        ctx = "\n\n".join(
            f"Note [{date}]: {title}\n{_truncate(body)}" if date else f"Note: {title}\n{_truncate(body)}"
            for title, body, _, date in pii_items[:5]
        )
        tasks.append(("pii", "pii", f"Question: {question}\n\nRelevant notes:\n{ctx}"))

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
    # Parallel timeout: Groq answers in ~1-2s; Ollama (PII path) on local CPU can take 60-120s.
    # We wait at most _PARALLEL_TIMEOUT_S seconds total. Any task not done by then is dropped.
    _PARALLEL_TIMEOUT_S = 3.0
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
            logger.warning("ask_brain: %s adapter timed out after %ss — dropping", sensitivity, _PARALLEL_TIMEOUT_S)
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
