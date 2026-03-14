---
phase: 01-foundation
plan: "03"
subsystem: database
tags: [sqlite, fts5, pathlib, python, engine]

# Dependency graph
requires:
  - phase: 01-foundation/01-01
    provides: pyproject.toml, uv environment, test infrastructure (conftest.py with db_conn and brain_root fixtures)
  - phase: 01-foundation/01-02
    provides: DevContainer + Docker Compose with brain-index-data named volume
provides:
  - engine/paths.py — BRAIN_ROOT, INDEX_ROOT, DB_PATH, META_DIR, BRAIN_SUBDIRS (pathlib-only, single source of truth)
  - engine/db.py — get_connection(), init_schema() with FTS5 virtual table and 3 triggers, idempotent
  - engine/init_brain.py — validate_drive_mount(), create_brain_structure(), generate_vscode_settings(), main() CLI
  - tests/test_db.py — 3 tests covering schema completeness, idempotency, trigger existence
  - tests/test_init_brain.py — 4 tests covering subdir creation, write validation, vscode settings, created-vs-existed reporting
affects:
  - all future phases that import from engine.*
  - Phase 2+ commands that use /sb-init, get_connection, init_schema

# Tech tracking
tech-stack:
  added: [sqlite3 (stdlib), FTS5 virtual table, pathlib]
  patterns: [TDD red-green, executescript for multi-statement SQL, probe-file Drive validation]

key-files:
  created:
    - engine/__init__.py
    - engine/paths.py
    - engine/db.py
    - engine/init_brain.py
    - tests/test_db.py (stubs replaced)
    - tests/test_init_brain.py (stubs replaced)
  modified: []

key-decisions:
  - "Used conn.executescript() instead of splitting on semicolons — trigger bodies contain semicolons which break naive split"
  - "validate_drive_mount writes a .sb-write-probe file and unlinks it — validates mount is writable before any mkdir"
  - "init_schema uses IF NOT EXISTS throughout — safe to call on any existing DB without data loss"

patterns-established:
  - "Pattern 1: All path constants live in engine/paths.py — no hardcoded paths anywhere else"
  - "Pattern 2: init_schema(conn, reset=False) — callers pass connection, function is pure (no side effects beyond schema)"
  - "Pattern 3: Drive validation ALWAYS before structural changes — validate_drive_mount called at start of main()"

requirements-completed: [FOUND-03, FOUND-04, FOUND-05, FOUND-06, FOUND-12]

# Metrics
duration: 8min
completed: 2026-03-14
---

# Phase 1 Plan 03: Engine Foundation Summary

**SQLite schema with FTS5 full-text search and 3 sync triggers, pathlib-only path constants, and idempotent /sb-init that validates Drive mount before creating 9 brain subdirectories**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-14T13:28:56Z
- **Completed:** 2026-03-14T13:36:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- engine/paths.py with canonical BRAIN_ROOT, INDEX_ROOT, DB_PATH, META_DIR, BRAIN_SUBDIRS — no os.path anywhere
- engine/db.py with idempotent init_schema (IF NOT EXISTS), FTS5 virtual table, 3 content-sync triggers, get_connection with WAL mode
- engine/init_brain.py with Drive validation (write-probe), idempotent subdir creation, VS Code binary-file exclusions, main() CLI

## Task Commits

Each task was committed atomically:

1. **Task 1: Create engine/ package — paths.py and db.py** - `d5ce4d5` (feat)
2. **Task 2: Create engine/init_brain.py and fill tests/test_init_brain.py** - `af8cacb` (feat)

_Note: TDD tasks — tests written first (RED), then implementation (GREEN)_

## Files Created/Modified

- `engine/__init__.py` - Empty package marker
- `engine/paths.py` - BRAIN_ROOT, INDEX_ROOT, DB_PATH, META_DIR, TEMPLATES_DIR, CONFIG_FILE, BRAIN_SUBDIRS (9 subdirs)
- `engine/db.py` - SCHEMA_SQL, DROP_SQL, get_connection(), init_schema(conn, reset=False)
- `engine/init_brain.py` - validate_drive_mount(), create_brain_structure(), generate_vscode_settings(), main()
- `tests/test_db.py` - 3 tests: schema_complete, schema_idempotent, fts5_triggers_exist
- `tests/test_init_brain.py` - 4 tests: creates_subdirs, drive_validation_blocks_on_unwritable, vscode_settings_generated, init_reports_created_vs_existed

## Decisions Made

- Used `conn.executescript()` instead of splitting SCHEMA_SQL on ";" — trigger bodies contain semicolons and break naive splitting (auto-fixed during GREEN phase)
- Drive probe pattern: write `.sb-write-probe` then unlink — validates actual write permission, not just directory existence

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed executescript vs split-on-semicolon for SQL schema**
- **Found during:** Task 1 (GREEN phase, first test run)
- **Issue:** SCHEMA_SQL split on ";" broke at semicolons inside CREATE TRIGGER bodies → sqlite3.OperationalError: incomplete input
- **Fix:** Replaced `for statement in SQL.split(";")` loop with `conn.executescript(SQL)` which handles multi-statement SQL correctly
- **Files modified:** engine/db.py
- **Verification:** All 3 test_db.py tests pass after fix
- **Committed in:** d5ce4d5 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in SQL execution approach)
**Impact on plan:** Necessary correctness fix. No scope creep.

## Issues Encountered

None beyond the executescript fix above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- engine/ package is importable and all 7 tests pass
- /sb-init CLI is ready (python -m engine.init_brain) — requires BRAIN_ROOT (/workspace/brain) to exist inside DevContainer
- Phase 4+ can call get_connection() and init_schema() directly
- SQLite schema is final for v1 — adding columns requires migration strategy

---
*Phase: 01-foundation*
*Completed: 2026-03-14*
