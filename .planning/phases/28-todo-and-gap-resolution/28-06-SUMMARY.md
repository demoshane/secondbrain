---
phase: 28-todo-and-gap-resolution
plan: "06"
subsystem: mcp
tags: [mcp, people, context, aggregation]
dependency_graph:
  requires: [engine/mcp_server.py, engine/db.py]
  provides: [sb_person_context MCP tool]
  affects: [engine/mcp_server.py, tests/test_mcp.py]
tech_stack:
  added: []
  patterns: [row_factory=sqlite3.Row for named column access, body-mention detection]
key_files:
  created: []
  modified:
    - engine/mcp_server.py
    - tests/test_mcp.py
decisions:
  - "[28-06] sb_person_context sets conn.row_factory = sqlite3.Row locally — get_connection() does not set it globally, so named column access requires explicit row_factory on each connection"
  - "[28-06] meetings detection uses body-only scan (person_title in body) — consistent with note_meta() body-mention pattern"
  - "[28-06] actions dedup uses seen_ids set — assigned + mentioned rows combined with id deduplication"
  - "[28-06] mentions query excludes type IN ('person','people') — prevents person notes appearing as mentions of themselves"
metrics:
  duration: "20 min"
  completed: "2026-03-19"
  tasks_completed: 1
  files_modified: 2
requirements_satisfied: [28-PERSON-01]
---

# Phase 28 Plan 06: sb_person_context MCP Tool Summary

One-line: sb_person_context MCP tool collapses 4+ person-context calls into one, returning note body + meetings + actions + mentions via body-mention detection.

## What Was Built

Added `sb_person_context(path: str) -> dict` to `engine/mcp_server.py`. The tool takes a person note path and returns a single aggregated dict with all available context about that person:

- `note`: the person note's title and body
- `meetings`: all meeting notes where the person's name appears in the body (case-insensitive)
- `actions`: action items assigned to the person (via `assignee_path`) plus items mentioning them by name in text, deduplicated by id
- `mentions`: non-person notes where the person's name appears in body

Returns `{"error": "not found", "path": path}` gracefully for unknown paths.

## Tests Added (TDD)

5 tests in `tests/test_mcp.py` with `mcp_person_brain` fixture providing full DB isolation:

| Test | What it verifies |
|------|-----------------|
| `test_sb_person_context_returns_note_body` | note.body contains person note text |
| `test_sb_person_context_returns_meetings` | meetings list includes seeded meeting with name in body |
| `test_sb_person_context_returns_actions` | actions list includes assigned action item |
| `test_sb_person_context_returns_mentions` | mentions list includes regular note mentioning the person |
| `test_sb_person_context_unknown_path` | returns `{"error": "not found"}` for absent path |

All 5 pass. Full suite (non-GUI) green: no regressions.

## Key Technical Decisions

- `conn.row_factory = sqlite3.Row` set locally inside `sb_person_context` — `get_connection()` does not set it globally. Named column access (`row["title"]`) requires this.
- Meetings use body-only scan: `person_title.lower() in body.lower()` — consistent with `note_meta()` body-mention detection pattern established in Phase 27.7.
- Actions dedup: assigned rows collected first into `seen_ids` set; mentioned rows appended only if id not already seen.
- Mentions query: `type NOT IN ('person', 'people')` prevents person notes from appearing as their own mentions.
- BRAIN_ROOT imported locally (inside function body) — consistent with plan requirement for test isolation.

## Deviations from Plan

**Pre-existing implementation discovered:** `sb_person_context` was already present in `engine/mcp_server.py` and `tests/test_mcp.py` as of commit `478f2c5 feat(28-02)`. The implementation exactly matches the plan specification. The TDD write cycle in this execution confirmed the implementation is correct and all 5 tests pass. No additional changes were needed.

## Self-Check

- [x] `sb_person_context` present in `engine/mcp_server.py` — confirmed via grep
- [x] 5 tests present in `tests/test_mcp.py` — confirmed via grep (16 hits for `sb_person_context`)
- [x] All 5 tests pass: `5 passed in 23.25s`
- [x] Full non-GUI suite: no `F` or `E` in output (dots + xfail markers only)

## Self-Check: PASSED
