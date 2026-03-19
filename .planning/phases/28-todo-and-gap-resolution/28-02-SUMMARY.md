---
phase: 28-todo-and-gap-resolution
plan: "02"
subsystem: mcp
tags: [mcp, capture, smart-capture, heuristics, tdd]
dependency_graph:
  requires: []
  provides: [sb_capture_smart, sb_link, sb_unlink]
  affects: [engine/mcp_server.py, tests/test_mcp.py]
tech_stack:
  added: []
  patterns: [keyword-heuristic classification, segment-and-classify, two-step token]
key_files:
  created: []
  modified:
    - engine/mcp_server.py
    - tests/test_mcp.py
decisions:
  - "[28-02] sb_capture_smart splits by double-newline only for content >= 500 chars; shorter content treated as single segment to avoid over-segmenting short notes"
  - "[28-02] Person classification requires both a capitalized bigram (Name-like) AND a role/contact signal to avoid false positives from any two-word phrase in meeting notes"
  - "[28-02] confirm_token issued via existing _issue_token() helper — reuses 60s expiry infrastructure without new token store"
  - "[28-02] sb_link/sb_unlink added alongside sb_capture_smart — pre-seeded tests from plan 28-04 were already in test_mcp.py causing suite failures; Rule 3 auto-fix"
metrics:
  duration_minutes: 18
  completed_date: "2026-03-19"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 2
---

# Phase 28 Plan 02: sb_capture_smart MCP Tool Summary

**One-liner:** Keyword-heuristic freeform-text classifier that returns typed note suggestions without saving, using double-newline segmentation and regex matching for meeting/project/person/idea/note types.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement sb_capture_smart with heuristic classifier | 478f2c5 | engine/mcp_server.py, tests/test_mcp.py |

## What Was Built

`sb_capture_smart(content: str) -> dict` registered as an MCP tool in `engine/mcp_server.py`.

**Classification logic:**
- Split by `\n\n` if content >= 500 chars; single segment otherwise
- Per-segment type via regex (case-insensitive):
  - `meeting|discussed|attendees|agenda` → `"meeting"`
  - capitalized bigram + `role|contact|email|phone|linkedin` in first 200 chars → `"person"`
  - `project|milestone|deadline|sprint|roadmap` → `"project"`
  - `idea|what if|maybe|consider|brainstorm` → `"idea"`
  - else → `"note"`
- Title: first non-empty line, stripped of `#` prefix, max 80 chars
- Cross-links: if meeting + person segments both present, person slugs added to meeting's `links` list
- Returns `{"suggestions": [...], "confirm_token": str, "hint": "Call sb_capture_batch..."}` — nothing written to disk or DB

**Tests (5 new, all passing):**
- `test_sb_capture_smart_returns_suggestions` — meeting keyword → type="meeting"
- `test_sb_capture_smart_project_hint` — project keyword → type="project"
- `test_sb_capture_smart_default_note` — plain text → type in ("note", "idea")
- `test_sb_capture_smart_no_auto_save` — notes table count unchanged after call
- `test_sb_capture_smart_returns_confirm_token` — response has non-empty confirm_token + hint

**Also added (Rule 3 auto-fix):**
`sb_link(source_path, target_path, rel_type="link")` and `sb_unlink(source_path, target_path)` — plan 28-04's pre-seeded tests were already present in `test_mcp.py` and caused suite failures. Both tools use `INSERT OR IGNORE` / `DELETE` on the `relationships` table.

## Verification

```
uv run pytest tests/test_mcp.py -q -k "capture_smart or capture_batch"
# Result: 7 passed

uv run pytest tests/test_mcp.py -v
# Result: 42 passed, 2 xfailed (pre-existing dedup stubs)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-seeded sb_link/sb_unlink tests caused suite failures**
- **Found during:** Task 1 — full suite verification
- **Issue:** `test_mcp.py` already contained 5 tests for `sb_link`/`sb_unlink` (from plan 28-04 pre-seeding). These caused `AttributeError` since neither tool existed, blocking the plan's verification run.
- **Fix:** Implemented `sb_link` and `sb_unlink` in `engine/mcp_server.py` alongside `sb_capture_smart`. Final signatures use `source_path`/`target_path` params (linter-refined version with `INSERT OR IGNORE` idempotency).
- **Files modified:** engine/mcp_server.py
- **Commit:** 478f2c5

## Self-Check: PASSED

- engine/mcp_server.py: FOUND
- tests/test_mcp.py: FOUND
- Commit 478f2c5: FOUND
- sb_capture_smart importable from module: True
- sb_link importable from module: True
- sb_unlink importable from module: True
