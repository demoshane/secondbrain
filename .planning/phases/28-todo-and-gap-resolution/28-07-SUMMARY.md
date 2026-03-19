---
phase: 28-todo-and-gap-resolution
plan: "07"
subsystem: tests
tags: [pytest, playwright, conftest, test-isolation, gui]
dependency_graph:
  requires: [28-01, 28-02, 28-03, 28-04, 28-05, 28-06]
  provides: [full-suite-ci-green]
  affects: [tests/conftest.py]
tech_stack:
  added: []
  patterns: [session-scoped sentinel + autouse function-scoped re-anchor fixture]
key_files:
  created: []
  modified:
    - tests/conftest.py
decisions:
  - "_GUI_DB_PATH module-level sentinel set by gui_brain after patching DB_PATH; allows _restore_gui_db to know when to re-anchor (skips re-anchor before gui_brain has run)"
  - "_restore_gui_db is function-scoped autouse (not session-scoped) — it runs both before the test body (setup side) and after (yield/teardown side) so monkeypatch.undo() on teardown is immediately overwritten"
  - "Re-anchor both engine.db.DB_PATH and engine.paths.DB_PATH — get_connection() reads from engine.db.DB_PATH; Flask route handlers also import from engine.paths; both must agree"
metrics:
  duration: "12 min"
  completed_date: "2026-03-19"
  tasks_completed: 1
  files_modified: 1
---

# Phase 28 Plan 07: GUI DB_PATH Isolation Fix Summary

Session-scoped GUI test DB re-anchored after every test via autouse fixture and module-level sentinel, making 9 Playwright tests that failed only in full-suite context pass reliably.

## Objective

Fix 9 Playwright test failures that occurred only when the full suite ran, caused by other test files' function-scoped monkeypatches restoring `engine.db.DB_PATH` / `engine.paths.DB_PATH` to the real `~/SecondBrain` path mid-session.

## What Was Done

### Task 1: Diagnose and fix conftest.py

**Root cause confirmed:** `gui_brain` (session-scoped) sets `_db.DB_PATH = tmp_db` via direct assignment. Other test files use `monkeypatch.setattr(engine.db, "DB_PATH", ...)` in function-scoped fixtures. `monkeypatch` captures the attribute value at setup time (which may be BEFORE `gui_brain` runs, since session fixture ordering across files is not guaranteed). On teardown, `monkeypatch.undo()` restores the captured original value — the real `~/SecondBrain` path — mid-session. The Flask server's subsequent calls to `get_connection()` then read the wrong DB.

**Fix applied:**

1. Added module-level sentinel `_GUI_DB_PATH = None` at the top of `conftest.py`.
2. Updated `gui_brain` fixture to set `global _GUI_DB_PATH; _GUI_DB_PATH = tmp_db` immediately after patching the module attributes — so the sentinel is only set once the correct tmp DB is known.
3. Added `_restore_gui_db` autouse function-scoped fixture that runs before and after every test. It checks `_GUI_DB_PATH is not None` and if so, re-anchors both `engine.db.DB_PATH` and `engine.paths.DB_PATH` to the sentinel value. The post-yield re-anchor runs AFTER `monkeypatch.undo()` teardown, overwriting any accidental restore.

**Key property:** For tests that do NOT use `gui_brain` (i.e., before the session fixture has run), `_GUI_DB_PATH` is `None` and the fixture is a no-op — non-GUI tests are unaffected.

## Verification

```
uv run pytest tests/test_gui.py -k "test_people_detail_opens or ..." --tb=short -v
= 9 passed in 15.24s

uv run pytest tests/ --tb=no -q
Exit code: 0 (all tests pass)
```

## Deviations from Plan

None — plan executed exactly as written. The `_restore_gui_db` autouse function-scoped pattern from the plan's "Alternative" section was chosen as it is simpler than the `pytest_runtest_teardown` hook approach and covers both pre-test and post-teardown re-anchoring in a single fixture.

## Self-Check: PASSED

- FOUND: tests/conftest.py
- FOUND: commit fcb6d37
