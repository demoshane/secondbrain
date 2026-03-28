"""Capture pipeline: atomic two-phase write, frontmatter, DB indexing, audit log."""
import datetime
import json
import os
import sqlite3
import tempfile
from pathlib import Path

import frontmatter

from engine.paths import store_path as _store_path

# Maps CLI --type value to brain subdirectory name where types differ
TYPE_TO_DIR: dict[str, str] = {
    "idea": "ideas",
    "link": "links",
}

def _suggest_note_type_from_title(title: str) -> str | None:
    """Suggest a note type based on title heuristics. Returns None if confidence is low.

    Uses classify_note_type with title-only input.  Requires confidence >= 0.80
    (higher bar than the general threshold because no body context is available).

    Returns:
        note_type string if confident, or None if type is unclear.
    """
    from engine.typeclassifier import classify_note_type
    note_type, confidence = classify_note_type(title, "")
    if note_type == "note" or confidence < 0.80:
        return None
    return note_type


def _embed_texts_for_dedup(texts: list[str]) -> list:
    """Thin wrapper around embed_texts for monkeypatching in tests."""
    from engine.embeddings import embed_texts
    return embed_texts(texts)


def check_capture_dedup(
    title: str, body: str, conn: sqlite3.Connection, threshold: float = 0.92,
    max_body_len: int = 2000,
) -> list[dict]:
    """Return similar notes if embedding cosine similarity >= threshold.

    Best-effort: returns [] on any error (model not loaded, extension absent, empty table).
    Never raises. Never blocks capture.

    Args:
        title: Note title to embed.
        body: Note body to embed.
        conn: Open SQLite connection with note_embeddings table.
        threshold: Minimum similarity to report (0.0-1.0). Default 0.92 is intentionally
                   higher than find_similar()'s 0.8 to avoid false positives at capture time.
        max_body_len: If body exceeds this length, embed title only (avoids embedding
                      thousands of tokens for large inputs). Default 2000.

    Returns:
        List of {"path": str, "similarity": float} dicts, most similar first.
        Empty list if no matches or if embeddings unavailable.
    """
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

    def _run_dedup():
        text_to_embed = title if len(body) > max_body_len else f"{title}\n{body}"
        blobs = _embed_texts_for_dedup([text_to_embed])
        if not blobs:
            return []
        query_blob = blobs[0]
        rows = conn.execute(
            """
            SELECT ne.note_path, (1.0 - vec_distance_cosine(ne.embedding, ?)) AS similarity
            FROM note_embeddings ne
            WHERE similarity >= ?
            ORDER BY similarity DESC
            LIMIT 5
            """,
            (query_blob, threshold),
        ).fetchall()
        return [{"path": row[0], "similarity": row[1]} for row in rows]

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_run_dedup)
            return future.result(timeout=8)
    except (FuturesTimeout, Exception):
        return []


def build_post(
    note_type: str,
    title: str,
    body: str,
    tags: list,
    people: list,
    content_sensitivity: str = "public",
    importance: str = "medium",
) -> frontmatter.Post:
    """Build a frontmatter.Post with all 8 required fields.

    Args:
        note_type: The type of note (e.g. 'meeting', 'note').
        title: Note title.
        body: Note body content.
        tags: List of tag strings.
        people: List of people strings.
        content_sensitivity: Sensitivity level ('public', 'internal', 'confidential').

    Returns:
        frontmatter.Post with metadata set and body as content.
    """
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.date.today().isoformat()

    post = frontmatter.Post(body)
    post["type"] = note_type
    post["title"] = title
    post["date"] = today
    post["tags"] = list(tags)
    post["people"] = list(people)
    post["created_at"] = now
    post["updated_at"] = now
    post["content_sensitivity"] = content_sensitivity
    post["importance"] = importance
    if note_type in ("projects", "project"):
        post["deadline"] = None
    if note_type in ("meeting", "meetings"):
        post["meeting_date"] = today
    return post


def log_audit(conn: sqlite3.Connection, event_type: str, note_path: str) -> None:
    """Insert an audit log entry. Caller is responsible for conn.commit().

    Args:
        conn: Open SQLite connection.
        event_type: Event name (e.g. 'create', 'update').
        note_path: Path of the affected note.
    """
    created_at = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT INTO audit_log (event_type, note_path, created_at) VALUES (?, ?, ?)",
        (event_type, note_path, created_at),
    )


def write_note_atomic(
    target: Path,
    post: frontmatter.Post,
    conn: sqlite3.Connection,
    update: bool = False,
    *,
    url: str | None = None,
) -> None:
    """Write a note file atomically with DB indexing in a single transaction.

    Order of operations:
    1. Create temp file in same directory as target (never /tmp).
    2. Write frontmatter.dumps(post) to temp file.
    3. INSERT (or INSERT OR REPLACE when update=True) into notes + log_audit + conn.commit().
    4. os.replace(tmp, target) — atomic rename.

    On any exception: delete temp file and re-raise.
    Error messages never include post body or metadata values.

    Args:
        target: Final destination path for the note.
        post: frontmatter.Post to serialize.
        conn: Open SQLite connection with schema initialized.
        update: When True, uses INSERT OR REPLACE (upsert) to overwrite existing row.
                When False (default), uses INSERT — preserves backward compatibility.
        url: Optional URL to store in the notes.url column (link captures only).
    """
    tmp_path = None
    tmp_fd = None
    try:
        # Phase 1: write to temp file in same directory (same filesystem = atomic rename)
        tmp_fd, tmp_name = tempfile.mkstemp(dir=target.parent)
        tmp_path = Path(tmp_name)
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(frontmatter.dumps(post))
        tmp_fd = None  # fd is now closed by fdopen context manager

        # Phase 2: index in DB + audit log — commit before rename
        tags_json = json.dumps(post.get("tags", []))
        people_json = json.dumps(post.get("people", []))
        created_at = post.get("created_at", datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
        updated_at = post.get("updated_at", created_at)
        sensitivity = post.get("content_sensitivity", "public")
        deadline = post.get("deadline") or None
        meeting_date = post.get("meeting_date") or None
        importance = post.get("importance", "medium")

        # ARCH-01: store relative path in DB for portability.
        # Fall back to absolute resolved path if target is outside BRAIN_ROOT
        # (e.g. test fixtures that write outside brain directory).
        try:
            resolved_path = _store_path(target.resolve())
        except ValueError:
            resolved_path = str(target.resolve())
        sql_verb = "INSERT OR REPLACE" if update else "INSERT"
        conn.execute(
            f"{sql_verb} INTO notes"
            " (path, type, title, body, tags, people, created_at, updated_at, sensitivity, url, deadline, meeting_date, importance)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                resolved_path,
                post.get("type", "note"),
                post.get("title", ""),
                post.content,
                tags_json,
                people_json,
                created_at,
                updated_at,
                sensitivity,
                str(url) if url else None,
                deadline,
                meeting_date,
                importance,
            ),
        )
        log_audit(conn, "update" if update else "create", resolved_path)
        # Store entities in DB column if present in post (best-effort)
        entities_val = post.get("entities")
        if entities_val is not None:
            conn.execute(
                "UPDATE notes SET entities = ? WHERE path = ?",
                (json.dumps(entities_val), resolved_path),
            )
        # ARCH-05/15: Dual-write to junction tables (note_tags, note_people) in same transaction.
        # Junction tables exist after 32-03 migration — guard with try/except for backward compat.
        try:
            tags_list = post.get("tags", [])
            conn.execute("DELETE FROM note_tags WHERE note_path=?", (resolved_path,))
            for tag in (tags_list or []):
                if tag:
                    conn.execute(
                        "INSERT OR IGNORE INTO note_tags (note_path, tag) VALUES (?, ?)",
                        (resolved_path, tag),
                    )
        except Exception:
            pass  # junction table may not exist on very old schemas
        try:
            people_list = post.get("people", [])
            conn.execute("DELETE FROM note_people WHERE note_path=?", (resolved_path,))
            for person in (people_list or []):
                if person:
                    conn.execute(
                        "INSERT OR IGNORE INTO note_people (note_path, person) VALUES (?, ?)",
                        (resolved_path, person),
                    )
        except Exception:
            pass  # junction table may not exist on very old schemas
        conn.commit()

        # Phase 3: atomic rename — only after DB commit succeeds
        os.replace(tmp_name, target)

    except Exception as e:
        # Clean up temp file on any failure
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        # GDPR-safe: never include post body or metadata values in error message
        raise RuntimeError(f"Failed to write {target}: {type(e).__name__}") from e


def update_note(
    note_path: str,
    title: str,
    body: str,
    tags: list,
    conn: sqlite3.Connection,
    brain_root: Path,
) -> dict:
    """Update an existing note's title, body, tags, and updated_at atomically.

    Reads the existing frontmatter, patches only the changed fields, writes back
    using the same atomic tempfile + os.replace pattern as write_note_atomic, and
    updates the DB record in the same operation.

    Args:
        note_path: Absolute path string to the existing note file.
        title: New title value.
        body: New body content.
        tags: New tags list.
        conn: Open SQLite connection.
        brain_root: Brain root Path (used only to verify the path is inside the brain).

    Returns:
        {"status": "updated", "path": note_path}
    """
    target = Path(note_path)
    post = frontmatter.load(str(target))
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    post["title"] = title
    post["updated_at"] = now
    post["tags"] = list(tags)
    post.content = body

    # ARCH-01: normalize to relative path for DB write boundary
    try:
        db_path = _store_path(target.resolve())
    except ValueError:
        db_path = note_path  # outside BRAIN_ROOT — keep as-is for backward compat

    tmp_path = None
    tmp_fd = None
    try:
        tmp_fd, tmp_name = tempfile.mkstemp(dir=target.parent)
        tmp_path = Path(tmp_name)
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(frontmatter.dumps(post))
        tmp_fd = None

        tags_json = json.dumps(list(tags))
        conn.execute(
            "UPDATE notes SET title=?, body=?, tags=?, updated_at=? WHERE path=?",
            (title, body, tags_json, now, db_path),
        )
        log_audit(conn, "update", db_path)
        # ARCH-05/15: Dual-write tags to note_tags junction table in same transaction.
        try:
            conn.execute("DELETE FROM note_tags WHERE note_path=?", (db_path,))
            for tag in (tags or []):
                if tag:
                    conn.execute(
                        "INSERT OR IGNORE INTO note_tags (note_path, tag) VALUES (?, ?)",
                        (db_path, tag),
                    )
        except Exception:
            pass  # junction table may not exist on very old schemas
        # ARCH-13: Re-extract entities on edit, merge with existing people
        try:
            from engine.entities import extract_entities
            ents = extract_entities(title, body)
            extracted_people = ents.get("people", [])
            # Get existing people from DB or frontmatter
            existing_row = conn.execute("SELECT people FROM notes WHERE path=?", (db_path,)).fetchone()
            existing_people = json.loads(existing_row[0] or "[]") if existing_row else []
            merged_people = list(dict.fromkeys(
                [str(p) for p in existing_people] + extracted_people
            ))
            conn.execute(
                "UPDATE notes SET people=?, entities=? WHERE path=?",
                (json.dumps(merged_people), json.dumps(ents), db_path),
            )
            # Refresh note_people junction table
            conn.execute("DELETE FROM note_people WHERE note_path=?", (db_path,))
            for person in merged_people:
                conn.execute(
                    "INSERT OR IGNORE INTO note_people (note_path, person) VALUES (?, ?)",
                    (db_path, person),
                )
        except Exception:
            pass  # entity extraction is best-effort
        conn.commit()

        os.replace(tmp_name, target)
    except Exception as e:
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise RuntimeError(f"Failed to update {target}: {type(e).__name__}") from e

    return {"status": "updated", "path": note_path}


def main(argv=None) -> None:
    """CLI entry point for sb-capture."""
    import argparse
    from engine.db import get_connection, init_schema, migrate_add_people_column, migrate_add_entities_column

    parser = argparse.ArgumentParser(description="Capture a note into the second brain")
    parser.add_argument(
        "--type",
        required=True,
        choices=["note", "meeting", "person", "coding", "strategy", "idea", "projects", "personal"],
        dest="note_type",
    )
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", default="")
    parser.add_argument("--tags", default="")
    parser.add_argument("--people", default="")
    parser.add_argument(
        "--sensitivity",
        default="public",
        choices=["public", "private", "pii"],
    )
    args = parser.parse_args(argv)

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    people = [p.strip() for p in args.people.split(",") if p.strip()]

    from engine.paths import BRAIN_ROOT, CONFIG_PATH
    from engine.ai import ask_followup_questions
    from engine.classifier import classify

    # Classify sensitivity (runs locally, no network — AI-02)
    sensitivity = classify(args.sensitivity, args.body)

    # Use classifier result as the actual sensitivity (may have been upgraded by keyword scan)
    args.sensitivity = sensitivity

    conn = get_connection()
    init_schema(conn)
    migrate_add_people_column(conn)
    migrate_add_entities_column(conn)

    # AI-01: Ask 2-3 follow-up questions (best-effort, never blocks capture)
    try:
        questions = ask_followup_questions(args.note_type, args.title, sensitivity, CONFIG_PATH, conn)
        if questions:
            print("\nFollow-up questions to enrich your note:")
            enrichment_answers = []
            for i, q in enumerate(questions, 1):
                print(f"  {i}. {q}")
                answer = input(f"     Answer (or press Enter to skip): ").strip()
                if answer:
                    enrichment_answers.append(f"**{q}**\n{answer}")
            if enrichment_answers:
                args.body = args.body + "\n\n" + "\n\n".join(enrichment_answers)
    except Exception as e:
        print(f"[AI enrichment skipped: {type(e).__name__}]")

    path = capture_note(args.note_type, args.title, args.body, tags, people, args.sensitivity, BRAIN_ROOT, conn)
    conn.close()
    # CAP-06: best-effort memory update — outside transaction, never blocks capture
    if sensitivity != "pii":
        try:
            from engine.ai import update_memory
            update_memory(args.note_type, f"{args.note_type} note: {args.title}", CONFIG_PATH)
        except Exception as e:
            print(f"[sb-capture] Memory update skipped: {type(e).__name__}")
    print(str(path))


def capture_note(
    note_type: str,
    title: str,
    body: str,
    tags: list,
    people: list,
    content_sensitivity: str,
    brain_root: Path,
    conn: sqlite3.Connection,
    *,
    url: str | None = None,
    source_type: str | None = None,
    importance: str = "medium",
) -> Path:
    """Build and atomically write a note, returning its final path.

    Args:
        note_type: Note type subfolder name (e.g. 'meetings').
        title: Note title.
        body: Note body content.
        tags: List of tag strings.
        people: List of people strings.
        content_sensitivity: Sensitivity level.
        brain_root: Root path of the brain directory.
        conn: Open SQLite connection.
        url: Optional URL for link captures — written into frontmatter and DB.
        source_type: Optional source type (e.g. 'article', 'video') — written into frontmatter.

    Returns:
        Path to the written note file.
    """
    if note_type == "person":
        slug = title[:40].replace(" ", "-").lower()
    else:
        slug = datetime.date.today().isoformat() + "-" + title[:40].replace(" ", "-").lower()
    subdir = TYPE_TO_DIR.get(note_type, note_type)
    target = brain_root / subdir / f"{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    # Resolve slug collisions: if path exists on disk or in DB, append -2, -3, …
    # ARCH-01: check both relative path (new) and absolute path (backward compat) in DB
    counter = 2
    while True:
        if target.exists():
            target = brain_root / subdir / f"{slug}-{counter}.md"
            counter += 1
            continue
        abs_str = str(target.resolve())
        try:
            rel_str = _store_path(target.resolve())
        except ValueError:
            rel_str = abs_str
        if conn.execute(
            "SELECT 1 FROM notes WHERE path=? OR path=?", (rel_str, abs_str)
        ).fetchone():
            target = brain_root / subdir / f"{slug}-{counter}.md"
            counter += 1
            continue
        break

    # Entity enrichment: best-effort, never blocks capture.
    # CRITICAL ORDER: extract BEFORE build_post so merged_people is written into
    # the people frontmatter field and the DB people column (PEO-02 write-back).
    try:
        from engine.entities import extract_entities
        entities = extract_entities(title, body)
    except Exception:
        entities = {"people": [], "places": [], "topics": [], "orgs": []}

    # Merge caller-supplied people with extracted people (caller first, dedup preserve order)
    extracted_people = entities.get("people", [])
    merged_people = list(dict.fromkeys(people + extracted_people))

    post = build_post(note_type, title, body, tags, merged_people, content_sensitivity, importance=importance)
    if url:
        post["url"] = url
    if source_type:
        post["source_type"] = source_type
    post["entities"] = entities
    write_note_atomic(target, post, conn, url=url)

    # Auto-backlink: update referenced people's profiles
    if merged_people:
        from engine.links import add_backlinks
        add_backlinks(target, merged_people, brain_root, conn)

    # Wiki-link relationships: parse [[...]] links from body
    # ARCH-01: use relative path for DB storage
    from engine.links import update_wiki_link_relationships
    try:
        _wiki_source = _store_path(target.resolve())
    except ValueError:
        _wiki_source = str(target.resolve())
    update_wiki_link_relationships(conn, _wiki_source, body)

    # Phase 15: best-effort intelligence hooks — run in background, never block capture
    import threading
    _target_str = str(target)
    _body = body
    _sensitivity = content_sensitivity
    _brain_root = brain_root

    def _run_intelligence_hooks():
        try:
            from engine.db import get_connection as _get_conn
            from engine.intelligence import check_connections, extract_action_items
            # check_connections is fast — short-lived connection, closed before AI work
            _conn = _get_conn()
            try:
                check_connections(Path(_target_str), _conn, _brain_root)
                _conn.commit()
            finally:
                _conn.close()
        except Exception:
            pass
        try:
            from engine.db import get_connection as _get_conn
            from engine.intelligence import extract_action_items
            # extract_action_items runs claude -p (slow) then writes — fresh conn
            # so the AI wait doesn't hold an open connection blocking concurrent captures
            _conn2 = _get_conn()
            try:
                extract_action_items(Path(_target_str), _body, _sensitivity, _conn2)
            finally:
                _conn2.close()
        except Exception:
            pass

    threading.Thread(target=_run_intelligence_hooks, daemon=True).start()

    return target
