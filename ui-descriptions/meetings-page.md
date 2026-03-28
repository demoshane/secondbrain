# Meetings Page

## Intent
Structured view of all meeting notes. Separate from the generic notes browser because meetings have specific metadata (date, participants, open actions) worth surfacing as columns. Lets the user find a meeting by date or participant and review its outcomes without opening the full Notes view.

## Layout
Two-column split: meeting list (left, fixed width table) + meeting detail panel (right, flex).

## Components

### Left column — Meeting list
- **Filter input** — filters list by title as you type.
- **New Meeting button** — opens NewEntityModal configured for meetings type.
- **Meeting table** — columns: Title · People (participant count) · Date · Actions (open action count) · delete icon (hover-reveal). Row click selects the meeting.

### Right column — Meeting detail
Empty state: "Select a meeting to view details."

When selected:
- **Meeting title heading** + "Open in Notes" button (navigates to Notes view).
- **Note section** (collapsible) — rendered markdown body of the meeting note.
- **Participants section** (collapsible) — list of participant names.
- **Action Items section** (collapsible) — open action items from this meeting. Checkbox display only (not interactive here).
- **Backlinks section** (collapsible) — other notes that link to this meeting.

## Known issues
- Action items in the detail panel are display-only (checkboxes are `disabled`). Can't mark them done without going to Actions page or the note.
- Participant names are plain text — not linked to their person profiles.
- Backlink titles in the detail panel are not clickable — can't navigate to the linked note.
- Delete icon only becomes visible on row hover due to CSS, but the CSS class `group-hover:opacity-100` requires a `group` class on the parent row which is missing — delete icon may never appear.
- No sort controls on the table columns.
