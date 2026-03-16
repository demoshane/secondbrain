---
phase: 23-navigation-polish
plan: "02"
subsystem: gui-sidebar
tags: [sidebar, navigation, hierarchy, collapse, localStorage, css]
dependency_graph:
  requires: ["23-01"]
  provides: ["renderHierarchySidebar", "renderFlatList", "folderName", "getCollapseState", "setCollapseState"]
  affects: ["engine/gui/static/app.js", "engine/gui/static/style.css"]
tech_stack:
  added: []
  patterns: ["localStorage collapse state", "folder > type 2-level hierarchy", "independent section collapse/expand"]
key_files:
  created: []
  modified:
    - engine/gui/static/app.js
    - engine/gui/static/style.css
decisions:
  - "folder-section.collapsed > ul CSS selector hides all child ul elements for both folder and type sections"
  - "Recent section uses green left-border accent to distinguish from regular folder sections"
  - "folderName() uses parts[-2] — works for typical /brain/folder/file.md paths; falls back to 'other'"
metrics:
  duration: 5 min
  completed: "2026-03-16"
  tasks_completed: 2
  files_modified: 2
requirements:
  - GNAV-01
---

# Phase 23 Plan 02: Hierarchy Sidebar with Collapse State Summary

Replaced the flat type-grouped sidebar with a two-level folder > type hierarchy featuring persistent collapse/expand state via localStorage. Search results continue to use the original flat list path.

## What Was Built

### Task 1: app.js — hierarchy sidebar + collapse state
- `getCollapseState()` / `setCollapseState(key, collapsed)` — localStorage helpers with try/catch for private-mode safety, key `sb-sidebar-collapse`
- `folderName(notePath)` — extracts the top-level folder from an absolute note path using `parts[-2]`
- `renderFlatList(notes)` — identical to the original `renderSidebar()` behavior (type-grouped flat list); used by `runSearch()` and future tag-filter mode
- `renderHierarchySidebar(notes)` — new 2-level hierarchy:
  - "Recent" section at top showing first 10 notes (server returns created_at DESC), collapsible, green left-accent
  - Per-folder sections showing `folderName/ (total_count)`, each independently collapsible
  - Per-type sub-sections within each folder showing `typeName (count)`, independently collapsible
  - Collapse state restored from localStorage on every render; toggle updates DOM and localStorage
- `loadNotes()` now calls `renderHierarchySidebar()` (was `renderSidebar()`)
- `runSearch()` now calls `renderFlatList()` (was `renderSidebar()`)

### Task 2: style.css — folder/type headers and collapse toggles
- `.folder-header` — clickable section header, `font-weight: 600`, 3px left border accent (blue `#2c6fcf`), `cursor: pointer`, `user-select: none`
- `.type-header` — indented sub-section header (`padding-left: 24px`), lighter weight, same pointer/select rules
- `.collapse-toggle` — 9px inline span for ▼/▶ indicator
- `.folder-section.collapsed > ul, .type-section.collapsed > ul { display: none }` — hides collapsed content
- `.section-count` — muted color (`#aaa`), `font-size: 0.8em` for count badges
- `.folder-section.recent-section > .folder-header` — green left-border variant for Recent section

## Verification

Test suite: 259 passed, 1 skipped, 1 xfailed (pre-existing unrelated failures in test_intelligence.py and test_precommit.py excluded — confirmed pre-existing before this plan).

Manual: Sidebar shows "Recent" at top then folder sections; click folder header collapses it; click type header collapses independently; reload restores state. Search returns flat list.

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | cac36df | feat(23-02): hierarchy sidebar with collapse state |
| 2 | 6527651 | feat(23-02): style folder/type headers and collapse toggles |

## Self-Check: PASSED
