# Inbox Page

## Intent
Triage queue for things that need processing. Three categories: unassigned action items, unprocessed notes (recently captured but not yet linked or tagged), and empty notes. Goal: get to zero — dismiss everything or process it into the right place. Modelled on GTD inbox concept.

## Layout
Two-column split: triage list (left, fixed 320px) + note preview (right, flex).

## Components

### Left column — Triage list

**Header:** Total count of items needing attention, or "All clear" message with last-checked time.

**Unassigned Actions section** (collapsible):
- Source note filter input (debounced, filters actions by originating note).
- Each action card: action text + source note path + inline assignee dropdown + Dismiss button.
- "Load more" button for pagination (20 at a time).

**Unprocessed Notes section** (collapsible):
- Each note card: title + created date + "Add Backlink" button (expands BacklinkPicker inline) + Dismiss button.
- BacklinkPicker: search input with debounced results, select a note to create a relationship.

**Empty Notes section** (collapsible):
- "Delete all" button (confirms via browser dialog).
- Each note card: title + Delete button + Dismiss button.

### Right column — Note preview
When an item is selected from the left list, the corresponding note is shown in NoteViewer (read-only). Empty state: "Select an item to preview."

## Known issues
- "Dismiss" removes the item from the inbox view but does not take any action — it just flags the item as acknowledged. Not clear to users what dismiss means vs. actually processing.
- Unprocessed notes section has no clear criteria for what makes a note "unprocessed" — users may not understand why a note appears here.
- The backlink picker (inline search) is very small and easy to miss.
- Source note path shown in action cards is a full absolute path — unreadable.
- No keyboard navigation between items.
