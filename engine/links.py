"""Backlink maintenance and orphan checker (PEOPLE-03, PEOPLE-04, SEARCH-03)."""
from pathlib import Path
import sqlite3
import datetime


def add_backlinks(
    note_path: Path,
    people: list[str],
    brain_root: Path,
    conn: sqlite3.Connection,
) -> None:
    """Append backlink to each person's profile and record in relationships table.

    - Normalizes person slug: strip, lowercase, spaces -> hyphens
    - Searches brain_root/people/ with glob *{slug}*.md (handles date-prefixed files)
    - Appends backlink only if not already present (idempotent)
    - Inserts relationships row with INSERT OR IGNORE (idempotent)
    - Never raises — missing person file is silently skipped
    """
    for person_raw in people:
        slug = person_raw.strip().lower().replace(" ", "-")
        matches = list((brain_root / "people").glob(f"*{slug}*.md"))
        if not matches:
            continue
        person_file = matches[0]
        text = person_file.read_text(encoding="utf-8")
        backlink = f"\n- [[{note_path}]]"
        if str(note_path) not in text:
            person_file.write_text(text + backlink, encoding="utf-8")
        try:
            conn.execute(
                "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type, created_at)"
                " VALUES (?, ?, ?, ?)",
                (str(person_file), str(note_path), "backlink",
                 datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")),
            )
            conn.commit()
        except Exception:
            pass  # relationship is best-effort; never blocks capture


def check_links(brain_root: Path, conn: sqlite3.Connection) -> list[dict]:
    """Return list of orphan dicts {source, target, issue} from relationships table."""
    orphans = []
    rows = conn.execute(
        "SELECT source_path, target_path, rel_type FROM relationships"
    ).fetchall()
    for source_str, target_str, rel_type in rows:
        source = Path(source_str)
        target = Path(target_str)
        if not source.exists():
            orphans.append({"source": source_str, "target": target_str, "issue": "source missing"})
            continue
        if not target.exists():
            orphans.append({"source": source_str, "target": target_str, "issue": "target missing"})
            continue
        if rel_type == "backlink":
            target_text = target.read_text(encoding="utf-8")
            if source_str not in target_text and source.stem not in target_text:
                orphans.append({
                    "source": source_str, "target": target_str,
                    "issue": "target does not reference source"
                })
    return orphans


def main_check_links() -> None:
    """CLI entry point for sb-check-links."""
    from engine.db import get_connection, init_schema
    from engine.paths import BRAIN_ROOT
    conn = get_connection()
    init_schema(conn)
    orphans = check_links(BRAIN_ROOT, conn)
    conn.close()
    if not orphans:
        print("No orphaned links found.")
        return
    print(f"Found {len(orphans)} orphaned link(s):")
    for o in orphans:
        print(f"  {o['source']} -> {o['target']}: {o['issue']}")
