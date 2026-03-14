---
phase: 02-storage-and-index
plan: "00"
subsystem: testing
tags: [pytest, tdd, sqlite, conftest]

requires:
  - phase: 01-foundation
    provides: engine.db (init_schema, db_conn fixture), conftest.py base fixtures, uv test runner pattern

provides:
  - Failing test stubs for all Phase 2 requirements (11 tests across 3 files)
  - seeded_db fixture (1000 synthetic notes for perf tests)
  - initialized_db fixture (schema-only DB for capture tests)

affects: [02-01-PLAN, 02-02-PLAN, 02-03-PLAN]

tech-stack:
  added: []
  patterns:
    - "Deferred imports inside test bodies so pytest --collect-only succeeds before engine modules exist"
    - "seeded_db builds on db_conn fixture — schema via init_schema then bulk INSERT 1000 rows"

key-files:
  created:
    - tests/test_capture.py
    - tests/test_search.py
    - tests/test_audit.py
  modified:
    - tests/conftest.py

key-decisions:
  - "Defer engine.capture/engine.search imports to test body (not module level) so --collect-only succeeds while modules are absent"
  - "seeded_db and initialized_db both guard against missing 'people' column via PRAGMA table_info check"

patterns-established:
  - "Phase 2 TDD scaffold: collection clean, all stubs fail RED before any implementation"

requirements-completed: [CAP-01, CAP-02, CAP-03, CAP-07, SEARCH-01, SEARCH-02, GDPR-03, GDPR-05, GDPR-06]

duration: 8min
completed: 2026-03-14
---

# Phase 2 Plan 00: Phase 2 Test Scaffold Summary

**Pytest test stubs for all 9 Phase 2 requirements — 11 tests collected cleanly, all failing RED, with seeded_db (1000 notes) and initialized_db fixtures**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-14T15:15:00Z
- **Completed:** 2026-03-14T15:23:00Z
- **Tasks:** 4 (conftest update + 3 test files)
- **Files modified:** 4

## Accomplishments

- Added `seeded_db` and `initialized_db` fixtures to conftest.py for Phase 2 tests
- Created test_capture.py with 5 stubs covering CAP-01, CAP-02, CAP-03, CAP-07, GDPR-05
- Created test_search.py with 3 stubs covering SEARCH-01, SEARCH-02 (incl. 1000-note perf test)
- Created test_audit.py with 3 stubs covering GDPR-03, GDPR-06, detect-secrets baseline

## Task Commits

Each task was committed atomically:

1. **All test files + conftest** - `fe97d1d` (test: Phase 2 failing test stubs and conftest fixtures)

## Files Created/Modified

- `tests/conftest.py` — Added seeded_db (1000 synthetic notes) and initialized_db fixtures
- `tests/test_capture.py` — 5 stubs for capture requirements (engine.capture not yet implemented)
- `tests/test_search.py` — 3 stubs for search requirements (engine.search not yet implemented)
- `tests/test_audit.py` — 3 stubs for audit/GDPR requirements

## Decisions Made

- Deferred `from engine.capture import ...` and `from engine.search import ...` to inside test bodies (not module-level) so `pytest --collect-only` succeeds cleanly before Plans 01-02 exist. This is the correct RED state: collection passes, execution fails.
- Both `seeded_db` and `initialized_db` guard against the missing `people` column via `PRAGMA table_info` check, matching the pattern established in Phase 1 reindex tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Moved imports to test body to fix collection failures**
- **Found during:** Verification (--collect-only)
- **Issue:** Plan specified top-level `from engine.capture import ...` which causes ImportError at collection time, failing the success criterion of "11 tests collected, 0 errors"
- **Fix:** Moved all engine.capture / engine.search imports inside each test function body; collection now passes, tests still fail RED at runtime
- **Files modified:** tests/test_capture.py, tests/test_search.py, tests/test_audit.py
- **Verification:** `pytest --collect-only -q` shows 11 tests, 0 errors; running tests shows 11 FAILED
- **Committed in:** fe97d1d

---

**Total deviations:** 1 auto-fixed (Rule 1 - correctness bug in import placement)
**Impact on plan:** Required to satisfy the plan's own success criterion. No scope creep.

## Issues Encountered

None beyond the import placement deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 11 failing test stubs ready for Plans 01-03 to make them pass
- `seeded_db` fixture ready for search perf test (test_search_1000_notes_perf)
- `initialized_db` fixture ready for capture/audit tests
- Pre-commit hooks passed cleanly — detect-secrets found no issues

---
*Phase: 02-storage-and-index*
*Completed: 2026-03-14*
