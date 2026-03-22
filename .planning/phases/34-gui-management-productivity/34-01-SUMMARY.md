---
phase: 34-gui-management-productivity
plan: "01"
subsystem: frontend-components
tags: [gui, action-items, react, typescript, shared-component]
dependency_graph:
  requires: []
  provides: [ActionItemList shared component, interactive action items on all surfaces]
  affects: [ActionsPage, NoteViewer, PeoplePage, RightPanel]
tech_stack:
  added: []
  patterns: [shared-component extraction, prop-driven toggle/assign, client-side fetch+filter]
key_files:
  created:
    - frontend/src/components/ActionItemList.tsx
  modified:
    - frontend/src/components/ActionsPage.tsx
    - frontend/src/components/NoteViewer.tsx
    - frontend/src/components/PeoplePage.tsx
    - frontend/src/components/RightPanel.tsx
decisions:
  - ActionItemList receives people as prop (no internal fetch) — parent owns data, component owns rendering
  - NoteViewer and RightPanel both filter client-side (fetch all actions, filter by note_path) — acceptable for small brain; server-side filter is future optimization
  - PeoplePage reloadActions refetch uses assignee param (server-side filter already existed for person detail)
metrics:
  duration: "150s"
  completed: "2026-03-22"
  tasks_completed: 2
  files_changed: 5
---

# Phase 34 Plan 01: ActionItemList Shared Component Summary

Extracted a shared `ActionItemList` component from `ActionsPage` and embedded it across all note-context surfaces: NoteViewer, PeoplePage detail panel, and RightPanel.

## What Was Built

**ActionItemList.tsx (new):** Reusable interactive action item table with Radix Checkbox (toggle done), Radix Select (assign person, `h-7 w-36 text-xs`), done-item strike-through, optional ExternalLink source-note icon (per D-02, `showSourceLink` prop), and inline empty-state text. Props: `actions`, `people`, `onToggle`, `onAssign`, `showSourceLink?`, `onOpenNote?`.

**ActionsPage.tsx (refactored):** Removed inline table rendering. Now renders `<ActionItemList showSourceLink onOpenNote={openNote} />`. Filter/sort/fetch logic remains in ActionsPage. Uses `useNoteContext` `openNote` for source note navigation.

**NoteViewer.tsx:** Added `noteActions` + `actionPeople` state. Fetches all actions on note load, filters client-side by `note_path`. Renders `<ActionItemList>` below markdown body when actions exist, with local `toggleDone`/`assignTo` handlers (PUT `/actions/:id` + refetch).

**PeoplePage.tsx:** Added `peopleNotes` state (for assignee picker). Replaced static `<input type="checkbox" disabled>` list with `<ActionItemList>` in the Open Actions section. Added `toggleDone`/`assignTo` with `reloadActions` (refetches via existing `/actions?assignee=` param).

**RightPanel.tsx:** Added `noteActions` + `actionPeople` state. Fetches actions on `currentPath` change, filters client-side. Renders `<ActionItemList>` section below People badges when actions exist.

## Verification Results

- `npx tsc --noEmit`: zero errors (both tasks)
- `grep -r "ActionItemList" frontend/src/components/`: 11 references across 5 files (requirement: ≥5)
- `ExternalLink` import present in ActionItemList.tsx
- `aria-label="Open source note"` present
- `No action items` empty state present
- `<input type="checkbox" disabled` removed from PeoplePage
- All acceptance criteria met

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All action item surfaces fetch live data from `/api/actions`. The client-side filter in NoteViewer and RightPanel (fetch all, filter by `note_path`) is a documented trade-off acknowledged in the plan, not a stub.

## Self-Check: PASSED

- `frontend/src/components/ActionItemList.tsx`: FOUND
- `frontend/src/components/ActionsPage.tsx`: FOUND (contains `import.*ActionItemList`)
- `frontend/src/components/NoteViewer.tsx`: FOUND (contains `ActionItemList`, `Action Items` heading)
- `frontend/src/components/PeoplePage.tsx`: FOUND (contains `ActionItemList`, no disabled checkbox)
- `frontend/src/components/RightPanel.tsx`: FOUND (contains `ActionItemList`)
- Commits dc0268d, 2c0ec33: FOUND in git log
