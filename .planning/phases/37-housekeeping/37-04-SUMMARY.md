---
phase: 37-housekeeping
plan: 04
status: complete
---

# 37-04 Summary — Cascade delete gaps + impact preview

## What was done
Fixed two cascade delete gaps (orphaned assignee_path references, stale note_people entries when deleting person notes), and added pre-delete impact preview to the GUI modal, sb_forget MCP first-step, and a new API endpoint.

## Changes

### engine/delete.py
- Added `get_delete_impact(path_str, conn)` — returns `{action_items, relationships, appears_in_people_of}` counts.
- In `delete_note()`: capture note type BEFORE the DELETE, then if `type == "person"`: NULL `assignee_path` on action_items and DELETE from `note_people`.

### engine/forget.py
- After DB deletions (2d), added step 2d-bis: NULL `assignee_path` for all erased person paths.

### engine/api.py
- Added `GET /notes/<path>/impact` → returns `get_delete_impact()` result.
- Added `POST /actions` (from 37-02, already done in this session).

### engine/mcp_server.py
- `sb_forget` first-step response now includes impact counts in the message (e.g. "Impact: 3 action items, 2 relationships, mentioned in 1 notes.").

### frontend/src/components/DeleteNoteModal.tsx
- Added `impact`/`loadingImpact` state.
- `useEffect` on modal open fetches `GET /notes/{path}/impact`.
- Renders impact summary block (action_items · relationships · appears_in) when any count > 0.
- Loading skeleton while fetching.

### tests
- `tests/test_delete.py`: 3 new tests — person note NULLs assignee_path, person note cleans note_people, get_delete_impact counts.
- `tests/test_forget.py`: 1 new test — forget_person NULLs assignee_path.

## Verification
- `uv run pytest tests/test_delete.py tests/test_forget.py` — 29 passed, 1 pre-existing failure (test_delete_endpoint_404 308→404)
- `npx tsc --noEmit` — clean
