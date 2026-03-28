"""Note rename — title update with optional file rename and full DB cascade."""
from __future__ import annotations

import datetime
import os
import sqlite3
import tempfile
from pathlib import Path

import frontmatter as _fm

from engine.paths import store_path


def _atomic_write(target: Path, post: _fm.Post) -> None:
    """Write frontmatter post atomically to target via temp-file swap."""
    with tempfile.NamedTemporaryFile(
        "w", dir=target.parent, delete=False, suffix=".tmp", encoding="utf-8"
    ) as f:
        f.write(_fm.dumps(post))
        tmp = f.name
    try:
        os.replace(tmp, target)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def _rewrite_wiki_links(
    file_path: Path, old_abs: Path, new_abs: Path, brain_root: Path
) -> bool:
    """Replace [[old_path]] references with [[new_path]] in file_path.

    Handles both absolute-path form (as written by add_backlinks) and
    relative-path form. Returns True if the file was modified.
    """
    text = file_path.read_text(encoding="utf-8")
    old_abs_str = str(old_abs)
    new_abs_str = str(new_abs)
    try:
        old_rel_str = str(old_abs.relative_to(brain_root))
        new_rel_str = str(new_abs.relative_to(brain_root))
    except ValueError:
        old_rel_str = old_abs_str
        new_rel_str = new_abs_str

    new_text = text.replace(f"[[{old_abs_str}]]", f"[[{new_abs_str}]]")
    new_text = new_text.replace(f"[[{old_rel_str}]]", f"[[{new_rel_str}]]")

    if new_text == text:
        return False

    with tempfile.NamedTemporaryFile(
        "w", dir=file_path.parent, delete=False, suffix=".tmp", encoding="utf-8"
    ) as f:
        f.write(new_text)
        tmp = f.name
    try:
        os.replace(tmp, file_path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise
    return True


def rename_note(
    old_abs: Path,
    new_title: str,
    brain_root: Path,
    conn: sqlite3.Connection,
) -> dict:
    """Rename a note's title.

    Strategy by note type:
    - **Non-person notes**: update frontmatter title + DB title only. The
      filename (date-prefixed slug) is unchanged — all path-based connections
      remain intact automatically.
    - **Person notes**: also rename the file (slug derived from new title),
      then cascade the path change across all 7 referencing DB tables, and
      rewrite [[wiki-link]] text in every other note (handles both absolute-
      and relative-path forms).

    Returns:
        {
            "new_path": str,          # absolute path of the (possibly renamed) file
            "renamed_file": bool,     # True if the file was physically renamed
            "wiki_links_updated": int # number of notes whose body was rewritten
        }

    Raises:
        ValueError: if old_abs does not exist or new_title is blank.
    """
    if not old_abs.exists():
        raise ValueError(f"NOTE_NOT_FOUND: {old_abs!r}")

    new_title = new_title.strip()
    if not new_title:
        raise ValueError("TITLE_EMPTY: title must not be blank")

    post = _fm.load(str(old_abs))
    old_title = post.metadata.get("title", old_abs.stem)
    note_type = post.metadata.get("type", "note")
    now = datetime.datetime.utcnow().isoformat()

    if new_title == old_title:
        return {"new_path": str(old_abs), "renamed_file": False, "wiki_links_updated": 0}

    post.metadata["title"] = new_title

    # ------------------------------------------------------------------ #
    # Non-person notes: title-only (file path unchanged)                   #
    # ------------------------------------------------------------------ #
    if note_type != "person":
        _atomic_write(old_abs, post)
        old_rel = store_path(old_abs)
        conn.execute(
            "UPDATE notes SET title=?, updated_at=? WHERE path=?",
            (new_title, now, old_rel),
        )
        conn.commit()
        return {"new_path": str(old_abs), "renamed_file": False, "wiki_links_updated": 0}

    # ------------------------------------------------------------------ #
    # Person notes: rename file + cascade                                  #
    # ------------------------------------------------------------------ #
    new_slug = new_title[:40].replace(" ", "-").lower()
    new_abs = old_abs.parent / f"{new_slug}.md"

    # Resolve slug collision (skip if same path)
    counter = 2
    while new_abs.exists() and new_abs != old_abs:
        new_abs = old_abs.parent / f"{new_slug}-{counter}.md"
        counter += 1

    # Slug produced the same filename (e.g. only case changed in title)
    if new_abs == old_abs:
        _atomic_write(old_abs, post)
        old_rel = store_path(old_abs)
        conn.execute(
            "UPDATE notes SET title=?, updated_at=? WHERE path=?",
            (new_title, now, old_rel),
        )
        conn.commit()
        return {"new_path": str(old_abs), "renamed_file": False, "wiki_links_updated": 0}

    old_rel = store_path(old_abs)
    new_rel = store_path(new_abs)

    # Rewrite wiki-link text in all other notes BEFORE touching DB/filesystem
    # so that any failure leaves notes in a consistent state.
    wiki_count = 0
    for md_file in brain_root.rglob("*.md"):
        if md_file.resolve() == old_abs.resolve():
            continue
        try:
            if _rewrite_wiki_links(md_file, old_abs, new_abs, brain_root):
                wiki_count += 1
        except Exception:
            pass  # best-effort — never block the rename

    # Write new file, cascade DB, remove old file
    tmp_path: str | None = None
    original_fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=old_abs.parent, delete=False, suffix=".tmp", encoding="utf-8"
        ) as f:
            f.write(_fm.dumps(post))
            tmp_path = f.name

        # Disable FK checks so we can rewrite all path references in one transaction
        # (same pattern as migrate_paths_to_relative in db.py)
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(
            "UPDATE notes SET path=?, title=?, updated_at=? WHERE path=?",
            (new_rel, new_title, now, old_rel),
        )
        for table, col in [
            ("relationships", "source_path"),
            ("relationships", "target_path"),
            ("attachments", "note_path"),
            ("note_tags", "note_path"),
            ("note_people", "note_path"),
            ("action_items", "note_path"),
            ("note_embeddings", "note_path"),
        ]:
            conn.execute(  # noqa: S608
                f"UPDATE {table} SET {col}=? WHERE {col}=?",
                (new_rel, old_rel),
            )
        conn.commit()

        # Filesystem: land new file, remove old
        os.replace(tmp_path, new_abs)
        tmp_path = None
        old_abs.unlink()

    except Exception:
        if tmp_path and Path(tmp_path).exists():
            Path(tmp_path).unlink(missing_ok=True)
        raise
    finally:
        conn.execute(f"PRAGMA foreign_keys = {original_fk}")  # noqa: S608

    return {
        "new_path": str(new_abs),
        "renamed_file": True,
        "wiki_links_updated": wiki_count,
    }
