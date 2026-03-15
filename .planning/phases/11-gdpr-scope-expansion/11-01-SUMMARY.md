---
phase: 11-gdpr-scope-expansion
plan: "01"
subsystem: gdpr
tags: [sqlite, json, argparse, audit-log, data-portability]

# Dependency graph
requires:
  - phase: 11-00
    provides: sb-export entry point wired in pyproject.toml; xfail test stubs in tests/test_export.py
  - phase: 05-gdpr-and-maintenance
    provides: audit_log table schema and insert pattern (forget.py)
provides:
  - export_brain() — queries all notes (including PII), writes atomic JSON, inserts audit_log row, returns count
  - sb-export CLI — argparse main() with --output and --brain-root flags
affects:
  - 11-02
  - 11-03
  - 12-sign-off

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Atomic file write via mkstemp + os.replace within output_path.parent (same filesystem, no cross-device replace)
    - Audit-log row inserted after every export with detail='format:json count:N'
    - PII notes included unconditionally — Article 20 covers all personal data

key-files:
  created: []
  modified:
    - engine/export.py
    - tests/test_export.py

key-decisions:
  - "export_brain() writes a flat JSON list (not wrapped object) — simplest portable shape; consumers parse without schema knowledge"
  - "note_path=None in audit_log INSERT — export is an operation-level event, not per-note; consistent with forget and search patterns"
  - "No passphrase gate on export — user owns their own data; Article 20 does not permit withholding personal data behind an extra credential"
  - "output_path.parent.mkdir(parents=True, exist_ok=True) — caller need not pre-create destination directory"

patterns-established:
  - "GDPR portability pattern: SELECT all columns FROM notes (no sensitivity filter) → JSON → audit_log INSERT → return count"

requirements-completed: [GDPR-02]

# Metrics
duration: pre-committed
completed: 2026-03-15
---

# Phase 11 Plan 01: GDPR Export (Art. 20) Summary

**export_brain() and sb-export CLI implementing GDPR Article 20 data portability — all notes (including PII) serialized to atomic JSON with audit_log trail**

## Performance

- **Duration:** pre-committed (commit e5d4a42)
- **Started:** 2026-03-15
- **Completed:** 2026-03-15
- **Tasks:** 1 (TDD)
- **Files modified:** 2

## Accomplishments

- Replaced NotImplementedError stub in engine/export.py with full export_brain() implementation
- Atomic JSON write via mkstemp + os.replace; parent directories auto-created
- audit_log row inserted on every call: event_type='export', note_path=NULL, detail='format:json count:N'
- sb-export CLI: argparse with --output (timestamped default) and --brain-root flags; prints "Exported N notes to <path>"; exits 0
- Removed xfail markers from tests/test_export.py; added export_db fixture (initializes schema, seeds 1 public + 1 PII note); all 4 tests pass
- Full suite: 137 passed, 0 regressions

## Task Commits

1. **Task 1: Implement export_brain() and sb-export CLI main()** - `e5d4a42` (feat)

## Files Created/Modified

- `engine/export.py` — full export_brain() + main(); replaces NotImplementedError stub
- `tests/test_export.py` — xfail markers removed; export_db fixture added; 4 tests pass

## Decisions Made

- No passphrase gate: Article 20 does not permit withholding personal data behind an extra credential; user owns their data.
- note_path=None in audit_log: export is operation-level (not per-note), consistent with forget.py and search.py audit patterns.
- Flat JSON list (no wrapper object): simplest portable shape; consumers parse without needing a schema.
- output_path.parent.mkdir(parents=True, exist_ok=True): caller need not pre-create destination.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- export_brain() and sb-export CLI fully operational; GDPR-02 satisfied.
- Ready for 11-02 (retention/purge) and 11-03 (consent gate) without further changes to export.py.

---
*Phase: 11-gdpr-scope-expansion*
*Completed: 2026-03-15*
