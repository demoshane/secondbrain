---
phase: 33-performance-scale-hardening
plan: "02"
subsystem: intelligence, reindex
tags: [performance, cooldown, incremental-reindex, tdd]
dependency_graph:
  requires: []
  provides: [check_connections_cooldown, incremental_reindex]
  affects: [engine/intelligence.py, engine/reindex.py]
tech_stack:
  added: []
  patterns: [module-level monotonic cooldown, mtime-vs-updated_at incremental skip]
key_files:
  created: []
  modified:
    - engine/intelligence.py
    - engine/reindex.py
    - tests/test_intelligence.py
    - tests/test_reindex.py
key_decisions:
  - "Cooldown resets on both empty-match and successful runs (not only on full scan completion)"
  - "Incremental skip uses utcfromtimestamp(mtime) vs fromisoformat(updated_at) — both UTC, no timezone suffix"
  - "skipped key added to reindex return dict for observability"
metrics:
  duration: ~20 minutes
  completed_date: "2026-03-22T10:05:06Z"
  tasks_completed: 2
  files_modified: 4
requirements: [PERF-02, PERF-03]
---

# Phase 33 Plan 02: Cooldown Gate and Incremental Reindex Summary

30-minute monotonic cooldown on `check_connections` and mtime-based incremental skip in `reindex_brain` — capping the two biggest O(n) operations at realistic frequencies.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add failing tests (RED) for cooldown and incremental reindex | 050a6f9 | tests/test_intelligence.py, tests/test_reindex.py |
| 2 | Implement cooldown gate and incremental reindex (GREEN) | 8734fba | engine/intelligence.py, engine/reindex.py |

## What Was Built

### Cooldown gate on `check_connections` (PERF-02)

Added module-level variables to `engine/intelligence.py`:
- `_check_connections_last_run: float = 0.0` — tracks last run via `time.monotonic()`
- `_CHECK_CONNECTIONS_COOLDOWN_SECS: int = 30 * 60` — 30-minute window

The cooldown check fires as the FIRST guard in `check_connections`, before `budget_available`. This means repeat calls within 30 minutes skip the O(n) `find_similar` scan entirely — no DB queries, no embedding lookups. The cooldown timestamp resets after both empty-result and successful runs (any path that gets past the cooldown and budget gate counts as a run).

### Incremental mtime detection in `reindex_brain` (PERF-03)

In `engine/reindex.py`, the main file loop now checks mtime before loading frontmatter:
- Looks up `updated_at` from DB for the current file path
- Converts `st_mtime` to UTC via `datetime.utcfromtimestamp()` (matches DB's no-timezone ISO format)
- If `file_mtime_utc <= db_updated_at`, skips the file (increments `skipped` counter)
- `full=True` bypasses this check entirely — forces full reprocess
- `skipped` key added to return dict; `main()` prints it alongside `indexed`

Note: `disk_paths` collection still walks all files for orphan-pruning — incremental only affects the upsert pass.

## Deviations from Plan

### Auto-fixed Issues

None.

### Out-of-scope pre-existing failure

`TestConnectionSuggestion::test_check_connections_prints_suggestion` was already failing before this plan (confirmed by stash-test). The test asserts on `captured.out` but `check_connections` uses `logger.info` — nothing goes to stdout. Not caused by cooldown changes. Logged here for awareness; deferred to a separate fix.

## Self-Check: PASSED

All 5 files confirmed present. Both commits (050a6f9, 8734fba) confirmed in git log.
