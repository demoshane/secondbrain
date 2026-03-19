---
phase: 28-todo-and-gap-resolution
plan: "01"
subsystem: engine/capture
tags: [dedup, embeddings, performance, tdd]
dependency_graph:
  requires: []
  provides: [check_capture_dedup-max_body_len, _embed_texts_for_dedup]
  affects: [engine/mcp_server.py sb_capture]
tech_stack:
  added: []
  patterns: [title-only-fast-path, monkeypatch-helper-extraction]
key_files:
  created: []
  modified:
    - engine/capture.py
    - tests/test_capture.py
decisions:
  - "[28-01] check_capture_dedup max_body_len=2000: body > 2000 chars → embed title only; body <= 2000 → embed full title+body (unchanged)"
  - "[28-01] _embed_texts_for_dedup() extracted as module-level helper so tests can monkeypatch it without patching inside a closure"
metrics:
  duration: "3 min"
  completed: "2026-03-19"
  tasks_completed: 1
  files_changed: 2
---

# Phase 28 Plan 01: Dedup Title-Only Fast-Path Summary

**One-liner:** Added `max_body_len=2000` fast-path to `check_capture_dedup()` that embeds only the title for large bodies, eliminating the 8s timeout risk on `sb_capture` for long inputs.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add title-only fast-path to check_capture_dedup | 1237093 | engine/capture.py, tests/test_capture.py |

## What Was Built

`check_capture_dedup()` in `engine/capture.py` now accepts a `max_body_len: int = 2000` parameter. When the note body exceeds this length, only the title is embedded for dedup comparison instead of the full `f"{title}\n{body}"` string. This eliminates the root cause of MCP tool timeouts on large captures: the embedding model was processing thousands of tokens for the full body.

A module-level `_embed_texts_for_dedup()` helper was extracted to make the embed call monkeypatchable in tests without replacing closures.

Two new deterministic tests verify both code paths:
- `test_dedup_title_only_large_body`: 2001-char body → `embed_texts` called with `["My Title"]`
- `test_dedup_short_body_uses_full_text`: 10-char body → `embed_texts` called with `["My Title\nshort body"]`

No callers were modified (default param preserves backward compatibility).

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `engine/capture.py` modified: FOUND
- `tests/test_capture.py` modified: FOUND
- Commit 1237093: FOUND (`/usr/bin/git -C /Users/tuomasleppanen/second-brain log --oneline -1` confirms)
- All capture tests green: PASSED (`uv run pytest tests/test_capture.py -q` → 11 passed, 2 xfailed)
