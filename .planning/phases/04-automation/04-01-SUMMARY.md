---
phase: 04-automation
plan: "01"
subsystem: database
tags: [sqlite, backlinks, relationships, orphan-check, links, people]

requires:
  - phase: 04-00
    provides: stub engine/links.py and test scaffold

provides:
  - add_backlinks() — appends [[note_path]] to person file, idempotent, best-effort DB insert
  - check_links() — returns orphan dicts for source/target missing from relationships table
  - main_check_links() — CLI entry point for sb-check-links
  - capture_note() wired to call add_backlinks() after every successful atomic write

affects: [04-02, 04-03, 04-04, 04-05, 04-06]

tech-stack:
  added: []
  patterns:
    - Deferred import of add_backlinks inside capture_note() body to avoid circular imports
    - INSERT OR IGNORE for idempotent relationship rows — same primary key (source, target, rel_type)
    - Backlink append is text-level idempotency check before write (str(note_path) in text)
    - add_backlinks() wraps DB insert in try/except — relationship is best-effort, never blocks capture

key-files:
  created:
    - engine/links.py
    - tests/test_links.py
  modified:
    - engine/capture.py

key-decisions:
  - "add_backlinks() is best-effort: DB insert failure caught silently so capture is never blocked"
  - "Deferred import (from engine.links import add_backlinks inside function body) avoids circular import"
  - "Backlink idempotency via str(note_path) in text check before appending — INSERT OR IGNORE handles DB dedup"
  - "test_work_templates_exist kept as xfail(strict=False) — templates already existed from 04-03 but marker preserved"

patterns-established:
  - "Best-effort side effects: wrap in try/except, never raise from add_backlinks"
  - "Orphan detection: check_links queries relationships table and verifies both ends exist on disk"

requirements-completed: [PEOPLE-03, PEOPLE-04, PEOPLE-05, SEARCH-03]

duration: 12min
completed: 2026-03-14
---

# Phase 4 Plan 01: Backlink Maintenance and Orphan Checker Summary

**Bidirectional backlink engine using SQLite relationships table — add_backlinks() appends wiki-links to person profiles on capture, check_links() reports orphaned relationship rows**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-14T18:12:58Z
- **Completed:** 2026-03-14T18:25:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `engine/links.py` fully implemented: `add_backlinks()`, `check_links()`, `main_check_links()`
- `capture_note()` in `engine/capture.py` now calls `add_backlinks()` after every successful atomic write when `people` list is non-empty
- 7 unit tests in `tests/test_links.py` all pass; `test_work_templates_exist` is xfail(strict=False)

## Task Commits

Both tasks were already committed in prior session as part of commit 78f6fd3 (feat(04-03)):

1. **Task 1: Implement engine/links.py** - `78f6fd3` (feat)
2. **Task 2: Wire add_backlinks into capture_note()** - `78f6fd3` (feat)

_Note: Both tasks landed in a single prior-session commit. Full test suite: 76 passed, 0 failures._

## Files Created/Modified

- `engine/links.py` — add_backlinks(), check_links(), main_check_links() full implementations
- `tests/test_links.py` — 8 tests (7 passing, 1 xfail for templates pending 04-03)
- `engine/capture.py` — deferred add_backlinks() call after write_note_atomic() succeeds

## Decisions Made

- `add_backlinks()` wraps its DB insert in a bare `except Exception: pass` — relationship rows are best-effort; a DB failure must never block the note write that already succeeded
- Deferred import pattern (`from engine.links import add_backlinks` inside function body) avoids circular imports between capture and links modules
- Idempotency at two levels: text-level (`str(note_path) in text`) before file write, DB-level (`INSERT OR IGNORE`) for the relationship row

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed broken monkeypatch in test_cli_no_orphans**
- **Found during:** Task 1 (TDD GREEN phase)
- **Issue:** Initial test used `monkeypatch.setattr("engine.links.main_check_links.__globals__", {})` which raises `AttributeError: readonly attribute` in Python 3.14
- **Fix:** Replaced with proper module-level monkeypatching of `engine.db.get_connection`, `engine.db.init_schema`, and `engine.paths.BRAIN_ROOT`
- **Files modified:** tests/test_links.py
- **Verification:** test_cli_no_orphans passes
- **Committed in:** 78f6fd3 (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test setup)
**Impact on plan:** Necessary correction for test validity. No scope creep.

## Issues Encountered

- Both tasks were already committed in a prior session (78f6fd3) — execution confirmed existing implementation matched the plan spec exactly. Full test suite verified green before proceeding to summary.

## Next Phase Readiness

- `add_backlinks()` and `check_links()` are complete and tested — ready for use in watcher (04-04) and any future automation that captures meeting notes with people references
- `sb-check-links` CLI entry point registered (pending pyproject.toml entry in 04-00 or later plan)

---
*Phase: 04-automation*
*Completed: 2026-03-14*
