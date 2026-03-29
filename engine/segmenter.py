"""Segmenter utilities for sb_capture_smart.

Phase 31-02 additions:
- resolve_entities(): link segment entities to existing person/project notes or create stubs
- dedup_segment(): three-path dedup heuristic (superset/complementary/ambiguous)

Note: The segment_blob() function and its structural splitting helpers were moved to
engine/passes/__init__.py (Plan 43-03) where decompose() is the sole entry point.
"""
import difflib
import hashlib
import re
import sqlite3

from engine.db import PERSON_TYPES, PERSON_TYPES_PH
from pathlib import Path


# ---------------------------------------------------------------------------
# Phase 31-02: Entity resolution
# ---------------------------------------------------------------------------

def resolve_entities(
    entities: dict,
    conn: sqlite3.Connection,
    brain_root: Path,
) -> dict:
    """Resolve extracted entities to existing notes or flag as new stubs.

    For each person/project entity:
    - Try FTS5 lookup (search_notes by name + note_type)
    - If no FTS5 hit, try fuzzy match via difflib against all known person/project titles
    - If still no match: flag as new_stub

    Args:
        entities: {"people": [str, ...], "topics": [str, ...], ...}
        conn: Open SQLite connection.
        brain_root: Brain root path (used when creating stubs via capture_note).

    Returns:
        {
            "existing": [{"name": str, "path": str}, ...],
            "new_stubs": [{"name": str, "type": str}, ...],
        }
    """
    from engine.search import search_notes

    existing: list[dict] = []
    new_stubs: list[dict] = []

    # Build lookup tables for fuzzy matching (all person + project titles in DB)
    _person_rows = conn.execute(
        f"SELECT path, title FROM notes WHERE type IN ({PERSON_TYPES_PH})", PERSON_TYPES
    ).fetchall()
    _project_rows = conn.execute(
        "SELECT path, title FROM notes WHERE type IN ('project', 'projects')"
    ).fetchall()
    _person_titles = [r[1] for r in _person_rows if r[1]]
    _project_titles = [r[1] for r in _project_rows if r[1]]
    _person_title_to_path = {r[1]: r[0] for r in _person_rows if r[1]}
    _project_title_to_path = {r[1]: r[0] for r in _project_rows if r[1]}

    def _resolve_one(name: str, note_type: str, title_list: list[str], title_to_path: dict) -> None:
        """Resolve one entity name. Mutates existing / new_stubs."""
        # Guard: skip empty names
        if not name.strip():
            return

        # Step 1: FTS5 lookup
        try:
            hits = search_notes(conn, name, note_type=note_type, limit=3)
        except Exception:
            hits = []

        if hits:
            # Take the top result as a match
            existing.append({"name": name, "path": hits[0]["path"]})
            return

        # Step 2: fuzzy match
        matches = difflib.get_close_matches(name, title_list, n=1, cutoff=0.75)
        if matches:
            matched_title = matches[0]
            path = title_to_path.get(matched_title, "")
            existing.append({"name": name, "path": path})
            return

        # Step 3: no match — new stub
        new_stubs.append({"name": name, "type": note_type})

    # Resolve people
    for person_name in entities.get("people", []):
        _resolve_one(person_name, "person", _person_titles, _person_title_to_path)

    # Resolve topics that look like project entities (optional — topics may not be project-typed)
    # Not required by current plan spec; people resolution is the primary requirement.

    return {"existing": existing, "new_stubs": new_stubs}


# ---------------------------------------------------------------------------
# Phase 31-02: Three-path dedup heuristic
# ---------------------------------------------------------------------------

def dedup_segment(
    title: str,
    body: str,
    conn: sqlite3.Connection,
    brain_root: Path,
) -> dict:
    """Three-path dedup heuristic for a segment before saving.

    Calls check_capture_dedup() to find similar notes, then classifies:
    - "save_new": no similar notes found
    - "update_existing": new body is a superset of existing (longer + overlapping key phrases)
    - "save_complementary": different angle on same topic — save new + mark as similar
    - "ambiguous": 3+ matches all above threshold — return options without saving

    Args:
        title: Segment title.
        body: Segment body text.
        conn: Open SQLite connection.
        brain_root: Brain root path (unused here, kept for interface consistency).

    Returns:
        {
            "action": "save_new" | "update_existing" | "save_complementary" | "ambiguous",
            # action-specific keys:
            "path": str,               # for update_existing
            "existing_body": str,      # for update_existing
            "similar_path": str,       # for save_complementary
            "options": list[dict],     # for ambiguous
        }
    """
    from engine.capture import check_capture_dedup

    matches = check_capture_dedup(title, body, conn)

    if not matches:
        return {"action": "save_new"}

    # Ambiguous: 3+ matches all above threshold
    if len(matches) >= 3:
        return {"action": "ambiguous", "options": matches}

    # Take top match
    top_match = matches[0]
    match_path = top_match["path"]

    # Read existing body from DB
    row = conn.execute(
        "SELECT body FROM notes WHERE path=?", (match_path,)
    ).fetchone()
    if row is None:
        # DB inconsistency — treat as no match
        return {"action": "save_new"}

    existing_body: str = row[0] or ""

    # Superset check: new body is significantly longer AND shares key phrases from existing
    is_longer = len(body) > len(existing_body) * 1.2
    if is_longer and existing_body:
        # Extract "key phrases" = words >4 chars from first 200 chars of existing body
        key_words = re.findall(r'\b\w{5,}\b', existing_body[:200])
        # Use first 5 unique key phrases
        key_phrases = list(dict.fromkeys(key_words))[:5]
        overlap_count = sum(1 for kp in key_phrases if kp.lower() in body.lower())
        if len(key_phrases) == 0 or overlap_count >= 2:
            # New body is a superset — update existing
            changelog_hash = hashlib.sha256(existing_body.encode()).hexdigest()[:8]
            return {
                "action": "update_existing",
                "path": match_path,
                "existing_body": existing_body,
                "changelog_hash": changelog_hash,
            }

    # Complementary: different angle on same topic
    return {"action": "save_complementary", "similar_path": match_path}
