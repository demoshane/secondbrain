# Phase 34: GUI Management Productivity - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade the GUI from read-heavy to genuinely productive: interactive action items embedded in all note-context surfaces via a shared component, Cmd+K command palette for navigation and capture, entity create/delete directly from People/Meetings/Projects pages, tag autocomplete in NoteViewer, and polish (toasts, Inbox improvements). The `sb_create_person` MCP tool ships alongside the GUI create flow.

</domain>

<decisions>
## Implementation Decisions

### Action Items (GUI-01, GUI-02)
- **D-01:** Build a shared `ActionItemList` component (toggle done, assignee picker) — embed it in NoteViewer, IntelligencePage, RightPanel, and any other note-context surface. Do not duplicate per-page implementations.
- **D-02:** Source note link on ActionsPage: icon button (e.g. `ExternalLink` from lucide-react), shown conditionally only when `note_path` is present on the action item. Clicking opens the note in NoteViewer.
- **D-03:** "Link persons to notes in sidebar" todo folded into scope — person links in note context covered by the shared ActionItemList + NoteViewer integration.

### Cmd+K Palette (GUI-03)
- **D-04:** Add `cmdk` library. Scope: navigation commands (jump to note by title, switch between pages) + capture commands (quick-capture, trigger SmartCaptureModal).
- **D-05:** Trigger: both `Cmd+K` (Mac) and `Ctrl+K` (cross-platform) — pywebview runs on desktop, both bindings required.

### Entity Create/Delete (GUI-04, GUI-07)
- **D-06:** Create: modal dialog pattern, consistent with existing `NewNoteModal`. Required field: name. Optional: role/title for people. People page, Meetings page, Projects page all get a "New [entity]" button.
- **D-07:** Delete: cascade warning dialog — before confirming deletion of a person/project, show what is linked (meeting notes that mention them, action items assigned to them). User confirms with full awareness. Follows `DeleteNoteModal` structure but adds a "linked data" section.
- **D-08:** `sb_create_person` MCP tool ships alongside the GUI create flow, using the same backend endpoint.

### Tag Autocomplete (GUI-06)
- **D-09:** Dropdown suggestions while typing in the tag input in NoteViewer. Pulls existing tags from `note_tags` junction table (Phase 32). Keyboard-navigable (arrow keys + Enter). Dismiss on Escape or click-outside.

### Intelligence Actionable Items (GUI-05)
- **D-10:** Intelligence page action items rendered via the shared `ActionItemList` component — interactive (toggle, assignee) in-place, not read-only text.

### Toasts + Inbox Polish (GUI-05, GUI-06)
- **D-11:** Toast feedback on mutations: action item toggle, entity create/delete, tag save. Claude's discretion on toast library (shadcn/ui `sonner` or similar that fits the Radix/Tailwind stack).
- **D-12:** Inbox polish: Claude's discretion on specific improvements — focus on making the review queue more actionable.

### Claude's Discretion
- Toast library choice (sonner vs Radix Toast vs other — must fit existing shadcn/ui stack)
- Exact fields in entity create modals beyond the required name field
- Inbox-specific UI improvements
- Tag autocomplete positioning (above/below input) and max visible suggestions count

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontend architecture
- `frontend/src/components/ActionsPage.tsx` — existing action item toggle + assignee patterns to replicate in shared component
- `frontend/src/components/NoteViewer.tsx` — existing tag editing pattern (double-click inline), integration point for ActionItemList and tag autocomplete
- `frontend/src/components/IntelligencePage.tsx` — integration point for ActionItemList
- `frontend/src/components/PeoplePage.tsx` — integration point for entity create/delete
- `frontend/src/components/NewNoteModal.tsx` — modal creation pattern to follow for entity create modals
- `frontend/src/components/DeleteNoteModal.tsx` — delete confirmation pattern to extend with cascade warning

### Backend
- `engine/api.py` — existing `/actions`, `/people`, `/notes` endpoints; add entity create/delete and tag suggestions endpoints here
- `engine/mcp_server.py` — add `sb_create_person` MCP tool here
- `engine/people.py` — `list_people_with_metrics()` shared service (Phase 32)
- `engine/db.py` — `note_tags` junction table (Phase 32) for tag autocomplete query

### Dependencies
- `frontend/package.json` — current deps; `cmdk` must be added for palette

### Phase context
- `.planning/phases/32-architecture-hardening/32-CONTEXT.md` — note_tags junction table, note_people, cascade patterns
- `.planning/ROADMAP.md` — Phase 34 requirements GUI-01 through GUI-07

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/ui/checkbox.tsx` — Radix Checkbox, already used in ActionsPage for done toggle
- `frontend/src/components/ui/dialog.tsx` — Radix Dialog, already used — use for entity create/delete modals
- `frontend/src/components/ui/input.tsx` — use for tag autocomplete input and entity name fields
- `frontend/src/components/ui/button.tsx` — for "New Person/Project" buttons
- `lucide-react` — already installed, use `ExternalLink` for source note icon, `Plus` for create buttons

### Established Patterns
- Modal dialogs: `NewNoteModal` + `DeleteNoteModal` define the create/delete modal contract — follow exactly
- Inline tag editing: double-click to activate input in NoteViewer — tag autocomplete extends this with a dropdown
- Action item toggle: `toggleDone` + `assignTo` in ActionsPage — extract these into the shared `ActionItemList` component
- API fetch pattern: `fetch(getAPI() + '/endpoint')` with JSON body — consistent across all components

### Integration Points
- `NoteViewer.tsx` — embed `ActionItemList` below the note body; replace plain tag input with autocomplete-enabled input
- `IntelligencePage.tsx` — replace static action item list with `ActionItemList` component
- `RightPanel.tsx` — embed `ActionItemList` if/when note is selected
- `PeoplePage.tsx`, `MeetingsPage.tsx`, `ProjectsPage.tsx` — add "New [entity]" button + delete button per row
- `engine/api.py` — new endpoint `GET /tags` (all unique tags from note_tags) for autocomplete; new endpoints for entity create/delete

</code_context>

<specifics>
## Specific Ideas

- `cmdk` is the standard React command palette library (used by shadcn/ui docs, Vercel, Linear) — fits the existing Radix/shadcn stack well
- Cascade warning on person delete: query `note_people` and `action_items` tables to count linked items before showing the dialog
- Tag autocomplete: fetch `/tags` on first keystroke (debounced), filter client-side for subsequent characters

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

### Reviewed Todos (not folded)
- **Add tests for git hooks** — testing concern, deferred (low relevance to GUI work)
- **Fix sb_edit wiping YAML frontmatter** — MCP bug, separate phase or hotfix
- **Fix sb-recap returning nothing despite existing entries** — intelligence bug, separate phase or hotfix

</deferred>

---

*Phase: 34-gui-management-productivity*
*Context gathered: 2026-03-22*
