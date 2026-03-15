---
phase: 11-gdpr-scope-expansion
plan: "02"
subsystem: gdpr
tags: [gdpr, anonymize, pii, sqlite, fts5, audit-log, python-frontmatter, re]

# Dependency graph
requires:
  - phase: 11-gdpr-scope-expansion
    provides: Wave 0 scaffolding — sb-anonymize entry point wired, xfail stub in tests/test_anonymize.py
  - phase: 05-gdpr-and-maintenance
    provides: forget.py atomic write pattern, error message convention (type(e).__name__ only), audit_log schema
provides:
  - anonymize_note() — GDPR Article 17 runtime PII token scrubbing with case-insensitive re.sub + re.escape
  - Atomic file write via mkstemp(dir=path.parent) + os.replace for same-filesystem guarantee
  - DB UPDATE notes SET body/title/sensitivity/updated_at; FTS5 via notes_au trigger (automatic)
  - audit_log INSERT event_type='anonymize' with token count detail
  - Sensitivity downgrade pii->private when downgrade_sensitivity=True
  - main() CLI entry point for sb-anonymize
affects: [gdpr-consumers, sb-anonymize-cli, phase-12-future]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "re.escape(token) before re.sub — always escape user-supplied tokens (email dots, hyphens are regex metacharacters)"
    - "FTS5 via trigger — no manual rebuild needed for single-note updates; notes_au fires on UPDATE notes"
    - "Atomic write: mkstemp(dir=path.parent) not /tmp — same filesystem mandatory for POSIX os.replace atomicity"
    - "DB errors best-effort: appended to errors list, never raised — function returns partial result"
    - "Error messages: type(e).__name__ only — GDPR-05 compliance, no PII in logs"

key-files:
  created: []
  modified:
    - engine/anonymize.py
    - tests/test_anonymize.py

key-decisions:
  - "re.escape(token) always applied before re.sub — tokens may contain email dots, hyphens, parens which are regex metacharacters"
  - "redacted_count counts occurrences in original body (pre-replacement) using re.findall, not replacements made — consistent count semantics"
  - "Sensitivity field read from 'content_sensitivity' frontmatter key (not 'sensitivity') — matches codebase convention"
  - "FTS5 updated automatically by notes_au trigger on UPDATE notes — no manual rebuild needed for single-note anonymize"
  - "DB errors are best-effort (appended to errors list) — file write is source of truth; DB failure never blocks anonymization"

patterns-established:
  - "Token scrubbing pattern: re.escape + re.sub(flags=re.IGNORECASE) — safe for arbitrary user-supplied strings"
  - "Atomic note update: load frontmatter -> modify -> mkstemp(dir=parent) -> fdopen write -> os.replace -> UPDATE DB -> audit_log INSERT -> commit"

requirements-completed: [GDPR-03]

# Metrics
duration: unknown
completed: 2026-03-15
---

# Phase 11 Plan 02: anonymize_note() — GDPR Article 17 Runtime Token Scrubbing Summary

**anonymize_note() replaces PII tokens with [REDACTED] using re.escape + case-insensitive re.sub, atomic file write via mkstemp(dir=parent), DB UPDATE with FTS5 via notes_au trigger, and audit_log INSERT — 6 tests passing**

## Performance

- **Duration:** unknown (pre-committed)
- **Started:** unknown
- **Completed:** 2026-03-15
- **Tasks:** 1 (TDD: test RED + feat GREEN)
- **Files modified:** 2

## Accomplishments

- anonymize_note() fully implemented: re.escape safety, case-insensitive token scrubbing across body and title, redacted_count accurate
- Atomic write via mkstemp(dir=path.parent) + os.replace — same filesystem as note file, POSIX atomicity guaranteed
- DB row updated (body, title, sensitivity, updated_at); FTS5 index kept in sync automatically by notes_au trigger
- audit_log INSERT event_type='anonymize' with tokens count in detail field on every call
- Sensitivity downgrade (pii -> private) when downgrade_sensitivity=True
- Noop path: no token match returns redacted_count=0 with no error, no file write
- All 6 tests in tests/test_anonymize.py pass; full suite 143 passed, 5 skipped, 1 xfailed

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement anonymize_note() in engine/anonymize.py** - `b5055b0` (feat — TDD RED+GREEN combined)

## Files Created/Modified

- `engine/anonymize.py` - Full implementation of anonymize_note() and main() CLI entry point
- `tests/test_anonymize.py` - Removed xfail markers, fixed to create note files on disk and use absolute DB paths; all 6 tests pass

## Decisions Made

- re.escape(token) always applied before re.sub — user-supplied tokens may contain email dots, hyphens, parentheses which are regex metacharacters (see RESEARCH Pitfall 4)
- redacted_count uses re.findall on the original body text (before replacement) to count occurrences — avoids double-counting across chained substitutions
- Sensitivity frontmatter key is 'content_sensitivity' (not 'sensitivity') — matches the established codebase convention from engine/capture.py
- DB write is best-effort: exception appended to errors list but file write (source of truth) already completed at that point
- FTS5 updated automatically by notes_au trigger on UPDATE notes — no manual rebuild needed, consistent with Phase 2 design

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- anonymize_note() ready for integration into sb-anonymize CLI flow
- Pattern established (re.escape + atomic write + audit_log) usable by future token-scrubbing operations
- Full test suite green at 143 passed

---
*Phase: 11-gdpr-scope-expansion*
*Completed: 2026-03-15*
