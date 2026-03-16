# Phase 21: Live Refresh SSE - Context

**Gathered:** 2026-03-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a Server-Sent Events (SSE) endpoint to the Flask API and a watchdog-based file observer for `~/SecondBrain`. When `.md` files are created, modified, or deleted, the GUI sidebar and viewer update automatically without a page restart. Covers GUIX-01.

New capabilities (file capture, batch capture, intelligence panel triggers) are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Change scope
- Watch `~/SecondBrain` recursively for `.md` file changes only (not `files/` or binary files)
- Trigger on: created, modified, and deleted events
- Watch all changes regardless of origin — CLI captures, `sb-capture`, direct Finder/editor edits all trigger refresh
- Exclude non-`.md` files (`.db`, `.json`, temp files) from events

### Client behavior — sidebar
- Silent auto-refresh: sidebar list silently reloads when any change event arrives
- No "N new" indicator needed — just update the list in-place

### Client behavior — viewer (open note)
- If the currently open note is modified externally: auto-reload the viewer content
- If the editor has **unsaved changes** (dirty state) when an external update arrives for the same note:
  - Do NOT auto-reload
  - Show a conflict banner: "Note was updated externally — keep your edits or load the new version?" with explicit Keep/Load choices
- If the currently open note is deleted externally: clear the viewer and show "Note was deleted"

### SSE connection lifecycle
- Use native `EventSource` — browser handles auto-reconnect with exponential backoff
- Show a persistent status dot in the GUI indicating live-refresh connection state (green = connected, grey = disconnected)
- On reconnect after a drop: perform a full notes list refresh to catch any changes missed during the gap
- Each browser tab maintains its own SSE connection (no shared worker)

### Event granularity
- Each event carries: `{ type: "created" | "modified" | "deleted", path: "relative/note.md" }`
- SSE stream is designed as general-purpose (notes, actions, intelligence events) even if only note events are wired in this phase — use named event types so future resource types can be added cleanly
- Debounce on the **backend**: batch rapid file changes within a short window (≈300ms) before firing events — prevents flooding during `sb-reindex` or bulk captures
- Notes only in this phase; `files/` subdirectory changes do not produce events

### Claude's Discretion
- Exact debounce implementation (timer per path vs global flush)
- Flask SSE streaming approach (generator + `Response(stream_with_context(...))` or a queue-based approach)
- Status dot placement and exact styling
- How to wire the watchdog observer into the Flask server startup lifecycle

</decisions>

<specifics>
## Specific Ideas

- Event payload shape locked: `{"type": "modified", "path": "people/alice.md"}` — consistent with what was shown in discussion
- Status dot: always visible, reflects live connection state (not transient)
- Conflict resolution UX: explicit two-choice banner, not auto-save or silent discard

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/watcher.py` — `watchdog` Observer + `FileSystemEventHandler` already in use for `files/` drop watching. Same pattern extends to `~/SecondBrain` note watching for SSE.
- `engine/api.py` — Flask app with `flask-cors`; SSE endpoint added here as a generator route
- `engine/gui/static/app.js` — `loadNotes()` function is the natural refresh trigger; `EventSource` wired alongside existing `fetch()` calls

### Established Patterns
- Backend is authoritative for data transformation (from Phase 20 context)
- Vanilla JS only — no framework; `EventSource` is a browser native API, fits the stack
- Flask `>=3.0` — supports `stream_with_context` for SSE generators natively

### Integration Points
- New `/events` (or `/stream`) GET endpoint on the Flask app — SSE stream
- Watchdog observer started alongside Flask server (in `main()` of `api.py`)
- `app.js`: `new EventSource(...)` on page load, event listeners for `created`/`modified`/`deleted` named events

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 21-live-refresh-sse*
*Context gathered: 2026-03-16*
