---
phase: 34
plan: 04
subsystem: frontend
tags: [gui, action-items, autocomplete, toast, intelligence]
dependency_graph:
  requires: [34-01, 34-03]
  provides: [tag-autocomplete, interactive-intelligence-actions, toast-feedback]
  affects: [IntelligencePage, NoteViewer, PeoplePage, RightPanel, InboxPage, api.py]
tech_stack:
  added: [TagAutocomplete component, GET /tags endpoint]
  patterns: [keyboard-navigable dropdown, click-outside dismiss, toast mutation feedback]
key_files:
  created:
    - frontend/src/components/TagAutocomplete.tsx
  modified:
    - engine/api.py
    - frontend/src/components/NoteViewer.tsx
    - frontend/src/components/IntelligencePage.tsx
    - frontend/src/components/PeoplePage.tsx
    - frontend/src/components/RightPanel.tsx
decisions:
  - TagAutocomplete calls onSelect for both dropdown picks and plain Enter — single callback handles all cases
  - InboxPage count badges satisfied by pre-existing Section({count}) pattern — no structural change needed
  - People fetched from /people endpoint in IntelligencePage (returns PersonSummary[] not Note[]) — cast-compatible for ActionItemList prop
metrics:
  duration: 25
  completed_date: "2026-03-22"
  tasks_completed: 2
  files_modified: 6
---

# Phase 34 Plan 04: Interactive Intelligence + Tag Autocomplete Summary

**One-liner:** Tag autocomplete with keyboard nav replaces plain tag input; IntelligencePage gains interactive ActionItemList; toast feedback added across all action mutation surfaces.

## Tasks Completed

| # | Name | Commit | Key Files |
|---|------|--------|-----------|
| 1 | GET /tags endpoint and TagAutocomplete component | 95f4971 | engine/api.py, TagAutocomplete.tsx, NoteViewer.tsx |
| 2 | ActionItemList on IntelligencePage + toast retrofix | 1978d7c | IntelligencePage.tsx, PeoplePage.tsx, RightPanel.tsx |

## What Was Built

### Task 1: GET /tags + TagAutocomplete

**engine/api.py — GET /tags endpoint:**
- Queries `note_tags` junction table for all distinct tags
- Fallback inside the same `with get_connection()` block: reads JSON `tags` column if `note_tags` is empty
- Returns `{"tags": [...]}` sorted alphabetically

**frontend/src/components/TagAutocomplete.tsx (new):**
- Props: `value`, `onChange`, `onSelect`, `onBlur`, `placeholder`
- Fetches `/tags` once on first focus/keystroke via ref flag (no repeat fetches)
- Filters client-side by prefix match on each keystroke
- Dropdown: `max-h-[160px]` scrollable, `bg-accent text-accent-foreground` highlight
- Keyboard: ArrowDown/Up navigate, Enter selects highlight or submits typed value, Escape closes
- Click-outside: `mousedown` listener on document closes dropdown

**frontend/src/components/NoteViewer.tsx:**
- Replaced plain `<input>` in `addingTag` section with `<TagAutocomplete>`
- `saveTagsFieldLevel` now calls `toast.success('Tags saved')` on success, `toast.error(...)` on failure

### Task 2: Interactive ActionItemList on IntelligencePage + toast retrofix

**IntelligencePage.tsx:**
- Added `actions: ActionItem[]` and `people: Note[]` state
- `loadActions()` fetches `/actions`, handles both `data.items` and `data.actions` response keys
- `loadPeople()` fetches `/people`
- `toggleDone` calls PUT `/actions/:id` with `done` toggle + `toast.success` feedback
- `assignTo` calls PUT `/actions/:id` with `assignee_path`
- New "Action Items" section renders `<ActionItemList actions={actions.filter(a => !a.done)} ...>`

**Toast retrofix (Plan 01 surfaces):**
- **RightPanel.tsx**: `toggleDone` and `assignTo` wrapped in try/catch with `toast.success`/`toast.error`
- **PeoplePage.tsx**: `toggleDone` wrapped in try/catch with `toast.success`/`toast.error`
- **NoteViewer.tsx**: Already handled in Task 1 (tag save toast)

**InboxPage.tsx:** No changes needed — Section component already renders `{title} ({count})` satisfying the count badge requirement. Unassigned actions already render as interactive cards with Select/Dismiss.

## Verification

- `npx tsc --noEmit`: zero errors (verified)
- `grep "ActionItemList" IntelligencePage.tsx`: present
- `grep "TagAutocomplete" NoteViewer.tsx`: present
- `grep "list_tags" engine/api.py`: present
- `grep "toast" IntelligencePage.tsx`: present
- `grep "toast" PeoplePage.tsx`: present
- `grep "toast" RightPanel.tsx`: present

## Deviations from Plan

### Minor deviations (auto-resolved)

**1. [Rule 2 - Missing functionality] TagAutocomplete plain-Enter fallback**
- **Found during:** Task 1 implementation
- **Issue:** Plan said "Enter: if dropdown open and highlightIndex >= 0, call onSelect(...); otherwise let event propagate". Propagating Enter in a div with no parent handler would silently drop the input.
- **Fix:** When no dropdown item highlighted but value is non-empty, `onSelect(value.trim())` is called directly. Single `onSelect` callback handles both cases. Added `onBlur` prop for Escape key dismiss.
- **Files modified:** TagAutocomplete.tsx, NoteViewer.tsx

**2. [Rule 1 - Observation] InboxPage count badges already present**
- The plan action said "Add count badges next to section headers". The Section component already renders `{title} ({count})` — requirement satisfied without modification. Noted and skipped.

## Known Stubs

None — all wired data sources, no hardcoded empty values in rendered output.

## Self-Check: PASSED
