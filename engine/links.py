"""Backlink maintenance and orphan checker (PEOPLE-03, PEOPLE-04, SEARCH-03)."""
from pathlib import Path
import re
import sqlite3
from engine.db import _now_utc

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
        now = _now_utc()
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
    # Canonical subdirectory is "person/" — confirmed by BRAIN_SUBDIRS in engine/paths.py (F-30).
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
    now = _now_utc()
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

    People entries can be:
    - Name strings: "Eino Kiiski" → slugified to find/create profile
    - Relative paths: "person/eino-kiiski.md" → resolved directly against brain_root

    - Appends backlink only if not already present (idempotent)
    - Inserts relationships row with INSERT OR IGNORE using relative DB paths (idempotent)
    - Never raises — DB errors are silently swallowed (best-effort)
    """
    from engine.paths import store_path as _store_path

    # Resolve note_path to relative DB path for relationship storage
    try:
        note_db_path = _store_path(note_path.resolve())
    except ValueError:
        note_db_path = str(note_path)

    for person_raw in people:
        person_raw = person_raw.strip()
        # Detect path-format entries (contain / or end with .md)
        if "/" in person_raw or person_raw.endswith(".md"):
            person_file = brain_root / person_raw
            if not person_file.exists():
                # Path doesn't exist — fall back to slug-based resolution
                slug = Path(person_raw).stem.lower().replace(" ", "-")
                person_file = ensure_person_profile(slug, brain_root, conn)
        else:
            slug = person_raw.lower().replace(" ", "-")
            person_file = ensure_person_profile(slug, brain_root, conn)

        # Use relative paths for DB relationship storage
        try:
            person_db_path = _store_path(person_file.resolve())
        except ValueError:
            person_db_path = str(person_file)

        # Skip self-referencing backlinks (person note mentioning itself)
        if person_db_path == note_db_path:
            continue

        text = person_file.read_text(encoding="utf-8")
        # Use relative path for on-disk wiki-links (portable, consistent with DB)
        backlink = f"\n- [[{note_db_path}]]"
        if note_db_path not in text and str(note_path) not in text:
            person_file.write_text(text + backlink, encoding="utf-8")

        try:
            conn.execute(
                "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type, created_at)"
                " VALUES (?, ?, ?, ?)",
                (person_db_path, note_db_path, "backlink", _now_utc()),
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
        # DB stores relative paths — resolve against brain_root for disk access
        source = brain_root / source_str
        target = brain_root / target_str
        if not source.exists():
            orphans.append({"source": source_str, "target": target_str, "issue": "source missing"})
            continue
        if not target.exists():
            orphans.append({"source": source_str, "target": target_str, "issue": "target missing"})
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
