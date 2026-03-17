---
phase: 27-search-quality-tuning
plan: "04"
subsystem: ui
tags: [flask, javascript, sqlite, people, sidebar, meta-api]

requires:
  - phase: 27-01
    provides: "BM25 search tuning and test fixtures baseline"

provides:
  - "GET /notes/<path>/meta now returns people array from notes.people column"
  - "Sidebar People section with clickable person chips in note viewer"
  - "Chip click navigates to matching people-type note when found"

affects: [27-05, people-page, sidebar-features]

tech-stack:
  added: []
  patterns:
    - "Meta endpoint extended by querying additional notes columns alongside existing backlinks/related"
    - "person-chip click handler uses _allNotes cache to resolve name -> path navigation"

key-files:
  created: []
  modified:
    - engine/api.py
    - engine/gui/static/app.js
    - engine/gui/static/index.html
    - engine/gui/static/style.css

key-decisions:
  - "people column stores JSON array string; json.loads() with [] fallback handles NULL/empty"
  - "Chip click uses _allNotes cache with type='people' + title.toLowerCase() match — no extra API call"
  - "people-section placed inside #meta-panel as sibling of backlinks/related — consistent sidebar structure"

patterns-established:
  - "Meta endpoint: add new sidebar data by querying notes table columns and appending to jsonify() response"
  - "Chip navigation: find note by type + lowercased title in _allNotes cache, then openNote(match.path)"

requirements-completed:
  - ENGL-02

duration: 8min
completed: 2026-03-17
---

# Phase 27 Plan 04: Person Chips Sidebar Summary

**People frontmatter field exposed via /meta API and rendered as clickable sidebar chips that navigate to the matching person note**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-17T18:00:00Z
- **Completed:** 2026-03-17T18:08:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Extended `GET /notes/<path>/meta` to return a `people` array by reading the `people` column from SQLite
- Added `#people-section` / `#people-list` to the right-panel sidebar in `index.html`
- Updated `loadMeta()` in `app.js` to populate people chips and wire click-to-navigate behaviour
- Added `.person-chip` CSS styles to `style.css`

## Task Commits

1. **Task 1: Extend GET /notes/<path>/meta to include people array** - `b38d1a2` (feat)
2. **Task 2: Render person chips in sidebar via loadMeta()** - `bd4ff38` (feat)

## Files Created/Modified

- `engine/api.py` - `note_meta()` handler queries `people` column and includes it in JSON response
- `engine/gui/static/app.js` - `loadMeta()` destructures `people`, renders `.person-chip` list items with click handlers
- `engine/gui/static/index.html` - Added `#people-section` with `#people-list` inside `#meta-panel`
- `engine/gui/static/style.css` - Added `.person-chip` and `.person-chip:hover` styles

## Decisions Made

- `json.loads()` with `[] ` fallback handles both NULL and empty-string `people` column values
- Chip navigation uses `_allNotes` module-level cache (type `'people'`, title case-insensitive match) — no extra API round-trip needed
- `#people-section` placed after Related inside `#meta-panel` — consistent with existing backlinks/related structure

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

- Sidebar now shows people chips for notes with `people` frontmatter
- Full People Page (Phase 27.4 per plan context) can build on this foundation
- "Link persons to notes in sidebar" TODO resolved

---
*Phase: 27-search-quality-tuning*
*Completed: 2026-03-17*

## Self-Check: PASSED

- engine/api.py: FOUND
- engine/gui/static/app.js: FOUND
- engine/gui/static/index.html: FOUND
- engine/gui/static/style.css: FOUND
- Commit b38d1a2: FOUND
- Commit bd4ff38: FOUND
