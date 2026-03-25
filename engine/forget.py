import datetime
import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def forget_person(slug: str, brain_root: Path, conn: sqlite3.Connection) -> dict:
    """Erase all traces of a person from brain and index. GDPR-01, GDPR-02.

    ARCH-08 order: DB first, files second.
    1. Classify meetings (sole-reference vs shared).
    2. DB transaction: DELETE notes, clean people JSON in surviving notes.
    3. COMMIT.
    4. Delete files from disk (after DB commit).
    5. Clean frontmatter people field in surviving note files on disk.
    6. FTS5 rebuild + audit log.

    Error messages: type(e).__name__ only — no file content (GDPR-05).
    """
    import frontmatter  # deferred: available as python-frontmatter dep
    brain_root = brain_root.resolve()

    # Check both new "person/" and legacy "people/" directories
    person_file = brain_root / "person" / f"{slug}.md"
    if not person_file.exists():
        person_file = brain_root / "people" / f"{slug}.md"
    deleted_files: list[str] = []
    cleaned_backlinks: list[str] = []
    cleaned_people_fields: list[str] = []
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
    person_path = str(person_file)
    sole_ref_paths = [str(p) for p in sole_ref_meetings]
    exact_delete_paths = [person_path] + sole_ref_paths

    # Also build relative paths for DB lookups (ARCH-01 compat)
    from engine.paths import store_path
    relative_delete_paths = []
    for p in exact_delete_paths:
        try:
            relative_delete_paths.append(store_path(p))
        except ValueError:
            relative_delete_paths.append(p)
    all_delete_paths = list(set(exact_delete_paths + relative_delete_paths))

    # --- 2. DB TRANSACTION: delete notes + clean people JSON in surviving notes ---
    # Person name variants for matching in people JSON
    person_title = slug.replace("-", " ").title()
    person_variants = {slug, person_title, person_path}
    for rp in relative_delete_paths:
        person_variants.add(rp)

    # 2a. DELETE FROM notes (FK cascade handles junction tables if enabled)
    if all_delete_paths:
        placeholders = ",".join("?" * len(all_delete_paths))
        conn.execute(
            f"DELETE FROM notes WHERE path IN ({placeholders})",
            all_delete_paths,
        )

    # 2b. DELETE FROM note_embeddings
    if all_delete_paths:
        placeholders = ",".join("?" * len(all_delete_paths))
        conn.execute(
            f"DELETE FROM note_embeddings WHERE note_path IN ({placeholders})",
            all_delete_paths,
        )

    # 2c. DELETE FROM relationships
    if all_delete_paths:
        placeholders = ",".join("?" * len(all_delete_paths))
        conn.execute(
            f"DELETE FROM relationships WHERE source_path IN ({placeholders}) OR target_path IN ({placeholders})",
            all_delete_paths + all_delete_paths,
        )

    # 2d. DELETE FROM audit_log for erased paths
    if all_delete_paths:
        placeholders = ",".join("?" * len(all_delete_paths))
        conn.execute(
            f"DELETE FROM audit_log WHERE note_path IN ({placeholders})",
            all_delete_paths,
        )

    # 2d-bis. NULL assignee_path for all erased person paths
    if all_delete_paths:
        for pth in all_delete_paths:
            conn.execute("UPDATE action_items SET assignee_path=NULL WHERE assignee_path=?", (pth,))

    # 2e. Clean person from people JSON column in surviving notes (ARCH-08 GDPR gap)
    rows = conn.execute("SELECT path, people FROM notes WHERE people IS NOT NULL AND people != '[]'").fetchall()
    for row in rows:
        try:
            people_list = json.loads(row[1] or "[]")
        except (json.JSONDecodeError, TypeError):
            continue
        cleaned = [p for p in people_list if str(p) not in person_variants]
        if len(cleaned) != len(people_list):
            conn.execute(
                "UPDATE notes SET people=? WHERE path=?",
                (json.dumps(cleaned), row[0]),
            )
            # Also clean note_people junction table
            for variant in person_variants:
                conn.execute(
                    "DELETE FROM note_people WHERE note_path=? AND person=?",
                    (row[0], variant),
                )
            cleaned_people_fields.append(row[0])

    # 2f. FTS5 rebuild
    conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")

    # --- 3. COMMIT DB transaction ---
    conn.commit()
    logger.info("forget_person: DB transaction committed for slug=%s", slug)

    # --- 4. Delete files from disk (AFTER DB commit per ARCH-08) ---
    # 4a. Delete sole-reference meeting files
    for md in sole_ref_meetings:
        try:
            md.unlink()
            deleted_files.append(str(md))
        except Exception as e:
            logger.warning("forget_person: could not delete %s: %s", md.name, type(e).__name__)
            errors.append(f"Could not delete {md.name}: {type(e).__name__}")

    # 4b. Delete person file
    if person_file.exists():
        try:
            person_file.unlink()
            deleted_files.append(person_path)
        except Exception as e:
            logger.warning("forget_person: could not delete person file: %s", type(e).__name__)
            errors.append(f"Could not delete person file: {type(e).__name__}")

    # --- 5. Clean frontmatter people field in surviving note files on disk ---
    for md in brain_root.rglob("*.md"):
        if md == person_file or md in sole_ref_meetings:
            continue
        try:
            text = md.read_text(encoding="utf-8")
            if slug not in text:
                continue
            post = frontmatter.load(str(md))
            people = post.get("people", [])
            if isinstance(people, list):
                cleaned = [p for p in people if str(p) not in person_variants]
                if len(cleaned) != len(people):
                    post["people"] = cleaned
                    md.write_text(frontmatter.dumps(post), encoding="utf-8")
                    cleaned_backlinks.append(str(md))
                    continue
            # Also clean backlink lines
            new_lines = [line for line in text.splitlines() if slug not in line]
            if len(new_lines) != len(text.splitlines()):
                md.write_text("\n".join(new_lines), encoding="utf-8")
                cleaned_backlinks.append(str(md))
        except Exception as e:
            logger.warning("forget_person: could not clean %s: %s", md.name, type(e).__name__)
            errors.append(f"Could not clean {md.name}: {type(e).__name__}")

    # --- 6. Log the erasure event (note_path=NULL so it is never self-deleted) ---
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
        "cleaned_people_fields": cleaned_people_fields,
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
    print(f"Cleaned people fields in {len(result['cleaned_people_fields'])} note(s).")
    if result["errors"]:
        print(f"Errors ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"  ! {e}")
    print("FTS5 index rebuilt. Erasure complete.")
