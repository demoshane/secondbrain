"""Digest generation for the second brain. Phase 16."""

import datetime
from pathlib import Path


DIGEST_SYSTEM_PROMPT = (
    "You are a knowledge assistant. Read the following note excerpts captured this week "
    "and identify 3-5 key themes. Be concise. Output as a short paragraph (3-5 sentences)."
)


def _week_filename() -> str:
    """Return ISO week filename like '2026-W11.md' using ISO week year (%G-%V)."""
    return datetime.date.today().strftime("%G-W%V") + ".md"


def _render_digest_body(key_themes: str, open_actions: str, stale_notes: str, captures: str) -> str:
    return (
        f"## Key Themes\n\n{key_themes}\n\n"
        f"## Open Actions\n\n{open_actions}\n\n"
        f"## Stale Notes\n\n{stale_notes}\n\n"
        f"## Captures This Week\n\n{captures}"
    )


def generate_digest(conn, digests_dir: Path) -> Path:
    """Generate weekly digest. Idempotent: skips if this week's file already exists."""
    import frontmatter as fm
    from engine.intelligence import _router, get_stale_notes
    from engine.paths import CONFIG_PATH

    digests_dir = Path(digests_dir)
    digests_dir.mkdir(parents=True, exist_ok=True)

    filename = _week_filename()
    out_path = digests_dir / filename
    if out_path.exists():
        print(f"Digest for this week already exists: {out_path}")
        return out_path

    # 1. Captures this week
    captures = "No captures this week."
    if conn is not None:
        try:
            capture_rows = conn.execute(
                "SELECT title, type FROM notes WHERE created_at >= datetime('now', '-7 days') ORDER BY created_at DESC"
            ).fetchall()
            if capture_rows:
                captures = "\n".join(f"- {r[0]} ({r[1]})" for r in capture_rows)
        except Exception:
            pass

    # 2. Open actions
    open_actions = "No open actions."
    if conn is not None:
        try:
            action_rows = conn.execute(
                "SELECT action_text, due_date FROM action_items WHERE status='open' ORDER BY due_date ASC NULLS LAST LIMIT 20"
            ).fetchall()
            if action_rows:
                open_actions = "\n".join(
                    f"- {r[0]}" + (f" (due: {r[1]})" if r[1] else "") for r in action_rows
                )
        except Exception:
            pass

    # 3. Stale notes
    stale_notes = "No stale notes."
    if conn is not None:
        try:
            stale_rows = get_stale_notes(conn)
            if stale_rows:
                stale_notes = "\n".join(f"- {r.get('title', r.get('path', '?'))}" for r in stale_rows)
        except Exception:
            pass

    # 4. Key themes via AI (best-effort; PII-aware)
    key_themes = "Key Themes unavailable."
    if conn is not None:
        try:
            body_rows = conn.execute(
                "SELECT body, sensitivity FROM notes WHERE created_at >= datetime('now', '-7 days')"
            ).fetchall()
            pii_texts = [r[0][:500] for r in body_rows if r[1] == "pii"]
            public_texts = [r[0][:500] for r in body_rows if r[1] != "pii"]

            summaries = []
            if pii_texts:
                adapter = _router.get_adapter("pii", CONFIG_PATH)
                summaries.append(adapter.generate(
                    user_content="\n\n".join(pii_texts),
                    system_prompt=DIGEST_SYSTEM_PROMPT,
                ))
            if public_texts:
                adapter = _router.get_adapter("public", CONFIG_PATH)
                summaries.append(adapter.generate(
                    user_content="\n\n".join(public_texts),
                    system_prompt=DIGEST_SYSTEM_PROMPT,
                ))
            if summaries:
                key_themes = "\n\n".join(summaries)
        except Exception:
            pass  # best-effort; key_themes stays as fallback

    body = _render_digest_body(key_themes, open_actions, stale_notes, captures)
    post = fm.Post(
        content=body,
        title=f"Weekly Digest {filename[:-3]}",
        date=datetime.date.today().isoformat(),
        type="digest",
    )
    out_path.write_text(fm.dumps(post), encoding="utf-8")
    return out_path


def digest_main(argv=None) -> None:
    """CLI entry point for sb-digest."""
    from engine.db import get_connection, init_schema
    from engine.paths import BRAIN_ROOT

    conn = get_connection()
    init_schema(conn)
    digests_dir = BRAIN_ROOT / ".meta" / "digests"
    out_path = generate_digest(conn, digests_dir)
    print(f"Digest written: {out_path}")
    conn.close()
