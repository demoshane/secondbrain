---
phase: 21-live-refresh-sse
plan: 02
subsystem: api
tags: [sse, server-sent-events, watchdog, flask, streaming, live-refresh]

# Dependency graph
requires:
  - phase: 21-01
    provides: RED test stubs for NoteChangeHandler and SSE subscriber registry
provides:
  - NoteChangeHandler class in engine/watcher.py with debounce, filtering, and relative paths
  - SSE subscriber registry (_subscribe/_unsubscribe/_broadcast) in engine/api.py
  - GET /events streaming endpoint with 15s heartbeat
  - start_note_observer() callable from both api.main() and gui/__init__.py
  - Observer startup wired into api.main() and engine/gui/__init__.py
affects: [21-03, 21-04, frontend-live-refresh]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Per-client queue subscriber registry with thread-safe lock for fan-out broadcast
    - Per-path debounce timer pattern (cancel + recreate on each rapid event)
    - Observer daemon thread with stop/join in finally block for clean shutdown
    - Lazy import of start_note_observer in gui/__init__.py after health check

key-files:
  created: []
  modified:
    - engine/watcher.py
    - engine/api.py
    - engine/gui/__init__.py

key-decisions:
  - "Queue maxsize=50 with put_nowait + pass on Full: slow clients silently dropped rather than blocking broadcast"
  - "NoteChangeHandler._is_note() uses Path.parts for 'files' segment check, not substring match, to avoid false positives"
  - "Observer started in gui/__init__.py _start_sidecar() after health check, not before — ensures sidecar is ready"
  - "waitress threads increased to 8 in api.main() to prevent SSE connections exhausting the pool"

patterns-established:
  - "SSE pattern: Response(stream_with_context(generate()), mimetype='text/event-stream') with finally: _unsubscribe(q)"
  - "Broadcast pattern: module-level _subscribers list + lock; put_nowait skips full queues silently"

requirements-completed: [GUIX-01]

# Metrics
duration: 8min
completed: 2026-03-16
---

# Phase 21 Plan 02: SSE Backend Summary

**SSE streaming endpoint with per-client queue registry, NoteChangeHandler debounce watcher, and observer startup wired into both api.main() and gui/__init__.py — all 8 tests GREEN**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-16T12:05:00Z
- **Completed:** 2026-03-16T12:13:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- NoteChangeHandler added to engine/watcher.py: filters non-.md and files/ paths, per-path 300ms debounce, emits relative paths via BRAIN_PATH
- SSE subscriber registry in engine/api.py: thread-safe queue fan-out, GET /events with heartbeat, start_note_observer()
- api.main() upgraded to threads=8 and starts/stops observer around waitress serve
- gui/__init__.py wired to call start_note_observer() after sidecar health check passes
- All 8 tests from Plan 01 RED stubs now GREEN; full suite shows only 2 pre-existing failures unrelated to this plan

## Task Commits

Each task was committed atomically:

1. **Task 1: Add NoteChangeHandler to engine/watcher.py** - `fe8f727` (feat)
2. **Task 2: Add SSE subscriber registry and /events route** - `b619254` (feat)

## Files Created/Modified

- `engine/watcher.py` - Added NoteChangeHandler class with _is_note(), _schedule(), _fire(), on_created/modified/deleted
- `engine/api.py` - Added json/queue/threading imports, _subscribers registry, _subscribe/_unsubscribe/_broadcast, GET /events route, start_note_observer(), threads=8 in main()
- `engine/gui/__init__.py` - Injected start_note_observer() call after health check loop in _start_sidecar()

## Decisions Made

- Queue maxsize=50 with `put_nowait` + silent pass on `queue.Full`: slow/disconnected clients don't block fast broadcast
- `Path.parts` for files segment check prevents substring false positives (e.g. "myfiles/note.md" would wrongly match a naive `"files/" in path` check)
- Observer started after health check in GUI init — ensures waitress is accepting connections before watchdog begins emitting

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Two pre-existing test failures (`test_claude_md_contains_session_hook` and `test_blocks_api_key`) are environment-specific and unrelated to SSE changes.

## Next Phase Readiness

- SSE backend is complete and tested. Plan 21-03 can wire the JavaScript EventSource client to the /events endpoint.
- The `_broadcast` function is the sole integration point — frontend just needs to connect to `http://127.0.0.1:37491/events` and listen for `event: note` frames.

---
*Phase: 21-live-refresh-sse*
*Completed: 2026-03-16*
