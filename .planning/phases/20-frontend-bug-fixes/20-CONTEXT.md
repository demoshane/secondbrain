# Phase 20: Frontend Bug Fixes - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix four broken viewer behaviors in the GUI: mouse scroll in the note viewer, markdown rendering (HTML not raw text), title sync after edit, and correct backlinks display. Pure JS/CSS/Python fixes — no new features, no new UI sections.

</domain>

<decisions>
## Implementation Decisions

### Frontmatter display
- Strip YAML frontmatter **in the API** before returning content — server returns body-only
- Viewer shows clean rendered HTML with no frontmatter visible
- Stripping in the API benefits all consumers (GUI, MCP, future CLI)
- The `/notes/<path>` GET endpoint should strip the `---...---` block before returning `content`

### Editor (interim, until Phase 23)
- EasyMDE editor shows **body only** — frontmatter is read-only for now
- Frontmatter fields (tags, type, date) are not editable in Phase 20
- Phase 23 will replace this with proper metadata form fields

### Save + reindex UX
- **Silent save**: Ctrl+S saves, no toast or banner on success
- **Instant sidebar refresh**: After save, update the sidebar title immediately (parse new title from saved content)
- **SQLite updated immediately**: After save, re-index the single note — update `notes` row (title, updated_at) by parsing frontmatter from the saved file. No stale DB state.
- **Save failure**: Inline red error message in the viewer toolbar — stays visible until user retries

### Backlinks accuracy
- Replace the fuzzy filename substring match with **FTS5 content search**: find notes whose body contains the current note's title (case-insensitive)
- Use SQLite FTS5 MATCH or `LIKE '%title%'` (case-insensitive via `LOWER()`) — no schema migration required
- Empty backlinks: show `None` text (keep section visible, consistent structure)
- Case-insensitive matching

### Claude's Discretion
- Exact CSS fix for scroll (overflow constraints vs height fix — whichever is cleaner)
- How to efficiently parse frontmatter in Python for the single-note re-index (yaml.safe_load or regex)
- Exact FTS5 query formulation for backlinks

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/api.py` — `/notes/<path>` GET returns `{"content": raw_file_text}`. Needs frontmatter stripped before returning.
- `engine/api.py` — `save_note` PUT endpoint overwrites file but doesn't update SQLite. Needs post-save re-index.
- `engine/api.py` — `note_meta` `/notes/<path>/meta` returns backlinks via buggy fuzzy query. Replace query.
- `engine/gui/static/app.js` — `renderMarkdown(md)` calls `marked.parse(md)`. Will work correctly once API strips frontmatter.
- `engine/gui/static/style.css` — `#viewer { flex: 1; overflow-y: auto; }` — scroll should work; debug height constraints.
- `engine/init_brain.py` or indexing module — find single-note index function to reuse after save.

### Established Patterns
- `marked.parse()` for rendering (EasyMDE bundles it) — keep using, just ensure frontmatter is stripped first
- SQLite `notes` table has `path`, `title`, `type`, `created_at` columns
- FTS5 table exists (used by `search_notes`) — can query it for backlinks content search

### Integration Points
- API `/notes/<path>` — strip frontmatter here (body-only response)
- API `save_note` — add post-save index update (parse title from saved frontmatter, update notes row)
- API `note_meta` — replace fuzzy backlinks query with FTS5/LIKE content search
- `app.js` sidebar render — after save, update the clicked list item's title text (no full reload needed)

</code_context>

<specifics>
## Specific Ideas

- The API response for `/notes/<path>` should add a `body` field (stripped content) alongside or instead of `content` (raw). Prefer returning `body` so callers know they get clean content.
- For single-note re-index after save: parse `title:` from frontmatter, run `UPDATE notes SET title=?, updated_at=? WHERE path=?`

</specifics>

<deferred>
## Deferred Ideas

- **Smart backlink disambiguation on capture**: When user mentions "Alice" (first name only) during capture, detect ambiguous people names and ask "Did you mean Alice Smith or Alice Jones?" — intelligent capture-time backlink resolution. Phase 24+ or its own phase.
- **Separate metadata form fields (tags, type, date) in editor**: Replace frontmatter YAML editing with proper GUI form. Phase 23 (Navigation Polish) scope.

</deferred>

---

*Phase: 20-frontend-bug-fixes*
*Context gathered: 2026-03-16*
