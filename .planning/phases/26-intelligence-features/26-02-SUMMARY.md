---
phase: 26-intelligence-features
plan: "02"
subsystem: intelligence
tags: [recap, action-items, digest, api]
dependency_graph:
  requires: [26-01]
  provides: [generate_recap_on_demand, POST /intelligence/recap, digest column fix, action item dedup]
  affects: [engine/intelligence.py, engine/digest.py, engine/api.py]
tech_stack:
  added: []
  patterns: [PII-aware adapter routing, lazy import inside route handler, SELECT COUNT dedup guard]
key_files:
  created: []
  modified:
    - engine/intelligence.py
    - engine/digest.py
    - engine/api.py
decisions:
  - "generate_recap_on_demand() reads from notes table directly; no file existence check"
  - "extract_action_items() gains dual call signature: (note_path, body, sensitivity, conn) and (note_path, conn) — second reads frontmatter from disk"
  - "dedup guard uses SELECT COUNT(*) before each INSERT, not batch pre-check, for simplicity"
  - "POST /intelligence/recap uses lazy import to avoid circular import risk"
metrics:
  duration: 4 min
  completed_date: "2026-03-17"
  tasks_completed: 2
  files_modified: 3
---

# Phase 26 Plan 02: Recap Backend Summary

On-demand recap generation, action item deduplication, digest column fix, and POST /intelligence/recap API endpoint.

## What Was Built

- `generate_recap_on_demand(conn)` in `engine/intelligence.py`: queries notes from last 7 days, routes PII vs public separately through `_router`, returns plain prose or fallback strings — no idempotency guard
- Dedup guard in `extract_action_items()`: `SELECT COUNT(*)` check before each `INSERT INTO action_items` prevents duplicate rows when same note is captured twice
- Updated `extract_action_items()` signature to support `(note_path, conn)` call style (reads file and frontmatter from disk) in addition to original `(note_path, body, sensitivity, conn)` style
- `RECAP_SYSTEM_PROMPT` replaced with specific 5-part version: 3-5 sentences covering what was worked on, key decisions, open threads; mentions note titles by name; plain prose
- `engine/digest.py`: fixed column names in action_items query — `text` and `done=0` (was `action_text` and `status='open'`)
- `POST /intelligence/recap` added to `engine/api.py` immediately after `GET /intelligence`

## Test Results

- `test_generate_recap_on_demand_returns_string` — xpassed (was xfail stub)
- `test_extract_action_items_no_duplicate_on_recapture` — xpassed (was xfail stub)
- `test_generate_digest_open_actions_uses_correct_column` — xpassed (was xfail stub)
- All existing `test_intelligence.py`, `test_digest.py`, `test_api.py` tests — pass (48 passed, 1 xfailed, 2 xpassed)
- Pre-existing failure: `TestClaudeMdHook.test_claude_md_contains_session_hook` — checks global CLAUDE.md for `sb-recap`; out of scope for this plan

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] extract_action_items() dual call signature**
- **Found during:** Task 1
- **Issue:** The test stub calls `extract_action_items(note_path, conn)` with only 2 args, but existing signature requires `(note_path, body, sensitivity, conn)` — would cause TypeError
- **Fix:** Added argument detection: if second arg is not a str, treat as conn and read note from disk via frontmatter
- **Files modified:** engine/intelligence.py
- **Commit:** c358bc1

## Self-Check: PASSED

- engine/intelligence.py contains `generate_recap_on_demand` — verified
- engine/digest.py uses `text` and `done=0` — verified
- engine/api.py contains `@app.post("/intelligence/recap")` — verified
- Commit c358bc1 exists
