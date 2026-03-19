---
phase: 29-add-link-capture
plan: "01"
subsystem: testing
tags: [tdd, xfail, link-capture, phase-29]
dependency_graph:
  requires: []
  provides: [test-stubs-29]
  affects: [tests/test_link_capture.py]
tech_stack:
  added: []
  patterns: [xfail-strict-false, client-fixture, monkeypatch-isolation]
key_files:
  created:
    - tests/test_link_capture.py
  modified: []
decisions:
  - "[29-01] xfail(strict=False) used for Phase 29 stubs — auto-promotes to PASS once Wave 1 ships engine/link_capture.py, url column, sb_capture_link, and /links API"
  - "[29-01] client fixture patches both engine.db.DB_PATH and engine.paths.DB_PATH + BRAIN_PATH env var — consistent with meetings/people/inbox test pattern"
  - "[29-01] fetch_link_metadata imported from engine.link_capture (not engine.link_fetcher) — module name confirmed by plan interfaces section"
  - "[29-01] MCP tool registry check uses mcp._local_provider._components — same pattern as test_mcp.py test_tool_parity and test_sb_remind_tool_exists"
metrics:
  duration: "3 min"
  completed: "2026-03-19"
  tasks_completed: 1
  files_modified: 1
---

# Phase 29 Plan 01: Link Capture xfail Stubs Summary

**One-liner:** Six xfail(strict=False) stubs for Phase 29 link capture — url column, metadata fetch (success + fallback), MCP tool registration, /links API, and duplicate URL warning.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write xfail stubs for all Phase 29 behaviors | 247dd3f | tests/test_link_capture.py |

## What Was Built

Created `tests/test_link_capture.py` with 6 xfail stubs covering the full Phase 29 behavior surface:

1. **test_url_column_exists** — verifies `url` column in `notes` table after `init_schema`
2. **test_fetch_metadata_returns_title** — monkeypatches `urllib.request.urlopen`; asserts `title` key present and non-empty
3. **test_fetch_metadata_fallback_on_error** — patches urlopen to raise `OSError`; asserts hostname fallback (`"unreachable.invalid"`) and empty description
4. **test_sb_capture_link_registered** — checks `mcp._local_provider._components` for `"sb_capture_link"` tool key
5. **test_links_api_returns_list** — `GET /links` returns 200 with `{"links": [...]}` JSON
6. **test_capture_link_duplicate_warn** — captures same URL twice; second call returns `status="duplicate_url_warning"`

## Verification

```
uv run pytest tests/test_link_capture.py -v
→ 6 xfailed in 5.78s

uv run pytest tests/ --ignore=tests/test_gui.py --ignore=tests/test_preflight.py
→ 381 passed, 1 skipped, 12 xfailed, 38 xpassed (0 errors, 0 failures)
```

## Deviations from Plan

**1. [Rule 1 - Pre-existing file] Replaced non-xfail test file with xfail stubs**

- **Found during:** Task 1
- **Issue:** `tests/test_link_capture.py` already existed with 9 regular `FAILED` tests (no xfail decorators). The plan's `done` condition requires all tests to be XFAIL, not FAILED.
- **Fix:** Rewrote the file with the 6 prescribed xfail(strict=False) stubs from the plan's `<behavior>` section.
- **Files modified:** tests/test_link_capture.py
- **Commit:** 247dd3f

## Self-Check: PASSED

- [x] `tests/test_link_capture.py` exists
- [x] 6 tests collected
- [x] All 6 XFAIL (no FAILED, no ERROR)
- [x] Full suite 381 passed, 0 errors
- [x] Commit 247dd3f exists
