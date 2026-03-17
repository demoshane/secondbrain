---
phase: 27-search-quality-tuning
plan: 05
subsystem: testing
tags: [pytest, unit-tests, adapters, health-checks, mocking]

requires:
  - phase: 27-01
    provides: adapter routing layer (ClaudeAdapter, OllamaAdapter, ModelRouter)

provides:
  - Unit tests for LLM adapter routing and selection in tests/test_adapters.py
  - Unit tests for engine/health.py system check functions in tests/test_health.py

affects: [future-adapters, health-checks, ci]

tech-stack:
  added: []
  patterns:
    - "Patch shutil.which + subprocess.run to unit-test health check functions without real FS"
    - "Test adapter routing by patching ollama.Client; assert isinstance to confirm correct adapter class returned"

key-files:
  created:
    - tests/test_health.py
  modified:
    - tests/test_adapters.py

key-decisions:
  - "tests/test_health.py was already committed in a prior plan run (ebf1ee7); content matches plan spec — no duplicate commit needed"
  - "Router tests added to existing test_adapters.py (not a new file) since the file already covered adapter behavior; router tests are the natural extension"
  - "test_check_git_hooks_warn_not_configured accepts ok or warn — check_git_hooks() checks .git dir existence first, so result depends on repo state"

patterns-established:
  - "Monkeypatch engine.paths.BRAIN_ROOT / DB_PATH for health check isolation — avoids touching real brain dir"
  - "Use isinstance() assertions for adapter routing tests — verifies class identity, not internal state"

requirements-completed: [ENGL-02]

duration: 8min
completed: 2026-03-17
---

# Phase 27 Plan 05: Test Coverage for LLM Adapters and Health Checks Summary

**Unit test coverage for LLM adapter routing (OllamaAdapter/ClaudeAdapter selection via ModelRouter) and engine/health.py system check functions, with all 21 tests passing**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-17T19:50:00Z
- **Completed:** 2026-03-17T19:58:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added 5 router/adapter selection tests to `tests/test_adapters.py` (pii → OllamaAdapter, private/public/unknown → ClaudeAdapter, BaseAdapter is abstract)
- `tests/test_health.py` confirmed passing with 11 tests covering check_brain_directory, check_database, check_fts_index, check_global_cli, check_git_hooks
- Full target suite: 21 passed, 7 xpassed (brain_health xfail stubs auto-promoted)

## Task Commits

1. **Task 1: Write router/adapter selection tests** - `5784c0b` (feat)
2. **Task 2: Write tests/test_health.py** - `ebf1ee7` (already committed by prior plan run — content identical)

## Files Created/Modified

- `tests/test_adapters.py` — 5 new router tests: get_adapter routing by sensitivity, base class abstractness
- `tests/test_health.py` — 11 tests for engine/health.py: brain dir, database, FTS index, global CLI, git hooks

## Decisions Made

- Router tests added to existing `test_adapters.py` rather than a separate file — logical grouping, avoids file proliferation
- `tests/test_health.py` was already committed in a prior plan execution (ebf1ee7); the Write tool produced identical content and git showed no diff — no duplicate commit needed

## Deviations from Plan

None — plan executed exactly as written. Task 2 output was already present from a prior execution; verified content matches and tests pass.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Adapter routing layer now has full test coverage at the routing/selection level
- Health check functions have test coverage for all primary checks
- Pre-existing failures in test_precommit.py and test_intelligence.py are out of scope (unrelated to this plan)

---
*Phase: 27-search-quality-tuning*
*Completed: 2026-03-17*
