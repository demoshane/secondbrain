---
phase: 16-semantic-search-and-digest
plan: "03"
subsystem: intelligence
tags: [recap, entity-recap, pii-routing, semantic-search, srch-03, srch-04]
dependency_graph:
  requires: [16-02]
  provides: [recap_entity, entity-recap-cli]
  affects: [engine/intelligence.py, tests/conftest.py]
tech_stack:
  added: []
  patterns: [pii-aware-routing, tagged-people-lookup, hybrid-search-supplement]
key_files:
  created: []
  modified:
    - engine/intelligence.py
    - tests/conftest.py
decisions:
  - "recap_entity returns string (not None) to satisfy TestRecapEntity assertion on result length; also prints to stdout for CLI use"
  - "Tagged people/tags query is authoritative source; search_hybrid results are supplementary (title-match filtered) to prevent false positives from FTS stub returning unrelated notes"
  - "seeded_db fixture extended with 3 alice PII meeting notes so TestRecapEntity* have data without requiring real notes on disk"
  - "Tasks 1 and 2 (recap_entity + recap_main update) committed together since both modify engine/intelligence.py"
metrics:
  duration: "5 minutes"
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_changed: 2
requirements:
  - SRCH-03
  - SRCH-04
---

# Phase 16 Plan 03: Entity Recap with PII Routing Summary

**One-liner:** `recap_entity(name, conn)` with people/tags-authoritative note lookup, PII-to-Ollama / public-to-Claude routing, and empty-state guard for unknown entities.

## What Was Built

Added `recap_entity(name, conn) -> str | None` to `engine/intelligence.py` and updated `recap_main()` to route explicit entity name arguments through it.

### recap_entity() behavior

1. **Note discovery:** Runs `people LIKE %name%` / `tags LIKE %name%` SQL query as the authoritative match. Supplements with `search_hybrid()` results filtered to title-mentions only (prevents FTS stub false positives).
2. **Empty state:** Prints `No notes found about '{name}'. Capture a meeting or note to build context.` and returns `None`.
3. **PII routing:** Splits notes into `pii` (sensitivity == "pii") and non-pii groups. PII notes go to `_router.get_adapter("pii", CONFIG_PATH)` (Ollama); others go to `_router.get_adapter("public", CONFIG_PATH)` (Claude).
4. **Body truncation:** Each note body capped at 500 chars before synthesis.
5. **Return value:** Returns the combined summary string (also prints to stdout); returns `None` on empty.

### recap_main() update

`recap_main()` now checks `args.context` first. If explicitly provided, delegates to `recap_entity(args.context, conn)` and returns. No-argument invocation falls through to the original git-context session recap, preserving full backward compatibility.

### conftest.py update

`seeded_db` fixture extended with 3 synthetic `alice` PII meeting notes so `TestRecapEntity*` tests have data without needing real vault files.

## Test Results

| Class | Tests | Status |
|-------|-------|--------|
| TestRecapEntity | 1 | GREEN |
| TestRecapEntityEmpty | 1 | GREEN |
| TestRecapEntityPIIRouting | 1 | GREEN |
| All TestRecap* (prior) | 2 | GREEN |
| Full test_intelligence.py | 21 | GREEN |

Pre-existing RED stubs in `test_digest.py` and `test_read.py` (Plan 16-04 scope) remain unchanged.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] search_hybrid returns false positives for unknown entities**
- **Found during:** Task 1 verification (TestRecapEntityEmpty failing)
- **Issue:** `search_hybrid` falls back to `bm25[:limit]` which, with stub embeddings returning identical vectors for all 100 seeded notes, caused results to appear even for "unknown_xyz_entity_404"
- **Fix:** Changed merge logic so `hybrid_results` are only added to `merged_paths` if the entity name appears in the result's title (lower-case substring match). The `tagged` SQL query remains the authoritative source.
- **Files modified:** `engine/intelligence.py`
- **Commit:** 0f1a5bc

**2. [Rule 2 - Missing return value] recap_entity must return string, not None**
- **Found during:** Reading TestRecapEntity (`assert result is not None; assert len(result) > 0`)
- **Issue:** Plan spec says "returns None (prints to stdout directly)" but test expects a non-empty return value
- **Fix:** Implemented `recap_entity` to both print and return the summary string; returns `None` only on empty state
- **Files modified:** `engine/intelligence.py`
- **Commit:** 0f1a5bc

**3. [Scope] Tasks 1 and 2 committed in single commit**
- Both tasks modify `engine/intelligence.py` only; `recap_main()` update was implemented alongside `recap_entity()` in the same editing pass. Single commit captures both.

## Commits

| Hash | Message |
|------|---------|
| 0f1a5bc | feat(16-03): implement recap_entity() with PII-aware synthesis routing |

## Self-Check

- [x] `engine/intelligence.py` modified — recap_entity + recap_main updated
- [x] `tests/conftest.py` modified — seeded_db has alice PII notes
- [x] Commit 0f1a5bc exists
- [x] `from engine.intelligence import recap_entity` — import OK
- [x] 21/21 test_intelligence.py tests GREEN
