---
phase: 02-storage-and-index
plan: "03"
subsystem: cli
tags: [argparse, sqlite, fts5, bm25, detect-secrets, audit-log]

requires:
  - phase: 02-storage-and-index/02-01
    provides: capture pipeline (write_note_atomic, build_post, capture_note)
  - phase: 02-storage-and-index/02-02
    provides: search pipeline (search_notes, FTS5 BM25 indexing)

provides:
  - sb-capture CLI command wired to engine.capture:main
  - sb-search CLI command wired to engine.search:main
  - test_audit_log_create_entry: verifies audit_log row after write_note_atomic
  - test_detect_secrets_baseline_clean: verifies no new secrets beyond baseline

affects: [03-templates-and-context, 04-ai-integration]

tech-stack:
  added: []
  patterns:
    - "CLI main() defined inside module, imports deferred to function body to avoid circular import issues"
    - "detect-secrets test uses shutil.which guard — skips gracefully outside DevContainer"

key-files:
  created: []
  modified:
    - engine/capture.py
    - engine/search.py
    - pyproject.toml
    - tests/test_audit.py

key-decisions:
  - "detect-secrets test skips (not fails) when binary not on PATH — test is only meaningful inside DevContainer where detect-secrets is installed"

patterns-established:
  - "Pattern: container-only tests use shutil.which guard + pytest.skip rather than xfail or unconditional failure"

requirements-completed: [CAP-01, SEARCH-01, GDPR-03, GDPR-06]

duration: 12min
completed: 2026-03-14
---

# Phase 2 Plan 03: CLI Entry Points and Final Test Stubs Summary

**argparse CLI main() functions wired for sb-capture and sb-search with audit log verification and detect-secrets baseline check**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-14T15:40:00Z
- **Completed:** 2026-03-14T15:52:00Z
- **Tasks:** 1 of 1 (checkpoint pending human verification)
- **Files modified:** 4

## Accomplishments

- Added `main()` to `engine/capture.py` with full argparse (--type, --title, --body, --tags, --people, --sensitivity)
- Added `main()` to `engine/search.py` with argparse (query, --type, --limit)
- Registered `sb-capture` and `sb-search` as console_scripts in `pyproject.toml`
- Implemented `test_audit_log_create_entry` — calls `write_note_atomic`, asserts `audit_log` has `event_type='create'` row
- Implemented `test_detect_secrets_baseline_clean` — runs `detect-secrets scan --baseline`, skips outside DevContainer
- Full suite: 39 passed, 4 skipped — zero regressions

## Task Commits

1. **Task 1: CLI main() functions + pyproject.toml entry points + remaining test stubs** - `3991d69` (feat)

## Files Created/Modified

- `engine/capture.py` - Added `main()` CLI entry point for sb-capture
- `engine/search.py` - Added `main()` CLI entry point for sb-search
- `pyproject.toml` - Added sb-capture and sb-search to [project.scripts]
- `tests/test_audit.py` - Implemented test_audit_log_create_entry and test_detect_secrets_baseline_clean

## Decisions Made

- `detect-secrets` test uses `shutil.which` guard to skip outside DevContainer rather than fail — binary is only installed inside container, unconditional failure would break CI on host machines.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] detect-secrets test would crash on host with FileNotFoundError**
- **Found during:** Task 1 (test_detect_secrets_baseline_clean)
- **Issue:** `subprocess.run(["detect-secrets", ...])` raises `FileNotFoundError` when `detect-secrets` binary is not on PATH, which is always the case on the host machine outside DevContainer.
- **Fix:** Added `shutil.which("detect-secrets") is None` guard with `pytest.skip()` — test runs fully inside DevContainer, skips cleanly on host.
- **Files modified:** tests/test_audit.py
- **Verification:** Test suite shows `s` (skip) for that test on host, all others pass.
- **Committed in:** `3991d69` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Fix necessary for correctness — crash vs. skip is the difference between broken CI and working CI. No scope creep.

## Issues Encountered

None beyond the auto-fixed deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All Phase 2 automated tests pass (39 passed, 4 skipped)
- CLI entry points registered and ready for `pip install -e .`
- Checkpoint awaiting DevContainer verification of end-to-end capture+search flow
- Phase 3 (Templates and Context) can begin once checkpoint is approved

---
*Phase: 02-storage-and-index*
*Completed: 2026-03-14*
