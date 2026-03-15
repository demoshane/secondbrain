"""Intelligence layer: session recap, action items, stale nudges, connection suggestions."""
import json
import datetime
import subprocess
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
    "You are a personal assistant. Given a list of recent notes about a context, "
    "write a 3-5 sentence summary of recent activity, key themes, and open threads. "
    "Be concise. Output plain text, no bullet points."
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

def extract_action_items(note_path: Path, body: str, sensitivity: str, conn) -> None:
    """Extract and store action items from note body. Best-effort — never raises."""
    try:
        from engine.paths import CONFIG_PATH
        adapter = _router.get_adapter(sensitivity, CONFIG_PATH)
        raw = adapter.generate(user_content=body, system_prompt=ACTION_ITEM_SYSTEM_PROMPT)
        lines = [line.strip() for line in raw.splitlines() if line.strip() and line.strip() != "NONE"]
        for line in lines:
            conn.execute(
                "INSERT INTO action_items (note_path, text) VALUES (?, ?)",
                (str(note_path.resolve()), line),
            )
        conn.commit()
    except Exception:
        pass  # Best-effort — never blocks capture


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
        matches = find_similar(str(note_path.resolve()), conn)
        if not matches:
            return
        print("\nRelated notes found:")
        for m in matches:
            matched_path = Path(m["note_path"])
            print(f"  - {matched_path.name}  (similarity: {m['similarity']:.2f})")
            # Phase 17 revisit: skip append for pii-sensitivity notes
            _append_related_link(note_path, matched_path.stem)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Session recap (INTL-02)
# ---------------------------------------------------------------------------

def recap_main(argv=None) -> None:
    """Entry point for sb-recap CLI."""
    import argparse

    parser = argparse.ArgumentParser(prog="sb-recap", description="Summarise recent activity")
    parser.add_argument("context", nargs="?", help="Context name (default: auto-detect from git)")
    args = parser.parse_args(argv)

    context_name = args.context or detect_git_context()
    if not context_name:
        print("No context detected — try sb-recap <name>")
        return

    conn = get_connection()
    init_schema(conn)

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
    conn.close()

    if not rows:
        print(f"No notes found for context: {context_name}")
        return

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
