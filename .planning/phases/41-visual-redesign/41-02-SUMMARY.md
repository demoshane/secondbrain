---
phase: 41
plan: 02
subsystem: frontend-ui
tags: [topbar, tabbar, command-palette, app-shell, visily-redesign]
dependency_graph:
  requires: [41-01]
  provides: [app-shell-v2]
  affects: [frontend/src/App.tsx, frontend/src/components/Topbar.tsx, frontend/src/components/TabBar.tsx, frontend/src/components/CommandPalette.tsx]
tech_stack:
  added: []
  patterns: [showAdvanced state for hidden search mode, EmptyState for no-note-selected, lucide icons in TabBar]
key_files:
  created: []
  modified:
    - frontend/src/components/Topbar.tsx
    - frontend/src/components/TabBar.tsx
    - frontend/src/components/CommandPalette.tsx
    - frontend/src/App.tsx
decisions:
  - "Search mode selector hidden behind SlidersHorizontal toggle (showAdvanced state, default false)"
  - "New Note is variant=default (primary CTA), Smart Capture is variant=outline, Batch is variant=ghost"
  - "TabBar uses native <button> elements instead of shadcn Button to allow border-b-2 bottom border without variant interference"
  - "CommandPalette splits notes into separate Notes group (separate from Navigation group) for clearer visual hierarchy"
  - "Inline Upload/Delete action bar removed from App.tsx — plan 03 re-adds delete inside NoteViewer"
metrics:
  duration_seconds: 96
  completed_date: "2026-03-28"
  tasks_completed: 2
  files_modified: 4
---

# Phase 41 Plan 02: App Shell Redesign Summary

**One-liner:** Rebuilt Topbar (52px, labeled buttons, hidden search mode), TabBar (40px, 8 tabs with lucide icons and active border), CommandPalette (dark popover bg, bg-black/60 backdrop), and App.tsx (EmptyState for no-note-selected, inline action bar removed).

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Rebuild Topbar and TabBar | f95050a | Topbar.tsx, TabBar.tsx |
| 2 | Rebuild CommandPalette and update App.tsx | a094a61 | CommandPalette.tsx, App.tsx |

## What Was Built

**Topbar (h-[52px]):**
- Layout: `h-[52px] flex items-center gap-2 px-4 border-b border-border bg-background`
- Search input with magnifier icon — Enter to search, Escape to clear
- `SlidersHorizontal` ghost button toggles `showAdvanced` state (default false) to show/hide search mode Select
- New Note button: `variant="default"` (primary CTA) with Plus icon + "New Note" label
- Smart Capture button: `variant="outline"` with `text-orange-400` Sparkles icon + "Smart Capture" label
- Batch button: `variant="ghost"` with FolderUp icon + "Batch" label
- SSE status dot: green-500 (connected) / red-500 (disconnected)

**TabBar (h-10):**
- Layout: `h-10 flex items-center border-b border-border bg-card px-2`
- 8 tabs: Notes (FileText), Actions (CheckSquare), People (Users), Meetings (Calendar), Projects (Briefcase), Intelligence (Brain), Inbox (Inbox), Links (Link)
- Active: `border-b-2 border-primary text-foreground font-semibold`
- Inactive: `border-b-2 border-transparent text-muted-foreground`
- Hover: `hover:text-foreground hover:bg-secondary/50`
- All data-testid attributes preserved (`tab-${tab.id}`)

**CommandPalette:**
- Backdrop: `bg-black/60` (was `bg-black/50`)
- Panel: `max-w-[600px] w-full bg-popover border border-border rounded-lg shadow-2xl`
- Item selected state: `aria-selected:bg-secondary`
- Split into 3 groups: Navigation, Notes, Capture (was: Navigation + Capture merged, notes inside Navigation)
- All existing functionality preserved: note navigation, Smart Capture, New Note, page navigation

**App.tsx:**
- Removed inline Upload/Delete action bar between Topbar and NoteViewer
- No-note-selected state now uses `EmptyState` with `FileText` icon, heading "No note open", body "Select a note from the sidebar or create a new one.", action "New Note"
- `showDelete` / `showUpload` state and modals kept (upload modal still used; delete modal available for plan 03)
- All other behavior unchanged

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all components are fully implemented. The `showDelete` and `showUpload` state variables remain in App.tsx but are no longer triggered from the shell; they will be wired inside NoteViewer in plan 03.

## Self-Check: PASSED

Files verified to exist on disk:
- frontend/src/components/Topbar.tsx — FOUND
- frontend/src/components/TabBar.tsx — FOUND
- frontend/src/components/CommandPalette.tsx — FOUND
- frontend/src/App.tsx — FOUND

Commits verified:
- f95050a — FOUND (Task 1: Topbar + TabBar)
- a094a61 — FOUND (Task 2: CommandPalette + App.tsx)
