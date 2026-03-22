---
phase: 34-gui-management-productivity
plan: "03"
subsystem: frontend+backend
tags: [entity-crud, people, meetings, projects, modal, mcp-tool, api]
dependency_graph:
  requires: [34-01]
  provides: [NewEntityModal, DeleteEntityModal, POST /people, POST /meetings, POST /projects, DELETE /people, DELETE /meetings, DELETE /projects, GET /people/links, sb_create_person]
  affects:
    - frontend/src/components/PeoplePage.tsx
    - frontend/src/components/MeetingsPage.tsx
    - frontend/src/components/ProjectsPage.tsx
    - engine/api.py
    - engine/mcp_server.py
tech_stack:
  added: []
  patterns:
    - Entity create via capture_note() with people/meeting/projects note types
    - Cascade delete: NULL assignee_path in action_items before unlink
    - Link count fetch (GET /people/<path>/links) for cascade warning UX
    - Modal components follow NewNoteModal/DeleteNoteModal contract
    - sonner toast.success/toast.error on all mutations
key_files:
  created:
    - frontend/src/components/NewEntityModal.tsx
    - frontend/src/components/DeleteEntityModal.tsx
  modified:
    - engine/api.py
    - engine/mcp_server.py
    - frontend/src/components/PeoplePage.tsx
    - frontend/src/components/MeetingsPage.tsx
    - frontend/src/components/ProjectsPage.tsx
    - tests/test_people.py
    - tests/test_mcp.py
decisions:
  - "DELETE /people clears assignee_path (UPDATE … SET assignee_path = NULL) before calling delete_note — prevents orphan action items"
  - "note_people junction uses `person` column (not `person_path`) — DELETE clause uses WHERE person = path_str"
  - "Worktree rebased onto main after plan-01+02 were merged — no conflict"
  - "sb_create_person uses capture_note(note_type='people') — consistent with API endpoint pattern"
metrics:
  duration: ~25min
  completed: "2026-03-22T18:33:11Z"
  tasks_completed: 2
  files_changed: 9
---

# Phase 34 Plan 03: Entity Create/Delete Flows Summary

Entity create and delete flows for People, Meetings, and Projects pages — backend API endpoints, frontend modals, and sb_create_person MCP tool.

## What Was Built

**Backend (engine/api.py):**
- `POST /people` — creates person note via `capture_note(note_type='people')`
- `POST /meetings` — creates meeting note via `capture_note(note_type='meeting')`
- `POST /projects` — creates project note via `capture_note(note_type='projects')`
- `GET /people/<path>/links` — returns `{meeting_count, action_count}` for cascade warning
- `DELETE /people/<path>` — NULLs `assignee_path` in action_items, removes from note_people junction, then delegates to `delete_note()`
- `DELETE /meetings/<path>` — delegates to `delete_note()`
- `DELETE /projects/<path>` — delegates to `delete_note()`

**MCP tool (engine/mcp_server.py):**
- `sb_create_person(name, role="")` — creates person note, returns `{path, title}`

**Frontend:**
- `NewEntityModal` — entity creation modal for people/meetings/projects. People modal shows optional role field. Enter-key support, loading state, toast on success/error.
- `DeleteEntityModal` — entity deletion modal with cascade warning for people (fetches link counts, shows "N meeting notes mention this person"). "Keep Person/Meeting/Project" dismiss label per UI-SPEC. Toast on success/error.
- `PeoplePage`, `MeetingsPage`, `ProjectsPage` — all three pages updated with New Entity button in header, per-row delete icon, and both modals mounted.

## Test Coverage

- `test_create_person_post_happy_path` — POST /people returns 201 with path
- `test_create_person_missing_name` — POST /people without name returns 400
- `test_delete_person_clears_assignee` — DELETE /people NULLs assignee_path in action_items
- `test_sb_create_person_happy_path` — sb_create_person returns path + title
- `test_sb_create_person_missing_name` — empty name returns error dict

## Deviations from Plan

**1. [Rule 1 - Bug] Fixed double-close on delete_person**
- **Found during:** Task 1 test run
- **Issue:** delete_person had both `conn.close()` in except block and `finally: conn.close()` — caused double-close OperationalError
- **Fix:** Removed `conn.close()` from except block, kept only in finally
- **Files modified:** engine/api.py

**2. [Rule 1 - Bug] Fixed note_people column name**
- **Found during:** Task 1 test run
- **Issue:** `DELETE FROM note_people WHERE person_path = ?` — column is `person`, not `person_path`
- **Fix:** Changed to `WHERE person = ?`
- **Files modified:** engine/api.py

**3. [Deviation] Worktree rebase before Task 2**
- Worktree was missing Plan 01+02 changes (sonner, ActionItemList, updated PeoplePage)
- Rebased worktree branch onto main before implementing frontend components

## Self-Check

### Files Created
- FOUND: frontend/src/components/NewEntityModal.tsx
- FOUND: frontend/src/components/DeleteEntityModal.tsx

### Commits
- FOUND: feat(34-03): add backend entity CRUD endpoints + sb_create_person MCP tool
- FOUND: feat(34-03): NewEntityModal and DeleteEntityModal + entity page create/delete wiring

## Self-Check: PASSED
