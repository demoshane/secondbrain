---
phase: 06-integration-gap-closure
plan: "02"
subsystem: capture
tags: [capture, memory, ai, claude, subprocess]

requires:
  - phase: 06-00
    provides: update_memory() function in engine/ai.py with passing tests

provides:
  - update_memory() call site in capture.py:main() — wired after conn.close(), guarded by sensitivity != "pii", wrapped in try/except
  - main() accepts optional argv parameter for testability

affects:
  - 06-03
  - any future plan touching capture.py:main()

tech-stack:
  added: []
  patterns:
    - "Deferred import inside if-block: `from engine.ai import update_memory` inside try block — best-effort import pattern consistent with add_backlinks"
    - "Best-effort post-close call: side effects that must not block capture run after conn.close() with try/except logging type(e).__name__"
    - "Patch deferred imports at source module (engine.db.get_connection) not call site (engine.capture.get_connection) — deferred imports are not module-level attributes"

key-files:
  created: []
  modified:
    - engine/capture.py
    - tests/test_capture.py

key-decisions:
  - "Deferred import (`from engine.ai import update_memory` inside try block) consistent with add_backlinks pattern — avoids circular import and keeps import failure caught by try/except"
  - "argv=None parameter added to main() — xfail stub tests required it; consistent with argparse convention"
  - "Patch target for deferred imports is source module (engine.db.get_connection), not call site module (engine.capture.get_connection) — Python 3.14 unittest.mock requirement"

patterns-established:
  - "Post-capture best-effort hooks: after conn.close(), before print(path) — memory update, potential future hooks follow this slot"

requirements-completed:
  - CAP-06

duration: 15min
completed: 2026-03-14
---

# Phase 6 Plan 02: CAP-06 Memory Update Call Site Summary

**CAP-06 wired: capture.py:main() now calls update_memory() after every non-PII capture, best-effort, outside DB transaction**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-14T22:47:51Z
- **Completed:** 2026-03-14T23:02:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- update_memory() call site inserted between conn.close() and print(str(path)) in capture.py:main()
- PII guard: sensitivity != "pii" check ensures memory never updated for PII notes
- try/except wrapper: any exception (ImportError, subprocess, filesystem) is caught and logged — capture never blocked
- main() now accepts optional argv parameter — enables hermetic unit testing without sys.argv
- xfail CAP-06 stubs promoted to real passing tests with correct patch targets

## Task Commits

1. **Task 1: Wire update_memory() call site in capture.py:main()** - `b8c3446` (feat)

## Files Created/Modified

- `engine/capture.py` — main() now accepts argv=None; update_memory() call site inserted after conn.close()
- `tests/test_capture.py` — xfail markers removed from CAP-06 tests; patch targets corrected to source modules

## Decisions Made

- Deferred import pattern (`from engine.ai import update_memory` inside try block) — consistent with existing add_backlinks deferred import in capture_note(); ImportError caught automatically
- argv=None added to main() — the pre-existing xfail stubs called `main([...])` with explicit argv; this param was always the intended interface
- Patch deferred imports at source module not call site — `engine.db.get_connection` patches correctly; `engine.capture.get_connection` does not exist as module attribute (Python 3.14 unittest.mock is strict about this)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed patch targets in CAP-06 test stubs**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Pre-existing xfail stubs patched `engine.capture.get_connection` etc. — these are deferred imports, not module-level attributes of engine.capture; patching them raises AttributeError in Python 3.14
- **Fix:** Changed patch targets to source modules: `engine.db.get_connection`, `engine.db.init_schema`, `engine.db.migrate_add_people_column`, `engine.ai.ask_followup_questions`, `engine.classifier.classify`
- **Files modified:** tests/test_capture.py
- **Verification:** All 7 test_capture tests pass GREEN
- **Committed in:** b8c3446 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in pre-existing test stubs)
**Impact on plan:** Fix necessary for tests to pass at all; no scope change.

## Issues Encountered

Pre-existing XPASS(strict) in `tests/test_reindex.py::test_reindex_stores_absolute_paths` — the SEARCH-01 fix was already applied in a prior session but the xfail marker was not removed. Logged to `deferred-items.md`. Out of scope for this plan.

## Next Phase Readiness

- CAP-06 complete: memory update fires after every non-PII capture
- Full suite: 98 passed, 5 skipped, 1 xfailed — only pre-existing test_reindex XPASS blocks -x run (deferred)
- Ready for 06-03

---
*Phase: 06-integration-gap-closure*
*Completed: 2026-03-14*
