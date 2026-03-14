---
phase: 07-fix-path-format-split
plan: "01"
subsystem: database
tags: [sqlite, pathlib, capture, rag, forget, symlinks]

# Dependency graph
requires:
  - phase: 07-fix-path-format-split
    provides: RED test stubs for path-format split (07-00)
  - phase: 02-storage-and-index
    provides: write_note_atomic() in engine/capture.py
provides:
  - write_note_atomic() stores str(target.resolve()) — canonical absolute path in DB
  - RAG reads succeed without '[note file not readable]' fallback
  - forget_person exact-match DELETE finds rows without sb-reindex
affects:
  - engine/rag.py
  - engine/forget.py
  - any future plan that reads path column from notes table

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "resolved_path = str(target.resolve()) — always resolve symlinks before storing path in DB"
    - "extract resolved path to local var, use for both INSERT and log_audit — single source of truth"

key-files:
  created: []
  modified:
    - engine/capture.py

key-decisions:
  - "Use .resolve() not .absolute() — .absolute() does not follow symlinks; macOS tmp_path is /var/folders/... (symlink to /private/var/folders/...) so .resolve() is required"
  - "Single resolved_path local variable used for both INSERT and log_audit — eliminates any future divergence between DB row and audit log"
  - "No changes to rag.py or forget.py — root cause was exclusively in capture's path storage; consumers were already correct"

patterns-established:
  - "Path canonicalization at write time: resolve symlinks when storing paths in DB, not at read time"

requirements-completed: [SEARCH-01, SEARCH-04, GDPR-01]

# Metrics
duration: 5min
completed: 2026-03-15
---

# Phase 7 Plan 01: Fix Path Format Split Summary

**One-line fix in write_note_atomic() resolves DB path-format split — str(target.resolve()) replaces str(target), making RAG reads and forget deletions reliable without sb-reindex**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-15T00:00:00Z
- **Completed:** 2026-03-15T00:05:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Fixed root cause of path-format split: capture stored unresolved symlink paths on macOS (/var/...) while RAG and forget operated on resolved paths (/private/var/...)
- All 4 phase-7 RED tests turned GREEN with a 3-line change (add resolved_path var, update INSERT, update log_audit)
- Full suite clean: 127 passed, 5 skipped, 1 xfailed — zero regressions

## Task Commits

1. **Task 1: Fix write_note_atomic() — str(target) to str(target.resolve())** - `3142ff1` (fix)
2. **Task 2: Full suite regression check** - verified, no separate commit needed (no code change)

## Files Created/Modified

- `engine/capture.py` - Extract `resolved_path = str(target.resolve())` before INSERT; use for both INSERT VALUES and log_audit

## Decisions Made

- Use `.resolve()` not `.absolute()` — `.absolute()` does not follow symlinks. macOS `tmp_path` returns `/var/folders/...` which is a symlink to `/private/var/folders/...`. Only `.resolve()` guarantees canonical form.
- No changes needed to `rag.py` or `forget.py` — both already use the path from DB directly and resolve correctly once capture stores the canonical form.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- `uv run --no-project --with pytest tests/test_capture.py::test_name` fails with "No such file or directory" when `::` notation is used as direct args to uv. Workaround: pass `pytest` explicitly as the command before the test paths (`uv run --no-project --with pytest pytest tests/...::test_name`).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 7 complete: path-format split eliminated at source
- DB rows from capture now use canonical absolute paths on all platforms
- RAG retrieval and forget deletion are reliable without requiring sb-reindex after capture
- No blockers for v1.5 milestone

---
*Phase: 07-fix-path-format-split*
*Completed: 2026-03-15*
