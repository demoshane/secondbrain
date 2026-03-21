"""Two-pass blob segmentation for sb_capture_smart.

Pass 1 (structural): split on headings, horizontal rules, date stamps, RE:/Subject: markers.
Pass 2 (name-cluster): detect topic shifts in large segments based on entity people changes.

Code blocks and tables are protected before splitting — their content is never split.

Phase 31-02 additions:
- resolve_entities(): link segment entities to existing person/project notes or create stubs
- dedup_segment(): three-path dedup heuristic (superset/complementary/ambiguous)
"""
import difflib
import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Any

from engine.entities import extract_entities

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MIN_SEGMENT_LEN = 50
_MIN_SEGMENT_LINES = 2
_MAX_SEGMENTS = 20

# Structural split markers (compiled multiline pattern)
# Splits BEFORE: # headings, --- horizontal rules, date stamps (YYYY-MM-DD),
# RE: / Subject: email markers
_STRUCTURAL_SPLIT = re.compile(
    r'(?m)^(?=#{1,3}\s|---\s*$|\d{4}-\d{2}-\d{2}|RE:\s|Subject:\s)',
)

# URL detection
_URL_PAT = re.compile(r'https?://\S+')

# Table row detection (line starts with |)
_TABLE_ROW = re.compile(r'(?m)^\|')


# ---------------------------------------------------------------------------
# Protected-region masking
# ---------------------------------------------------------------------------

def _mask_protected_regions(content: str) -> tuple[str, list[tuple[int, int]]]:
    """Replace code blocks and table blocks with placeholder text of the same length.

    Returns (masked_content, [(start, end), ...]) where start/end mark the original
    protected regions. The caller uses these positions to detect if a split falls
    inside a protected region.
    """
    protected: list[tuple[int, int]] = []
    result = list(content)

    # --- Fenced code blocks (``` or ~~~) ---
    fence_pat = re.compile(r'(?m)^(`{3,}|~{3,})[^\n]*\n.*?^\1\s*$', re.DOTALL)
    for m in fence_pat.finditer(content):
        protected.append((m.start(), m.end()))
        # Replace content inside fences with spaces (preserve line structure)
        for i in range(m.start(), m.end()):
            if result[i] != '\n':
                result[i] = ' '

    masked = ''.join(result)

    # --- Markdown tables: consecutive lines starting with | ---
    # Find runs of | lines
    table_pat = re.compile(r'(?m)(^\|[^\n]*\n)+')
    for m in table_pat.finditer(masked):
        start, end = m.start(), m.end()
        # Check if already covered
        if not any(s <= start < e for s, e in protected):
            protected.append((start, end))
            for i in range(start, end):
                if masked[i] != '\n':
                    result[i] = ' '

    return ''.join(result), protected


def _split_at_safe_positions(content: str, protected: list[tuple[int, int]]) -> list[str]:
    """Split content on structural markers, but only at positions outside protected regions."""
    split_positions = [m.start() for m in _STRUCTURAL_SPLIT.finditer(content)]

    # Filter out positions that fall inside protected regions
    safe_positions = [
        pos for pos in split_positions
        if not any(s <= pos < e for s, e in protected)
    ]

    if not safe_positions:
        return [content]

    parts = []
    prev = 0
    for pos in safe_positions:
        if pos > prev:
            parts.append(content[prev:pos])
        prev = pos
    parts.append(content[prev:])
    return parts


# ---------------------------------------------------------------------------
# Segment classification
# ---------------------------------------------------------------------------

def _classify_segment(text: str) -> str:
    """Classify segment into a note type based on content signals."""
    # URL check takes priority
    if _URL_PAT.search(text):
        return "link"

    low = text.lower()
    if re.search(r'\bmeeting\b|\bdiscussed\b|\battendees\b|\bagenda\b|\bstandup\b|\bsync\b|\bretro\b', low):
        return "meeting"
    # Person: capitalized bigram + contact/role signal
    if re.search(r'[A-Z][a-z]+ [A-Z][a-z]+', text[:200]) and \
            re.search(r'\brole\b|\bcontact\b|\bemail\b|\bphone\b|\blinkedin\b|\btitle\b', low):
        return "person"
    if re.search(r'\bproject\b|\bmilestone\b|\bdeadline\b|\bsprint\b|\broadmap\b', low):
        return "project"
    if re.search(r'\bidea\b|\bwhat if\b|\bmaybe\b|\bconsider\b|\bbrainstorm\b', low):
        return "idea"
    return "note"


def _derive_title(text: str) -> str:
    """Extract a title from the first non-empty line, stripping # prefix."""
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:80]
    return "Untitled"


# ---------------------------------------------------------------------------
# Short-segment merge
# ---------------------------------------------------------------------------

def _merge_short_segments(segments: list[str]) -> list[str]:
    """Merge segments that are too short into the adjacent segment.

    Merge into previous if available, else defer to next pass (will merge forward).
    Two passes: first backward (short → previous), then forward (short → next).
    """
    if not segments:
        return segments

    # Pass 1: backward — merge short into previous
    result: list[str] = []
    for seg in segments:
        stripped = seg.strip()
        is_short = len(stripped) < _MIN_SEGMENT_LEN or stripped.count('\n') < _MIN_SEGMENT_LINES - 1
        if is_short and result:
            result[-1] = result[-1].rstrip() + "\n\n" + seg
        else:
            result.append(seg)

    # Pass 2: forward — merge remaining short segments into next
    final: list[str] = []
    i = 0
    while i < len(result):
        stripped = result[i].strip()
        is_short = len(stripped) < _MIN_SEGMENT_LEN or stripped.count('\n') < _MIN_SEGMENT_LINES - 1
        if is_short and i + 1 < len(result):
            # Merge current into next
            result[i + 1] = result[i].rstrip() + "\n\n" + result[i + 1]
            i += 1
        else:
            final.append(result[i])
            i += 1

    return final if final else segments


# ---------------------------------------------------------------------------
# Max-cap enforcement
# ---------------------------------------------------------------------------

def _enforce_max_cap(segments: list[str]) -> list[str]:
    """Merge smallest pairs until segment count is <= _MAX_SEGMENTS."""
    while len(segments) > _MAX_SEGMENTS:
        # Find shortest segment by length
        min_idx = min(range(len(segments)), key=lambda i: len(segments[i]))
        # Merge with adjacent (prefer previous, else next)
        if min_idx > 0:
            merge_into = min_idx - 1
            segments[merge_into] = segments[merge_into].rstrip() + "\n\n" + segments[min_idx]
            segments.pop(min_idx)
        else:
            segments[1] = segments[0].rstrip() + "\n\n" + segments[1]
            segments.pop(0)

    return segments


# ---------------------------------------------------------------------------
# Pass 2: name-cluster shift detection
# ---------------------------------------------------------------------------

def _pass2_name_cluster(segment: str) -> list[str]:
    """Sub-split a large segment on topic shifts detected by people name changes.

    For segments >500 chars without structural markers, detect if people names
    shift significantly between paragraph blocks.
    """
    if len(segment) < 500:
        return [segment]

    paragraphs = [p.strip() for p in re.split(r'\n{2,}', segment) if p.strip()]
    if len(paragraphs) <= 2:
        return [segment]

    # Extract people per paragraph
    para_people: list[set[str]] = []
    for para in paragraphs:
        ents = extract_entities("", para)
        para_people.append(set(ents.get("people", [])))

    # Detect shift: if people set changes significantly, split there
    result_blocks: list[list[str]] = [[paragraphs[0]]]
    for i in range(1, len(paragraphs)):
        prev_people = para_people[i - 1]
        curr_people = para_people[i]
        # Significant shift: both sets non-empty and disjoint
        if prev_people and curr_people and prev_people.isdisjoint(curr_people):
            result_blocks.append([paragraphs[i]])
        else:
            result_blocks[-1].append(paragraphs[i])

    return ["\n\n".join(block) for block in result_blocks]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def segment_blob(content: str) -> list[dict[str, Any]]:
    """Segment freeform text into typed note dicts.

    Two-pass segmentation:
    1. Structural: split on headings, ---, date stamps, RE:/Subject:
    2. Name-cluster: detect topic shifts in large segments

    Short segments merge into previous. Output capped at 20.

    Returns:
        [{"title": str, "type": str, "body": str, "links": [], "entities": dict}, ...]
    """
    if not content or not content.strip():
        return [{"title": "Untitled", "type": "note", "body": content, "links": [], "entities": {}}]

    # Protect code blocks and tables from splitting
    masked_content, protected = _mask_protected_regions(content)

    # Pass 1: structural split (on masked content, but keep original text)
    raw_parts = _split_at_safe_positions(masked_content, protected)

    # Re-extract original text slices from content using split positions
    # We split the masked content but return original content slices
    original_parts = _extract_original_parts(content, masked_content, raw_parts)

    # Pass 2: name-cluster on large segments
    all_segments: list[str] = []
    for part in original_parts:
        if part.strip():
            sub = _pass2_name_cluster(part)
            all_segments.extend(sub)

    # Merge short segments
    all_segments = _merge_short_segments(all_segments)

    # Enforce max cap
    all_segments = _enforce_max_cap(all_segments)

    # Build result dicts
    result = []
    for seg in all_segments:
        if not seg.strip():
            continue
        seg_type = _classify_segment(seg)
        title = _derive_title(seg)
        entities = extract_entities(title, seg)
        result.append({
            "title": title,
            "type": seg_type,
            "body": seg.strip(),
            "links": [],
            "entities": entities,
        })

    if not result:
        result = [{"title": "Untitled", "type": "note", "body": content.strip(), "links": [], "entities": {}}]

    return result


def _extract_original_parts(original: str, masked: str, masked_parts: list[str]) -> list[str]:
    """Given parts of the masked string, recover the corresponding original text slices."""
    if len(masked_parts) == 1:
        return [original]

    # Reconstruct by character position tracking
    result = []
    pos = 0
    for part in masked_parts:
        end = pos + len(part)
        result.append(original[pos:end])
        pos = end

    return result


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
        "SELECT path, title FROM notes WHERE type IN ('person', 'people')"
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
