"""Intelligence layer: session recap, action items, stale nudges, connection suggestions."""
import json
import datetime
import logging
import subprocess

logger = logging.getLogger(__name__)
from pathlib import Path

from engine.router import get_adapter as _get_adapter
from engine.db import get_connection, init_schema, migrate_add_action_items_table

STATE_PATH = Path.home() / ".meta" / "intelligence_state.json"
VAULT_GATE = 20  # minimum notes before any proactive offer fires

ACTION_ITEM_SYSTEM_PROMPT = (
    "You are an assistant that extracts action items from notes. "
    "Output ONLY a newline-separated list of action items — one per line. "
    "Each line must be a concrete, specific commitment or to-do. "
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


class _RouterShim:
    """Thin wrapper so tests can patch `engine.intelligence._router`."""

    def get_adapter(self, sensitivity: str, config_path):
        return _get_adapter(sensitivity, config_path)


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
        adapter = _router.get_adapter(sensitivity, CONFIG_PATH)
        raw = adapter.generate(user_content=body, system_prompt=ACTION_ITEM_SYSTEM_PROMPT)
        lines = [line.strip() for line in raw.splitlines() if line.strip() and line.strip() != "NONE"]
        for line in lines:
            existing = conn.execute(
                "SELECT COUNT(*) FROM action_items WHERE note_path=? AND text=?",
                (str(note_path.resolve()), line),
            ).fetchone()[0]
            if existing == 0:
                conn.execute(
                    "INSERT INTO action_items (note_path, text, done) VALUES (?, ?, 0)",
                    (str(note_path.resolve()), line),
                )
        conn.commit()
    except Exception:
        logger.warning("Action item extraction failed", exc_info=True)


def list_actions(conn, done: bool = False, assignee: str | None = None, note_path: str | None = None) -> list[dict]:
    """Return action items as a list of dicts. done=False returns open items only.

    Args:
        conn: SQLite connection (must have row_factory=sqlite3.Row for dict() to work).
        done: If True, return completed items; False returns open items (default).
        assignee: If set, filter to items where assignee_path matches this value.
        note_path: If set, filter to items where note_path matches this value.
    """
    import sqlite3 as _sqlite3
    conn.row_factory = _sqlite3.Row
    sql = "SELECT id, text, note_path, created_at, assignee_path, done, due_date FROM action_items WHERE done=?"
    params: list = [1 if done else 0]
    if assignee is not None:
        sql += " AND assignee_path=?"
        params.append(assignee)
    if note_path is not None:
        sql += " AND note_path=?"
        params.append(note_path)
    sql += " ORDER BY created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_overdue_actions(conn) -> list[dict]:
    """Return open action items whose due_date is in the past (due_date < today)."""
    import sqlite3 as _sqlite3
    conn.row_factory = _sqlite3.Row
    rows = conn.execute(
        "SELECT id, text, note_path, created_at, assignee_path, done, due_date "
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
    try:
        if not budget_available(conn):
            return
        matches = find_similar(str(note_path.resolve()), conn)
        if not matches:
            return
        logger.info("Related notes found for %s:", note_path.name)
        for m in matches:
            matched_path = Path(m["note_path"])
            logger.info("  - %s  (similarity: %.2f)", matched_path.name, m["similarity"])
            # Phase 17 revisit: skip append for pii-sensitivity notes
            _append_related_link(note_path, matched_path.stem)
        consume_budget()
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

    # 2. Also fetch by explicit people/tags match
    try:
        tagged = conn.execute(
            "SELECT path, title, body, sensitivity FROM notes "
            "WHERE people LIKE ? OR tags LIKE ? ORDER BY updated_at DESC LIMIT 20",
            (f"%{name}%", f"%{name}%"),
        ).fetchall()
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

    # 5. Load full note bodies from DB
    placeholders = ",".join("?" * len(merged_paths))
    rows = conn.execute(
        f"SELECT path, title, body, sensitivity FROM notes WHERE path IN ({placeholders})",
        merged_paths,
    ).fetchall()

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
# On-demand recap (GUIF-02 / ENGL-03)
# ---------------------------------------------------------------------------

def generate_recap_on_demand(conn) -> str:
    """Generate recap from last 7 days of notes. Always regenerates (no idempotency guard).
    Returns the summary string. Returns fallback string on error or empty DB."""
    try:
        # Overdue actions — always prepend if any exist, regardless of recent notes
        overdue = get_overdue_actions(conn)
        overdue_section = ""
        if overdue:
            lines = ["## Overdue Actions"]
            for item in overdue:
                due = item["due_date"]
                lines.append(f"- {item['text']} (due {due})")
            overdue_section = "\n".join(lines) + "\n\n"

        rows = conn.execute(
            "SELECT title, body, sensitivity FROM notes "
            "WHERE created_at >= datetime('now', '-7 days') "
            "ORDER BY created_at DESC LIMIT 30"
        ).fetchall()
        if not rows:
            return overdue_section + "No notes captured in the last 7 days."
        # Separate PII from public
        pii_parts = []
        public_parts = []
        for title, body, sensitivity in rows:
            snippet = f"## {title}\n{body[:300]}"
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
# Session recap (INTL-02)
# ---------------------------------------------------------------------------

def recap_main(argv=None) -> None:
    """Entry point for sb-recap CLI."""
    import argparse

    parser = argparse.ArgumentParser(prog="sb-recap", description="Summarise recent activity or recap a person/project")
    parser.add_argument("context", nargs="?", help="Entity name (person/project) or leave blank for session recap")
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
        conn.close()
        print("No context detected — try sb-recap <name>")
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
