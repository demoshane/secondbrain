# Phase 23: Navigation Polish - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Sidebar navigation by folder/type hierarchy with collapse/expand, inline tag editing from the note viewer, and tag-based filtering. Creating/capturing notes is out of scope.

</domain>

<decisions>
## Implementation Decisions

### Sidebar grouping model
- **Hybrid hierarchy: folder first, then note type inside** (e.g. `projects/ → note (3), idea (2)`)
- Top level = brain folder (people/, meetings/, projects/, etc.)
- Second level = note type within that folder
- Count shown per section: `people/ (8)`, `person (8)`
- **"Recent" section at top** — flat list of most-recently-modified notes, collapsible like other sections
- Both levels (folder and type-within-folder) are independently collapsible

### Collapse/expand behaviour
- **Start state: restore from localStorage** — whatever the user left it as
- If no saved state (first visit): all sections expanded
- Collapse state persisted in localStorage per folder + type key
- Both folder-level and type-level collapse states persisted independently

### Tag chip placement
- Tags displayed **below the note title** in the viewer, before the body
- Layout: `#idea  #work  #urgent  [+ Add tag]`

### Tag editing interaction
- Click a tag chip → chip transforms into an **inline text input** in-place
- Press Enter to save, Escape to cancel
- `[+ Add tag]` button at end of chips — click to open a new inline input
- **Silent save**: optimistic update, chip snaps back immediately; red flash on failure
- No "Saved" toast
- Save updates both frontmatter file AND database — no full reindex required (targeted UPDATE)

### Tag filter UX
- Activated by **clicking any tag chip in the note viewer** — no separate filter UI
- Sidebar switches to **flat filtered list** (same as search results, no grouping) showing all notes with that tag
- **Filter banner** shown above note list: `🏷️ Filtering: #work  ×` — click × to clear
- Tag filter + text search: **AND logic** — both must match
- When filter is active, text search narrows within the filtered set

### Search results / filtered results display
- Both search results and tag-filtered results use the same **flat list** (no grouping)
- Grouped hierarchy only shown in the default "all notes" browse mode

### Claude's Discretion
- Exact CSS styling for chips (colors, font size, border-radius)
- Transition/animation for chip-to-input transform
- How to handle very long folder names in sidebar
- Exact localStorage key schema for collapse state

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `renderSidebar(notes)` in `app.js`: already groups by type — extend to support folder > type hierarchy
- `#new-note-modal` + `#delete-note-modal`: proven modal/overlay pattern for any future overlays
- `.type-group-header` CSS class: reuse/extend for folder headers and type-within-folder headers
- `runSearch(query)` in `app.js`: reuse the flat result rendering for tag-filtered results
- SSE `connectSSE()`: tag edits fire a `modified` SSE event → sidebar auto-refreshes

### Established Patterns
- Fetch/optimistic update: established in delete flow (`suppress_next_delete`, optimistic sidebar removal)
- Path security: `_resolve_note_path()` in `api.py` — all note paths validated against BRAIN_PATH
- Tags stored as JSON array in `notes.tags` column — already exists, no migration needed
- `engine/api.py:PUT /notes/<path>`: existing save endpoint — extend to accept `tags` update
- `marked.min.js` vendored offline (no CDN) — same for any new JS

### Integration Points
- `api.py`: add `tags` field to PUT `/notes/<path>` endpoint (currently only saves body/title)
- `api.py:POST /search`: add optional `tags` parameter for AND-filtering
- `app.js:renderSidebar()`: refactor to support 2-level hierarchy (folder > type)
- `index.html`: add tag chip row below note title, add filter banner slot above note list
- `style.css`: add `.tag-chip`, `.tag-chip-input`, `.filter-banner` classes

</code_context>

<specifics>
## Specific Ideas

- Sidebar hierarchy mirrors the visual from discussion: `▼ projects/ → ▼ note (3) → • MVP plan`
- Tag filter banner mirrors the mockup: `🏷️ Filtering: #work  ×`
- Chip-to-input transform mockup: `[idea        ✕]  #work  #urgent`
- "Recent" is a named flat section at the very top — same collapsible behaviour as folders

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 23-navigation-polish*
*Context gathered: 2026-03-16*
