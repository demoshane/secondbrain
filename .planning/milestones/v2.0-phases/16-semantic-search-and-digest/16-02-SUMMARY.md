---
phase: 16-semantic-search-and-digest
plan: "02"
subsystem: search
tags: [semantic-search, hybrid-search, rrf, sqlite-vec, bm25, fts5]
dependency_graph:
  requires:
    - 16-01  # Wave 0 RED scaffold with test stubs
    - engine/embeddings.py  # embed_texts for query embedding
    - engine/db.py  # note_embeddings table DDL
  provides:
    - search_semantic()  # sqlite-vec KNN cosine search
    - search_hybrid()    # BM25 + vector RRF fusion
    - _rrf_merge()       # Reciprocal Rank Fusion helper
    - --semantic flag    # sb-search pure vector mode
    - --keyword flag     # sb-search pure BM25 mode
  affects:
    - engine/search.py   # three new functions + updated main()
    - tests/conftest.py  # seeded_db now includes note_embeddings rows
tech_stack:
  added: []
  patterns:
    - "RRF merge: rank-position 1/(k+rank+1) fusion, k=60 default"
    - "sqlite-vec loaded per-connection via conn.enable_load_extension(True)"
    - "main() accepts optional argv list for testability (no sys.argv in tests)"
    - "conftest seeded_db seeds 100 note_embeddings rows with stub BLOBs"
key_files:
  created: []
  modified:
    - engine/search.py
    - tests/conftest.py
    - tests/test_search.py
decisions:
  - "search_semantic returns [] (not FTS5 fallback) when note_embeddings is empty — prints 'Semantic unavailable. Run sb-reindex to enable.'"
  - "search_hybrid silently falls back to FTS5 when search_semantic returns [] (empty table case)"
  - "main() argv parameter added for test injection — avoids sys.argv patching in TestKeywordFlag"
  - "conftest seeded_db seeds 100 note_embeddings rows so TestSemanticSearch can assert len(results) > 0"
  - "Wave 0 test stubs (TestKeywordFlag) needed engine.db.get_connection patching since main() does local import"
metrics:
  duration: "~8 minutes"
  completed: "2026-03-15"
  tasks_completed: 2
  files_modified: 3
---

# Phase 16 Plan 02: Semantic Search and Hybrid RRF Summary

Implemented semantic vector search and hybrid RRF search in `engine/search.py` using sqlite-vec cosine KNN; extended `main()` with `--semantic`/`--keyword` flags making default mode hybrid BM25+vector RRF fusion.

## What Was Built

### New Functions in engine/search.py

**`_rrf_merge(bm25_results, vec_results, k=60, limit=20)`**
Reciprocal Rank Fusion using enumerate-index rank positions (not raw scores). Scores deduplicated by path, sorted descending.

**`search_semantic(conn, query, limit=20)`**
- Loads sqlite-vec per-connection via `enable_load_extension(True)`
- Embeds query using `embed_texts` from `engine.embeddings` (stubbed in tests)
- Runs `vec_distance_cosine` KNN against `note_embeddings` table
- Returns `score = 1.0 - dist` (higher = better)
- Empty table: prints "Semantic unavailable. Run sb-reindex to enable." → returns []
- >50 missing embeddings: prints warning, proceeds with indexed subset
- sqlite-vec load failure: returns []

**`search_hybrid(conn, query, limit=20)`**
- Calls `search_notes(conn, query, limit*2)` for BM25 candidates
- Calls `search_semantic(conn, query, limit*2)` for vector candidates
- Falls back to `bm25[:limit]` on exception or empty vector results
- Returns `_rrf_merge(bm25, vec_results, k=60, limit=limit)`

### Updated main()

Added `argv: list[str] | None = None` parameter for test injection. New mutually exclusive mode group:
- `--semantic`: calls `search_semantic()`
- `--keyword`: calls `search_notes()` (pure BM25, no sqlite-vec)
- default (no flag): calls `search_hybrid()`

Score display and stale nudge hook unchanged.

## Test Results

All 5 Wave 0 test classes GREEN:

| Class | Test | Status |
|-------|------|--------|
| TestSemanticSearch | test_semantic_returns_similar | PASS |
| TestSemanticFallback | test_warns_when_too_many_unembed | PASS |
| TestHybridSearch | test_hybrid_returns_merged_results | PASS |
| TestKeywordFlag | test_keyword_bypasses_vector | PASS |
| TestHybridFallback | test_no_embeddings_falls_back_to_fts | PASS |

Full `test_search.py` (8 tests including pre-existing): all PASS. No regressions introduced.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] conftest seeded_db lacked note_embeddings rows**
- **Found during:** Task 1 GREEN phase
- **Issue:** `TestSemanticSearch.test_semantic_returns_similar` asserts `len(results) > 0` but `seeded_db` had no `note_embeddings` rows. With empty table, `search_semantic` returns `[]`.
- **Fix:** Added embedding seed loop to `seeded_db` fixture — inserts stub BLOBs (`[0.1]*384`) for first 100 notes. Consistent with `stub_engine_embeddings` conftest fixture.
- **Files modified:** `tests/conftest.py`

**2. [Rule 2 - Missing functionality] TestKeywordFlag needed DB patching**
- **Found during:** Task 2 GREEN phase
- **Issue:** `s.main(["topic_0", "--keyword"])` calls `get_connection()` (real filesystem DB). Would fail in test environment.
- **Fix:** Updated `TestKeywordFlag` to patch `engine.db.get_connection` returning `seeded_db`, and `engine.db.init_schema` as no-op.
- **Files modified:** `tests/test_search.py`

**3. [Rule 2 - Missing functionality] main() needed argv parameter for testability**
- **Found during:** Task 2 GREEN phase
- **Issue:** `s.main(["topic_0", "--keyword"])` requires `main()` to accept args, but original signature was `main() -> None` using `sys.argv`.
- **Fix:** Changed to `main(argv: list[str] | None = None)`, passed to `parser.parse_args(argv)`.
- **Files modified:** `engine/search.py`

## Self-Check: PASSED

- engine/search.py: FOUND
- tests/conftest.py: FOUND
- tests/test_search.py: FOUND
- Commit e65c077: FOUND
