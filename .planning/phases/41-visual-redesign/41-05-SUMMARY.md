---
phase: 41-visual-redesign
plan: "05"
subsystem: frontend
tags: [ui, redesign, actions, inbox, intelligence, links]
dependency_graph:
  requires: ["41-01"]
  provides: ["ActionsPage", "InboxPage", "IntelligencePage", "LinksPage"]
  affects: ["frontend/src/components/ActionsPage.tsx", "frontend/src/components/InboxPage.tsx", "frontend/src/components/IntelligencePage.tsx", "frontend/src/components/LinksPage.tsx"]
tech_stack:
  added: []
  patterns: ["ActionItemRow with showSource", "CollapsibleSection from 41-01", "EmptyState from 41-01", "HealthScoreGauge from 41-01", "SkeletonList from 41-01", "ConfirmDialog from 41-01"]
key_files:
  created: []
  modified:
    - frontend/src/components/ActionsPage.tsx
    - frontend/src/components/InboxPage.tsx
    - frontend/src/components/IntelligencePage.tsx
    - frontend/src/components/LinksPage.tsx
decisions:
  - "ActionsPage uses button-group filter (Open/Done/All) instead of Select dropdown per UI-SPEC interaction pattern"
  - "IntelligencePage removes Chrome Extension section — moved out of scope per UI-SPEC two-column layout"
  - "LinksPage adds markdown rendering for body (was <pre>) and delete capability via ConfirmDialog"
metrics:
  duration_seconds: 233
  completed_date: "2026-03-28"
  tasks_completed: 2
  files_modified: 4
---

# Phase 41 Plan 05: Actions, Inbox, Intelligence, Links Pages Summary

Four page components rebuilt to Visily two-column/full-width layouts using shared UI primitives from plan 41-01.

## What Was Built

### Task 1: ActionsPage + InboxPage (commit 73bd65d)

**ActionsPage** — full-width single column:
- Header with "Action Items" title + "New Action" button (variant=default, icon=Plus)
- Button-group filter bar: Open / Done / All (ghost buttons with active bg-secondary state), plus assignee Select
- ActionItemRow per item with `showSource={true}`
- Three EmptyState variants: All clear (CheckCircle2), No matching items (Filter + Clear filters action), loading SkeletonList
- ConfirmDialog for delete with "Remove Item" / "Go Back" copy per UI-SPEC

**InboxPage** — two-column (w-80 bg-card list + flex-1 bg-background detail):
- Header shows "Inbox" + total count badge
- Three CollapsibleSection sections with localStorage persistence:
  1. Unassigned Actions — action cards with source title (not raw path), Select assign, Dismiss
  2. Unprocessed Notes — note cards with date, Add Backlink (outline), Dismiss
  3. Empty Notes — Delete all + per-note Delete/Dismiss
- SkeletonList while first load
- EmptyState (Inbox, "Inbox ready") when no selection in detail panel
- Kept full BacklinkPicker inline search from previous implementation

### Task 2: IntelligencePage + LinksPage (commit 7de0120)

**IntelligencePage** — two unequal columns (flex-[2] left ~65% / flex-1 right ~35%):
- Left: bg-card Brain Health card with HealthScoreGauge, 5-stat row (total/orphans/empty/broken/duplicates, color-coded red/amber), CollapsibleSection for each issue category; CollapsibleSection "Stale Notes" below
- Right: bg-card Weekly Recap card with EmptyState ("No recap generated") + Generate Recap button; Quick Actions (Run Health Check)
- SkeletonList for health card loading state
- Removed Chrome Extension section (out of scope for this two-column layout redesign)

**LinksPage** — two-column (w-80 bg-card list + flex-1 bg-background detail):
- List: SkeletonList loading, search + tag filter, link rows with title/domain/date/tags
- Detail: EmptyState "Select a link" (no selection) / "No saved links" (empty list)
- Detail panel: title, clickable domain URL (text-primary), date, tag badges, markdown-rendered body (upgraded from `<pre>`)
- Trash icon button + ConfirmDialog for delete (new capability)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] LinksPage delete capability added**
- **Found during:** Task 2
- **Issue:** Plan spec called for ConfirmDialog import on LinksPage, but original component had no delete. UI-SPEC required it.
- **Fix:** Added Trash2 icon button + ConfirmDialog + DELETE /notes/:path API call + toast feedback
- **Files modified:** frontend/src/components/LinksPage.tsx
- **Commit:** 7de0120

**2. [Rule 2 - Missing functionality] LinksPage body upgraded from `<pre>` to markdown**
- **Found during:** Task 2
- **Issue:** Original used `<pre>` — ui-descriptions/links-page.md called this out as a known issue. Plan spec implied markdown rendering (uses `prose prose-sm prose-invert` pattern from other pages).
- **Fix:** Added `react-markdown` + `remark-gfm` rendering for link body content
- **Files modified:** frontend/src/components/LinksPage.tsx
- **Commit:** 7de0120

**3. [Rule 1 - Scope] IntelligencePage Chrome Extension section removed**
- **Found during:** Task 2
- **Issue:** Chrome Extension section did not fit in the new two-column layout and is a one-time setup feature not a daily-use panel. UI-SPEC two-column layout had no place for it.
- **Fix:** Removed from IntelligencePage. Can be added to Settings page if needed.
- **Files modified:** frontend/src/components/IntelligencePage.tsx
- **Commit:** 7de0120

## Known Stubs

None. All four pages connect to real API endpoints (GET /actions, GET /inbox, GET /brain-health, GET /intelligence, GET /links).

## Verification

- TypeScript compilation: PASS (no errors)
- Vite build: PASS (built in 2.12s, chunk size warning is pre-existing)
- ActionsPage.tsx: ActionItemRow (2), EmptyState (3), SkeletonList — all present
- InboxPage.tsx: w-80 (1), bg-card (1), CollapsibleSection (3), EmptyState (2), SkeletonList — all present
- IntelligencePage.tsx: HealthScoreGauge (2), flex-[2] (1), CollapsibleSection (6), EmptyState (2), SkeletonList — all present
- LinksPage.tsx: w-80 (1), EmptyState (3), ConfirmDialog (1), SkeletonList — all present

## Self-Check: PASSED
