"""Backlink maintenance and orphan checker (PEOPLE-03, PEOPLE-04, SEARCH-03)."""
from pathlib import Path
import re
import sqlite3
import datetime

_WIKI_LINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")


def extract_wiki_links(body: str) -> list[str]:
    """Return list of paths found inside [[...]] patterns in body.

    Handles both absolute paths ([[/path/to/note.md]]) and relative forms.
    Strips leading/trailing whitespace from each match.
    """
    return [m.strip() for m in _WIKI_LINK_RE.findall(body)]


def update_wiki_link_relationships(
    conn: sqlite3.Connection, source_path: str, body: str
) -> None:
    """Parse wiki-links in body and upsert them into relationships table.

    Deletes all existing wiki-link rows for source_path first (clean-before-insert),
    then inserts a row for each target path found in [[...]] patterns.
    Never raises — DB errors are silently swallowed (best-effort).
    """
    try:
        conn.execute(
            "DELETE FROM relationships WHERE source_path = ? AND rel_type = 'wiki-link'",
            (source_path,),
        )
        targets = extract_wiki_links(body)
        now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        for target in targets:
            conn.execute(
                "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type, created_at)"
                " VALUES (?, ?, ?, ?)",
                (source_path, target, "wiki-link", now),
            )
        conn.commit()
    except Exception:
        pass  # best-effort; never blocks capture or reindex


def ensure_person_profile(
    slug: str, brain_root: Path, conn: sqlite3.Connection | None = None
) -> Path:
    """Return path to an existing or newly-created person note for slug.

    Resolution order:
    1. brain_root/person/{slug}.md already exists → return it (idempotent).
    2. conn provided → search DB for any note with type='person' and matching
       title (case-insensitive). If found, return that file's path so backlinks
       land on the canonical note instead of spawning a duplicate skeleton.
    3. No match → create brain_root/person/{slug}.md with full frontmatter
       (type: person) so it is immediately indexed correctly.
    """
    person_file = brain_root / "person" / f"{slug}.md"
    if person_file.exists():
        return person_file

    display_name = slug.replace("-", " ").title()

    if conn is not None:
        try:
            row = conn.execute(
                "SELECT path FROM notes WHERE type='person' AND LOWER(title)=LOWER(?)",
                (display_name,),
            ).fetchone()
            if row:
                return brain_root / row[0]
        except Exception:
            pass  # best-effort; fall through to skeleton creation

    person_file.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    person_file.write_text(
        f"---\ntitle: {display_name}\ntype: person\n"
        f"created_at: '{now}'\nupdated_at: '{now}'\n"
        f"people: []\ntags: []\ncontent_sensitivity: public\n---\n\n",
        encoding="utf-8",
    )
    return person_file


def add_backlinks(
    note_path: Path,
    people: list[str],
    brain_root: Path,
    conn: sqlite3.Connection,
) -> None:
    """Append backlink to each person's profile and record in relationships table.

    - Normalizes person slug: strip, lowercase, spaces -> hyphens
    - Calls ensure_person_profile(slug, brain_root) to get/create the profile
    - Appends backlink only if not already present (idempotent)
    - Inserts relationships row with INSERT OR IGNORE (idempotent)
    - Never raises — DB errors are silently swallowed (best-effort)
    """
    for person_raw in people:
        slug = person_raw.strip().lower().replace(" ", "-")
        person_file = ensure_person_profile(slug, brain_root, conn)
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
