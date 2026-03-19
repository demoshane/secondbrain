---
phase: 29-add-link-capture
plan: "04"
subsystem: frontend
tags: [link-capture, react, ui, links-page, tab-bar]
dependency_graph:
  requires:
    - 29-03  # GET /links + GET /links/<path> Flask endpoints
  provides:
    - LinksPage React component (list + detail panel)
    - Links tab in TabBar
    - 'links' view in UIContext
  affects:
    - frontend/src/contexts/UIContext.tsx
    - frontend/src/components/TabBar.tsx
    - frontend/src/App.tsx
    - frontend/src/components/LinksPage.tsx
tech_stack:
  added: []
  patterns:
    - two-column list+detail panel (MeetingsPage pattern)
    - tag chip filter with active badge display
    - window.open noopener for external URL visit
    - parseTags() helper handles JSON array tags from API
key_files:
  created:
    - frontend/src/components/LinksPage.tsx
  modified:
    - frontend/src/contexts/UIContext.tsx
    - frontend/src/components/TabBar.tsx
    - frontend/src/App.tsx
    - .secrets.baseline
decisions:
  - "[29-04] LinksPage uses pre-wrap rendering for body — avoids marked.js dependency; body is plain text + annotation notes"
  - "[29-04] parseTags() helper wraps JSON.parse with try/catch + Array.isArray guard — tags column is JSON TEXT, may be null or malformed"
  - "[29-04] Visit Link button placed prominently in detail panel header (not buried) — primary action for link notes"
  - "[29-04] Tag chip click in list sets tagFilter (stops propagation to avoid row select) — single-click UX consistent with Inbox pattern"
  - "[29-04] .secrets.baseline updated to include new vite bundle (index-DMTF-UMF.js) — same false-positive pattern as Phase 27.4/27.8"
metrics:
  duration: 6 min
  completed: 2026-03-19
  tasks_completed: 2
  files_modified: 5
---

# Phase 29 Plan 04: Link Capture — Frontend LinksPage Summary

Links tab + LinksPage React component wiring Phase 29's GUI layer: links are now browseable via a two-column list/detail panel with search, tag filtering, and a Visit Link button.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | UIContext + TabBar + App.tsx wiring | 27f81a5 | UIContext.tsx, TabBar.tsx, App.tsx, LinksPage.tsx (stub), .secrets.baseline |
| 2 | LinksPage.tsx full implementation | 3cfb418 | LinksPage.tsx, .secrets.baseline |

## What Was Built

### Task 1 — UIContext + TabBar + App.tsx wiring

- `UIContext.tsx` line 3: added `'links'` to View type union
- `TabBar.tsx`: added `{ id: 'links' as const, label: 'Links' }` to TABS array
- `App.tsx`: imported `LinksPage`, added `: currentView === 'links' ? <LinksPage /> :` branch before final `: null`
- `LinksPage.tsx`: stub `export function LinksPage() { return null; }` created so build resolves the import

### Task 2 — LinksPage.tsx full implementation

Two-column layout (320px list | flex-1 detail) following MeetingsPage pattern:

**Left column (list panel):**
- shadcn `Input` for search (filters title + description)
- Active tag filter shown as dismissible `Badge`
- List items: title (bold), domain (muted), date (right-aligned), description snippet (truncated), tags as clickable `Badge` chips
- Clicking a tag chip: `e.stopPropagation()` then `setTagFilter(tag)` — prevents row selection
- Active row: `bg-muted` highlight
- Empty state: "No links saved yet — use sb_capture_link in Claude" (no filter) or "No links match your filter" (with filter)

**Right column (detail panel):**
- Header: title (h2), domain + date row (muted), **Visit Link** button (default variant, `ExternalLink` icon)
- `window.open(url, '_blank', 'noopener')` — secure external open
- Tags chips row (read-only `Badge` secondary)
- Body: `<pre className="whitespace-pre-wrap">` — plain text rendering
- Placeholder "Select a link to view details" when nothing selected

**Data flow:**
- Mount: `fetch('/links')` → `setLinks(d.links)`
- Select row: `fetch('/links/<enc>')` → `setLinkDetail(d)`
- Both fetches use `getAPI()` base URL for correct port resolution

## Checkpoint Reached

Task 3 is `type="checkpoint:human-verify"` — pending human verification. The full Phase 29 implementation is:

- `engine/link_capture.py` — fetch_link_metadata (Plan 02)
- DB `url` column migration (Plan 02)
- `TYPE_TO_DIR["link"] = "links"` in capture.py (Plan 02)
- `sb_capture_link` MCP tool (Plan 03)
- `GET /links` + `GET /links/<path>` Flask routes (Plan 03)
- `LinksPage` React component (this plan)
- Links tab in tab bar (this plan)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Updated .secrets.baseline for new Vite bundle**
- **Found during:** Task 1 + Task 2 commit
- **Issue:** detect-secrets pre-commit hook blocks commits when new minified JS bundle contains false-positive "Secret Keyword" patterns (same issue as Phase 27.4 and 27.8)
- **Fix:** Scanned new bundle hash with `detect-secrets scan`, added entry to `.secrets.baseline`; ran twice as hook modified baseline on first pass to update line numbers
- **Files modified:** `.secrets.baseline`
- **Commits:** included in 27f81a5 and 3cfb418

## Self-Check: PASSED

- frontend/src/components/LinksPage.tsx: FOUND (full implementation, 165 lines)
- frontend/src/contexts/UIContext.tsx: FOUND ('links' in View type)
- frontend/src/components/TabBar.tsx: FOUND (Links tab in TABS array)
- frontend/src/App.tsx: FOUND (LinksPage import + render branch)
- Commit 27f81a5: FOUND (Task 1)
- Commit 3cfb418: FOUND (Task 2)
- Build: PASSED (no TypeScript errors, built in 2.87s)
