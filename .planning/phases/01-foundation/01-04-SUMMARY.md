---
phase: 01-foundation
plan: "04"
subsystem: database
tags: [sqlite, fts5, python-frontmatter, reindex, pathlib]

# Dependency graph
requires:
  - phase: 01-foundation/01-03
    provides: engine/db.py (get_connection, init_schema), engine/paths.py (BRAIN_ROOT, DB_PATH)
provides:
  - engine/reindex.py with reindex_brain() — walks brain_root rglob("*.md"), parses YAML frontmatter, upserts notes via ON CONFLICT DO UPDATE, rebuilds FTS5
  - /sb-reindex CLI entry point (main())
  - tests/test_reindex.py — 4 tests covering insert, idempotency, empty brain, frontmatter field parsing
affects: [all phases that depend on notes index being populated, Phase 2 search/retrieval]

# Tech tracking
tech-stack:
  added: [python-frontmatter]
  patterns: [TDD red-green for index rebuild, reindex_brain accepts optional conn for testability, pathlib-only path handling]

key-files:
  created:
    - engine/reindex.py
    - tests/test_reindex.py (replaced stubs)
  modified: []

key-decisions:
  - "reindex_brain accepts optional conn parameter so tests can pass an in-memory SQLite connection without touching disk"
  - "FTS5 rebuild triggered via INSERT INTO notes_fts(notes_fts) VALUES('rebuild') after full scan — ensures consistency even when triggers may have fired during upserts"
  - "Relative path used as canonical note identifier (relative_to brain_root) — portable across installs"

patterns-established:
  - "Pattern: Injectable connection — functions accept optional conn for testability, fall back to get_connection() in production"
  - "Pattern: tags stored as JSON array string in SQLite TEXT column"

requirements-completed: [FOUND-07, FOUND-12]

# Metrics
duration: 3min
completed: 2026-03-14
---

# Phase 1 Plan 04: Reindex Summary

**SQLite brain reindex command using python-frontmatter and FTS5 rebuild, with 4 passing TDD tests covering insert, idempotency, empty brain, and frontmatter parsing**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-14T12:53:04Z
- **Completed:** 2026-03-14T12:54:51Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- `engine/reindex.py` walks `brain_root.rglob("*.md")`, parses YAML frontmatter via python-frontmatter, and upserts every note into the notes table using `ON CONFLICT(path) DO UPDATE`
- FTS5 index rebuilt after each full scan via `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')`
- `main()` entry point provides `/sb-reindex` CLI (recovery path for FOUND-07)
- All 4 TDD tests pass: insert, idempotency (no duplicates on second run), empty brain (zero errors), frontmatter field parsing (type/title/tags/sensitivity)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create engine/reindex.py and fill tests/test_reindex.py** - `452f484` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified

- `engine/reindex.py` — reindex_brain() + main() CLI; pathlib-only, no os.path
- `tests/test_reindex.py` — replaced stubs with 4 full tests using brain_root + db_conn fixtures

## Decisions Made

- `reindex_brain` accepts an optional `conn` parameter so tests inject an in-memory SQLite connection without touching disk
- FTS5 rebuild via `VALUES('rebuild')` post-scan ensures full consistency (not relying solely on triggers during upserts)
- Relative path from `brain_root` used as canonical note ID — portable across installs and containers

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `engine/reindex.py` is ready; `/sb-reindex` command can be wired into `pyproject.toml` scripts in a later plan
- FTS5 index is now populatable from disk — prerequisite for Phase 2 search commands

---
*Phase: 01-foundation*
*Completed: 2026-03-14*
