---
phase: 30-people-graph-hardening
plan: "03"
subsystem: mcp
tags: [mcp, people, person-context, column-lookup, json_each]
dependency_graph:
  requires: [30-01]
  provides: [sb_person_context-column-lookup, sb_list_people]
  affects: [engine/mcp_server.py, tests/test_mcp.py]
tech_stack:
  added: []
  patterns: [json_each virtual table, correlated subquery metrics, TDD RED-GREEN]
key_files:
  modified:
    - engine/mcp_server.py
    - tests/test_mcp.py
    - CLAUDE.md
decisions:
  - "sb_person_context uses json_each people column lookup exclusively — no body-scan fallback"
  - "Name input resolved via LOWER(title) match against type IN ('person','people'); path input detected by '/' presence"
  - "LIKE match on person_title in json_each WHERE allows people column entries that are name strings (not paths)"
  - "Body-only meetings (empty people column) intentionally excluded — column is source of truth after 30-01/30-02"
  - "Old mcp_person_brain fixture updated to seed people column so existing tests align with new column model"
  - "sb_list_people uses correlated subqueries (consistent with 27.4-02 pattern); ordered alphabetically"
  - "CLAUDE.md tool count updated 13 → 22 with full tool list"
metrics:
  duration: 25 min
  completed: "2026-03-20"
  tasks_completed: 2
  files_modified: 3
---

# Phase 30 Plan 03: sb_person_context + sb_list_people Summary

**One-liner:** Column-based sb_person_context (json_each people lookup, name/path input, relationship metrics) and new sb_list_people CRM directory tool.

## What Was Built

### Task 1: Enhanced sb_person_context

Rewrote the existing `sb_person_context` MCP tool in `engine/mcp_server.py`:

**Input resolution:** Accepts `name_or_path` — if contains `/`, treated as direct path; otherwise fuzzy-matched against person note titles via `LOWER(title)=LOWER(?)`.

**Meetings/mentions via json_each:** Replaced the body-scan loop with SQL using the virtual `json_each(COALESCE(n.people, '[]'))` table. Exact path match OR name-like match covers both path-stored and name-stored people column values.

**Return shape (new fields added):**
- `found: True/False` (was missing; returned raw error string before)
- `org`: extracted from entities JSON first orgs entry
- `last_interaction_date`: max created_at across meetings + mentions, sliced to date
- `total_meetings`, `total_mentions`, `total_actions`: integer counts
- Meetings ordered DESC by created_at (newest first)

**Old fixture migration:** Updated `mcp_person_brain` fixture to seed meetings/mentions with people column populated, aligning with the new column-based model.

### Task 2: New sb_list_people

New `sb_list_people()` MCP tool returns all `type IN ('person','people')` notes as a directory with per-person metrics via correlated subqueries:
- `open_actions`: undone action_items with assignee_path = person
- `last_interaction`: MAX meeting created_at where person in people column
- `total_meetings`: meeting count from people column
- `total_mentions`: non-person/people/meeting note count from people column
- `org`: from entities JSON

Results ordered alphabetically by title.

**CLAUDE.md** updated to reflect 22 registered MCP tools (was 13).

## Tests Added

| Test | Fixture | What It Verifies |
|------|---------|-----------------|
| test_person_context_column_lookup | mcp_person_brain_v2 | Column match includes 2 meetings; body-only meeting excluded |
| test_person_context_by_name | mcp_person_brain_v2 | "Anna Korhonen" string resolves to correct path |
| test_person_context_metrics | mcp_person_brain_v2 | total_meetings=2, last_interaction_date not null |
| test_person_context_not_found | mcp_person_brain_v2 | found=False for nonexistent name |
| test_person_context_chronological | mcp_person_brain_v2 | Meetings DESC by created_at |
| test_sb_list_people | mcp_list_people_brain | 2 people returned, Alice has 1 open_action + 1 meeting |
| test_sb_list_people_empty | inline | Empty DB returns empty list, no error |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Old mcp_person_brain fixture incompatible with column-based lookup**
- **Found during:** Task 1 GREEN verification (5 old tests ran on updated implementation)
- **Issue:** Old fixture seeded meetings with body text only (people column not set). 4 passing tests became 1 failing after the body-scan was removed.
- **Fix:** Updated `mcp_person_brain` to pass `people=json.dumps([person_path])` in all meeting/mention INSERT statements, aligning the test data with the new column model.
- **Files modified:** tests/test_mcp.py
- **Commit:** b1f0832

**2. [Rule 1 - Bug] test_sb_person_context_unknown_path expected old error string**
- **Found during:** Task 1 after fixture update
- **Issue:** Old test asserted `result.get("error") == "not found"` (short string). New implementation returns `found=False` + longer error message.
- **Fix:** Updated assertion to `result.get("found") is False` and `"error" in result`.
- **Files modified:** tests/test_mcp.py
- **Commit:** b1f0832

## Self-Check: PASSED

- engine/mcp_server.py: FOUND
- tests/test_mcp.py: FOUND
- 30-03-SUMMARY.md: FOUND
- Commit b1f0832 (Task 1): FOUND
- Commit 0050b0c (Task 2): FOUND
