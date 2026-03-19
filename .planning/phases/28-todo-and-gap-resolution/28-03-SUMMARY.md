---
phase: 28-todo-and-gap-resolution
plan: "03"
subsystem: mcp-server
tags: [mcp, tags, fuzzy-match, confirm-token, tdd]
dependency_graph:
  requires: []
  provides: [sb_tag MCP tool]
  affects: [engine/mcp_server.py, tests/test_mcp.py]
tech_stack:
  added: [difflib]
  patterns: [confirm-token gate, atomic frontmatter write, fuzzy tag matching]
key_files:
  created: []
  modified:
    - engine/mcp_server.py
    - tests/test_mcp.py
decisions:
  - "[28-03] sb_tag add with fuzzy match (cutoff 0.8) applies existing tag immediately; no confirm needed"
  - "[28-03] sb_tag add with no close match returns confirm_token before saving (same _issue_token/_consume_token pattern as sb_forget)"
  - "[28-03] sb_tag remove is unconditional (case-insensitive, idempotent, no confirm gate)"
  - "[28-03] _save_tags() helper is not a registered MCP tool — shared internal helper for atomic disk+DB write"
  - "[28-03] dict.fromkeys(current_tags + [final_tag]) used for deduplication while preserving insertion order"
metrics:
  duration: "19 min"
  completed_date: "2026-03-19"
  tasks_completed: 1
  files_modified: 2
requirements_completed: [28-TAG-01]
---

# Phase 28 Plan 03: sb_tag MCP Tool Summary

**One-liner:** sb_tag MCP tool with difflib fuzzy matching (cutoff 0.8) and confirm-token gate for new tags, preventing "meeting"/"meetings" proliferation.

## What Was Built

Added `sb_tag(path, action, tag, confirm_token)` to `engine/mcp_server.py`. The tool adds or removes tags on notes with two safety mechanisms:

1. **Fuzzy matching** — when adding a tag, all existing tags are fetched from DB via `json_each`. `difflib.get_close_matches(cutoff=0.8)` finds close variants. If a match is found, the existing tag is used immediately and returned with `matched` + `applied` keys.

2. **Confirm-token gate** — when a tag is brand-new (no fuzzy match), the tool returns a `confirm_token` without saving anything. The caller must pass the token back within 60s to save. Uses the existing `_issue_token` / `_consume_token` infrastructure.

3. **Remove** — case-insensitive removal, no token needed, idempotent (removing a non-existent tag is safe).

Helper `_save_tags(note_path, new_tags, abs_path, conn)` handles the atomic write: loads existing frontmatter via python-frontmatter, sets the tags key, writes via `tempfile + os.replace`, then `UPDATE notes SET tags=?`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement sb_tag with fuzzy matching and confirm-token gate | 478f2c5 | engine/mcp_server.py, tests/test_mcp.py |

## Tests

5 TDD tests added to `tests/test_mcp.py`:
- `test_sb_tag_adds` — add a brand-new tag via 2-step confirm flow; verifies disk + DB
- `test_sb_tag_removes` — remove an existing tag; verifies disk + DB
- `test_sb_tag_fuzzy_match` — "meeting" matches "meetings"; returns matched/applied
- `test_sb_tag_new_requires_confirm` — brand-new tag returns token, nothing saved
- `test_sb_tag_new_with_confirm` — second call with valid token saves tag

All 5 pass. Full `test_mcp.py` suite: all passing (2 expected xfails).

## Deviations from Plan

None — plan executed exactly as written.

Note: The 28-02 parallel agent commit (478f2c5) included this plan's changes in the same commit. The implementation was already present at HEAD when the task commit attempt ran. The work is correctly committed.

## Self-Check: PASSED

- `engine/mcp_server.py` contains `def sb_tag(` and `def _save_tags(` — FOUND
- `tests/test_mcp.py` contains all 5 test functions — FOUND
- Commit 478f2c5 exists and includes both files — FOUND
- All 5 sb_tag tests pass — CONFIRMED
