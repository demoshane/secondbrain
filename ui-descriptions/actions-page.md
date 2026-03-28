# Actions Page

## Intent
A centralised view of all action items extracted from notes across the entire brain. Lets the user manage their to-do list without going into individual notes — filter by status or assignee, mark items done, assign to people, set due dates, delete.

## Layout
Single-column, full height. Header row with filters, then scrollable action item list below.

## Components

- **Page heading** — "Action Items" h2.
- **Status filter** — dropdown: Open (default) / Done / All. Filters the list by completion state.
- **Assignee filter** — dropdown: All assignees (default) + one entry per person note in the brain. Filters to actions assigned to a specific person.
- **ActionItemList** — shared component rendering the filtered list. Each item shows:
  - Checkbox (toggles done/open)
  - Action text
  - Source note link ("from: [note title]") — clicking opens the source note in the Notes view
  - Assignee picker dropdown
  - Due date picker
  - Delete button (opens confirmation dialog)
- **Delete confirmation dialog** — modal asking "Delete action item? / This cannot be undone." with Keep / Delete buttons.

## Behavior
- List re-fetches on filter change.
- All mutations (toggle, assign, due date, delete) are immediate API calls followed by list reload.
- Clicking a source note link calls `openNote()` + navigates to Notes view.

## Known issues
- No way to create a standalone action item from this page — actions can only be created by adding them to a note body or via the `[ ]` checkbox syntax in markdown.
- No bulk operations (e.g., mark all done, bulk assign).
- No grouping by source note, due date, or assignee.
- Empty state when all actions are done shows nothing — no "all clear" message.
- Status filter defaults to "Open" but the dropdown shows the current value without a label; it's not clear what the dropdown controls without reading the options.
