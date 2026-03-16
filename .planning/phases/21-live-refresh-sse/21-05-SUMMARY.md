---
phase: 21-live-refresh-sse
plan: "05"
subsystem: watcher
tags: [watchdog, sse, threading, waitress, flask]

# Dependency graph
requires:
  - phase: 21-live-refresh-sse
    provides: NoteChangeHandler, SSE broadcast, save_note endpoint
provides:
  - suppress_next_delete() in watcher.py — gates false-positive deleted events after atomic save
  - api.py save_note calls suppress_next_delete() after os.replace()
  - GUI sidecar waitress thread pool set to 8
affects: [21-live-refresh-sse, 22-deletion]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Suppression-set pattern: atomic-save produces OS deleted event; suppress it for 500ms window using threading.Timer"
    - "Thread pool sizing: SSE keeps one thread alive per client; pool must exceed expected concurrent SSE + API connections"

key-files:
  created: []
  modified:
    - engine/watcher.py
    - engine/api.py
    - engine/gui/__init__.py

key-decisions:
  - "500ms suppress window chosen to outlast typical FSEvents propagation delay after os.replace()"
  - "suppress_next_delete is module-level (not instance-level) so any NoteChangeHandler instance in the process shares the same suppression set"
  - "threads=8 matches api.py main() — single source of truth for thread count is now consistent between sidecar and standalone server"

patterns-established:
  - "Suppression set pattern: add path before atomic op, auto-clear via Timer, guard in _fire handler"

requirements-completed: [GUIX-01]

# Metrics
duration: 5min
completed: 2026-03-16
---

# Phase 21 Plan 05: Save-Suppression and Thread Fix Summary

**watchdog delete-on-save false positive fixed via 500ms suppression set; GUI sidecar thread pool doubled from 4 to 8**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-16T13:05:00Z
- **Completed:** 2026-03-16T13:10:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `suppress_next_delete()` added to `engine/watcher.py` — module-level suppression set with threading.Timer auto-clear
- `NoteChangeHandler._fire` now skips deleted broadcast when path is in suppression set
- `api.py save_note` calls `suppress_next_delete(str(p))` immediately after `os.replace()` so the FSEvents deleted event is silently dropped
- GUI sidecar `_start_sidecar` corrected from `threads=4` to `threads=8`, matching standalone `api.py main()`

## Task Commits

1. **Task 1: Add save-suppression to NoteChangeHandler and api.py save_note** - `c42b4f9` (fix)
2. **Task 2: Fix GUI sidecar thread count to 8** - `7c82e43` (fix)

## Files Created/Modified

- `engine/watcher.py` — added `_save_suppress` set, `_save_suppress_lock`, `suppress_next_delete()`, `_clear_suppress()`, guard in `_fire`
- `engine/api.py` — added `from engine.watcher import suppress_next_delete` import; call after `os.replace()`
- `engine/gui/__init__.py` — changed `threads=4` to `threads=8` in `_start_sidecar`

## Decisions Made

- 500ms suppress window: chosen to comfortably outlast FSEvents propagation delay on macOS after an atomic rename
- Module-level suppression set: shared across all `NoteChangeHandler` instances in-process; correct because there is only one `save_note` hot path
- No new dependencies: pure stdlib threading primitives

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- Phase 21 bug backlog is now clear: conflict banner (21-06) is the only remaining plan before phase close
- GUIX-01 requirement resolved by this fix (false-positive delete notification eliminated)

---
*Phase: 21-live-refresh-sse*
*Completed: 2026-03-16*

## Self-Check: PASSED
