"""Capture pipeline: atomic two-phase write, frontmatter, DB indexing, audit log."""
import datetime
import json
import os
import sqlite3
import tempfile
from pathlib import Path

import frontmatter


def build_post(
    note_type: str,
    title: str,
    body: str,
    tags: list,
    people: list,
    content_sensitivity: str = "public",
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
) -> None:
    """Write a note file atomically with DB indexing in a single transaction.

    Order of operations:
    1. Create temp file in same directory as target (never /tmp).
    2. Write frontmatter.dumps(post) to temp file.
    3. INSERT into notes + log_audit + conn.commit().
    4. os.replace(tmp, target) — atomic rename.

    On any exception: delete temp file and re-raise.
    Error messages never include post body or metadata values.

    Args:
        target: Final destination path for the note.
        post: frontmatter.Post to serialize.
        conn: Open SQLite connection with schema initialized.
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

        conn.execute(
            "INSERT INTO notes (path, type, title, body, tags, people, created_at, updated_at, sensitivity)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(target),
                post.get("type", "note"),
                post.get("title", ""),
                post.content,
                tags_json,
                people_json,
                created_at,
                updated_at,
                sensitivity,
            ),
        )
        log_audit(conn, "create", str(target))
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


def capture_note(
    note_type: str,
    title: str,
    body: str,
    tags: list,
    people: list,
    content_sensitivity: str,
    brain_root: Path,
    conn: sqlite3.Connection,
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

    Returns:
        Path to the written note file.
    """
    slug = datetime.date.today().isoformat() + "-" + title[:40].replace(" ", "-").lower()
    target = brain_root / note_type / f"{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    post = build_post(note_type, title, body, tags, people, content_sensitivity)
    write_note_atomic(target, post, conn)
    return target
