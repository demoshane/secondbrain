---
phase: 38-scale-architecture-100k-notes
plan: "06"
subsystem: database
tags: [tiered-storage, summarization, sqlite, llm-adapter, intelligence]

# Dependency graph
requires:
  - phase: 38-01
    provides: "ANN index and scale architecture foundation"
provides:
  - "archived INTEGER column on notes — cold note tiering"
  - "search_notes/search_semantic filter archived=0 by default"
  - "get_archived_count() in brain_health.py"
  - "summary TEXT column on notes — auto-generated summaries"
  - "summarize_note(conn, note_path, force=False) in intelligence.py"
  - "summarize_unsummarized(conn, limit) batch function"
affects: [brain_health, search, intelligence, api, mcp_server]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tiered storage: archived flag excludes cold notes from default search"
    - "LLM summarization via router adapter pattern (no direct API key)"
    - "Idempotent migration with PRAGMA table_info column check"

key-files:
  created:
    - tests/test_tiered_storage.py
    - tests/test_summarization.py
  modified:
    - engine/db.py
    - engine/search.py
    - engine/api.py
    - engine/brain_health.py
    - engine/intelligence.py

key-decisions:
  - "summarize_note uses _router.get_adapter('public') — consistent with recap_entity pattern, not direct call_claude"
  - "SUMMARY_THRESHOLD=2000 chars, SUMMARY_MAX_INPUT=8000 chars — balance coverage vs token cost"
  - "summarize_note returns existing_summary on cache hit (force=False) — idempotent by default"
  - "Archived notes excluded via WHERE archived=0 in search_notes and search_semantic"

patterns-established:
  - "Column migration: PRAGMA table_info check → ALTER TABLE → commit"
  - "LLM feature in intelligence.py: threshold gate → cache check → adapter.generate → UPDATE → commit"

requirements-completed:
  - SCALE-05
  - SCALE-07

# Metrics
duration: 25min
completed: 2026-03-26
---

# Phase 38 Plan 06: Tiered Storage and Summarization Summary

**Archived-note cold-tier flag with search exclusion, plus LLM-powered summarize_note() storing results in notes.summary column**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-03-26T14:55:00Z
- **Completed:** 2026-03-26T15:20:00Z
- **Tasks:** 2 (Task 1 pre-committed; Task 2 completed in this session)
- **Files modified:** 7

## Accomplishments

- Archived notes (archived=1) are excluded from default FTS5 and semantic search — cold notes don't pollute active search results
- `get_archived_count()` added to `brain_health.py` — health reports include cold tier volume
- `/notes` API endpoint accepts `include_archived` param (default false)
- `summarize_note()` generates and stores 2-3 sentence LLM summaries for notes >2000 chars
- `summarize_unsummarized()` batch-processes unsummarized long notes up to a configurable limit
- 20 tests total (10 tiered storage + 10 summarization), all green

## Task Commits

1. **Task 1: Tiered storage — archived flag + search exclusion** - `675fc4c` (feat)
2. **Task 2: Summarization layer for long notes** - `c6d58c5` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `engine/db.py` — `migrate_add_archived_column()`, `migrate_add_summary_column()`, both called from `init_schema()`
- `engine/search.py` — `AND n.archived = 0` added to `search_notes()` and `search_semantic()`
- `engine/api.py` — `/notes` route accepts `include_archived` query param
- `engine/brain_health.py` — `get_archived_count(conn) -> int`
- `engine/intelligence.py` — `SUMMARY_THRESHOLD`, `SUMMARY_MAX_INPUT`, `summarize_note()`, `summarize_unsummarized()`
- `tests/test_tiered_storage.py` — 10 tests covering archived flag, search exclusion, API param, health count
- `tests/test_summarization.py` — 10 tests covering threshold gate, LLM call, DB writeback, cache hit, force flag, batch

## Decisions Made

- `summarize_note` uses `_router.get_adapter("public", CONFIG_PATH)` — matches the recap_entity pattern rather than importing `call_claude` directly. Consistent with intelligence.py adapter usage.
- SUMMARY_THRESHOLD=2000 chars chosen as the breakeven point where summaries add value; SUMMARY_MAX_INPUT=8000 caps token usage.
- Idempotent by default (returns cached summary unless `force=True`) — safe to call on capture without re-generating.

## Deviations from Plan

None — plan executed exactly as written. The `intelligence.py` and `tests/test_summarization.py` were pre-staged on disk but not yet committed; this session committed them.

## Issues Encountered

`test_api_tags.py::TestTagSearch::test_filter_returns_matching` was already failing before this plan (last modified in Phase 23). Confirmed pre-existing, out of scope.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Tiered storage schema ready for archive-note API endpoint or CLI command (future plan)
- Summary column populated on demand; batch summarization available via `summarize_unsummarized()`
- Phase 38 core scale infrastructure complete (ANN index, sharding, chunked embeddings, backup/DR, tiered storage, summarization)

---
*Phase: 38-scale-architecture-100k-notes*
*Completed: 2026-03-26*
