# Phase 27: Search Quality Tuning - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Improve search result ranking so title matches always appear first, add a mild recency boost, and create a locked regression suite (5 precision + 5 recall queries). Also fix four accumulated pending todos: sb-recap empty results, sb_edit frontmatter wipe, capture context detection, and basic person→note links in sidebar.

</domain>

<decisions>
## Implementation Decisions

### Title vs body priority
- Title matches must **always** rank above body-only matches — no exceptions
- Use `bm25(notes_fts, 10.0, 1.0)` or equivalent heavy title weighting
- Exact phrase in title must beat scattered word matches in body
- Apply to all search modes: plain FTS5 and the FTS5 leg of hybrid search

### Recency boost
- Apply a **slight** recency boost — relevance still wins when the margin is large
- Use gradual exponential decay: full boost for notes < 7 days, fading over ~90 days
- Boost is a small tiebreaker applied across all search modes, never overrides strong relevance signal
- User pattern is mixed (recent + old), so boost must not bury older important notes

### Regression suite
- Self-contained synthetic fixture — creates its own test notes, no dependency on ~/SecondBrain
- Integrated into normal pytest suite (`tests/test_search_regression.py`)
- **5 precision queries** (exact title lookup must return as #1 result):
  - Person note: search by full person name
  - Person note: search by first name only (partial match)
  - Meeting note: search by meeting title
  - Meeting note: search by partial meeting title
  - Short title note: single-word title search
- **5 recall queries** (topic/semantic — relevant note must appear in top N results):
  - Topic in body only (not in title)
  - Semantic concept search (synonym, not literal string)
  - Partial name match surfaces person note
  - Body keyword across multiple relevant notes
  - Mixed content search (topic + person in same query)
- Regression suite must pass before any RRF or BM25 parameter is changed

### Pending todos in scope
- **sb-recap fix**: `sb-recap` returns nothing despite existing recap entries — investigate and fix
- **sb_edit frontmatter fix**: `sb_edit` MCP tool wipes YAML frontmatter on edit — fix
- **Capture context detection**: Audit and improve how context (note_type, tags) is detected at capture time
- **Person→note links in sidebar**: Basic clickable person links in the sidebar note viewer (minimal version; full People Page is Phase 27.4)

### Claude's Discretion
- Exact BM25 weight value (10.0 vs 8.0 vs 15.0) — tune to pass regression suite
- Recency decay half-life exact value (7 days vs 14 days seed)
- How to surface person links in sidebar (inline chips, backlinks section, or dedicated row)
- Implementation of capture context detection improvements

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/search.py` — `search_notes()`, `search_semantic()`, `search_hybrid()`, `_rrf_merge()` all exist; changes are targeted edits
- `bm25(notes_fts)` in `search_notes()` — add column weights as 3rd/4th args: `bm25(notes_fts, 10.0, 1.0)`
- `_rrf_merge(bm25_results, vec_results, k=60, limit=limit)` — k is tunable
- `notes` table has `created_at` column — available for recency calculation
- `engine/mcp_server.py` — `sb_edit()` tool lives here; frontmatter wipe is a bug in its write path
- `engine/capture.py` — `capture_note()` is where context detection improvements go

### Established Patterns
- FTS5 BM25 column weights: `bm25(table, col1_weight, col2_weight)` — col order matches CREATE VIRTUAL TABLE (title, body)
- Test isolation: patch `engine.db.DB_PATH` and `engine.paths.DB_PATH` for all DB tests
- `xfail(strict=False)` for stubs that will auto-promote once implementation ships
- Recency boost: implement as post-BM25 score adjustment `adjusted = bm25_score * recency_multiplier`

### Integration Points
- `search_notes()` return value feeds into `search_hybrid()` — column weight change propagates automatically
- API endpoint `POST /search` in `engine/api.py` calls `search_hybrid()` or `search_notes()` — recency boost should be applied inside `search.py`, transparent to caller
- `sb-recap` CLI in `engine/recap.py` (or equivalent) — investigate why it returns empty

</code_context>

<specifics>
## Specific Ideas

- Title match must win "no exceptions" — the main pain point is searching a note title and having it buried
- Regression suite is the anchor: calibrate weights against the suite, not ad-hoc
- Person→note links in sidebar: minimal/basic only — full People Page is Phase 27.4

</specifics>

<deferred>
## Deferred Ideas

- Full People Page (person directory, per-person view) — Phase 27.4
- Full tag management UI (global rename/delete) — noted in STATE.md TODOs, future phase
- "Link persons to notes in sidebar" full implementation — only basic version in Phase 27; full in 27.4

</deferred>

---

*Phase: 27-search-quality-tuning*
*Context gathered: 2026-03-17*
