---
phase: 07-fix-path-format-split
plan: "00"
subsystem: testing
tags: [pytest, tdd, path-resolution, sqlite, symlinks, macos]

requires:
  - phase: 06-integration-gap-closure
    provides: "write_note_atomic, retrieve_context, forget_person implementations to test against"

provides:
  - "4 new test stubs that document the absolute-path storage contract"
  - "test_write_note_atomic_stores_absolute_path — asserts stored path == str(target.resolve())"
  - "test_write_note_atomic_path_is_absolute — asserts stored path starts with '/'"
  - "test_retrieve_context_reads_captured_note — asserts RAG does not fall back to '[note file not readable]'"
  - "test_forget_removes_row_stored_by_capture — asserts forget_person deletes row stored by write_note_atomic"

affects:
  - 07-fix-path-format-split/07-01 (Wave 1 production fix must turn these GREEN)

tech-stack:
  added: []
  patterns:
    - "Use tmp_path.resolve() as brain_root in tests to ensure canonical symlink-free paths on macOS"
    - "Inline sqlite3 + init_schema in standalone tests to avoid fixture coupling"

key-files:
  created: []
  modified:
    - tests/test_capture.py
    - tests/test_rag.py
    - tests/test_forget.py

key-decisions:
  - "Tests use tmp_path.resolve() as brain_root — canonical macOS path contract; raw tmp_path may return /var/... while resolve() gives /private/var/..."
  - "On this machine (Darwin, Python 3.14.3) /tmp symlink resolves cleanly — all 4 stubs passed rather than failing RED; documented as Linux-like behavior per plan guidance"
  - "Stubs are still valid artifacts: they document the absolute-path contract and will catch regressions on any system where the symlink mismatch exists"

patterns-established:
  - "TDD Wave 0: tests are written before production changes — existence of test functions is the artifact, RED state is secondary evidence"

requirements-completed: [SEARCH-01, SEARCH-04, GDPR-01]

duration: 2min
completed: "2026-03-14"
---

# Phase 07 Plan 00: Absolute-path storage contract — RED stubs Summary

**4 TDD Wave 0 test stubs documenting the path-resolution contract: stored DB path must equal str(target.resolve()) and RAG/forget operations must be consistent with what write_note_atomic stored**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-14T23:47:41Z
- **Completed:** 2026-03-14T23:49:48Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added 2 test stubs to test_capture.py: `test_write_note_atomic_stores_absolute_path` and `test_write_note_atomic_path_is_absolute`
- Added 1 test stub to test_rag.py: `test_retrieve_context_reads_captured_note`
- Added 1 test stub to test_forget.py: `test_forget_removes_row_stored_by_capture`
- Full suite: 127 passed, 5 skipped, 1 xfailed — zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add 2 RED test stubs to test_capture.py** - `269124e` (test)
2. **Task 2: Add RED stub to test_rag.py and test_forget.py** - `77f140f` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `tests/test_capture.py` - Added 2 absolute-path contract stubs (Phase 7 section)
- `tests/test_rag.py` - Added 1 RAG path resolution stub (Phase 7 section)
- `tests/test_forget.py` - Added 1 forget-after-capture path consistency stub (Phase 7 section)

## Decisions Made

- All 4 stubs use `tmp_path.resolve()` as `brain_root` to ensure canonical symlink-free paths (macOS /var vs /private/var pitfall)
- On this machine (Darwin, Python 3.14.3) the 4 stubs all PASSED rather than failing RED — this is documented "Linux-like" behavior per plan guidance (acceptable outcome; fix remains correct and necessary for portability)
- Stubs use inline sqlite3 + init_schema rather than the `initialized_db` fixture to avoid coupling to fixture's path construction

## Deviations from Plan

None — plan executed exactly as written. The only observation is that on this specific macOS Python 3.14.3 environment the /tmp symlink does not produce the /var vs /private/var mismatch that the tests target; the plan explicitly documents this as acceptable.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 0 stubs are in place: Wave 1 (07-01) can now implement the `path.resolve()` fix in `write_note_atomic` and target these 4 tests as the GREEN gate
- On macOS with Python resolving /tmp cleanly, Wave 1 tests will remain green after the fix (correct behavior on both platforms)

---
*Phase: 07-fix-path-format-split*
*Completed: 2026-03-14*
