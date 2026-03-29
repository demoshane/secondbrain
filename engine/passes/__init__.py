"""engine.passes — multi-pass decomposition pipeline.

decompose(content) orchestrates:
  Pass 1 (p1_entities): extract people, topics, etc. unconditionally
  Pass 2 (p2_urls):     strip URLs → produce LinkNote objects
  Pass 3 (p3_classify): classify URL-stripped content (with conversation boost)
  Pass 4 (p4_actions):  extract TODO/AP/action: keyword action items
  Pass 5 (p5_assemble): resolve entities → person_stubs + existing_people (requires conn)

Structural splitting helpers are defined here (moved from segmenter.py in Plan 03
when segment_blob() was deleted and decompose() became the sole entry point).
"""
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from engine.typeclassifier import CONFIDENCE_THRESHOLD  # re-export


@dataclass
class LinkNote:
    url: str
    title: str  # domain or extracted title
    body: str   # surrounding context line


@dataclass
class ActionItem:
    text: str
    owner: str | None
    due_date: str | None
    source: str  # "keyword" | "intent"


@dataclass
class DecomposedResult:
    primary_title: str
    primary_type: str
    primary_body: str
    confidence: float
    entities: dict
    link_notes: list[LinkNote] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
    person_stubs: list[dict] = field(default_factory=list)
    existing_people: list[dict] = field(default_factory=list)


# Sub-module imports must come AFTER dataclass definitions (LinkNote used by p2_urls)
from engine.passes.p1_entities import extract_all_entities  # noqa: E402
from engine.passes.p2_urls import extract_urls              # noqa: E402
from engine.passes.p3_classify import classify_content      # noqa: E402
from engine.passes.p4_actions import extract_keyword_actions  # noqa: E402


# ---------------------------------------------------------------------------
# Structural splitting helpers (formerly in engine/segmenter.py)
# ---------------------------------------------------------------------------

_MIN_SEGMENT_LEN = 50
_MIN_SEGMENT_LINES = 2
_MAX_SEGMENTS = 20

# Structural split markers (compiled multiline pattern)
# Splits BEFORE: # h1 headings only (## and ### are subheadings within a note, not boundaries),
# --- horizontal rules, date stamps (YYYY-MM-DD), RE: / Subject: email markers
_STRUCTURAL_SPLIT = re.compile(
    r'(?m)^(?=#\s|---\s*$|\d{4}-\d{2}-\d{2}|RE:\s|Subject:\s)',
)

# URL detection
_URL_PAT = re.compile(r'https?://\S+')

# Table row detection (line starts with |)
_TABLE_ROW = re.compile(r'(?m)^\|')


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


def _derive_title(text: str) -> str:
    """Extract a title from the first non-empty line, stripping # prefix."""
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:80]
    return "Untitled"


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


def _pass2_name_cluster(segment: str) -> list[str]:
    """Sub-split a large segment on topic shifts detected by people name changes.

    For segments >500 chars without structural markers, detect if people names
    shift significantly between paragraph blocks.
    """
    from engine.entities import extract_entities

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


def decompose(
    content: str,
    conn: sqlite3.Connection | None = None,
    brain_root: Path | None = None,
) -> list[DecomposedResult]:
    """Decompose freeform content into typed DecomposedResult objects.

    Structural splitting (protect code blocks / tables, then split on headings / ---).
    For each segment: Pass 1 extracts entities, Pass 2 strips URLs to LinkNotes,
    Pass 3 classifies the URL-stripped body, Pass 4 extracts keyword action items.

    Pass 5 (entity resolution) runs only when conn + brain_root are provided.
    """
    if not content or not content.strip():
        return [DecomposedResult(
            primary_title="Untitled",
            primary_type="note",
            primary_body=content,
            confidence=0.90,
            entities={},
        )]

    # Structural splitting (protect code blocks / tables, then split on headings / ---)
    masked_content, protected = _mask_protected_regions(content)
    raw_parts = _split_at_safe_positions(masked_content, protected)
    original_parts = _extract_original_parts(content, masked_content, raw_parts)

    # Name-cluster sub-splitting on large segments
    all_segments: list[str] = []
    for part in original_parts:
        if part.strip():
            all_segments.extend(_pass2_name_cluster(part))

    all_segments = _merge_short_segments(all_segments)
    all_segments = _enforce_max_cap(all_segments)

    results: list[DecomposedResult] = []
    for seg in all_segments:
        if not seg.strip():
            continue

        title = _derive_title(seg)

        # Pass 1 — entities (unconditional, before title is fully known)
        entities = extract_all_entities(seg)

        # Pass 2 — URL extraction; body fed to classifier is URL-stripped
        stripped_body, link_notes = extract_urls(seg)

        # Pass 3 — classify URL-stripped content (+ conversation boost)
        note_type, confidence = classify_content(title, stripped_body)

        # Pass 4 — keyword action item extraction
        action_items = extract_keyword_actions(stripped_body)

        results.append(DecomposedResult(
            primary_title=title,
            primary_type=note_type,
            primary_body=stripped_body,
            confidence=confidence,
            entities=entities,
            link_notes=link_notes,
            action_items=action_items,
        ))

    if not results:
        results = [DecomposedResult(
            primary_title="Untitled",
            primary_type="note",
            primary_body=content.strip(),
            confidence=0.90,
            entities={},
        )]

    # Pass 5 — entity resolution (optional, requires DB connection)
    if conn is not None and brain_root is not None:
        from engine.passes.p5_assemble import assemble
        results = assemble(results, conn, brain_root)

    return results
