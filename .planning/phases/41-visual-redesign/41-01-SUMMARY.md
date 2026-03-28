---
phase: 41
plan: 01
subsystem: frontend-ui
tags: [design-tokens, dark-palette, shared-components, shadcn]
dependency_graph:
  requires: []
  provides: [visily-palette, shared-ui-components]
  affects: [frontend/src/**]
tech_stack:
  added: []
  patterns: [CSS vars via hsl(var(--*)), noteType prop on Badge, LucideIcon typed prop]
key_files:
  created:
    - frontend/src/components/ui/note-type-badge.tsx
    - frontend/src/components/ui/tag-badge.tsx
    - frontend/src/components/ui/person-badge.tsx
    - frontend/src/components/ui/skeleton-list.tsx
    - frontend/src/components/ui/empty-state.tsx
    - frontend/src/components/ui/collapsible-section.tsx
    - frontend/src/components/ui/action-item-row.tsx
    - frontend/src/components/ui/confirm-dialog.tsx
    - frontend/src/components/ui/health-score-gauge.tsx
  modified:
    - frontend/src/index.css
    - frontend/tailwind.config.js
    - frontend/src/components/ui/badge.tsx
    - frontend/src/components/SmartCaptureModal.tsx
    - frontend/src/components/IntelligencePage.tsx
    - frontend/src/components/MeetingsPage.tsx
    - frontend/src/components/PeoplePage.tsx
    - frontend/src/components/ProjectsPage.tsx
decisions:
  - "prose-invert always applied (not dark:prose-invert) since app is always dark"
  - "noteTypeColorMap exported from badge.tsx so downstream components can import without re-declaring"
  - "CollapsibleSection uses max-h-[9999px] approach for CSS-only collapse animation (no framer-motion dependency)"
metrics:
  duration_seconds: 193
  completed_date: "2026-03-28"
  tasks_completed: 3
  files_modified: 17
---

# Phase 41 Plan 01: Design Tokens and Shared UI Components Summary

**One-liner:** Replaced shadcn light/dark CSS vars with Visily dark navy palette and built 9 shared components (NoteTypeBadge, TagBadge, PersonBadge, SkeletonList, EmptyState, CollapsibleSection, ActionItemRow, ConfirmDialog, HealthScoreGauge) for downstream plans to consume.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Replace design tokens and remove dark mode | 13d93ae | index.css, tailwind.config.js, 5 component files |
| 2a | Build display components | 06c7cae | badge.tsx + 5 new components |
| 2b | Build interactive components | 850af84 | 4 new interactive components |

## What Was Built

**Design token system:**
- Replaced the entire shadcn default palette (light + dark) with a single `:root {}` block containing Visily dark navy values (#0f1117 background, #151b27 cards, #5b6cf7 primary, etc.)
- Removed `darkMode: ['class']` from tailwind.config.js — app is always dark
- Eliminated all `dark:` Tailwind prefixes across 5 component files (4x `dark:prose-invert`, 6x TYPE_COLORS entries in SmartCaptureModal)

**9 shared UI components:**
- `NoteTypeBadge` — wraps Badge with per-type color mapping, 9 note types supported
- `TagBadge` — pill with # prefix, optional remove button
- `PersonBadge` — secondary pill with optional remove button
- `SkeletonList` — animated loading placeholders
- `EmptyState` — icon + heading + body + optional CTA button
- `CollapsibleSection` — chevron toggle with localStorage persistence keyed by sectionId
- `ActionItemRow` — checkbox, done strikethrough, overdue red date, hover-reveal delete
- `ConfirmDialog` — AlertTriangle destructive variant with ghost cancel / destructive confirm
- `HealthScoreGauge` — 32px score with green/amber/red thresholds (80+/50-79/<50)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Removed dark: prefixes from 4 page components**
- **Found during:** Task 1 verification
- **Issue:** `prose prose-sm dark:prose-invert` in PeoplePage, IntelligencePage, ProjectsPage, MeetingsPage — dead code after dark mode removal; prose text would appear black on dark background
- **Fix:** Changed to `prose prose-sm prose-invert` (always-on invert)
- **Files modified:** PeoplePage.tsx, IntelligencePage.tsx, ProjectsPage.tsx, MeetingsPage.tsx
- **Commit:** 13d93ae

**2. [Rule 1 - Bug] Replaced TYPE_COLORS in SmartCaptureModal**
- **Found during:** Task 1 (same grep sweep)
- **Issue:** TYPE_COLORS used light/dark conditional classes (`bg-blue-100 dark:bg-blue-900`) — would show light colors on dark background after dark mode removal
- **Fix:** Replaced with Visily spec hex pairs matching note-type-badge color map
- **Files modified:** SmartCaptureModal.tsx
- **Commit:** 13d93ae

## Known Stubs

None — all components are fully implemented. No data sources stubbed; these are pure UI primitives that receive props from callers.

## Notes for Downstream Plans

- Plans 02-05 can import all 9 components from `@/components/ui/[name]`
- `noteTypeColorMap` is exported from `badge.tsx` if any plan needs the raw map
- `make dev` must be run on HOST after all 5 plans complete (per plan output spec)

## Self-Check: PASSED

All 9 component files verified to exist on disk. All 3 commits verified in git log.
