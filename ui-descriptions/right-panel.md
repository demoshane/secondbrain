# Right Panel

## Intent
Contextual metadata for the currently open note — who it's linked to, what links back to it, and what actions it generated. Provides graph context without leaving the note. Visible only in Notes view.

## Appearance
Fixed width (256px / `w-64`). Right edge of the three-column notes layout. Hidden on all non-Notes tabs.

## Components

- **Backlinks section** — list of notes that link to the current note. Each is a clickable text link that opens the note in the viewer. Section heading: "BACKLINKS". Hidden when empty.
- **Persons section** — badge list of people associated with the current note (from the note's `people:` frontmatter field). Each badge is clickable and opens the person's profile note. Section heading: "PERSONS". Hidden when empty.
- **Action Items section** — list of action items belonging to the current note. Uses ActionItemList (same component as Actions page and Intelligence page). Includes checkbox toggle, assignee picker, and due date. Section heading: "ACTION ITEMS". Hidden when empty.

## Behavior
- Data is fetched from `/notes/:path/meta` whenever `currentPath` changes.
- Action item changes (toggle done, assign, due date) are saved immediately via PUT to `/actions/:id`.

## Known issues
- When all three sections are empty (new or orphaned note), the panel is completely blank with no empty state message.
- No way to add a backlink or relationship from this panel — read-only view of existing links.
- Persons section label says "PERSONS" but the People tab uses "People" — inconsistent terminology.
- No visual separator between sections; sections blend together when all are populated.
- Panel is not collapsible — always takes 256px even when empty.
