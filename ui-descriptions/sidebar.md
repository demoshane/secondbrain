# Sidebar

## Intent
Note browser — the left-side list of all notes, grouped by folder and type, visible only in the Notes view. Lets the user navigate their note collection by folder structure or by active search/tag filter.

## Appearance
Fixed width (224px / `w-56`). Hidden on all non-Notes tabs.

## Components

- **Tag filter banner** — appears at top when a tag filter is active. Shows the active tag name and an ✕ clear button. Replaces the normal note list with filtered results.
- **Folder sections** — notes are grouped first by folder (`notes/`, `meetings/`, `person/`, etc.), then by note type within each folder. Each level is a collapsible toggle.
  - Folder header: uppercase label + chevron. Clicking collapses/expands all types within.
  - Type sub-header: indented, lowercase label + chevron. Clicking collapses/expands notes of that type.
  - Note row: note title, truncated. Clicking opens the note in NoteViewer. Active note is highlighted.

## Behavior
- Collapse state is persisted per-session via `useCollapseState` hook.
- When search results are active (from Topbar search), the sidebar shows search results instead of full note list.
- When a tag filter is active (clicked from NoteViewer tag badges), sidebar filters to matching notes only.

## Known issues
- Fixed `w-56` width causes long note titles to be cut off with no tooltip — combined with deep folder nesting, this creates horizontal overflow / side-scroll on some titles.
- No way to resize the sidebar.
- No search/filter within the sidebar itself (separate from the global topbar search).
- Folder grouping is filesystem-derived — there's no way to reorder or rename groups from the UI.
- No count badges on folder/type headers showing how many notes are inside.
