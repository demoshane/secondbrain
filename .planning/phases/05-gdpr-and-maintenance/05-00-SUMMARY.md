---
phase: 05-gdpr-and-maintenance
plan: "00"
subsystem: testing
tags: [pytest, xfail, gdpr, tdd, stubs]

requires:
  - phase: 02-storage-and-index
    provides: engine.db.init_schema used in brain_tmp fixture
  - phase: 03-ai-layer
    provides: engine.search.search_notes referenced in test_search_zero_after_forget

provides:
  - 6 xfail test stubs covering GDPR-01 (person erasure) and GDPR-02 (meeting cleanup)
  - 4 xfail test stubs covering GDPR-04 (PII passphrase gate)
  - engine/forget.py stub with forget_person() signature
  - engine/read.py stub with read_note() signature
  - sb-forget and sb-read CLI entry points wired in pyproject.toml

affects: [05-01, 05-02]

tech-stack:
  added: []
  patterns:
    - "Deferred imports inside test bodies so --collect-only succeeds before engine modules are fully implemented"
    - "xfail(strict=True) on all Wave 0 stubs — RED before implementation is mandatory"
    - "brain_tmp fixture composes tmp_path + in-memory SQLite via engine.db.init_schema"

key-files:
  created:
    - tests/test_forget.py
    - tests/test_read.py
    - engine/forget.py
    - engine/read.py
  modified:
    - pyproject.toml

key-decisions:
  - "Deferred imports inside xfail test bodies ensure --collect-only works before engine.forget and engine.read are implemented"
  - "brain_tmp fixture uses engine.db.init_schema (not raw SQL) — consistent with project convention"
  - "sb-forget and sb-read wired in pyproject.toml now so Wave 1 implementation needs no toml edits"

patterns-established:
  - "Wave 0 stub pattern: test file + engine stub + entry point wired before any implementation"

requirements-completed: [GDPR-01, GDPR-02, GDPR-04]

duration: 2min
completed: 2026-03-14
---

# Phase 05 Plan 00: GDPR Wave 0 Stubs Summary

**10 xfail test stubs (6 forget, 4 read) with importable engine stubs and sb-forget/sb-read entry points wired in pyproject.toml**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-14T21:03:01Z
- **Completed:** 2026-03-14T21:04:27Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created tests/test_forget.py with 6 xfail stubs covering forget_person behaviour (file deletion, sole-attendee meeting deletion, multi-attendee meeting survival, backlink cleanup, search index empty, FTS5 rebuild)
- Created tests/test_read.py with 4 xfail stubs covering read_note passphrase gate (no passphrase, wrong passphrase, correct passphrase, public note bypasses gate)
- Created engine/forget.py and engine/read.py as importable NotImplementedError stubs
- Wired sb-forget and sb-read CLI entry points in pyproject.toml so Wave 1 needs no toml edits

## Task Commits

1. **Task 1: Create test stubs** - `8f4767b` (test)
2. **Task 2: Create engine stubs and wire entry points** - `ef18e7b` (feat)

## Files Created/Modified

- `tests/test_forget.py` - 6 xfail tests for GDPR-01 and GDPR-02
- `tests/test_read.py` - 4 xfail tests for GDPR-04
- `engine/forget.py` - forget_person() and main() stubs
- `engine/read.py` - read_note() and main() stubs
- `pyproject.toml` - sb-forget and sb-read entries added to [project.scripts]

## Decisions Made

- Deferred imports inside xfail test bodies: `from engine.forget import forget_person` lives inside each test function so pytest --collect-only succeeds before the module is implemented
- brain_tmp fixture uses engine.db.init_schema (not raw SQL) — consistent with the project's convention established in Phase 02
- Entry points wired now (Wave 0) so Wave 1 implementation plans have no pyproject.toml dependency

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 0 complete: all 10 tests are RED (xfail strict=True)
- Wave 1 plans (05-01 forget implementation, 05-02 read implementation) can now start immediately
- Both engine modules are importable — Wave 1 just needs to replace `raise NotImplementedError` with real logic

---
*Phase: 05-gdpr-and-maintenance*
*Completed: 2026-03-14*
