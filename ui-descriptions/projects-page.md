# Projects Page

## Intent
Structured view of all project notes. Mirrors the Meetings page pattern. Surfaces project status (last updated, open action count) at a glance without opening individual notes.

## Layout
Two-column split: project list (left, fixed width table) + project detail panel (right, flex). Identical structure to Meetings page.

## Components

### Left column — Project list
- **Filter input** — filters by title as you type.
- **New Project button** — opens NewEntityModal configured for projects type.
- **Project table** — columns: Title · Updated · Actions (open count) · delete icon (hover-reveal). Row click selects the project.

### Right column — Project detail
Empty state: "Select a project to view details."

When selected:
- **Project title heading** + "Open in Notes" button.
- **Note section** (collapsible) — rendered markdown body.
- **Action Items section** (collapsible) — open actions, display-only checkboxes.
- **Related Notes section** (collapsible) — backlinks from other notes, titles only (not clickable).

## Known issues
- Same structural issues as Meetings page: action items not interactive, related notes not clickable, hover-reveal delete likely broken.
- No project status field (active / paused / completed) — all projects look the same regardless of state.
- No way to link a meeting to a project from the UI.
- "Updated" column shows raw ISO timestamp, not a human-readable relative date.
