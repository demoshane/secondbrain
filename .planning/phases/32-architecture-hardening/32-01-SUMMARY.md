---
phase: 32-architecture-hardening
plan: "01"
title: "Relative path migration"
status: complete
started: 2026-03-21
completed: 2026-03-21
---

# Plan 32-01: Relative Path Migration — Summary

## What was built

- `store_path()` and `resolve_path()` helpers in `engine/paths.py` for converting between absolute and relative DB paths
- `migrate_paths_to_relative()` in `engine/db.py` — idempotent migration registered in `init_schema()`, runs in single transaction
- Call-site wiring: `capture_note()` and `update_note()` now call `store_path()` at DB write boundary
- Backward compat: `resolve_path()` handles both relative (new) and absolute (legacy) paths

## Key files

### Created
- `tests/test_paths.py` — tests for store_path/resolve_path helpers

### Modified
- `engine/paths.py` — added store_path(), resolve_path()
- `engine/db.py` — added migrate_paths_to_relative(), registered in init_schema()
- `engine/capture.py` — store_path() at write boundaries
- `tests/test_capture.py` — updated for relative path expectations
- `tests/test_db.py` — migration tests

## Commits
- `7b739d5` feat(32-01): add store_path/resolve_path helpers to engine/paths.py
- `7822251` feat(32-04): archival function, health report, export inclusion (included migration — scope leak)
- `5539057` feat(32-01): wire store_path at capture/update DB write boundaries

## Deviations
- Task 2 (migration in db.py) was implemented by the 32-04 agent which was modifying db.py concurrently. Scope leak but functionally correct.
- Read-side resolve_path() wiring deferred to Plan 05 per plan design.

## Self-Check: PASSED
- [x] store_path/resolve_path helpers tested
- [x] Migration converts absolute to relative, idempotent
- [x] capture_note() stores relative paths
- [x] All plan-specific tests pass
