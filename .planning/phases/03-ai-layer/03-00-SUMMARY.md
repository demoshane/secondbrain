---
phase: 03-ai-layer
plan: "00"
subsystem: testing
tags: [pytest, stubs, tdd, red-green, fixtures]

requires:
  - phase: 02-storage-and-index
    provides: conftest.py base fixtures (brain_root, db_conn, seeded_db, initialized_db)

provides:
  - 26 RED test stubs across 5 files covering all Phase 3 AI requirements
  - mock_adapter, tmp_config_toml, mock_subprocess_claude pytest fixtures
  - test_classifier.py (AI-02), test_router.py (AI-03/04/05/06), test_adapters.py, test_ai.py (AI-01/AI-10/CAP-06), test_subagent.py (AI-07/08/09)

affects:
  - 03-01-PLAN (classifier implementation must make test_classifier.py go GREEN)
  - 03-02-PLAN (router/adapters must make test_router.py and test_adapters.py go GREEN)
  - 03-03-PLAN (ai.py must make test_ai.py go GREEN)
  - 03-04-PLAN (subagent files and ratelimit must make test_subagent.py go GREEN)

tech-stack:
  added: []
  patterns:
    - "Defer engine imports to test body so --collect-only succeeds before modules exist"
    - "mock_subprocess_claude returns a patch context manager (not a MagicMock directly)"
    - "Manual YAML frontmatter parsing via str.split(':') — avoids pyyaml dep for subagent tests"

key-files:
  created:
    - tests/test_classifier.py
    - tests/test_router.py
    - tests/test_adapters.py
    - tests/test_ai.py
    - tests/test_subagent.py
  modified:
    - tests/conftest.py

key-decisions:
  - "mock_subprocess_claude is a context manager factory (returns patch()) so tests can use 'with mock_subprocess_claude as mock_run' or 'with mock_subprocess_claude:'"
  - "pyyaml not added as dependency — test_subagent_frontmatter_valid uses manual key extraction via splitlines()"
  - "test_classifier.py already existed from a prior phase stub; kept as-is (covers same AI-02 behaviors)"

patterns-established:
  - "Pattern: All Phase 3 test stubs import engine.* inside test bodies — no top-level import of engine modules"

requirements-completed: [AI-01, AI-02, AI-03, AI-04, AI-05, AI-06, AI-07, AI-08, AI-09, AI-10, CAP-06]

duration: 10min
completed: 2026-03-14
---

# Phase 3 Plan 00: AI Layer Test Stubs Summary

**26 RED pytest stubs across 5 files covering all Phase 3 AI requirements, with mock_adapter, tmp_config_toml, and mock_subprocess_claude fixtures added to conftest.py**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-14T16:45:00Z
- **Completed:** 2026-03-14T16:55:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Extended conftest.py with 3 Phase 3 fixtures (mock_adapter, tmp_config_toml, mock_subprocess_claude)
- Created 5 test stub files covering all Phase 3 requirements (AI-01 through AI-10, CAP-06)
- All 26 tests collect without import-time errors; all are in RED state (engine modules not yet built)

## Task Commits

1. **Task 1: Extend conftest.py with Phase 3 fixtures** - `db5a769` (feat)
2. **Task 2: Write test stubs for all Phase 3 modules** - `a5c6239` (test)

## Files Created/Modified

- `tests/conftest.py` - Added mock_adapter, tmp_config_toml, mock_subprocess_claude fixtures
- `tests/test_classifier.py` - AI-02 classify() unit tests (5 tests); already existed from prior stub
- `tests/test_router.py` - AI-03/04/05/06 get_adapter routing tests (5 tests)
- `tests/test_adapters.py` - OllamaAdapter and ClaudeAdapter unit tests (5 tests)
- `tests/test_ai.py` - AI-01/AI-10/CAP-06 ask_followup_questions and update_memory tests (5 tests)
- `tests/test_subagent.py` - AI-07/08/09 subagent files and rate limiter tests (6 tests)

## Decisions Made

- `mock_subprocess_claude` is a context manager factory returning `patch()` directly — this allows `with mock_subprocess_claude as mock_run:` usage in tests that need to inspect call args.
- pyyaml not added as dependency — `test_subagent_frontmatter_valid` uses manual line-splitting to check for required frontmatter keys.
- `test_classifier.py` already existed from a prior plan stub and covered the same AI-02 behaviors; kept as-is rather than overwriting.

## Deviations from Plan

None — plan executed exactly as written. The pre-existing `test_classifier.py` was compatible with the plan's spec; no overwrite needed.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 26 Phase 3 test stubs are in place and collected by pytest
- Plans 03-01 through 03-05 each have RED tests to drive implementation
- classifier, router, adapters, ai, ratelimit modules must be built to go GREEN

---
*Phase: 03-ai-layer*
*Completed: 2026-03-14*
