---
phase: 06-integration-gap-closure
plan: "01"
subsystem: engine/reindex + engine/watcher
tags: [reindex, watcher, pii, absolute-path, classifier, ai-routing]
dependency_graph:
  requires: [06-00]
  provides: [absolute-path-storage, per-file-pii-routing]
  affects: [engine/reindex.py, engine/watcher.py, RAG reads, watcher AI adapter selection]
tech_stack:
  added: []
  patterns: [deferred-import-classify, per-file-classify-before-route]
key_files:
  created: []
  modified:
    - engine/reindex.py
    - engine/watcher.py
    - tests/test_reindex.py
    - tests/test_watcher.py
key_decisions:
  - "Store str(md_path) absolute path in reindex — not relative_to(brain_root) — so RAG reads locate files without brain_root reconstruction"
  - "classify() called inside on_new_file() per-file with deferred import — mirrors capture.py pattern; removes daemon-level adapter binding"
  - "test_reindex_parses_frontmatter_fields updated to use LIKE '%typed.md' — required for absolute path compatibility"
metrics:
  duration: "~12 minutes"
  completed: "2026-03-15"
  tasks_completed: 2
  files_modified: 4
---

# Phase 06 Plan 01: Fix Reindex Absolute Path + Watcher PII Classification Summary

Two surgical fixes: reindex stores absolute paths (one-line change); watcher classifies each file before routing to adapter. Both flip Wave 0 xfail tests to GREEN.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix reindex.py absolute path (SEARCH-01) | ff59d31 | engine/reindex.py, tests/test_reindex.py |
| 2 | Fix watcher.py per-file PII classification (AI-02) | 3e976ee | engine/watcher.py, tests/test_watcher.py |

## What Was Built

### Task 1: Absolute Path Storage in reindex.py

Replaced the `try/except` block that computed a relative path with a single line:

```python
note_path = str(md_path)
```

All downstream INSERT references updated from `rel_path` to `note_path`. The `ON CONFLICT(path)` key is unchanged. After reindex, every row in `notes.path` is now an absolute filesystem path, which RAG reads can use directly without brain_root reconstruction.

Also updated `test_reindex_parses_frontmatter_fields` to query `WHERE path LIKE '%typed.md'` instead of `WHERE path='typed.md'` — necessary because the stored path is now absolute.

### Task 2: Per-File PII Classification in watcher.py

Removed the single daemon-level `adapter = router_mod.get_adapter("private", CONFIG_PATH)` that was bound once at daemon start. Rewrote `on_new_file()` to:

1. Read file content (best-effort, `errors="ignore"`)
2. Import and call `classify("private", text_content)` per file
3. Call `router_mod.get_adapter(sensitivity, CONFIG_PATH)` with the classified sensitivity
4. Pass `sensitivity` through to `capture_note()` (was hardcoded `"private"`)

Pattern mirrors `capture.py` exactly as specified by AI-02.

## Deviations from Plan

None — plan executed exactly as written.

The pre-existing `test_subagent_documents_all_commands` XPASS(strict) failure (CAP-08 xfail stub) is unrelated to this plan and was present before execution. Logged to deferred items.

## Verification Results

```
tests/test_reindex.py .....   5 passed
tests/test_watcher.py .........  9 passed

Full suite (excluding pre-existing CAP-08 XPASS):
116 passed, 5 skipped, 1 xfailed
```

Success criteria met:
- test_reindex_stores_absolute_paths: PASSED (was xfail)
- test_watcher_pii_routes_to_ollama: PASSED (was xfail)
- test_watcher_binary_fallback_to_private: PASSED (was xfail)
- test_main_on_new_file_no_input_on_ai_failure: PASSED
- All other existing tests: GREEN

## Self-Check: PASSED

- [x] engine/reindex.py exists and contains `note_path = str(md_path)`
- [x] engine/watcher.py exists and contains `from engine.classifier import classify`
- [x] Commits ff59d31 and 3e976ee exist
- [x] 14 tests in test_reindex.py + test_watcher.py all pass
