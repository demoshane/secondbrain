---
phase: 27-search-quality-tuning
plan: 01
subsystem: testing
tags: [pytest, xfail, bm25, fts5, search, regression, mcp]

requires: []
provides:
  - "Regression suite (tests/test_search_regression.py) with 10 xfail ranking assertions"
  - "test_sb_edit_preserves_frontmatter xfail stub in tests/test_mcp.py"
affects: [27-02, 27-03]

tech-stack:
  added: []
  patterns:
    - "xfail(strict=False) for Wave 0 stubs — auto-promotes to PASS when implementation ships"
    - "Module-scoped reg_conn fixture with tmp_path_factory for isolated search DB seeding"
    - "PRECISION_NOTES + RECALL_NOTES as module-level constants — decoupled from fixture"

key-files:
  created:
    - tests/test_search_regression.py
  modified:
    - tests/test_mcp.py

key-decisions:
  - "xfail(strict=False) chosen — tests auto-promote to PASS without any code change once Wave 2 ships; strict=True would flip suite to FAIL on improvement"
  - "reg_conn uses get_connection(str(db_path)) with tmp_path_factory scope=module — matches Phase 27.1 isolation pattern; no DB_PATH monkeypatching needed"
  - "search_notes called directly (not via API) in regression suite — pure unit-level ranking assertions unaffected by HTTP layer"
  - "sb_edit called as mcp_mod.sb_edit() directly (not .__wrapped__) — matches existing test_mcp.py style with no monkey-patching"

patterns-established:
  - "Regression fixture pattern: module-scoped isolated DB, insert fixture notes, yield conn"
  - "xfail stub pattern for Phase 27: annotate with reason citing specific Wave that fixes it"

requirements-completed: [ENGL-02]

duration: 5min
completed: 2026-03-17
---

# Phase 27 Plan 01: Search Regression Suite and sb_edit Frontmatter Stub Summary

**10-test xfail regression suite for BM25 ranking quality (5 precision + 5 recall) and sb_edit frontmatter-wipe stub, establishing the Wave 0 RED scaffold before any implementation ships**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-17T17:44:24Z
- **Completed:** 2026-03-17T17:49:30Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `tests/test_search_regression.py` with module-scoped `reg_conn` fixture seeding 10 notes into an isolated DB, plus 10 xfail tests (5 precision, 5 recall) asserting ranking contract
- Appended `test_sb_edit_preserves_frontmatter` xfail stub to `tests/test_mcp.py` — documents the known frontmatter-wipe bug with a concrete assertion
- All 11 tests collected, zero errors, suite exits 0

## Task Commits

1. **Task 1: Create tests/test_search_regression.py with 10 xfail tests** - `2b9ae8c` (test)
2. **Task 2: Add test_sb_edit_preserves_frontmatter stub to tests/test_mcp.py** - `491cd9a` (test)

## Files Created/Modified

- `tests/test_search_regression.py` — New regression suite: PRECISION_NOTES + RECALL_NOTES constants, reg_conn module-scoped fixture, 10 xfail search ranking tests
- `tests/test_mcp.py` — Appended test_sb_edit_preserves_frontmatter xfail stub under Phase 27 Wave 0 section

## Decisions Made

- `xfail(strict=False)` chosen — tests auto-promote to PASS when Wave 2 BM25 tuning ships; `strict=True` would require separate removal PR
- `reg_conn` uses `get_connection(str(db_path))` with `tmp_path_factory` (scope=module) — matches Phase 27.1 isolation pattern, no `DB_PATH` monkeypatching required
- `sb_edit` called as `mcp_mod.sb_edit()` directly (not `.__wrapped__`) — consistent with existing `test_mcp.py` style

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Wave 0 scaffold complete; Wave 1 (BM25 weight tuning) can now be implemented against these xfail contracts
- `test_sb_edit_preserves_frontmatter` stub is ready; sb_edit frontmatter fix (plan 27-02 or later) will promote it to pass

---
*Phase: 27-search-quality-tuning*
*Completed: 2026-03-17*
