---
phase: 22-note-deletion-security-hardening
plan: "01"
subsystem: testing
tags: [tdd, delete, security, scaffold]
dependency_graph:
  requires: []
  provides: [engine/delete.py, tests/test_delete.py]
  affects: [phase-22-plan-02, phase-22-plan-03]
tech_stack:
  added: []
  patterns: [tdd-red, cascade-delete, path-traversal-guard]
key_files:
  created:
    - engine/delete.py
    - tests/test_delete.py
  modified: []
decisions:
  - "delete_note() stub uses NotImplementedError per TDD RED contract; sb-hook immediately implemented full cascade on commit"
  - "relationships INSERT uses rel_type column (not relationship_type) — schema correction"
  - "tmp_api_note fixture uses monkeypatch BRAIN_PATH so endpoint tests resolve paths within tmp_path"
metrics:
  duration: "4 minutes"
  completed_date: "2026-03-16"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
requirements: [GUIX-06]
---

# Phase 22 Plan 01: TDD RED Scaffold — delete_note() stub + 12 failing test stubs

TDD RED scaffold: engine/delete.py importable stub + tests/test_delete.py with 12 test stubs covering full cascade delete, FTS5 cleanup, endpoint 200/404, and path-traversal 403 guards.

## What Was Built

**Task 1 — engine/delete.py stub**
Created `engine/delete.py` exporting `delete_note(abs_path, conn, brain_root)` as an importable stub raising `NotImplementedError`. This satisfied the TDD RED prerequisite: tests can be collected without ImportError.

**Task 2 — tests/test_delete.py (12 stubs)**
Wrote 12 test stubs covering:
- Unit (7): `test_delete_note_removes_file`, `test_delete_note_removes_db_row`, `test_delete_note_removes_embedding`, `test_delete_note_removes_relationships`, `test_delete_note_removes_action_items`, `test_delete_note_audit_log`, `test_fts5_clean_after_delete`
- Endpoint (2): `test_delete_endpoint_200`, `test_delete_endpoint_404`
- Security (3): `test_delete_endpoint_path_traversal_403`, `test_get_note_path_traversal_403`, `test_save_note_path_traversal_403`

## Verification

```
uv run pytest tests/test_delete.py --collect-only -q
# Result: 12 tests collected, 0 errors

uv run pytest tests/test_delete.py -q
# Result: 12 passed (see Deviations — implementation was auto-applied by sb-hook)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed relationships INSERT column name**
- **Found during:** Task 2 verification
- **Issue:** `note_file` fixture used `relationship_type` column; actual schema uses `rel_type`
- **Fix:** Changed INSERT to use `rel_type` with value `"link"`
- **Files modified:** `tests/test_delete.py`
- **Commit:** 5780fae

**2. [Rule 1 - Bug] Added BRAIN_PATH monkeypatch to tmp_api_note fixture**
- **Found during:** Task 2 (hook-applied)
- **Issue:** Endpoint test fixture needed BRAIN_PATH env var set to tmp_path for path resolution to work
- **Fix:** Added `monkeypatch.setenv("BRAIN_PATH", str(tmp_path))` to `tmp_api_note`
- **Files modified:** `tests/test_delete.py`
- **Commit:** 5780fae (hook also contributed)

### Unexpected Behavior

**sb-hook auto-implemented Plan 02 on commit**

The project's post-commit sb-hook executed a GSD plan run and implemented the full `delete_note()` cascade (commit `c306a7d`) immediately after the Task 1 commit. This caused the unit tests to go green (all 7 pass) rather than staying red. The TDD RED goal was partially bypassed by automation.

- Plan 01's deliverables are complete: 12 tests collected, no ImportError, correct schema
- Plan 02's `engine/delete.py` implementation was already applied by the hook
- Plan 02 should verify the auto-implementation matches spec rather than rewrite from scratch

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | d6fc76b | feat(22-01): add engine/delete.py stub with NotImplementedError |
| Task 1+2 | 03d4eee | test(22-01): add failing test stubs + delete_note() importable stub |
| Task 2 fix | 5780fae | test(22-01): fix note_file fixture schema + add BRAIN_PATH monkeypatch |
| Hook (out-of-scope) | c306a7d | feat(22-02): implement delete_note() cascade — applied by sb-hook |

## Self-Check: PASSED

- engine/delete.py: FOUND
- tests/test_delete.py: FOUND
- Commit d6fc76b: FOUND
- Commit 5780fae: FOUND
