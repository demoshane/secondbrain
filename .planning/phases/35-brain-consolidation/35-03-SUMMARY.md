---
phase: 35-brain-consolidation
plan: 03
subsystem: database, mcp, consolidation, install
tags: [sqlite, brain-health, snapshots, launchd, mcp, consolidation]

requires:
  - phase: 35-brain-consolidation
    plan: 02
    provides: archive_old_action_items, delete_dangling_relationships, take_health_snapshot, cleanup_old_snapshots interfaces

provides:
  - health_snapshots table via DB migration in engine/db.py
  - take_health_snapshot() in engine/brain_health.py — inserts daily snapshot with one-per-day guard
  - cleanup_old_snapshots() in engine/brain_health.py — 90-day retention cleanup
  - sb_health_trend MCP tool — returns snapshot time series for last N days
  - engine/consolidate.py — consolidate_main() scheduled job entry point
  - sb-consolidate CLI command
  - com.secondbrain.consolidate launchd plist — daily 03:00 trigger
  - scripts/install_native.py write_consolidate_plist() — plist generator

affects:
  - launchd install pipeline (install_native.py main() now registers 4 agents)
  - future MCP health trend analysis via sb_health_trend

tech-stack:
  added: []
  patterns:
    - "take_health_snapshot uses WHERE date(snapped_at) = ? for one-per-day guard — date() strips time component"
    - "cleanup_old_snapshots uses date('now', '-N days') SQLite date arithmetic for idempotent cleanup"
    - "consolidate_main imports engine.brain_health lazily inside function — avoids circular import at module level"
    - "sb-consolidate prints JSON to stdout — captured by launchd StandardOutPath for job logging"

key-files:
  created:
    - engine/consolidate.py
    - tests/test_consolidate.py
    - .planning/phases/35-brain-consolidation/35-03-SUMMARY.md
  modified:
    - engine/db.py
    - engine/brain_health.py
    - engine/mcp_server.py
    - scripts/install_native.py
    - pyproject.toml
    - tests/test_brain_health.py
    - tests/test_install_native.py

key-decisions:
  - "health_snapshots table migration added as last step in init_schema() — after all other migrations to avoid ordering issues"
  - "take_health_snapshot one-per-day guard uses date(snapped_at) = date('now') — strips time component so ISO date string comparison works"
  - "consolidate_main imports brain_health lazily inside function body — avoids potential circular import with engine.db"
  - "test_plist_keys pre-existing failure is out of scope — caused by uncommitted write_plist signature change from a prior phase, not from Plan 35-03 changes"

requirements-completed:
  - CONS-04
  - CONS-05

duration: 15min
completed: 2026-03-23
---

# Phase 35 Plan 03: Health Trend Tracking + Scheduled Consolidation Summary

**health_snapshots DB migration, take_health_snapshot() with one-per-day guard, cleanup_old_snapshots() 90-day retention, sb_health_trend MCP time series tool, consolidate_main() daily job with archive → dangling delete → snapshot → cleanup order, launchd plist at 03:00, install_native.py integration**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-23T18:00:00Z
- **Completed:** 2026-03-23T18:15:00Z
- **Tasks:** 2
- **Files modified:** 7 (+ 2 created)

## Accomplishments

- `migrate_add_health_snapshots_table()` in db.py — idempotent CREATE TABLE IF NOT EXISTS; called from init_schema()
- `take_health_snapshot(conn)` — queries all health functions, inserts row, returns typed dict; skips if snapshot already exists today
- `cleanup_old_snapshots(conn, days=90)` — DELETE with date arithmetic, returns rowcount
- `sb_health_trend(days=30)` MCP tool — SELECT from health_snapshots ordered ASC, returns `{snapshots, count, days}`
- `engine/consolidate.py` — new module with `consolidate_main()` running D-16 order: archive actions → delete dangling → snapshot → cleanup old snapshots
- `sb-consolidate` entry point in pyproject.toml
- `write_consolidate_plist()` in install_native.py — daily 03:00 StartCalendarInterval plist
- main() bootstraps com.secondbrain.consolidate launchd agent
- 8 tests total: 5 snapshot tests (TDD) + 2 consolidation tests + 1 plist test, all green

## Task Commits

1. **Task 1: health_snapshots migration + snapshot/cleanup functions** - `602cb43` (feat, TDD)
2. **Task 2: sb_health_trend MCP + consolidate entry point + launchd plist + install + tests** - `68f3ee0` (feat)

## Files Created/Modified

- `engine/db.py` — added `migrate_add_health_snapshots_table()`, called from `init_schema()`
- `engine/brain_health.py` — added `take_health_snapshot()` and `cleanup_old_snapshots()`
- `engine/mcp_server.py` — added `sb_health_trend` tool
- `engine/consolidate.py` — new file, `consolidate_main()` entry point
- `scripts/install_native.py` — added `write_consolidate_plist()`, updated `main()` to bootstrap consolidate agent
- `pyproject.toml` — added `sb-consolidate = engine.consolidate:consolidate_main`
- `tests/test_brain_health.py` — 5 tests: migration, insert, skip-dup, cleanup, keep-recent
- `tests/test_consolidate.py` — new file, 2 tests: clean run + idempotency
- `tests/test_install_native.py` — added `test_write_consolidate_plist`

## Decisions Made

- `health_snapshots` migration is last in `init_schema()` call chain — avoids ordering issues with other migrations.
- One-per-day guard uses `date(snapped_at) = ?` with `date.today().isoformat()` as the comparison value — SQLite's `date()` function strips the time component from stored TEXT, making the comparison work regardless of time-of-day.
- `consolidate_main()` imports from `engine.brain_health` inside the function body (lazy imports) to avoid any potential circular import at module load time.
- `test_plist_keys` pre-existing failure documented — the test calls `write_plist(fake_bin, fake_repo)` with the old signature, but the current file in the working tree already had a changed signature from a prior uncommitted phase change. Out of scope per SCOPE BOUNDARY rule.

## Deviations from Plan

None — plan executed exactly as written.

## Out-of-Scope Issues Found

- `tests/test_install_native.py::test_plist_keys` fails with `OSError: Read-only file system: '/fake'` — this is caused by a pre-existing `write_plist` signature change already in the working tree (not introduced by Plan 35-03). The test expects `write_plist(sb_watch_bin, repo_root, plist_path)` but the working tree has `write_plist(repo_root, plist_path)`. Logged to deferred-items.

## Known Stubs

None — all functionality is fully wired.

## Self-Check: PASSED

- engine/db.py contains `migrate_add_health_snapshots_table`: FOUND
- engine/brain_health.py contains `take_health_snapshot`: FOUND
- engine/brain_health.py contains `cleanup_old_snapshots`: FOUND
- engine/mcp_server.py contains `sb_health_trend`: FOUND
- engine/consolidate.py exists: FOUND
- scripts/install_native.py contains `write_consolidate_plist`: FOUND
- pyproject.toml contains `sb-consolidate`: FOUND
- tests/test_consolidate.py exists: FOUND
- commit 602cb43: FOUND
- commit 68f3ee0: FOUND

---
*Phase: 35-brain-consolidation*
*Completed: 2026-03-23*
