---
phase: 08-fix-update-memory-routing
plan: "00"
subsystem: testing
tags: [pytest, tdd, mock, update_memory, routing, ai]

requires:
  - phase: 03-ai-layer
    provides: engine.router.get_adapter and update_memory() implementation
  - phase: 06-integration-gap-closure
    provides: update_memory() deferred-import pattern confirmed

provides:
  - RED test test_update_memory_routing_uses_config in tests/test_ai.py asserting get_adapter is called by update_memory()

affects:
  - 08-01-fix (implementation plan that will turn this test GREEN)

tech-stack:
  added: []
  patterns:
    - "patch engine.router.get_adapter (module ref) to intercept routing calls inside update_memory()"

key-files:
  created: []
  modified:
    - tests/test_ai.py

key-decisions:
  - "Patch target is engine.router.get_adapter (module ref pattern) — consistent with Phase 3/4/4.1 decisions in STATE.md"

patterns-established:
  - "Nyquist RED stub committed before fix plan runs — guarantees regression protection"

requirements-completed:
  - AI-05

duration: 3min
completed: 2026-03-15
---

# Phase 08 Plan 00: Fix Update Memory Routing — RED Stub Summary

**RED test asserting update_memory() calls get_adapter("public", config_path) — currently fails because implementation hardcodes ClaudeAdapter() and never routes through ModelRouter**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-15T09:36:27Z
- **Completed:** 2026-03-15T09:39:30Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Added `test_update_memory_routing_uses_config` to tests/test_ai.py
- Confirmed test is RED: `AssertionError: Expected 'get_adapter' to be called once. Called 0 times.`
- All 5 pre-existing tests in test_ai.py remain GREEN (1 failed, 5 passed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add RED test for update_memory() routing** - `84505b0` (test)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `tests/test_ai.py` - Appended `test_update_memory_routing_uses_config` after `test_cap06_memory_update_uses_write_tool`

## Decisions Made
- Patch target is `engine.router.get_adapter` (module ref, not from-import) — consistent with existing pattern documented in STATE.md Phase 3 decisions

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- `uv run --no-project --with pytest tests/test_ai.py::test_id` with bare test path failed ("No such file or directory") — resolved by using `python -m pytest /absolute/path`. Not a deviation; shell cwd reset between Bash calls (documented environment constraint).

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- RED test stub committed and confirmed failing with correct AssertionError
- Ready for 08-01 (GREEN implementation): wire `engine.router.get_adapter("public", config_path)` inside `update_memory()`

---
*Phase: 08-fix-update-memory-routing*
*Completed: 2026-03-15*
