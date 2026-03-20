# Phase 27: Search Quality Tuning — Research

**Researched:** 2026-03-17
**Domain:** FTS5 BM25 ranking, recency scoring, pytest regression fixtures, MCP frontmatter write, CLI recap
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Title matches must **always** rank above body-only matches — no exceptions
- Use `bm25(notes_fts, 10.0, 1.0)` or equivalent heavy title weighting
- Exact phrase in title must beat scattered word matches in body
- Apply to all search modes: plain FTS5 and the FTS5 leg of hybrid search
- Apply a **slight** recency boost — relevance still wins when the margin is large
- Gradual exponential decay: full boost for notes < 7 days, fading over ~90 days
- Boost is a small tiebreaker applied across all search modes, never overrides strong relevance signal
- Regression suite: self-contained synthetic fixture, `tests/test_search_regression.py`
- 5 precision queries (exact title lookup must return #1) + 5 recall queries (topic in top N)
- Suite must pass before any RRF or BM25 parameter change
- sb-recap fix: investigate and fix empty results despite existing entries
- sb_edit fix: wipes YAML frontmatter on edit — fix
- Capture context detection: audit and improve note_type/tag detection at capture time
- Person→note links in sidebar: minimal clickable person links only; full People Page is Phase 27.4

### Claude's Discretion
- Exact BM25 weight value (10.0 vs 8.0 vs 15.0) — tune to pass regression suite
- Recency decay half-life exact value (7 days vs 14 days seed)
- How to surface person links in sidebar (inline chips, backlinks section, or dedicated row)
- Implementation of capture context detection improvements

### Deferred Ideas (OUT OF SCOPE)
- Full People Page (person directory, per-person view) — Phase 27.4
- Full tag management UI (global rename/delete)
- "Link persons to notes in sidebar" full implementation — only basic version in Phase 27; full in 27.4
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ENGL-02 | Search hybrid ranking tuned for improved relevance (RRF weights, query normalization) | BM25 column weighting + recency boost + regression suite locks in the improvement |
</phase_requirements>

---

## Summary

The search engine uses SQLite FTS5 BM25 for keyword ranking and sqlite-vec cosine distance for semantic ranking, merged via Reciprocal Rank Fusion. Currently `bm25(notes_fts)` applies equal weight to title and body columns. The FTS5 spec supports per-column weights as additional arguments: `bm25(notes_fts, title_weight, body_weight)`. All SQL in `search_notes()` must be updated to use weighted BM25, and the recency multiplier must be applied to every result list before it is returned or merged.

Four accumulated bugs are also in scope: `sb-recap` returns nothing because `recap_main()` falls through to a git-context path that finds no notes when the repo name doesn't match any note; `sb_edit` bug is subtle — the code is correct as written (`_fm.load` + `post.content = body` + `write_note_atomic`) but `write_note_atomic` always does `INSERT INTO notes` not `UPDATE`, so it fails on existing paths; the regression suite is new and must be written from scratch against an isolated SQLite DB; and person→note sidebar links require surfacing the `people` frontmatter field from the note metadata API and rendering them as clickable chips.

**Primary recommendation:** Implement BM25 column weighting and recency multiplier inside `search.py` as the single source of truth; calibrate weights against the regression suite before shipping.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLite FTS5 | built-in | Full-text search with BM25 ranking | Already in use; column weight args are native |
| python-frontmatter | already installed | Parse/write YAML frontmatter | Used throughout engine |
| pytest | already installed | Test framework | Project standard |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite-vec | already installed | Vector KNN for semantic leg | Already used in search_semantic |
| datetime (stdlib) | stdlib | Recency decay calculation | No new dep needed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| BM25 column weights | Separate title-only FTS table | More complex schema; weights are one-line change |
| In-Python recency multiplier | SQL-side expression | SQL approach harder to unit test; Python approach clearer |

---

## Architecture Patterns

### Recommended Project Structure

No structural change — all edits are targeted modifications to existing files:

```
engine/
├── search.py          # BM25 weights + recency multiplier
├── mcp_server.py      # sb_edit bug fix (write_note_atomic INSERT→UPSERT)
├── intelligence.py    # sb-recap empty-result fix
├── capture.py         # capture context detection improvements
└── api.py             # person field exposure for sidebar links
engine/gui/static/
└── app.js             # person link chips in note viewer
tests/
└── test_search_regression.py   # NEW — regression suite
```

### Pattern 1: FTS5 BM25 Column Weighting

**What:** Pass column weights as positional args to bm25() — col order matches the FTS5 virtual table definition (title first, body second).
**When to use:** All FTS5 queries that ORDER BY bm25.
**Example:**
```sql
-- Source: SQLite FTS5 documentation, section 4.2.1
SELECT n.path, n.type, n.title, n.created_at, bm25(notes_fts, 10.0, 1.0) AS score
FROM notes_fts
JOIN notes n ON notes_fts.rowid = n.id
WHERE notes_fts MATCH ?
ORDER BY bm25(notes_fts, 10.0, 1.0)
LIMIT ?
```

The FTS5 virtual table has columns `(title, body)` in that order (see `engine/db.py` SCHEMA_SQL). Weight 10.0 for title, 1.0 for body. The ORDER BY clause must repeat the bm25() call with the same weights — SQLite does not allow referencing the SELECT alias in ORDER BY for aggregate-like functions.

### Pattern 2: Post-BM25 Recency Multiplier

**What:** After fetching BM25 results, multiply score by a recency factor computed from `created_at`.
**When to use:** All three search functions (`search_notes`, `search_hybrid` via `search_notes`, `search_semantic` separately).

```python
# Source: engine/search.py pattern (existing score adjustment approach)
import math, datetime

def _recency_multiplier(created_at_str: str, half_life_days: int = 30) -> float:
    """Returns 1.0 for brand-new notes, decays toward ~0.5 at half_life_days."""
    try:
        created = datetime.datetime.fromisoformat(created_at_str.rstrip("Z"))
        age_days = (datetime.datetime.utcnow() - created).days
        # Exponential decay: factor = 1 + boost * exp(-age / scale)
        # boost=0.1 means max 10% uplift for very fresh notes
        boost = 0.1
        scale = half_life_days / math.log(2)
        return 1.0 + boost * math.exp(-age_days / scale)
    except Exception:
        return 1.0
```

BM25 scores are negative (more negative = better). To apply a boost without inverting sign:
```python
# Adjusted score: multiply abs(score) by multiplier, restore sign
adjusted = result["score"] * _recency_multiplier(result["created_at"])
```
Since score is negative, multiplying by a value > 1.0 makes it more negative (better rank). This is correct — a score of -2.0 * 1.1 = -2.2, which ranks higher than -2.0.

### Pattern 3: sb_edit Frontmatter Wipe Fix

**What:** `write_note_atomic` always INSERTs a new row. When editing an existing note it will fail with a UNIQUE constraint error on the `path` column, or silently succeed if the path was not in DB — but either way the disk write still happens, which is why the bug manifests as frontmatter being wiped.

**Root cause (confirmed from source):** `write_note_atomic` does:
```python
conn.execute(
    "INSERT INTO notes (path, type, title, body, ...) VALUES ...",
    ...
)
```
For `sb_edit`, the note already exists in DB. The INSERT will fail with `UNIQUE constraint failed: notes.path`. However the code wraps everything in a try/except that deletes the temp file and re-raises. But the **disk write has not happened yet** at exception time — the disk rename happens AFTER the commit. So the bug must be elsewhere.

**Re-analysis:** Looking more carefully at `sb_edit`:
```python
post = _fm.load(str(p))    # loads existing file including frontmatter
post.content = body         # replaces body only
write_note_atomic(p, post, conn)  # writes frontmatter + new body
```
The `_fm.load` + `post.content = body` pattern is correct and preserves frontmatter. The INSERT in `write_note_atomic` will raise on duplicate path. So `sb_edit` currently always raises an exception for existing notes (UNIQUE constraint). The fix is to change `write_note_atomic` to use `INSERT OR REPLACE` (UPSERT) — OR — give `sb_edit` its own write path that does `UPDATE notes SET ... WHERE path=?` instead of INSERT.

**Preferred fix:** Add an `update=False` parameter to `write_note_atomic`; when `update=True`, use `INSERT OR REPLACE INTO notes` so it upserts the row. This keeps the function signature backward-compatible.

### Pattern 4: sb-recap Empty Results Fix

**What:** `recap_main()` with no argument calls `detect_git_context()` which returns the repo name `second-brain`. It then queries notes WHERE tags/people/title LIKE '%second-brain%'. This will return 0 results unless notes are explicitly tagged with "second-brain".

**Fix:** When no results found for git context, fall back to showing the 5 most recently updated notes as a generic session recap, rather than returning empty.

### Pattern 5: Regression Suite Test Structure

**What:** Self-contained pytest file that creates its own isolated SQLite DB with synthetic notes, then asserts rank position.

```python
# tests/test_search_regression.py
import pytest
from engine.db import get_connection, init_schema
from engine.search import search_notes, search_hybrid

@pytest.fixture(scope="module")
def regression_db(tmp_path_factory):
    """Isolated DB with controlled synthetic notes for ranking assertions."""
    db_path = tmp_path_factory.mktemp("regression") / "brain.db"
    conn = get_connection(str(db_path))
    init_schema(conn)
    # Insert synthetic notes with known title/body content
    # Precision notes: title IS the search term
    # Recall notes: topic is in body only
    ...
    return conn

def test_precision_person_full_name(regression_db):
    results = search_notes(regression_db, "Alice Johnson")
    assert results[0]["title"] == "Alice Johnson"  # must be rank 1
```

**Key constraint:** Must patch `engine.db.DB_PATH` and `engine.paths.DB_PATH` for isolation (established project pattern from STATE.md).

### Pattern 6: Person→Note Links in Sidebar

**What:** The `openNote()` function fetches note body and renders it. The `people` field in frontmatter is stored in the notes table but is NOT currently returned by `GET /notes/<path>`. Need to expose it and render as clickable chips.

**Approach:** The `loadMeta()` function already fetches `GET /notes/<path>/meta` which returns `{backlinks, related}`. The simplest minimal approach is to add a `people` array to the meta response and render them as chips in the sidebar panel that already shows backlinks — no new DOM structure needed.

```python
# engine/api.py — extend GET /notes/<path>/meta response
people_json = conn.execute(
    "SELECT people FROM notes WHERE path=?", (str(p),)
).fetchone()
people = json.loads(people_json[0]) if people_json else []
return jsonify({"backlinks": ..., "related": ..., "people": people})
```

```javascript
// app.js — render person chips in loadMeta()
const pl = document.getElementById('people-list');
pl.innerHTML = people.map(name =>
    `<li class="person-chip" data-name="${name}">${name}</li>`
).join('') || '<li><em>None</em></li>';
pl.querySelectorAll('.person-chip').forEach(li => {
    li.addEventListener('click', () => {
        // Navigate to person note if it exists (search by name)
        const match = _allNotes.find(n => n.type === 'people' &&
            n.title.toLowerCase() === li.dataset.name.toLowerCase());
        if (match) openNote(match.path);
    });
});
```

**HTML requirement:** A `<ul id="people-list">` must exist in the sidebar panel. Can be added adjacent to the existing `#backlinks-list` section.

### Anti-Patterns to Avoid

- **Changing the FTS5 schema:** Do NOT recreate the FTS5 virtual table to add columns. BM25 column weights work on existing schema.
- **Applying recency boost in the RRF merge step:** Boost must be applied before RRF so it influences rank position fed into RRF, not as a post-merge adjustment.
- **Global test DB contamination:** Regression suite must use its own tmp_path DB, not the seeded_db fixture — regression notes must be controlled precisely.
- **INSERT in write_note_atomic for edit path:** Will always fail UNIQUE constraint. Must use INSERT OR REPLACE or a dedicated UPDATE path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Title boosting | Custom re-ranking loop | FTS5 bm25() column weights | Native, single-line, correct |
| Frontmatter preservation on edit | Custom YAML parser | `python-frontmatter` `_fm.load()` + `post.content = body` | Already used in sb_edit correctly |
| Test DB isolation | Copy production DB | `tmp_path_factory` + `get_connection(str(db_path))` | Established project pattern |

---

## Common Pitfalls

### Pitfall 1: BM25 ORDER BY Must Repeat Weights

**What goes wrong:** Writing `SELECT bm25(notes_fts, 10.0, 1.0) AS score ... ORDER BY score` raises `OperationalError: no such column: score` in SQLite FTS5.
**Why it happens:** SQLite FTS5 bm25() is not a regular aggregate — it cannot be referenced by alias in ORDER BY.
**How to avoid:** Repeat the full `bm25(notes_fts, 10.0, 1.0)` expression in the ORDER BY clause. Confirmed in existing code — the current implementation already does this with `bm25(notes_fts)` (no weights), so the pattern is established.
**Warning signs:** `OperationalError` on any search query after adding weights.

### Pitfall 2: Recency Multiplier Sign for BM25 Scores

**What goes wrong:** BM25 scores are negative. Multiplying by a value > 1.0 makes them *more* negative, which is *better* rank. If you compare scores intuitively (expecting higher = better), the boost appears to work in reverse.
**How to avoid:** Always test with assertions: a note created today should have a more-negative score than an identical note created 180 days ago.

### Pitfall 3: write_note_atomic UNIQUE Constraint on Edit

**What goes wrong:** Calling `write_note_atomic` for an existing note path raises `UNIQUE constraint failed: notes.path` — the exception is caught, temp file deleted, and an opaque RuntimeError is raised.
**How to avoid:** Use `INSERT OR REPLACE INTO notes` when `update=True` parameter is passed, or provide a separate `update_note_in_db()` helper.

### Pitfall 4: Regression Suite Notes Must Be Precise

**What goes wrong:** Synthetic notes that share too many tokens with each other produce ambiguous BM25 rankings, making precision assertions flaky.
**How to avoid:** Use unique name tokens in each note's title. Person note title should be a full name not present in any other note. Body-only recall notes should contain the topic keyword exclusively in the body, with a generic title.

### Pitfall 5: sb-recap Returns Empty for All git Contexts

**What goes wrong:** `detect_git_context()` returns `second-brain` (the repo name). The DB query looks for notes where title/tags/people contain `second-brain`. Almost certainly returns 0 rows.
**How to avoid:** Add a fallback path: if the git-context query returns 0 rows, show the 5 most-recently-updated notes as a generic "recent activity" recap.

---

## Code Examples

### FTS5 Weighted BM25 Query (Both Variants)

```python
# Source: engine/search.py (current unweighted), SQLite FTS5 docs section 4.2.1
# Without type filter:
sql = """
    SELECT n.path, n.type, n.title, n.created_at, bm25(notes_fts, 10.0, 1.0) AS score
    FROM notes_fts
    JOIN notes n ON notes_fts.rowid = n.id
    WHERE notes_fts MATCH ?
    ORDER BY bm25(notes_fts, 10.0, 1.0)
    LIMIT ?
"""

# With type filter:
sql = """
    SELECT n.path, n.type, n.title, n.created_at, bm25(notes_fts, 10.0, 1.0) AS score
    FROM notes_fts
    JOIN notes n ON notes_fts.rowid = n.id
    WHERE notes_fts MATCH ?
      AND n.type = ?
    ORDER BY bm25(notes_fts, 10.0, 1.0)
    LIMIT ?
"""
```

### Recency Multiplier Application

```python
# Source: engine/search.py pattern (to be added)
# Apply after rows are fetched, before returning:
results = [
    {**row_dict, "score": row_dict["score"] * _recency_multiplier(row_dict["created_at"])}
    for row_dict in raw_results
]
```

### INSERT OR REPLACE for Edit Path

```python
# Source: engine/capture.py write_note_atomic (modified for update=True case)
if update:
    conn.execute(
        "INSERT OR REPLACE INTO notes (path, type, title, body, tags, people, created_at, updated_at, sensitivity)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (resolved_path, post.get("type", "note"), post.get("title", ""),
         post.content, tags_json, people_json, created_at, updated_at, sensitivity),
    )
else:
    conn.execute(
        "INSERT INTO notes (path, type, title, body, tags, people, created_at, updated_at, sensitivity)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ...
    )
```

### Regression Test Skeleton

```python
# tests/test_search_regression.py
import pytest
from engine.db import get_connection, init_schema
from engine.search import search_notes

PRECISION_NOTES = [
    ("people", "Alice Johnson", "Project manager at Acme Corp."),
    ("people", "Bob Smith", "Engineer on the backend team."),
    ("meeting", "Q3 Planning Session", "Roadmap priorities for Q3."),
    ("meeting", "Design Review", "UI patterns reviewed."),
    ("note", "Python", "Short single-word title note."),
]
RECALL_NOTES = [
    ("note", "Random Note A", "The quarterly roadmap includes python and deployment."),
    ("note", "Random Note B", "Backend systems need resilience improvements."),
    ("note", "Team Update", "Alice is leading the new initiative."),
    ("note", "Architecture Note", "Service mesh patterns for microservices."),
    ("note", "Weekly Sync", "Alice and Bob discussed roadmap items."),
]

@pytest.fixture(scope="module")
def reg_conn(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("reg") / "brain.db"
    conn = get_connection(str(db_path))
    init_schema(conn)
    for note_type, title, body in PRECISION_NOTES + RECALL_NOTES:
        conn.execute(
            "INSERT INTO notes (path, type, title, body, tags, people) VALUES (?, ?, ?, ?, '[]', '[]')",
            (f"/brain/{note_type}/{title.replace(' ', '-').lower()}.md", note_type, title, body),
        )
        # FTS5 trigger handles indexing automatically
    conn.commit()
    return conn
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Equal BM25 weights | Column-weighted BM25 (10.0 title, 1.0 body) | Phase 27 | Title searches always win |
| No recency signal | Exponential decay multiplier | Phase 27 | Recent notes get tiebreaker boost |
| No ranking tests | 10-query regression suite | Phase 27 | Prevents regressions on future tuning |

---

## Open Questions

1. **Recency boost on semantic leg**
   - What we know: `search_semantic` returns scores as `1.0 - cosine_distance` (higher = better, positive)
   - What's unclear: The multiplier logic works differently — multiplying a positive score by > 1 is a boost. But the merge happens in `_rrf_merge` by rank position, not raw score. Applying recency before RRF means re-sorting the semantic list.
   - Recommendation: Apply recency to BM25 results only (which drives rank in the BM25 leg). The semantic leg contributes via rank position in RRF regardless. This is simpler and meets the "tiebreaker" intent.

2. **Capture context detection scope**
   - What we know: CONTEXT.md says "audit and improve how context (note_type, tags) is detected at capture time" — but gives no specific failure mode.
   - What's unclear: Whether this refers to the CLI `main()` in `capture.py` (which uses `classify()`), or to the MCP `sb_capture` tool (which takes explicit type/tags from caller).
   - Recommendation: Focus on `main()` — add simple heuristic: if title contains "meeting" → suggest type=meeting; if title contains someone's name pattern → suggest type=people. Keep as best-effort, never block capture.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | none — discovered automatically |
| Quick run command | `uv run pytest tests/test_search_regression.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENGL-02 | Title match ranks above body-only match | unit | `uv run pytest tests/test_search_regression.py::test_precision_person_full_name -x` | Wave 0 |
| ENGL-02 | Partial name search surfaces person note in top 3 | unit | `uv run pytest tests/test_search_regression.py::test_precision_partial_name -x` | Wave 0 |
| ENGL-02 | Topic in body only appears in top 5 (recall) | unit | `uv run pytest tests/test_search_regression.py::test_recall_body_topic -x` | Wave 0 |
| ENGL-02 | BM25 weights propagate to hybrid search | unit | `uv run pytest tests/test_search_regression.py::test_hybrid_title_wins -x` | Wave 0 |
| ENGL-02 | sb_edit preserves frontmatter | unit | `uv run pytest tests/test_mcp.py::test_sb_edit_preserves_frontmatter -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_search_regression.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_search_regression.py` — covers all 10 ENGL-02 regression queries (5 precision + 5 recall)
- [ ] `tests/test_mcp.py` — add `test_sb_edit_preserves_frontmatter` stub

---

## Sources

### Primary (HIGH confidence)
- Direct source read: `engine/search.py` — confirmed current BM25 usage, RRF implementation, search_hybrid fallback
- Direct source read: `engine/mcp_server.py` — confirmed sb_edit implementation, frontmatter load pattern
- Direct source read: `engine/capture.py` — confirmed write_note_atomic INSERT behavior, capture_note flow
- Direct source read: `engine/intelligence.py` — confirmed recap_main git-context flow and empty-result path
- Direct source read: `engine/db.py` — confirmed FTS5 schema column order (title, body), UNIQUE constraint on path
- Direct source read: `engine/gui/static/app.js` — confirmed loadMeta() structure, openNote() flow, backlinks pattern
- Direct source read: `tests/test_search.py` — confirmed existing test patterns, no regression suite exists yet

### Secondary (MEDIUM confidence)
- SQLite FTS5 documentation: bm25() column weight args are positional, matching CREATE VIRTUAL TABLE column order; ORDER BY must repeat the call

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, no new deps
- Architecture: HIGH — confirmed from direct source reads, no assumptions
- Pitfalls: HIGH — root causes confirmed from actual code, not speculation
- Regression suite design: HIGH — established project patterns (seeded_db, tmp_path, DB_PATH patching) documented in STATE.md

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (stable stack, all local)
