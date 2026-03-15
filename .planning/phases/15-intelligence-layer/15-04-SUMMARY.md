---
phase: 15-intelligence-layer
plan: "04"
subsystem: intelligence
tags: [intelligence, budget-gate, connection-suggestions, tdd, pytest]

requires:
  - phase: 15-03
    provides: check_stale_nudge with budget gate; budget_available/consume_budget implemented; 17 INTL tests GREEN

provides:
  - check_connections() gated by budget_available(conn) — returns silently when budget exhausted
  - check_connections() calls consume_budget() after printing suggestions
  - TestConnectionSuggestionBudgetExhausted asserting silence on exhausted budget

affects: [phase-16, phase-17, any future proactive-notification work]

tech-stack:
  added: []
  patterns:
    - "Budget gate pattern: budget_available(conn) guard as first statement inside try block before any work"
    - "Budget consume pattern: consume_budget() called after side-effecting output, inside try block"

key-files:
  created: []
  modified:
    - engine/intelligence.py
    - tests/test_intelligence.py

key-decisions:
  - "INTL-10: check_connections() and check_stale_nudge() both gate on budget_available() — at most one unsolicited offer per day total"
  - "TestConnectionSuggestion patched to include budget_available=True and consume_budget mock — required after budget gate was added"

patterns-established:
  - "Proactive functions follow: guard budget_available → do work → consume_budget; never the reverse"

requirements-completed: [INTL-10]

duration: 8min
completed: 2026-03-15
---

# Phase 15 Plan 04: Budget Gate for check_connections Summary

**INTL-10 closed: check_connections() now gates on budget_available(conn) and consumes budget after printing — single-notification-per-day contract enforced across all proactive functions**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-15T18:05:00Z
- **Completed:** 2026-03-15T18:13:00Z
- **Tasks:** 2 (1 TDD, 1 regression)
- **Files modified:** 2

## Accomplishments
- Added `budget_available(conn)` guard as first statement inside `check_connections()` try block
- Added `consume_budget()` call after the print loop in `check_connections()`
- Added `TestConnectionSuggestionBudgetExhausted` — patches budget to False, asserts no output
- Full suite: 188 passed, 5 skipped, 1 xfailed — zero new failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Add budget gate and consume_budget to check_connections; add exhausted-budget test** - `336eaa4` (feat)
2. **Task 2: Full suite regression check** - verification only, no file changes

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `engine/intelligence.py` - Added budget_available guard and consume_budget call inside check_connections()
- `tests/test_intelligence.py` - Added TestConnectionSuggestionBudgetExhausted; patched TestConnectionSuggestion to mock budget

## Decisions Made
- INTL-10: Both proactive functions (check_connections, check_stale_nudge) now gate on budget_available() and consume it after firing — the single-offer-per-day contract is fully enforced
- TestConnectionSuggestion required patching of budget_available and consume_budget after the guard was added (existing test had no budget mock, so budget_available returned False with empty DB)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TestConnectionSuggestion to mock budget_available and consume_budget**
- **Found during:** Task 1 (GREEN step)
- **Issue:** After adding the budget gate, `TestConnectionSuggestion` failed because it used an empty in-memory DB (0 notes), causing `budget_available()` to return False — test expected output but got silence
- **Fix:** Added `patch.object(intelligence, "budget_available", return_value=True)` and `patch.object(intelligence, "consume_budget")` to the existing test
- **Files modified:** tests/test_intelligence.py
- **Verification:** All 18 INTL tests GREEN after fix
- **Committed in:** `336eaa4` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in test after implementation change)
**Impact on plan:** Necessary correctness fix. No scope creep.

## Issues Encountered
- pyenv Python 3.13 not installed at OS level; used `.venv/bin/python` directly (pre-existing project condition, documented in MEMORY.md)

## Next Phase Readiness
- INTL-10 fully satisfied: both proactive functions gate on budget_available and consume budget
- Intelligence layer (Phase 15) complete: all 18 INTL tests GREEN, 188 total tests GREEN
- Ready for Phase 16 (GUI Hub) or whatever follows

## Self-Check: PASSED

- engine/intelligence.py: FOUND
- tests/test_intelligence.py: FOUND
- Commit 336eaa4: FOUND

---
*Phase: 15-intelligence-layer*
*Completed: 2026-03-15*
