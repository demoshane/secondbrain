# People Page

## Intent
Directory of all people in the brain. Each person has a profile note with backlinks to every note that mentions them. Primary use: look up a person and see all context — meetings, notes, action items — connected to them.

## Layout
Two-column split: person list (left, fixed width table) + person detail panel (right, flex).

## Components

### Left column — Person list
- **Search input** — filters list by name as you type.
- **Person table** — columns: Name · Notes (backlink count) · Actions (open action count). Each row is clickable, highlights the selected person.

### Right column — Person detail
Empty state: "Select a person to view details."

When selected:
- **Person name heading** + action buttons: "Open in Notes" (navigates to Notes view with person note open), "Delete" (red, opens DeleteEntityModal).
- **Profile note body** — rendered markdown of the person's profile note.
- **Meetings section** — collapsible list of meetings this person participated in. Each meeting title is clickable (opens meeting in Notes view).
- **Notes section** — collapsible list of notes that mention this person (backlinks). Each note title is clickable (opens in Notes view).
- **Action Items section** — collapsible list of open actions assigned to this person.

## Known issues
- No way to create a new person directly from this page's list (only via NewNoteModal with type=person or via note capture).
- The `+` button for adding a person to a note (in NoteViewer) has no label.
- Terminology inconsistency: tab says "People", internal headings say "Persons", command palette says "Persons".
- No avatar or visual identifier — all people look identical in the list.
- Delete button is visible immediately (not hover-reveal) which is risky for a destructive action.
