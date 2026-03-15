"""GDPR runtime anonymization — replace PII tokens in note body.

Non-destructive to git history. For full erasure use sb-forget.
GDPR Article 17 partial anonymization: identifying tokens are scrubbed from
the live file and DB row, but the note structure survives.

Note: does NOT remove original content from git history. Use sb-forget for
full erasure.
"""
import datetime
import os
import re
import sqlite3
import tempfile
from pathlib import Path

import frontmatter


def anonymize_note(
    path: Path,
    tokens: list[str],
    conn: sqlite3.Connection,
    downgrade_sensitivity: bool = False,
) -> dict:
    """Replace tokens with [REDACTED] in note body and title.

    Performs case-insensitive substring replacement using re.escape() to handle
    email addresses, hyphens and other regex metacharacters in token strings.

    Atomic write: tempfile in path.parent (same filesystem) + os.replace.
    FTS5 is updated automatically by the notes_au trigger on UPDATE notes.

    Args:
        path: Path to the note file.
        tokens: List of strings to replace with [REDACTED].
        conn: SQLite connection with notes and audit_log tables.
        downgrade_sensitivity: If True and current sensitivity=='pii', change to 'private'.

    Returns:
        dict with keys:
            redacted_count (int): total occurrences replaced across all tokens.
            sensitivity_changed (bool): True if sensitivity was downgraded.
            errors (list[str]): type(e).__name__ for any exceptions (GDPR-05).
    """
    path = path.resolve()
    errors: list[str] = []

    if not path.exists():
        return {
            "redacted_count": 0,
            "sensitivity_changed": False,
            "errors": [f"File not found: {path.name}"],
        }

    try:
        post = frontmatter.load(str(path))
    except Exception as e:
        return {"redacted_count": 0, "sensitivity_changed": False, "errors": [type(e).__name__]}

    body = post.content
    title = post.get("title", "")
    redacted_count = 0

    for token in tokens:
        if not token:
            continue
        pattern = re.escape(token)
        new_body = re.sub(pattern, "[REDACTED]", body, flags=re.IGNORECASE)
        new_title = re.sub(pattern, "[REDACTED]", title, flags=re.IGNORECASE)
        # Count occurrences replaced in body (case-insensitive)
        redacted_count += len(re.findall(pattern, body, flags=re.IGNORECASE))
        body = new_body
        title = new_title

    sensitivity_changed = False
    sensitivity = post.get("content_sensitivity", "public")
    if downgrade_sensitivity and sensitivity == "pii":
        sensitivity = "private"
        sensitivity_changed = True

    post.content = body
    post["title"] = title
    post["content_sensitivity"] = sensitivity
    post["updated_at"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Atomic write — mkstemp in path.parent ensures same filesystem (POSIX atomic)
    tmp_fd = None
    tmp_path_obj = None
    try:
        tmp_fd, tmp_name = tempfile.mkstemp(dir=path.parent)
        tmp_path_obj = Path(tmp_name)
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(frontmatter.dumps(post))
        tmp_fd = None  # fdopen took ownership; already closed by context manager
        os.replace(tmp_name, path)
    except Exception as e:
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if tmp_path_obj is not None and tmp_path_obj.exists():
            try:
                tmp_path_obj.unlink()
            except OSError:
                pass
        errors.append(type(e).__name__)
        return {"redacted_count": redacted_count, "sensitivity_changed": False, "errors": errors}

    # Update DB row — FTS5 updated automatically by notes_au trigger on UPDATE
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        conn.execute(
            "UPDATE notes SET body=?, title=?, sensitivity=?, updated_at=? WHERE path=?",
            (body, title, sensitivity, now, str(path)),
        )
        conn.execute(
            "INSERT INTO audit_log (event_type, note_path, detail, created_at)"
            " VALUES (?, ?, ?, ?)",
            ("anonymize", str(path), f"tokens:{len(tokens)}", now),
        )
        conn.commit()
    except Exception as e:
        errors.append(type(e).__name__)

    return {
        "redacted_count": redacted_count,
        "sensitivity_changed": sensitivity_changed,
        "errors": errors,
    }


def main() -> None:
    """CLI entry point for sb-anonymize (GDPR Article 17 partial anonymization)."""
    import argparse
    from engine.db import get_connection, init_schema
    from engine.paths import BRAIN_ROOT

    parser = argparse.ArgumentParser(
        description="Replace PII tokens in a note with [REDACTED] (GDPR Article 17)"
    )
    parser.add_argument("path", help="Relative or absolute path to the note file")
    parser.add_argument(
        "tokens",
        nargs="+",
        help="Token strings to redact (e.g. 'John Doe' 'john.doe@company.com')",
    )
    parser.add_argument(
        "--downgrade-sensitivity",
        action="store_true",
        default=False,
        help="If note sensitivity is 'pii', downgrade to 'private' after redaction",
    )
    args = parser.parse_args()

    note_path = Path(args.path)
    if not note_path.is_absolute():
        note_path = BRAIN_ROOT / note_path

    conn = get_connection()
    init_schema(conn)
    result = anonymize_note(note_path, args.tokens, conn, args.downgrade_sensitivity)
    conn.close()

    print(f"Redacted {result['redacted_count']} occurrence(s).")
    if result["sensitivity_changed"]:
        print("Sensitivity downgraded: pii -> private.")
    if result["errors"]:
        print(f"Errors ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"  ! {e}")
