---
phase: 25-file-capture-batch-capture
plan: "02"
subsystem: api, attachments, watcher
tags: [tdd, file-upload, batch-capture, attachments, dedup, watcher]
dependency_graph:
  requires: [25-01]
  provides: [attachments-module, upload-endpoint, attachments-list-endpoint, batch-capture-endpoint, watcher-dedup-guard]
  affects: [engine/attachments.py, engine/api.py, engine/watcher.py, tests/test_note_watcher.py]
tech_stack:
  added: []
  patterns: [suppress-before-write, lazy-import-dedup-guard, mime-allowlist, collision-suffix]
key_files:
  created:
    - engine/attachments.py
  modified:
    - engine/api.py
    - engine/watcher.py
    - tests/test_note_watcher.py
decisions:
  - "GET /notes/<path>/attachments uses note_path as a DB key only — no path-traversal guard needed since no file is opened"
  - "Watcher dedup guard uses lazy imports (from engine.attachments import ...) inside _fire() to avoid circular import at module load"
  - "suppress_next_create() called BEFORE f.save() so suppress window is open when FSEvents fires"
  - "TestWatcherDedup test body implemented in Wave 2 (not Wave 1) — stub only had pytest.xfail() call"
metrics:
  duration: 8 minutes
  completed_date: "2026-03-17"
  tasks_completed: 2
  files_modified: 4
---

# Phase 25 Plan 02: Backend Implementation Summary

Attachments module, three new API endpoints, and watcher dedup guard implemented; all 8 Wave 1 test stubs now pass (7 xpassed + 1 genuine pass).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | engine/attachments.py — save, list, suppress | 55f377f | engine/attachments.py |
| 2 | API endpoints + watcher dedup guard | 4356158 | engine/api.py, engine/watcher.py |
| 2b | TestWatcherDedup body implementation | ffe9b76 | tests/test_note_watcher.py |

## What Was Built

### engine/attachments.py (new)

- `save_attachment(note_path, file_path, filename, size) -> dict` — INSERT into attachments, return full row dict via lastrowid fetch
- `list_attachments(note_path) -> list[dict]` — SELECT all for note_path, ordered by id
- `suppress_next_create(abs_path, window=0.5)` — adds path to `_upload_suppress` set; Timer clears after window
- `is_upload_suppressed(abs_path) -> bool` — thread-safe read of suppress set
- Module-level `_upload_suppress: set[str]` + `_upload_suppress_lock` mirroring watcher.py pattern

### engine/api.py additions

- `ALLOWED_MIMES` constant — allowlist of safe MIME types (PDF, Office, images, text)
- `POST /files/upload` — MIME check → 415, secure_filename → 400 guard, collision-suffix handler, `suppress_next_create()` before `f.save()`, `save_attachment()` record
- `GET /notes/<path:note_path>/attachments` — note_path used as DB key only, returns `list_attachments(note_path)` directly (no path-traversal guard)
- `POST /batch-capture` — rglob("*.md") walk, skip hidden dirs (any part starts with `.`), skip already-indexed paths, INSERT with python-frontmatter title/type/body, `_broadcast` at end

### engine/watcher.py additions

- `NoteChangeHandler._fire()` dedup guard for `"created"` events: checks `is_upload_suppressed()` then queries both `notes` and `attachments` tables; returns early if already present

### tests/test_note_watcher.py

- `TestWatcherDedup::test_dedup_skips_already_indexed` — replaced `pytest.xfail()` stub with real test: isolated DB, pre-inserted note, `_ImmediateTimer`, `on_created` fires, `broadcast.assert_not_called()`

## Verification Results

```
uv run pytest tests/test_api_upload.py tests/test_note_watcher.py::TestWatcherDedup -v
-> 1 passed, 7 xpassed in 0.89s

uv run pytest tests/ --ignore=tests/test_intelligence.py --ignore=tests/test_mcp.py --ignore=tests/test_precommit.py
-> 260 passed, 1 skipped, 2 xfailed, 7 xpassed (no regressions)
```

Pre-existing failures (unrelated to Phase 25):
- `test_intelligence.py::TestClaudeMdHook::test_claude_md_contains_session_hook` — expects "sb-recap" in ~/.claude/CLAUDE.md
- `test_mcp.py::test_tool_parity` — asyncio.run() issue
- `test_precommit.py::test_blocks_api_key` — pre-commit hook test

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] GET /notes/<path>/attachments returned 403 for relative note_path**
- **Found during:** Task 2 verification
- **Issue:** Original implementation called `_resolve_note_path(note_path)` which rejects paths not rooted in brain_root. Test uses "test.md" as a simple key, not an absolute path.
- **Fix:** Removed `_resolve_note_path` guard from the attachments list endpoint — note_path is a DB lookup key, never opened as a file, so no traversal risk.
- **Files modified:** engine/api.py
- **Commit:** 4356158

**2. [Rule 2 - Missing functionality] TestWatcherDedup stub had no actual test assertions**
- **Found during:** Final verification (test still reporting xfailed)
- **Issue:** Wave 1 stub used `pytest.xfail("not implemented yet")` unconditional call — no assertions, so it could never auto-promote to pass even after production code shipped.
- **Fix:** Implemented the full test body in Wave 2 as part of Task 2 completion.
- **Files modified:** tests/test_note_watcher.py
- **Commit:** ffe9b76

## Self-Check: PASSED

- FOUND: engine/attachments.py (55f377f)
- FOUND: engine/api.py modified (4356158)
- FOUND: engine/watcher.py modified (4356158)
- FOUND: tests/test_note_watcher.py modified (ffe9b76)
- All 3 commits verified in git log
