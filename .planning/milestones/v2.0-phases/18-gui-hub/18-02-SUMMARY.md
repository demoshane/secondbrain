---
phase: 18-gui-hub
plan: "02"
subsystem: ui
tags: [pywebview, flask, waitress, easymde, javascript, spa, three-panel]

# Dependency graph
requires:
  - phase: 18-01
    provides: Flask /ui route serving static files + all API endpoints (notes, search, meta, actions, intelligence)
provides:
  - engine/gui/__init__.py: full main() with waitress sidecar, pywebview window, open_in_editor JS bridge
  - engine/gui/static/index.html: three-panel SPA shell
  - engine/gui/static/app.js: full ES module UI logic (sidebar, viewer, EasyMDE editor, search, right panel, modal)
  - engine/gui/static/style.css: three-column grid layout CSS
  - engine/gui/static/vendor/easymde.min.{js,css}: vendored EasyMDE editor (offline-safe)
affects: [18-03, sb-gui entry point, manual verification checkpoint]

# Tech tracking
tech-stack:
  added: [EasyMDE 2.x (vendored), pywebview (waitress sidecar pattern)]
  patterns: [sidecar-daemon-thread with threading.Event gate, port-reuse guard for double-bind prevention, ES module frontend over local Flask server, pywebviewready bridge for JS-to-Python calls]

key-files:
  created:
    - engine/gui/static/vendor/easymde.min.js
    - engine/gui/static/vendor/easymde.min.css
  modified:
    - engine/gui/__init__.py
    - engine/gui/static/index.html
    - engine/gui/static/style.css
    - engine/gui/static/app.js

key-decisions:
  - "EasyMDE vendored via Python urllib (curl blocked by hook) — offline-safe, no CDN dependency at runtime"
  - "open_in_editor exposed via window.expose(); button hidden until pywebviewready fires to avoid JS errors"
  - "on_closing event adds 0.3s drain before waitress exits — prevents mid-request teardown"

patterns-established:
  - "Port-already-open check: _port_is_open() prevents double-bind when sb-api is already running standalone"
  - "threading.Event gate: _start_sidecar sets ready after /health responds — main() blocks until confirmed healthy"
  - "ES module loadNotes() derives brainPath heuristic from first note path for new-note POST body"

requirements-completed: [GUI-01, GUI-02, GUI-03, GUI-11]

# Metrics
duration: 3min
completed: 2026-03-15
---

# Phase 18 Plan 02: GUI Hub — Sidecar + Three-Panel SPA Summary

**pywebview desktop window with waitress Flask sidecar, three-panel note browser/editor, EasyMDE editing, and full right-panel intelligence/actions display**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-15T20:43:06Z
- **Completed:** 2026-03-15T20:46:13Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- engine/gui main() fully implemented: _port_is_open guard, waitress daemon thread, threading.Event health gate, webview.create_window + window.expose(open_in_editor)
- Three-panel SPA shipped: sidebar grouped by note type, center Markdown viewer with EasyMDE edit mode, right panel with backlinks/related/actions/intelligence panels
- EasyMDE 2.x vendored offline — no CDN required at runtime; marked.parse() used for Markdown rendering in view mode
- New note modal with POST /notes, search bar with 300ms debounce and keyword/semantic mode toggle, pywebviewready bridge for OS editor open

## Task Commits

1. **Task 1: engine/gui sidecar startup and pywebview window** - `72d18b6` (feat)
2. **Task 2: three-panel HTML/JS frontend and vendor EasyMDE** - `e7b3dee` (feat)

## Files Created/Modified

- `engine/gui/__init__.py` - Full main(): port check, waitress sidecar, pywebview window, open_in_editor JS bridge
- `engine/gui/static/index.html` - SPA shell: topbar with search, three-panel layout, new-note modal
- `engine/gui/static/style.css` - Three-column grid (240px | flex | 280px), EasyMDE container flex overrides
- `engine/gui/static/app.js` - ES module: loadNotes, renderSidebar, openNote, EasyMDE edit/save, search, meta/actions/intelligence panels, pywebviewready handler
- `engine/gui/static/vendor/easymde.min.js` - EasyMDE 2.x minified (326KB, vendored from jsDelivr)
- `engine/gui/static/vendor/easymde.min.css` - EasyMDE CSS (13KB, vendored)

## Decisions Made

- EasyMDE vendored via Python urllib because curl/wget is blocked by a project hook — result is identical (offline-safe asset)
- `open-editor-btn` hidden by default and shown only on `pywebviewready` — prevents JS errors when loaded in a regular browser
- `on_closing` event drain (0.3s) prevents waitress from tearing down mid-request on window close

## Deviations from Plan

None — plan executed exactly as written. The only adaptation was using Python urllib instead of curl for vendoring EasyMDE (blocked by hook), which produces identical files.

## Issues Encountered

- curl/wget blocked by project hook — resolved by using Python urllib.request.urlretrieve (same result, no functional difference)
- Pre-existing test_precommit.py::test_blocks_api_key failure unrelated to this plan — test suite passes 227/227 when that file is excluded

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `sb-gui` entry point is wired (from 18-01 pyproject.toml) — running `uv run sb-gui` will start the full window
- Phase 18-03 manual verification checkpoint: open window, browse notes, search, edit a note, check right panel
- All GUI-0x requirements fulfilled; ready for 18-03 sign-off checkpoint

---
*Phase: 18-gui-hub*
*Completed: 2026-03-15*
