---
phase: 38
plan: 02
subsystem: brain-health, sharding, database
tags: [scale, audit-log, rotation, sharding, filesystem, sqlite, tdd]
dependency_graph:
  requires: []
  provides:
    - audit_log_archive table in brain.db
    - archive_old_audit_entries() function in brain_health.py
    - engine/sharding.py module with shard helpers
  affects:
    - engine/consolidate.py (daily job now runs audit rotation)
    - engine/db.py (new migration: audit_log_archive)
tech_stack:
  added: []
  patterns:
    - executemany+DELETE-per-row pattern (semgrep-safe, mirrors archive_old_action_items)
    - PRAGMA foreign_keys=OFF during atomic path rename transaction
key_files:
  created:
    - engine/sharding.py
    - tests/test_sharding.py
  modified:
    - engine/db.py
    - engine/brain_health.py
    - engine/consolidate.py
    - tests/test_brain_health.py
decisions:
  - archive_old_audit_entries uses executemany+DELETE per row — mirrors Phase 32 pattern for semgrep compliance
  - shard_note disables PRAGMA foreign_keys during transaction — SQLite has no deferred FK support for UPDATE; child tables (note_tags, note_people) have FK on notes.path; must disable to rename path atomically
  - shard_note works with absolute paths — tests use absolute tmp_path; relative paths also supported in shard_all_notes
metrics:
  duration_minutes: 25
  completed_date: "2026-03-26"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 6
---

# Phase 38 Plan 02: Audit Log Rotation and Filesystem Sharding Summary

Audit log rotation keeps the hot `audit_log` table performant at 100K+ note scale by archiving old entries. Filesystem sharding helpers enable moving notes into type-based subdirectories with a full atomic DB path cascade.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Audit log rotation — archive table + rotation function | 2071610 | engine/db.py, engine/brain_health.py, engine/consolidate.py, tests/test_brain_health.py |
| 2 | Filesystem sharding helpers | 5e95284 | engine/sharding.py, tests/test_sharding.py |

## What Was Built

### Task 1: Audit Log Rotation

- `migrate_create_audit_log_archive(conn)` in `engine/db.py`: creates `audit_log_archive` table with columns mirroring `audit_log` plus `archived_at` (DEFAULT timestamp).
- Called from `init_schema()` after `migrate_add_health_snapshots_table`.
- `archive_old_audit_entries(conn, days=90) -> int` in `engine/brain_health.py`: selects entries older than `days` days, bulk-inserts into `audit_log_archive`, deletes from `audit_log` per-row (semgrep-safe pattern). Returns archived count.
- `consolidate_main()` in `engine/consolidate.py` now calls `archive_old_audit_entries` after `archive_old_action_items`, adding `"archived_audit"` to the results dict logged to stdout.
- 4 new tests covering: moves old entries, no-op on recent entries, correct archive columns, count decreases.

### Task 2: Filesystem Sharding Helpers

- `engine/sharding.py` — new module with:
  - `SHARD_MAP`: maps note types to subdirectory names (meeting→meetings, person→people, etc.)
  - `DEFAULT_SHARD = "notes"` for unmapped types
  - `get_shard_path(brain_root, note_type, filename) -> Path`: returns target path, creates dir.
  - `shard_note(conn, old_path, new_path) -> None`: moves file, cascades path update across 8 DB tables atomically. Uses `PRAGMA foreign_keys = OFF` during transaction (SQLite has no deferred FK constraints for UPDATE). Rolls back DB and moves file back on failure.
  - `shard_all_notes(conn, brain_root, dry_run=True) -> list[dict]`: computes all moves needed, optionally executes them.
- 14 tests in `tests/test_sharding.py` covering all DB tables, FileNotFoundError, dry-run mode.

## Test Results

```
tests/test_brain_health.py  34 passed, 7 xpassed
tests/test_sharding.py      14 passed
Total: 48 passed, 7 xpassed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] FK constraint violation in shard_note**
- **Found during:** Task 2 GREEN phase (test run)
- **Issue:** `note_tags` and `note_people` have `FOREIGN KEY (note_path) REFERENCES notes(path) ON DELETE CASCADE`. Updating `notes.path` while child rows still reference the old path caused `sqlite3.IntegrityError: FOREIGN KEY constraint failed`.
- **Fix:** Wrap the path-rename transaction with `PRAGMA foreign_keys = OFF` / `PRAGMA foreign_keys = ON`. This is safe because all 8 UPDATE statements run atomically — FK integrity is maintained by the cascade logic itself.
- **Files modified:** engine/sharding.py
- **Commit:** 5e95284

**2. [Rule 1 - Bug] Test paths used relative filenames not resolvable by shard_note**
- **Found during:** Task 2 first test run
- **Issue:** Tests created files at `brain_root/filename` but passed bare `"filename"` to `shard_note`, which resolved to CWD, not brain_root. `Path("note.md").exists()` returned False.
- **Fix:** Updated tests to pass absolute paths (`str(brain_root / filename)`) consistent with `shard_note`'s path semantics.
- **Files modified:** tests/test_sharding.py
- **Commit:** 5e95284

## Known Stubs

None. Both features are fully wired:
- `archive_old_audit_entries` is called from `consolidate_main` (daily job).
- `shard_note` and `shard_all_notes` are standalone helpers ready for CLI/API integration in a future plan.

## Self-Check: PASSED

Files verified:
- engine/sharding.py — FOUND
- engine/brain_health.py — FOUND (contains `def archive_old_audit_entries`)
- engine/consolidate.py — FOUND (contains `archive_old_audit_entries` call)
- tests/test_sharding.py — FOUND (14 test functions)
- tests/test_brain_health.py — FOUND (4 new audit rotation tests)

Commits verified:
- 2071610 — FOUND (audit log rotation)
- 5e95284 — FOUND (filesystem sharding helpers)
