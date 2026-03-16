---
phase: 22-note-deletion-security-hardening
plan: "02"
subsystem: backend
tags: [deletion, security, api, path-traversal, cascade, tdd]
dependency_graph:
  requires: ["22-01"]
  provides: ["delete_note() cascade", "DELETE /notes/<path> endpoint", "_resolve_note_path guard"]
  affects: ["engine/api.py", "engine/delete.py", "tests/test_delete.py", "tests/test_api.py", "tests/test_api_extensions.py"]
tech_stack:
  added: []
  patterns: ["path traversal guard via Path.is_relative_to()", "lazy import to avoid circular deps", "watcher suppression before unlink", "monkeypatch BRAIN_PATH in test fixtures"]
key_files:
  created: []
  modified:
    - engine/delete.py
    - engine/api.py
    - tests/test_delete.py
    - tests/test_api.py
    - tests/test_api_extensions.py
decisions:
  - "Lazy import of suppress_next_delete inside delete_note() to avoid circular import with engine.watcher"
  - "Lazy import of delete_note inside delete_note_endpoint() to avoid circular import"
  - "_resolve_note_path reads BRAIN_PATH env var with expanduser fallback; both paths resolved before is_relative_to()"
  - "Test fixtures use monkeypatch.setenv(BRAIN_PATH, tmp_path) — guard requires path to be inside brain_root"
  - "notes_ad AFTER DELETE trigger handles FTS5 automatically — no explicit rebuild needed in delete_note()"
  - "Prior audit_log rows for the note are deleted (GDPR consistency) before inserting new delete_note entry with note_path=NULL"
metrics:
  duration: "12 min"
  completed: "2026-03-16"
  tasks_completed: 2
  files_modified: 5
---

# Phase 22 Plan 02: Delete Note Cascade + API Route Summary

**One-liner:** Full cascade delete_note() with watcher suppression + DELETE /notes/<path> Flask route with path traversal guard on all four note endpoints.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 22-01 (inline) | Create delete_note() stub + TDD RED tests | 03d4eee | engine/delete.py, tests/test_delete.py |
| 1 | Implement delete_note() cascade in engine/delete.py | c306a7d | engine/delete.py, tests/test_delete.py |
| 2 | Add DELETE route + _resolve_note_path guard to engine/api.py | eed059e | engine/api.py, tests/test_api.py, tests/test_api_extensions.py |

## What Was Built

### engine/delete.py

Full cascade implementation:
1. `suppress_next_delete(path_str)` — called before unlink to prevent watcher false-positive
2. `abs_path.unlink(missing_ok=True)` — removes file from disk
3. `DELETE FROM notes WHERE path=?` — notes_ad trigger handles FTS5 automatically
4. `DELETE FROM note_embeddings WHERE note_path=?`
5. `DELETE FROM relationships WHERE source_path=? OR target_path=?`
6. `DELETE FROM action_items WHERE note_path=?`
7. `DELETE FROM audit_log WHERE note_path=?` — GDPR consistency cleanup
8. `INSERT INTO audit_log (event_type="delete_note", note_path=NULL, detail=path_str)`
9. `conn.commit()`
Returns `{"deleted": True, "path": path_str}`.

### engine/api.py

- `_resolve_note_path(note_path)` helper: resolves both brain_root and note path, raises `ValueError("path traversal")` if note path is not relative to brain_root
- Guard applied to: `GET /notes/<path>`, `PUT /notes/<path>`, `GET /notes/<path>/meta`, `DELETE /notes/<path>`
- New `DELETE /notes/<path>` endpoint: 403 on traversal, 404 if missing, 200+`{deleted:True}` on success, 500+`{error: type(e).__name__}` on exception

## Test Results

- 12/12 tests in tests/test_delete.py pass
- 18/18 tests in tests/test_api.py pass (no regressions)
- 9/9 tests in tests/test_api_extensions.py pass (no regressions)
- Full suite: 249 passed, 1 skipped, 1 xfailed (2 pre-existing unrelated failures excluded)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 22-01 scaffold not executed**
- **Found during:** Pre-execution check
- **Issue:** engine/delete.py stub and tests/test_delete.py did not exist; plan depends_on 22-01 which had not been run
- **Fix:** Executed 22-01 tasks inline (created stub + 12 TDD RED test stubs), committed as 03d4eee
- **Files modified:** engine/delete.py, tests/test_delete.py
- **Commit:** 03d4eee

**2. [Rule 1 - Bug] Test fixtures used tmp_path without setting BRAIN_PATH**
- **Found during:** Task 2 verification
- **Issue:** _resolve_note_path guard correctly 403s any path outside BRAIN_PATH; existing test fixtures in test_api.py and test_api_extensions.py passed tmp_path-based absolute paths without setting BRAIN_PATH env var
- **Fix:** Added `monkeypatch.setenv("BRAIN_PATH", str(tmp_path))` to affected fixtures: `tmp_note`, `tmp_note_pair` (test_api.py), `TestSaveNote.test_put_note_saves_content`, `TestNoteMeta.test_get_note_meta_returns_structure` (test_api_extensions.py), and `tmp_api_note`, `test_delete_endpoint_404` (test_delete.py)
- **Files modified:** tests/test_api.py, tests/test_api_extensions.py, tests/test_delete.py
- **Commit:** eed059e

**3. [Rule 1 - Bug] relationships column name mismatch**
- **Found during:** Task 1 first test run
- **Issue:** Test file used `relationship_type` but schema has `rel_type`; a linter auto-corrected this in the file before re-run
- **Fix:** Linter-auto-corrected; confirmed schema column is `rel_type`
- **Files modified:** tests/test_delete.py

## Self-Check: PASSED

- FOUND: engine/delete.py
- FOUND: engine/api.py
- FOUND: tests/test_delete.py
- FOUND commit 03d4eee: test(22-01)
- FOUND commit c306a7d: feat(22-02) delete_note()
- FOUND commit eed059e: feat(22-02) DELETE route
