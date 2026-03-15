---
phase: 12-micro-code-fixes
plan: "02"
subsystem: database
tags: [sqlite, gdpr, export, schema-init]

requires:
  - phase: 11-gdpr-scope-expansion
    provides: export_brain() and sb-export CLI entry point wired in pyproject.toml
  - phase: 12-micro-code-fixes-00
    provides: Wave 0 regression test test_export_initialises_schema_on_fresh_db confirming OperationalError on fresh DB
provides:
  - init_schema(conn) called in export.py main() before export_brain() — fresh-DB OperationalError eliminated
affects: [gdpr, export, fresh-install, sb-export]

tech-stack:
  added: []
  patterns:
    - "Schema init at call site (main()), not inside library function — preserves single-responsibility contract"

key-files:
  created: []
  modified:
    - engine/export.py

key-decisions:
  - "init_schema called in main() not export_brain() — library function receives a ready conn; callers own schema lifecycle"

patterns-established:
  - "Lazy-import block in main() extended to include init_schema alongside get_connection — co-located imports for related DB setup calls"

requirements-completed: [GDPR-05]

duration: 5min
completed: 2026-03-15
---

# Phase 12 Plan 02: init_schema call in export.py main() Summary

**Added `init_schema(conn)` call in `export.py main()` after `get_connection()`, eliminating OperationalError on fresh installs and closing GDPR-05.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T12:00:00Z
- **Completed:** 2026-03-15T12:05:00Z
- **Tasks:** 1
- **Files modified:** 2 (engine/export.py, .secrets.baseline)

## Accomplishments

- `init_schema` added to lazy import block in `main()` alongside `get_connection`
- `init_schema(conn)` inserted immediately after `get_connection()`, before the `try:` block
- `export_brain()` body left unmodified — schema init responsibility stays with caller
- `test_export_initialises_schema_on_fresh_db` now passes GREEN; full suite 0 failures

## Task Commits

1. **Task 1: Add init_schema call in export.py main()** - `35f52e6` (fix)

## Files Created/Modified

- `engine/export.py` - Added `init_schema` import and `init_schema(conn)` call in `main()`
- `.secrets.baseline` - Regenerated (line-number update from detect-secrets pre-commit hook)

## Decisions Made

- `init_schema` called in `main()` not inside `export_brain()` — keeps `export_brain` a pure data-export function that receives a ready connection; callers own the schema lifecycle. Consistent with single-responsibility pattern used throughout the codebase.

## Deviations from Plan

None — plan executed exactly as written. `.secrets.baseline` re-stage was a pre-commit hook artifact (line-number update), not a code change.

## Issues Encountered

- `detect-secrets` pre-commit hook updated `.secrets.baseline` line numbers on first commit attempt — required re-staging the baseline and re-running the commit. Routine hook behavior, no code impact.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- GDPR-05 closed — `sb-export` no longer raises `OperationalError` on fresh installs
- Remaining 12-micro-code-fixes plans (12-03, 12-04) can proceed independently

---
*Phase: 12-micro-code-fixes*
*Completed: 2026-03-15*
