# Phase 41: Visual Redesign — Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the complete Visily UI redesign across the entire React frontend — new design system tokens, component library overhaul, app shell, command palette, and all 8 page redesigns (Notes, Actions, People, Meetings, Projects, Intelligence, Inbox, Links) to match the approved mockups in `ui-design-files/` and specifications in `ui-descriptions/`.

**This is pure frontend work.** All backend API endpoints required by the designs were completed in Phase 40.

**One Phase 40 deferred item lands here:** `POST /projects/<path>/meetings` write endpoint (link a meeting to a project from the UI).

</domain>

<decisions>
## Implementation Decisions

### Migration Approach
- **Rewrite page components to match Visily** — do NOT surgically restyle existing components.
- All 20 existing page components in `frontend/src/components/` should be rebuilt fresh to match the Visily designs.
- Reason: layout differences between current implementation and Visily designs are significant enough that restyling would produce frankenstein code.
- Existing API call logic and hook patterns may be referenced but components themselves should be rebuilt.

### Dark Mode
- **Always dark — no toggle, no light mode path.**
- Remove all `.dark` class conditionals. The app is dark-only.
- Simplify `index.css`: only the dark palette CSS vars needed; delete the `:root` light mode block.
- No theme toggle in Phase 41 or any subsequent phase unless explicitly added as a new requirement.

### Design Token Strategy
- **Fully replace the shadcn HSL CSS vars with the Visily palette.**
- Read the Visily mockups in `ui-design-files/*.png` and `ui-descriptions/UI-DESIGN-BRIEF.md` to extract the exact color palette.
- Remap all `--background`, `--foreground`, `--primary`, `--secondary`, `--muted`, `--accent`, `--border`, `--input`, `--ring` CSS vars to Visily colors.
- Keep the shadcn CSS variable architecture (other shadcn components depend on the variable names); just replace the values.
- shadcn/ui components already installed: badge, button, checkbox, dialog, input, scroll-area, select, table — restyle these via CSS vars, no need to reinstall.

### Sidebar Restructure
- **Drop folder-level grouping; group by note type only.**
- Current: Folder header (e.g. "NOTE") → Type sub-header → note rows (2-level nesting)
- New: Type header (e.g. "Meetings", "People", "Ideas") → note rows (1-level nesting)
- This frees horizontal space for note titles, reducing truncation.
- Keep collapsible sections per type, with chevron + note count badge.
- Tag filter banner and search result mode remain as-is (already working correctly).
- Width: 256px as per design brief. No drag-to-resize handle (not in scope).

### Topbar
- Add labels to Smart Capture ("Smart Capture" text + sparkles icon) and Batch Capture ("Batch" + icon) buttons.
- Hide search mode selector (Hybrid/BM25/Semantic) behind an advanced options toggle — it's expert-only noise.
- Center search input remains as-is functionally.

### TabBar
- Add icons to all 8 tabs (lucide-react is already installed, use appropriate icons).
- Active tab: distinct highlight as per Visily design.

### Project Meetings Write Endpoint (deferred from Phase 40)
- Implement `POST /projects/<path>/meetings` — allows linking a meeting to a project from the Projects detail panel.
- Response: updated project with `linked_meetings` array.
- Broadcast `notes_changed` SSE event on success.
- This is a backend addition that Phase 41's Projects page redesign will consume.

### Claude's Discretion
- Choice of specific Tailwind color values within the Visily palette — extract from mockups.
- Specific lucide-react icon choice per tab (match semantic intent, not pixel-matched to Visily icon set).
- Sidebar type grouping order — order by frequency of use (Meetings, People, Ideas, Projects, Notes, etc.).
- Whether to use CSS `resize` property or a custom drag handler for sidebar (if resize is added later).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design specifications (primary source of truth)
- `ui-descriptions/UI-DESIGN-BRIEF.md` — full design brief, all screens
- `ui-descriptions/app-shell.md` — topbar, tabbar layout and intent
- `ui-descriptions/sidebar.md` — sidebar behavior and known issues
- `ui-descriptions/notes-view.md` — NoteViewer, NoteEditor, three-column layout
- `ui-descriptions/right-panel.md` — right panel content and behavior
- `ui-descriptions/actions-page.md` — Actions page spec
- `ui-descriptions/people-page.md` — People page spec
- `ui-descriptions/meetings-page.md` — Meetings page spec
- `ui-descriptions/projects-page.md` — Projects page spec
- `ui-descriptions/intelligence-page.md` — Intelligence page spec
- `ui-descriptions/inbox-page.md` — Inbox page spec
- `ui-descriptions/links-page.md` — Links page spec
- `ui-descriptions/command-palette.md` — Command palette spec
- `ui-descriptions/modals.md` — Modal specs (NewNote, SmartCapture, Batch, etc.)
- `ui-design-files/*.png` — Visily mockup images (primary visual reference for color/layout)

### Existing frontend
- `frontend/src/index.css` — current CSS vars (to be replaced with Visily palette)
- `frontend/src/components/` — all 20 existing page components (to be rewritten)
- `frontend/src/components/ui/` — shadcn/ui base components (badge, button, checkbox, dialog, input, scroll-area, select, table) — keep these, restyle via CSS vars
- `frontend/tailwind.config.js` — current Tailwind config
- `frontend/package.json` — installed dependencies (lucide-react, cmdk, sonner already available)

### Backend (for the deferred Phase 40 item)
- `engine/api.py` — add `POST /projects/<path>/meetings` following existing route patterns
- `engine/db.py` — relationships table schema for the meeting link write
- `40-CONTEXT.md` (Phase 40 context, same directory level) — full context on the deferred write endpoint

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- All 8 pages have working components with correct API wiring — extract the data-fetching logic when rewriting
- `frontend/src/hooks/` — custom hooks (useSSE, etc.) — keep these unchanged
- `frontend/src/contexts/` — React contexts — keep these unchanged
- `cmdk` (command palette library) is already installed and wired in `CommandPalette.tsx`
- `sonner` (toasts) already configured in `App.tsx`
- `lucide-react` has all needed icons for tabs

### Design System Starting Point
- Current CSS vars are standard shadcn defaults (light blue/gray palette)
- Dark mode is currently `class`-based (`.dark {}` in CSS) — to be removed; always-dark means `:root {}` is the only block
- Tailwind config already has all shadcn color tokens mapped to CSS vars — just update the var values

### Integration Points
- `App.tsx` — app shell, tab routing, topbar — primary entry point for shell redesign
- `frontend/src/index.css` — CSS var definitions — replace entirely
- Each page component is self-contained with its own data fetching

</code_context>

<specifics>
## Specific Design Notes

- Sidebar type grouping should replace the current folder grouping — the folder level ("NOTE") adds no value when all notes live in typed folders anyway
- The right panel PERSONS section (currently showing person name tabs) is the most complex part of the Notes view — read `ui-descriptions/right-panel.md` carefully before planning that plan
- The Visily mockup images are the ground truth for visual style; the `ui-descriptions/` markdown files describe behavior and intent
- Page redesigns should address the known issues listed in each `ui-descriptions/` file (e.g., unlabelled `+` buttons, missing tooltips, truncation)

</specifics>

<deferred>
## Deferred Ideas

- Sidebar drag-to-resize handle — not in Phase 41 scope. Fixed 256px. User decided that flattening the type grouping hierarchy addresses the space problem more effectively.
- Light mode / theme toggle — always dark only. If a light mode is ever wanted, that is a future phase.
- Responsive layout below 1200px — out of scope (design brief targets desktop 1280px minimum).
- No-note-selected placeholder redesign — Claude's discretion, keep simple.

</deferred>

---

*Phase: 41-visual-redesign*
*Context gathered: 2026-03-28*
