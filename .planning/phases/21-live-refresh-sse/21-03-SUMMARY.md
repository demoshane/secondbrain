---
phase: 21-live-refresh-sse
plan: "03"
subsystem: frontend
tags: [sse, live-refresh, frontend, javascript, gui]
dependency_graph:
  requires: [21-02]
  provides: [SSE client connection, status dot, conflict banner, isDirty tracking]
  affects: [engine/gui/static/app.js, engine/gui/static/index.html, engine/gui/static/style.css]
tech_stack:
  added: []
  patterns: [EventSource API, dirty-state tracking, SSE event listener pattern]
key_files:
  created: []
  modified:
    - engine/gui/static/app.js
    - engine/gui/static/index.html
    - engine/gui/static/style.css
decisions:
  - "connectSSE() called at init after loadNotes() — no separate init ordering required"
  - "matchesCurrent uses endsWith('/' + path) because currentPath is absolute and SSE path is relative"
  - "_sseWasConnected flag gates the full loadNotes() refresh on reconnect to avoid spurious reloads on first connect"
metrics:
  duration: 5 min
  completed: 2026-03-16
  tasks_completed: 1
  files_changed: 3
---

# Phase 21 Plan 03: SSE Frontend Wiring Summary

SSE client in app.js: EventSource connects to /events, status dot toggles green/grey, conflict banner on external-edit-while-dirty, isDirty tracking via EasyMDE change event.

## What Was Built

Three frontend files modified to make the GUI react to server-sent events from the `/events` endpoint (implemented in Plan 02):

**engine/gui/static/app.js:**
- `isDirty` flag — set `true` on EasyMDE `change` event, reset to `false` on `enterEditMode` and on successful save
- `updateStatusDot(connected)` — toggles `sse-connected`/`sse-disconnected` CSS classes on `#sse-status`
- `showConflictBanner(path)` — injects a yellow warning banner above `#viewer` with Keep/Load buttons when an external edit arrives while `isDirty` is true
- `handleNoteEvent({ type, path })` — always calls `loadNotes()` for sidebar refresh; for the currently open note, handles `deleted` (clears viewer), `modified`/`created` (silent reload or conflict banner based on `isDirty`)
- `connectSSE()` — opens `new EventSource(`${API}/events`)`; on `open` fires `updateStatusDot(true)` and a full `loadNotes()` refresh if reconnecting; on `error` fires `updateStatusDot(false)`; listens for named `note` events
- `connectSSE()` called at bottom of init block after existing `loadNotes()` / `loadActions()` / `loadIntelligence()` calls

**engine/gui/static/index.html:**
- Added `<span id="sse-status" class="sse-dot sse-disconnected" title="Live refresh">` to the topbar

**engine/gui/static/style.css:**
- Added `.sse-dot`, `.sse-dot.sse-connected`, `.sse-dot.sse-disconnected` rules at end of file

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `engine/gui/static/app.js` — exists and contains `connectSSE`, `handleNoteEvent`, `showConflictBanner`, `updateStatusDot`, `isDirty`
- `engine/gui/static/index.html` — contains `id="sse-status"`
- `engine/gui/static/style.css` — contains `.sse-dot`
- Commit `73ba8f9` — present
