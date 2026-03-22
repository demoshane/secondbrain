# Phase 34: GUI Management Productivity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-22
**Phase:** 34-gui-management-productivity
**Areas discussed:** Action Items, Cmd+K Palette, Entity Create/Delete, Tag Autocomplete

---

## Action Items

| Option | Description | Selected |
|--------|-------------|----------|
| NoteViewer + IntelligencePage only | Inline checkboxes in open note and recap panel | |
| All note-context surfaces | NoteViewer, IntelligencePage, RightPanel, Meetings detail, People detail | |
| Shared ActionItemList component, embedded everywhere | Build once, drop into all relevant contexts | ✓ |

**User's choice:** Option 3 — shared component
**Notes:** Build reusable component with toggle/assignee, consistent behaviour across the app.

### Source Note Link (GUI-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Clickable note title | Show source note title as link in action row | |
| Icon button | Small "open note" icon, shown conditionally when note_path exists | ✓ |
| Column only if note exists | Hide column when no source | |

**User's choice:** Option 2 — icon button, shown conditionally
**Notes:** Less visual noise; only renders when action item has a source note.

---

## Cmd+K Palette

| Option | Description | Selected |
|--------|-------------|----------|
| Navigation only | Jump to note by title, switch pages | |
| Navigation + capture | Navigation + quick-capture + SmartCaptureModal trigger | ✓ |
| Full command set | Navigation, capture, plus in-app actions | |

**User's choice:** Option 2 — navigation + capture
**Notes:** Add cmdk library.

### Keyboard Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Cmd+K only | Mac-native | |
| Both Cmd+K and Ctrl+K | Cross-platform | ✓ |

**User's choice:** Both bindings
**Notes:** pywebview is desktop, both bindings needed.

---

## Entity Create/Delete

### Create

| Option | Description | Selected |
|--------|-------------|----------|
| Modal dialog | NewNoteModal pattern, consistent | ✓ |
| Inline form | Row appears at top of list | |
| Reuse SmartCaptureModal | Pre-set to people type | |

**User's choice:** Option 1 — modal dialog

### Delete

| Option | Description | Selected |
|--------|-------------|----------|
| Same as DeleteNoteModal | Simple confirmation | |
| Cascade warning | Show linked meetings/action items before confirming | ✓ |
| Claude's discretion | Follow DeleteNoteModal pattern | |

**User's choice:** Option 2 — cascade warning
**Notes:** Query note_people and action_items to count linked items, show before confirming.

---

## Tag Autocomplete

| Option | Description | Selected |
|--------|-------------|----------|
| Dropdown suggestions while typing | Filter existing tags as user types | ✓ |
| Show all tags on focus | Tag picker, filter as you type | |
| Claude's discretion | Dropdown is obvious choice | |

**User's choice:** Option 1 — dropdown suggestions while typing
**Notes:** Pulls from note_tags junction table (Phase 32). Keyboard-navigable.

---

## Claude's Discretion

- Toast library choice
- Exact fields in entity create modals beyond name
- Inbox-specific improvements
- Tag autocomplete positioning and max suggestions

## Deferred Ideas

None raised during discussion.
