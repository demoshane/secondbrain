from pathlib import Path
import sqlite3
import datetime


def forget_person(slug: str, brain_root: Path, conn: sqlite3.Connection) -> dict:
    """Erase all traces of a person from brain and index. GDPR-01, GDPR-02.

    Deletion order (FK-safe):
    1. Parse meetings to classify sole-reference vs. shared.
    2. Clean backlinks from surviving notes.
    3. Delete sole-reference meeting files from disk.
    4. Delete person file from disk.
    5. DELETE FROM notes using exact paths.
    6. DELETE FROM relationships using exact paths.
    7. DELETE FROM audit_log using exact paths.
    8. FTS5 explicit rebuild (GDPR-02).
    9. Commit + log the erasure event itself.

    Error messages: type(e).__name__ only — no file content (GDPR-05).
    """
    import frontmatter  # deferred: available as python-frontmatter dep
    brain_root = brain_root.resolve()  # canonicalize — symlink-safe (Phase 7 pattern)

    person_file = brain_root / "people" / f"{slug}.md"
    deleted_files: list[str] = []
    cleaned_backlinks: list[str] = []
    errors: list[str] = []

    # --- 1. Classify meeting files ---
    meetings_dir = brain_root / "meetings"
    sole_ref_meetings: list[Path] = []
    if meetings_dir.exists():
        for md in meetings_dir.glob("*.md"):
            try:
                post = frontmatter.load(str(md))
                people = post.get("people", [])
                if not isinstance(people, list):
                    people = []
                remaining = [
                    p for p in people
                    if str(p).strip().lower().replace(" ", "-") != slug
                ]
                if len(people) > 0 and len(remaining) == 0:
                    sole_ref_meetings.append(md)
            except Exception as e:
                errors.append(f"Could not parse {md.name}: {type(e).__name__}")

    # Build exact path strings for DB operations
    person_path = str(brain_root / "people" / f"{slug}.md")
    sole_ref_paths = [str(p) for p in sole_ref_meetings]
    exact_delete_paths = [person_path] + sole_ref_paths

    # --- 2. Clean backlink lines from surviving notes ---
    for md in brain_root.rglob("*.md"):
        if md == person_file or md in sole_ref_meetings:
            continue
        try:
            text = md.read_text(encoding="utf-8")
            if slug in text:
                new_lines = [line for line in text.splitlines() if slug not in line]
                md.write_text("\n".join(new_lines), encoding="utf-8")
                cleaned_backlinks.append(str(md))
        except Exception as e:
            errors.append(f"Could not clean {md.name}: {type(e).__name__}")

    # --- 3. Delete sole-reference meeting files ---
    for md in sole_ref_meetings:
        try:
            md.unlink()
            deleted_files.append(str(md))
        except Exception as e:
            errors.append(f"Could not delete {md.name}: {type(e).__name__}")

    # --- 4. Delete person file ---
    if person_file.exists():
        try:
            person_file.unlink()
            deleted_files.append(person_path)
        except Exception as e:
            errors.append(f"Could not delete person file: {type(e).__name__}")

    # --- 5. DELETE FROM notes using exact paths (Pitfall 5: no LIKE patterns) ---
    if exact_delete_paths:
        placeholders = ",".join("?" * len(exact_delete_paths))
        conn.execute(
            f"DELETE FROM notes WHERE path IN ({placeholders})",
            exact_delete_paths,
        )

    # --- 6. DELETE FROM relationships using exact paths ---
    if exact_delete_paths:
        placeholders = ",".join("?" * len(exact_delete_paths))
        conn.execute(
            f"DELETE FROM relationships WHERE source_path IN ({placeholders}) OR target_path IN ({placeholders})",
            exact_delete_paths + exact_delete_paths,
        )

    # --- 7. DELETE FROM audit_log for the erased paths only ---
    if exact_delete_paths:
        placeholders = ",".join("?" * len(exact_delete_paths))
        conn.execute(
            f"DELETE FROM audit_log WHERE note_path IN ({placeholders})",
            exact_delete_paths,
        )

    # --- 8. FTS5 explicit rebuild (GDPR-02) — flush shadow table tombstones ---
    conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")
    conn.commit()

    # --- 9. Log the erasure event (note_path=NULL so it is never self-deleted) ---
    conn.execute(
        "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?, ?, ?, ?)",
        (
            "forget",
            None,
            f"person:{slug}",
            datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        ),
    )
    conn.commit()

    return {
        "deleted_files": deleted_files,
        "cleaned_backlinks": cleaned_backlinks,
        "errors": errors,
    }


def main() -> None:
    """CLI entry point for sb-forget."""
    import argparse
    from engine.db import get_connection, init_schema
    from engine.paths import BRAIN_ROOT

    parser = argparse.ArgumentParser(
        description="Erase all traces of a person (GDPR right to erasure)"
    )
    parser.add_argument(
        "person",
        help="Person slug (e.g. 'alice-smith') or name (e.g. 'Alice Smith')",
    )
    args = parser.parse_args()

    slug = args.person.strip().lower().replace(" ", "-")

    conn = get_connection()
    init_schema(conn)
    result = forget_person(slug, BRAIN_ROOT, conn)
    conn.close()

    print(f"Deleted {len(result['deleted_files'])} file(s):")
    for f in result["deleted_files"]:
        print(f"  - {f}")
    print(f"Cleaned backlinks in {len(result['cleaned_backlinks'])} note(s).")
    if result["errors"]:
        print(f"Errors ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"  ! {e}")
    print("FTS5 index rebuilt. Erasure complete.")
