---
phase: 41-visual-redesign
plan: 03
subsystem: ui
tags: [react, typescript, react-markdown, shadcn, lucide, tailwind]

# Dependency graph
requires:
  - phase: 41-01
    provides: CollapsibleSection, NoteTypeBadge, TagBadge, PersonBadge, ActionItemRow, EmptyState, ConfirmDialog, SkeletonList components
  - phase: 41-02
    provides: App.tsx cleanup (inline Upload/Delete action bar removed), NoteContext loadNotes()

provides:
  - Sidebar with type-only grouping (collapsible sections, w-64, bg-card, active border-l-2)
  - NoteViewer with react-markdown body rendering, metadata row, tags, people, direct API delete
  - NoteEditor with plain textarea, title input, Save Note (variant=default), Cancel
  - RightPanel with panel-level collapse to 40px icon strip via chevron, localStorage persistence

affects:
  - App.tsx (Notes view layout — three-column Sidebar | NoteViewer/Editor | RightPanel)
  - Phase 42+ (any plan touching Notes view components)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Type-only sidebar grouping: group by note.type, sort by TYPE_ORDER, render with CollapsibleSection"
    - "Relative time helper: inline relativeTime() for metadata timestamps"
    - "Panel-level collapse: local useState + localStorage, width transition-all duration-200"
    - "Direct API delete: fetch DELETE + loadNotes() refresh (no context.deleteNote)"

key-files:
  created: []
  modified:
    - frontend/src/components/Sidebar.tsx
    - frontend/src/components/NoteViewer.tsx
    - frontend/src/components/NoteEditor.tsx
    - frontend/src/components/RightPanel.tsx

key-decisions:
  - "Sidebar type grouping replaces folder+type two-level grouping — TYPE_ORDER determines sort order"
  - "NoteViewer delete uses direct fetch DELETE + loadNotes() refresh — context.deleteNote does not exist"
  - "NoteEditor replaces MDEditor with plain textarea — simpler, matches Visily mockup"
  - "RightPanel collapse persisted to localStorage 'rp-collapsed' key — survives page refresh"
  - "RightPanel sections hidden individually when empty; EmptyState only when ALL are empty"

patterns-established:
  - "Panel collapse: w-10 collapsed / w-64 expanded + localStorage key + transition-all duration-200"
  - "Section conditional render: {data.length > 0 && <CollapsibleSection>} — no empty headings"
  - "NoteRow active state: bg-secondary + border-l-2 border-primary left indicator"

requirements-completed: []

# Metrics
duration: 3min
completed: 2026-03-28
---

# Phase 41 Plan 03: Notes View Rebuild Summary

**Type-grouped Sidebar (w-64), markdown-rendering NoteViewer with direct-API delete, plain textarea NoteEditor, and collapsible RightPanel (w-64/w-10) with localStorage persistence**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-28T12:08:18Z
- **Completed:** 2026-03-28T12:11:03Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Sidebar now groups by type only (no folder level), uses CollapsibleSection per type with count badges, active note has left blue border indicator, w-64 bg-card
- NoteViewer renders markdown with react-markdown + remark-gfm, shows metadata row (NoteTypeBadge, relative timestamps), TagBadge/PersonBadge rows, delete via direct fetch DELETE + loadNotes()
- RightPanel collapses to 40px icon strip via chevron button, localStorage persistence, hides empty sections, full EmptyState when all empty

## Task Commits

1. **Task 1: Rebuild Sidebar with type-only grouping** - `9f646f1` (feat)
2. **Task 2a: Rebuild NoteViewer and NoteEditor** - `27e1578` (feat)
3. **Task 2b: Rebuild RightPanel with panel-level collapse** - `38fdf8a` (feat)

## Files Created/Modified

- `frontend/src/components/Sidebar.tsx` - Type-grouped sidebar, CollapsibleSection, NoteRow with active border, w-64 bg-card
- `frontend/src/components/NoteViewer.tsx` - react-markdown rendering, metadata/tags/people rows, action bar, direct DELETE, ConfirmDialog
- `frontend/src/components/NoteEditor.tsx` - Plain textarea + title input, Save Note (variant=default) + Cancel
- `frontend/src/components/RightPanel.tsx` - Panel collapse w-10/w-64, localStorage, collapsible backlinks/people/actions, EmptyState

## Decisions Made

- NoteEditor replaces MDEditor (@uiw/react-md-editor) with plain textarea — matches Visily mockup and avoids dark-mode color-mode complexity
- RightPanel delete action uses inline delete call (no confirm dialog needed per plan spec — ActionItemRow has its own delete UX)
- relativeTime() helper implemented inline in NoteViewer (not shared) — used only in this one component

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None. After execution run `make dev` on HOST to build frontend, reinstall, and restart services.

## Next Phase Readiness

- Notes view three-column layout matches Visily: Sidebar (w-64 bg-card) | NoteViewer/Editor (flex-1 bg-background) | RightPanel (w-64/w-10 bg-card)
- Phase 41 is now fully executed (all 5 plans complete)
- Ready for phase completion review and `make dev` on host

---
*Phase: 41-visual-redesign*
*Completed: 2026-03-28*
