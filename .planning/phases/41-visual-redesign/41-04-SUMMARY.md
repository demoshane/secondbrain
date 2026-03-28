---
phase: 41-visual-redesign
plan: "04"
subsystem: frontend-ui, backend-api
tags: [ui, two-column-layout, people, meetings, projects, api]
dependency_graph:
  requires: ["41-01"]
  provides: ["PeoplePage", "MeetingsPage", "ProjectsPage", "POST /projects/<path>/meetings"]
  affects: ["frontend/src/components/PeoplePage.tsx", "frontend/src/components/MeetingsPage.tsx", "frontend/src/components/ProjectsPage.tsx", "engine/api.py"]
tech_stack:
  added: []
  patterns: ["two-column layout (w-80 list + flex-1 detail)", "EmptyState for empty list and no-selection", "CollapsibleSection with localStorage persistence", "ActionItemRow for action mutations", "PersonBadge for meeting participants", "NoteTypeBadge for linked meeting labels"]
key_files:
  created: []
  modified:
    - frontend/src/components/PeoplePage.tsx
    - frontend/src/components/MeetingsPage.tsx
    - frontend/src/components/ProjectsPage.tsx
    - engine/api.py
decisions:
  - "ProjectsPage uses inline select form for Link Meeting (not modal) — simpler UX, avoids extra dialog layer"
  - "MeetingsPage removed backlinks section — plan spec focuses on participants + actions; backlinks not in spec"
  - "link_meeting_to_project stores meeting_sp (resolved path) directly for SSE broadcast consistency"
metrics:
  duration: 203
  completed_date: "2026-03-28"
  tasks: 2
  files: 4
---

# Phase 41 Plan 04: People, Meetings, Projects Pages — Two-Column Layout Summary

Rebuilt three entity pages as two-column layouts (w-80 list + flex-1 detail) using shared UI components from Plan 01, and added the deferred POST /projects/<path>/meetings backend endpoint.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Rebuild PeoplePage and MeetingsPage | d124296 |
| 2 | Rebuild ProjectsPage + POST /projects/meetings endpoint | 353ecb8 |

## What Was Built

### PeoplePage.tsx
- Two-column layout: `w-80 bg-card` list column + `flex-1 bg-background` detail column
- List: header with "New Person" button, filter input, ScrollArea with person rows (name, org, open_actions badge)
- Empty states: "No people yet" (empty list) + "Select a person" (no selection), both using `EmptyState` component
- Detail: Brain Insight (`CollapsibleSection` with markdown body), Actions (`ActionItemRow` with toggle/delete), Related Notes
- Delete flow: ghost button → `ConfirmDialog` → `DeleteEntityModal` (existing pattern)
- `SkeletonList` during list load and detail load

### MeetingsPage.tsx
- Same two-column pattern
- List rows show title, meeting_date, participant count, open_actions badge
- Detail: Participants (`PersonBadge` for each), Actions (`ActionItemRow`), Notes (markdown body)
- Empty states: "No meetings yet" + "Select a meeting"
- Toast feedback on action mutations

### ProjectsPage.tsx
- Same two-column pattern
- List rows show title, updated_at, open_actions badge
- Detail header shows status badge (green=active, amber=paused, muted=completed)
- Linked Meetings section: lists linked meetings with `NoteTypeBadge` + title + date; inline "Link Meeting" form (select dropdown + POST)
- Actions section with `ActionItemRow`
- Related Notes section (backlinks from `/notes/<path>/meta`)

### engine/api.py — `link_meeting_to_project`
- Route: `POST /projects/<path:note_path>/meetings`
- Validates project exists with `type='projects'` and meeting exists with `type='meeting'`
- Checks for existing relationship before INSERT to prevent duplicates
- Inserts `rel_type='linked'` into `relationships` table
- Broadcasts `_broadcast({"type": "notes_changed", "path": sp})` after successful link
- Returns JSON: `{ project_path, meeting_path, linked: true }`

## Deviations from Plan

None — plan executed as written. The `DeleteEntityModal` pattern (existing component) was used in combination with the new `ConfirmDialog` for a two-step delete UX (confirm → delete), matching the UI-SPEC destructive action pattern.

## Known Stubs

None. All data flows are wired to real API endpoints.

## Self-Check: PASSED
