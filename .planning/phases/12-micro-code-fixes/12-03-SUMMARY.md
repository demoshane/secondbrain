---
phase: 12-micro-code-fixes
plan: "03"
subsystem: database
tags: [sqlite, reindex, pathlib, gdpr, people]

requires:
  - phase: 12-micro-code-fixes/12-00
    provides: RED regression tests confirming absolute path and people column bugs
  - phase: 07-fix-path-format-split
    provides: .resolve() pattern for canonical path storage
provides:
  - engine/reindex.py stores str(md_path.resolve()) — absolute, symlink-resolved paths
  - engine/reindex.py normalises people frontmatter field identical to tags
  - INSERT INTO notes includes people in column list, VALUES, and DO UPDATE SET
affects: [forget, rag, search, capture]

tech-stack:
  added: []
  patterns:
    - "people normalisation mirrors tags pattern: meta.get('people', []) + isinstance list guard"
    - ".resolve() on every md_path before str() — consistent with capture.py and forget.py"

key-files:
  created: []
  modified:
    - engine/reindex.py

key-decisions:
  - "Changes for 12-03 were committed as part of the fix(12-02) commit (35f52e6) in a prior session — no duplicate commit created"
  - "md_path.resolve() not .absolute() — dereferences macOS /var->-/private/var symlink; consistent with forget.py"
  - "people normalisation added after tags_json block — same pattern, no new imports (json already imported)"

patterns-established:
  - "All path storage in reindex uses .resolve() — canonical path contract across capture/reindex/forget/rag"
  - "Frontmatter list fields normalised with isinstance guard before json.dumps — tags and people both follow this"

requirements-completed: [GDPR-01, CAP-02]

duration: 5min
completed: 2026-03-15
---

# Phase 12 Plan 03: Reindex Absolute Path and People Column Fix Summary

**engine/reindex.py patched: md_path.resolve() for absolute paths (GDPR-01 DELETE match) and people column added to INSERT/DO UPDATE SET (CAP-02 field preservation)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T12:00:00Z
- **Completed:** 2026-03-15T12:05:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- `str(md_path)` replaced with `str(md_path.resolve())` — sb-forget DELETE now matches sb-reindex paths
- `people` frontmatter field normalised to JSON array (same pattern as `tags`) and persisted in INSERT
- DO UPDATE SET includes `people=excluded.people` — reindex no longer wipes people column to `[]`

## Task Commits

1. **Task 1: Fix path storage and add people column to reindex INSERT** - `35f52e6` (fix) — committed as part of fix(12-02) in prior session

## Files Created/Modified

- `/Users/tuomasleppanen/second-brain/engine/reindex.py` - absolute path via .resolve(); people normalisation block; INSERT/DO UPDATE SET with people column

## Decisions Made

- Changes were already committed in `35f52e6` (fix(12-02)) from a prior session. No duplicate commit created — idempotent execution confirmed by `git diff HEAD engine/reindex.py` returning empty and all 6 test_reindex.py tests passing GREEN.

## Deviations from Plan

None - plan executed exactly as written. Changes were pre-committed in a prior session.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three Wave 1 fix plans (12-01, 12-02, 12-03) complete
- 148 tests pass, 0 failures
- test_reindex_stores_absolute_paths and test_reindex_preserves_people_column both GREEN
- GDPR-01 and CAP-02 requirements closed

---
*Phase: 12-micro-code-fixes*
*Completed: 2026-03-15*
