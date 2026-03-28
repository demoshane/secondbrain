---
phase: 38-scale-architecture-100k-notes
plan: 05
subsystem: search
tags: [search, hnswlib, ann, sqlite-vec, excerpts, semantic-search, chunked-embeddings]

requires:
  - phase: 38-01
    provides: hnswlib ANN index (knn_query, load_or_build_index) in engine/ann_index.py
  - phase: 38-04
    provides: note_chunks table with chunk_text and embedding columns

provides:
  - search_semantic uses hnswlib ANN first (O(log n)), falls back to sqlite-vec on failure
  - _enrich_with_excerpts helper finds best matching chunk per result via cosine similarity
  - All search results (search_notes, search_semantic, search_hybrid) include excerpt field
  - API /search and MCP sb_search pass excerpt through (no stripping)

affects:
  - frontend (excerpt field available for display in search results)
  - mcp_server (sb_search results now carry excerpt)

tech-stack:
  added: []
  patterns:
    - "ANN-first with sqlite-vec fallback: try hnswlib knn_query, catch all exceptions and fall back"
    - "Excerpt enrichment post-processing: call _enrich_with_excerpts after any search path"
    - "Dimension-safe cosine: skip chunks where len(chunk_vec) != len(query_vec) instead of crashing"

key-files:
  created: []
  modified:
    - engine/search.py
    - tests/test_search.py

key-decisions:
  - "search_semantic uses ANN-first pattern: hnswlib knn_query tried first, any exception falls back to sqlite-vec — keeps existing sqlite-vec path intact"
  - "Dimension mismatch in _enrich_with_excerpts silently skipped (len check) — stub embed_texts returns 384-dim; index may have 768-dim; must not crash"
  - "_enrich_with_excerpts called at search_hybrid merge point (not in each sub-search) to avoid double enrichment"
  - "search_notes BM25 path sets excerpt=None statically — no chunk matching for pure FTS5"

requirements-completed:
  - SCALE-06
  - SCALE-02

duration: 10min
completed: 2026-03-26
---

# Phase 38 Plan 05: Search Integration — ANN + Excerpt Summary

**hnswlib ANN integrated into search_semantic with sqlite-vec fallback; all search results now include excerpt field containing best-matching chunk text (trimmed to 300 chars)**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-26T17:10:00Z
- **Completed:** 2026-03-26T17:20:14Z
- **Tasks:** 2 (Task 2 was verification-only, no code changes)
- **Files modified:** 2

## Accomplishments

- Added `_enrich_with_excerpts(conn, results, query)` helper that finds best chunk per result via cosine similarity against query embedding
- Modified `search_semantic` to try hnswlib `knn_query` first (O(log n)), falling back to sqlite-vec on any exception
- Added `excerpt: None` to `search_notes` BM25 path (no chunk matching for pure FTS5)
- `search_hybrid` calls `_enrich_with_excerpts` on RRF-merged results
- API `/search` and MCP `sb_search` pass excerpt through without stripping (verified — they add metadata but don't filter keys)
- Added `TestSearchExcerpt` test class covering all four excerpt scenarios

## Task Commits

1. **Task 1: Integrate hnswlib ANN into search_semantic + excerpt enrichment** - `9fdd74c` (feat)
2. **Task 2: Update API and MCP to pass through excerpt field** - no-op (verified pass-through, no code changes)

## Files Created/Modified

- `engine/search.py` — Added `_enrich_with_excerpts()`, modified `search_semantic` for ANN-first path, added `excerpt: None` to `search_notes`, updated `search_hybrid` to call enrichment
- `tests/test_search.py` — Added `TestSearchExcerpt` class with 4 tests covering BM25 excerpt=None, hybrid excerpt field, no-chunks case, and chunks-with-data case

## Decisions Made

- ANN-first pattern: try `knn_query`, catch broadly, fall back to sqlite-vec. This preserves existing sqlite-vec path 100% intact for environments without hnswlib.
- Dimension mismatch in `_enrich_with_excerpts` is silently skipped (`len(chunk_vec) != len(query_vec)` check) rather than crashing. The test stub returns 384-dim vectors while the production ANN uses 768-dim — graceful handling required.
- `_enrich_with_excerpts` called at the `search_hybrid` merge point (after RRF), not inside each sub-search function. Calling it in both `search_semantic` and `search_hybrid` would double-enrich results from the semantic sub-call.
- Task 2 required no code changes: both `api.py` and `mcp_server.py` add fields to results but never strip keys, so `excerpt` passes through automatically.

## Deviations from Plan

None - plan executed exactly as written. The only adaptation was the dimension-mismatch guard in `_enrich_with_excerpts` (Rule 2: prevents crash in test environments with 384-dim stubs vs 768-dim production embeddings).

## Issues Encountered

- `test_api_tags.py::TestTagSearch::test_filter_returns_matching` fails — pre-existing, confirmed by reverting our changes and reproducing. Out of scope.

## Next Phase Readiness

- Excerpt field now flows through all search paths and API/MCP surfaces
- Frontend can display excerpt in search results without backend changes
- No blockers for remaining phase 38 plans

---
*Phase: 38-scale-architecture-100k-notes*
*Completed: 2026-03-26*

## Self-Check: PASSED
