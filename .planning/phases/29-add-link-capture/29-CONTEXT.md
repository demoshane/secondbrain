# Phase 29: Add link capture - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a first-class `link` note type to the second brain: capture URLs via a dedicated MCP tool (`sb_capture_link`) with automatic page metadata enrichment, store in a new `links/` subfolder, and add a dedicated Links page to the GUI sidebar with search, tag filter, and note detail panel.

CLI and smart-capture integration are out of scope for this phase.

</domain>

<decisions>
## Implementation Decisions

### Metadata enrichment
- Auto-fetch page metadata at capture time: `og:title`, `og:description`, HTML `<title>` fallback
- Note title = fetched page title (fallback: URL domain if fetch fails)
- Note body = fetched `og:description` + optional user-provided annotation appended below
- URL stored as a dedicated `url:` field in YAML frontmatter (not just body)
- Fetch is best-effort: if it fails, capture the link anyway with URL as title — never blocks capture

### Capture surfaces
- Phase 29 scope: MCP tool only (`sb_capture_link`)
- Signature: `sb_capture_link(url, tags=[], people=[], notes='')`
  - `notes` is optional user annotation appended to body after fetched description
- Return rich confirmation: fetched title + domain + saved note path
  - e.g., `"Saved: 'React Docs' (react.dev) → links/2026-03-19-react-docs.md"`
- Duplicate URL handling: warn in confirmation but save anyway
  - e.g., `"Already captured this URL as X — saving new copy"`

### Link storage & folder
- New `links/` subfolder in `~/SecondBrain/`
- Note_type = `"link"` (new type; add to `TYPE_TO_DIR` mapping)
- Filename pattern: `YYYY-MM-DD-title-slug.md` — consistent with all other note types
- YAML frontmatter includes `url:` field alongside standard fields

### GUI — Links page
- Dedicated "Links" tab in sidebar (same level as Meetings, People)
- List view per link: title + domain + date + tags + description snippet
- Clicking a link opens right-panel note detail (same pattern as other notes)
- Note detail panel shows a prominent "Visit Link" button that opens the URL in browser
- In-page search bar + tag filter (same pattern as Meetings/Notes pages)

### Claude's Discretion
- HTTP fetch implementation (requests lib, httpx, or urllib — whichever fits Python 3.13 best)
- Fetch timeout value and retry count
- Exact frontmatter field ordering
- How domain is extracted from URL for display (just the hostname)
- Loading/skeleton states in GUI
- Empty state for Links page ("No links saved yet — use sb_capture_link in Claude")

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/capture.py` → `capture_note()`: single write path — add `link` type here
- `engine/mcp_server.py`: existing MCP tools pattern to follow for new `sb_capture_link`
- `frontend/src/components/NewNoteModal.tsx`: `NOTE_TYPES` array — add `'link'` here
- People page (`PeoplePage.tsx` pattern): reference for sidebar tab + list + right-panel layout
- `ActionsPage.tsx`: reference for in-page data fetching pattern (direct `fetch()` to Flask API)

### Established Patterns
- `TYPE_TO_DIR` dict in `capture.py`: maps type → subfolder (add `"link": "links"`)
- All note captures go through `capture_note()` — link capture must too
- Data fetching: direct `fetch()` calls to Flask API port 5001, no React Query
- shadcn/ui + Tailwind for all GUI components
- Note detail: right-panel pattern, same as existing note viewer

### Integration Points
- `engine/db.py`: `init_schema()` — may need migration for `url` field indexing
- `engine/api.py`: new `/api/links` route to list link notes (filtered by type)
- `engine/mcp_server.py`: add `sb_capture_link` tool
- `frontend/src/App.tsx`: add `'links'` to `currentView` union type
- Sidebar nav: add Links entry alongside Meetings, People

</code_context>

<specifics>
## Specific Ideas

- Links page list item: `Title | domain.com | Mar 19 | #tag1 #tag2` + description snippet below
- Note detail "Visit Link" button should be prominent — not buried in the note body
- Smart capture integration (Phase 31's `sb_capture_smart` should detect URL-shaped input and route to link capture) — deferred

</specifics>

<deferred>
## Deferred Ideas

- CLI `sb-capture --type link` — out of scope for Phase 29
- `sb_capture_smart` URL detection — Phase 31's job
- GUI "New Link" button in the Links page header — could be added but depends on GUI complexity budget; Claude's discretion
- Browser extension / share sheet integration — future phase

</deferred>

---

*Phase: 29-add-link-capture*
*Context gathered: 2026-03-19*
