---
phase: 35-brain-consolidation
plan: 02
subsystem: database, api, mcp
tags: [sqlite, brain-health, stub-detection, connection-cleanup, mcp]

requires:
  - phase: 35-brain-consolidation
    plan: 01
    provides: merge_notes() in engine/brain_health.py — needed for merge-first workflow context

provides:
  - get_stub_notes() in engine/brain_health.py — returns notes with < 50 words (D-04)
  - delete_dangling_relationships() in engine/brain_health.py — removes stale graph edges (D-07)
  - get_bidirectional_gaps() in engine/brain_health.py — flags one-way relationships (D-07)
  - sb_find_stubs MCP tool — stubs with similarity matches, merge/enrich routing (D-05, D-06)
  - sb_cleanup_connections MCP tool — deletes dangling + flags gaps, returns counts (D-08, D-09)
  - GET /brain-health response extended with stub_count and stub_notes fields

affects:
  - 35-03 (orphan cleanup — connection cleanup functions may reduce orphan count)
  - future GUI improvements to health panel (stub_count now in API response)

tech-stack:
  added: []
  patterns:
    - "get_stub_notes uses LENGTH(body) < 400 as DB pre-filter, Python word count for exact boundary"
    - "delete_dangling_relationships uses single DELETE with NOT IN subqueries — O(n) on notes table"
    - "get_bidirectional_gaps uses NOT EXISTS correlated subquery for clean asymmetry detection"
    - "sb_find_stubs catches store_path ValueError silently — paths outside BRAIN_ROOT still work"

key-files:
  created:
    - .planning/phases/35-brain-consolidation/35-02-SUMMARY.md
  modified:
    - engine/brain_health.py
    - engine/mcp_server.py
    - engine/api.py
    - tests/test_brain_health.py
    - tests/test_mcp.py

key-decisions:
  - "test_get_stub_notes_includes_empty uses empty string not NULL — notes.body has NOT NULL DEFAULT '' constraint, so NULL is impossible via normal insert path"
  - "sb_find_stubs silently catches find_similar exceptions — embeddings may not exist for all stubs, missing embeddings should not crash the tool"
  - "get_bidirectional_gaps flags gaps for review only, not auto-create — per D-07 design intent"

requirements-completed:
  - CONS-02
  - CONS-03

duration: 15min
completed: 2026-03-23
---

# Phase 35 Plan 02: Stub Detection + Connection Cleanup Summary

**get_stub_notes() / delete_dangling_relationships() / get_bidirectional_gaps() in brain_health.py; sb_find_stubs and sb_cleanup_connections MCP tools with merge-first routing; health API stub_count field**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-23T12:30:00Z
- **Completed:** 2026-03-23T12:45:15Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `get_stub_notes(conn, word_limit=50)` returns notes with body < 50 words using LENGTH pre-filter + Python count for accuracy — superset of `get_empty_notes()`
- `delete_dangling_relationships(conn)` deletes edges where source or target is absent from notes table; returns deleted count
- `get_bidirectional_gaps(conn)` identifies A->B relationships lacking a reciprocal B->A, filtered to valid nodes only
- `sb_find_stubs` enriches each stub with `find_similar` matches: routes as `merge` (has match) or `enrich` (no match)
- `sb_cleanup_connections` combines delete + gaps in one call; returns `deleted_dangling` count + `bidirectional_gaps` list + `gap_count`
- Health API now includes `stub_count` and `stub_notes[:20]` in `/brain-health` response
- 6 TDD tests + 1 MCP integration test, all green

## Task Commits

1. **Task 1: get_stub_notes() + cleanup functions + TDD tests** - `fcb2088` (feat + test)
2. **Task 2: MCP tools + API + MCP test** - `5e1c766` (feat)

## Files Created/Modified

- `engine/brain_health.py` — added `get_stub_notes()`, `delete_dangling_relationships()`, `get_bidirectional_gaps()`
- `engine/mcp_server.py` — added `sb_find_stubs` and `sb_cleanup_connections` tools
- `engine/api.py` — `GET /brain-health` now includes `stub_count` and `stub_notes`
- `tests/test_brain_health.py` — 6 tests covering word count, empty body, dangling delete, valid keep, gap detection, gap-excludes-dangling
- `tests/test_mcp.py` — `test_find_stubs_with_matches` confirms similar_notes and action fields

## Decisions Made

- `test_get_stub_notes_includes_empty` tests empty string `""` not NULL — the schema enforces `NOT NULL DEFAULT ''` on `notes.body`, so NULL inserts fail at the DB layer. The function handles NULL defensively but can't be triggered via normal test insert. Testing empty string covers the real-world case.
- `sb_find_stubs` wraps `find_similar` in a silent try/except — stubs by definition have short bodies and may have no embeddings; the tool must return the stub list even when similarity lookup fails.
- Bidirectional gaps are flagged for manual review only (per D-07 design intent). Auto-creating reverse links would corrupt the graph with false relationships.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_get_stub_notes_includes_empty: NULL insert fails schema constraint**
- **Found during:** Task 1 (TDD GREEN phase)
- **Issue:** Plan spec said "Insert note with NULL body" but `notes.body` has `NOT NULL DEFAULT ''` constraint — SQLite raised `IntegrityError: NOT NULL constraint failed: notes.body`
- **Fix:** Changed test to insert empty string `""` body, which covers the same semantic case (empty body as stub)
- **Files modified:** tests/test_brain_health.py
- **Verification:** test_get_stub_notes_includes_empty passes after fix
- **Committed in:** fcb2088 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — Bug)
**Impact on plan:** Minor test correction; function behavior unchanged. Plan spec's NULL handling is still covered by the function implementation (defensive `or ""` guard), just not triggered by normal DB inserts.

## Known Stubs

None — all stub detection and connection cleanup functionality is fully wired.

## Self-Check: PASSED

- engine/brain_health.py: FOUND (`get_stub_notes`, `delete_dangling_relationships`, `get_bidirectional_gaps`)
- engine/mcp_server.py: FOUND (`sb_find_stubs`, `sb_cleanup_connections`)
- engine/api.py: FOUND (`stub_count`)
- tests/test_brain_health.py: FOUND (`test_get_stub_notes_word_count`, `test_delete_dangling_relationships`, `test_bidirectional_gap_detection`)
- tests/test_mcp.py: FOUND (`test_find_stubs_with_matches`)
- commit fcb2088: FOUND
- commit 5e1c766: FOUND

---
*Phase: 35-brain-consolidation*
*Completed: 2026-03-23*
