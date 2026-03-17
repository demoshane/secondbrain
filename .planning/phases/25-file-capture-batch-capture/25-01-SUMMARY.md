---
phase: 25-file-capture-batch-capture
plan: "01"
subsystem: db-schema, test-scaffolds
tags: [tdd, db-migration, attachments, upload, batch-capture]
dependency_graph:
  requires: []
  provides: [attachments-table, test-stubs-upload, test-stubs-batch-capture, test-stub-watcher-dedup]
  affects: [engine/db.py, tests/test_api_upload.py, tests/test_note_watcher.py]
tech_stack:
  added: []
  patterns: [idempotent-migration, xfail-tdd-stubs]
key_files:
  created:
    - tests/test_api_upload.py
  modified:
    - engine/db.py
    - tests/test_note_watcher.py
decisions:
  - "attachments table uses TEXT note_path/file_path/filename (not FK) for loose coupling; matches existing action_items pattern"
  - "xfail(strict=False) chosen over pytest.skip — stubs are collected, counted, and will auto-promote to pass once Wave 2 ships"
  - "client fixture patches both engine.db.DB_PATH and engine.paths.DB_PATH for full isolation (learned from Phase 24)"
metrics:
  duration: 2 minutes
  completed_date: "2026-03-17"
  tasks_completed: 2
  files_modified: 3
---

# Phase 25 Plan 01: DB Migration + Test Scaffolds Summary

Idempotent `attachments` DB table migration added to `engine/db.py`; 7 failing test stubs for upload/batch-capture and 1 watcher-dedup stub scaffold the Wave 2 contract.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | DB migration — attachments table | cc0a0c0 | engine/db.py |
| 2 | Test scaffolds — upload, batch capture, watcher dedup | 7e1ffa9 | tests/test_api_upload.py, tests/test_note_watcher.py |

## What Was Built

### Task 1 — DB migration
- Added `migrate_add_attachments_table(conn)` to `engine/db.py` immediately after `migrate_add_action_items_table`
- Schema: `id, note_path, file_path, filename, size, uploaded_at` — uses `CREATE TABLE IF NOT EXISTS` for idempotency
- Called at end of `init_schema()` so all existing and future consumers get the table automatically

### Task 2 — Test scaffolds
**`tests/test_api_upload.py`** — 7 xfail stubs:
- `TestFileUpload::test_upload_saves_file` — expects file in `files/` dir after POST
- `TestFileUpload::test_upload_inserts_attachment_row` — expects DB row after POST
- `TestFileUpload::test_upload_rejects_executable` — expects 415 for .exe MIME
- `TestAttachmentsList::test_list_attachments` — expects JSON list from GET `/notes/<path>/attachments`
- `TestBatchCapture::test_batch_captures_unindexed` — unindexed .md appears in `succeeded`
- `TestBatchCapture::test_batch_skips_indexed` — already-indexed .md absent from `succeeded`
- `TestBatchCapture::test_batch_returns_structured_result` — response has `succeeded` + `failed` keys

**`tests/test_note_watcher.py`** — `TestWatcherDedup` class added at bottom with `test_dedup_skips_already_indexed` stub

## Verification Results

```
uv run pytest tests/test_db.py -x -q       -> 3 passed
uv run pytest tests/test_api_upload.py tests/test_note_watcher.py::TestWatcherDedup -v
                                            -> 8 xfailed (all collected, no ImportError)
sqlite3 :memory: init_schema -> SELECT name -> ('attachments',)
```

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- FOUND: engine/db.py (cc0a0c0)
- FOUND: tests/test_api_upload.py (7e1ffa9)
- FOUND: tests/test_note_watcher.py (7e1ffa9)
- All commits verified in git log
