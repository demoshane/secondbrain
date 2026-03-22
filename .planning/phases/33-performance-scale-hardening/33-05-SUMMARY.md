---
plan: 33-05
phase: 33-performance-scale-hardening
status: complete
completed_at: 2026-03-22
---

## Summary

`sb_person_context` now uses the `note_people` junction table (Phase 32) as a fast path, replacing two separate `json_each` scans with a single indexed JOIN query.

## What was built

**engine/mcp_server.py:**
- Before: 4 queries (person lookup + 2x json_each scans + action items)
- After: 3 queries when note_people is populated (person lookup + 1x JOIN + action items)
- Fast path: `SELECT COUNT(*) FROM note_people` check → single `note_people JOIN notes` query → Python split by type
- Fallback: json_each scan preserved for fresh installs where note_people is not yet populated
- Result shape identical — no breaking changes

**tests/test_mcp.py:**
- `test_sb_person_context_uses_note_people_fast_path` — inserts into `note_people` directly, verifies the meeting is returned via the fast path

## Test results

**53 passed, 2 xfailed** — zero failures

All existing `test_sb_person_context_*` tests pass (they hit the fallback path since fixture doesn't populate note_people — validates backwards compat).

## Key decisions

- One extra `COUNT(*)` query to gate the fast path — worth it to ensure correctness on fresh installs; the COUNT is indexed and cheap
- LIMIT 20 on the JOIN query (consistent with existing json_each behavior)
- Action items query (assignee_path + text LIKE) kept unchanged — already single indexed lookup

## Requirements satisfied

- PERF-07: sb_person_context DB roundtrips reduced from 4 to 3 (when note_people populated)
