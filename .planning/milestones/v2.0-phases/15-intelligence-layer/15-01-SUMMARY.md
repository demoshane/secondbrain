---
phase: 15-intelligence-layer
plan: "01"
subsystem: intelligence
tags: [tdd, red-scaffold, db-migration, test-infrastructure]
dependency_graph:
  requires: [14-embedding-infrastructure]
  provides: [intelligence-test-scaffold, action-items-ddl, intelligence-stubs]
  affects: [engine/db.py, engine/intelligence.py, tests/test_intelligence.py]
tech_stack:
  added: []
  patterns: [idempotent-migration, tdd-red-scaffold, module-stub-with-pass-bodies]
key_files:
  created:
    - engine/intelligence.py
    - tests/test_intelligence.py
  modified:
    - engine/db.py
decisions:
  - "_router = None placeholder added to intelligence.py so unittest.mock.patch can target it without AttributeError"
  - "action_items DDL placed both in SCHEMA_SQL constant and in migrate_add_action_items_table() for belt-and-suspenders coverage"
metrics:
  duration: "~3m 26s"
  completed: "2026-03-15"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 1
---

# Phase 15 Plan 01: Intelligence Layer RED Scaffold Summary

**One-liner:** TDD Wave 0 scaffold — action_items DDL migration in db.py, 10-function stub intelligence module, 18 RED tests covering all INTL-01 through INTL-10 requirements.

## What Was Built

### Task 1: action_items DDL + stub intelligence module

**engine/db.py** received:
- `action_items` CREATE TABLE added to `SCHEMA_SQL` constant (id, note_path, text, done, created_at)
- `migrate_add_action_items_table(conn)` idempotent migration function following `migrate_add_people_column` pattern
- Call to `migrate_add_action_items_table(conn)` appended to `init_schema()`

**engine/intelligence.py** created as a new stub module:
- Module docstring and imports (json, datetime, subprocess, pathlib.Path)
- Constants: `STATE_PATH`, `VAULT_GATE = 20`, `_router = None`
- 10 stub functions with correct type signatures and minimal return values: `_load_state`, `_save_state`, `budget_available`, `consume_budget`, `detect_git_context`, `extract_action_items`, `get_stale_notes`, `check_stale_nudge`, `find_similar`, `check_connections`, `recap_main`, `actions_main`

### Task 2: RED test stubs

**tests/test_intelligence.py** created with 13 test classes (18 tests):

| Class | Tests | RED/Pass |
|-------|-------|----------|
| TestBudgetGate | 3 | 1 RED, 2 pass |
| TestExplicitCommandsAlwaysWork | 1 | pass |
| TestExtractActionItems | 2 | 1 RED, 1 pass |
| TestActionsList | 1 | RED |
| TestActionsDone | 1 | RED |
| TestStaleNudge | 2 | 1 RED, 1 pass |
| TestEvergreenExempt | 1 | pass |
| TestStaleSnooze | 1 | pass |
| TestConnectionSuggestion | 1 | RED |
| TestConnectionSuggestionEmpty | 1 | pass |
| TestRecap | 1 | RED |
| TestRecapNoContext | 1 | RED |
| TestClaudeMdHook | 1 | RED |

**9 tests RED, 9 tests pass (expected pass — silent/skip behaviors).**
No ImportErrors or SyntaxErrors — clean RED state confirmed.

## Verification

- `python -m pytest tests/test_intelligence.py -q` — 9 FAILED, 9 passed, 0 errors
- `from engine.intelligence import budget_available, extract_action_items, find_similar, recap_main, actions_main` — OK
- `engine/db.py` SCHEMA_SQL contains "action_items" — verified
- `migrate_add_action_items_table` present and idempotent — verified

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `_router = None` placeholder to intelligence.py**
- **Found during:** Task 2 verification
- **Issue:** `patch("engine.intelligence._router")` raised `AttributeError: module does not have attribute '_router'` because the stub module had no `_router` attribute to patch against
- **Fix:** Added `_router = None` as a module-level constant after `VAULT_GATE`
- **Files modified:** engine/intelligence.py
- **Commit:** d109860

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 7c3ac6e | feat(15-01): add action_items DDL and stub intelligence module |
| 2 | d109860 | test(15-01): write RED scaffold for all INTL-01 through INTL-10 |

## Self-Check: PASSED

- engine/intelligence.py — FOUND
- tests/test_intelligence.py — FOUND
- .planning/phases/15-intelligence-layer/15-01-SUMMARY.md — FOUND
- commit 7c3ac6e — FOUND
- commit d109860 — FOUND
