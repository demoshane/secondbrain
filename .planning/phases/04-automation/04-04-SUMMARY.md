---
phase: 04-automation
plan: "04"
subsystem: automation
tags: [watchdog, threading, debounce, rate-limiting, file-watcher, daemon]

requires:
  - phase: 04-automation
    provides: RateLimiter(max_calls, window_seconds) from engine/ratelimit.py (Phase 3/04-00)
  - phase: 03-ai-layer
    provides: RateLimiter implementation and router/adapter pattern used in main()

provides:
  - FilesDropHandler: watchdog FileSystemEventHandler with debounce + rate-limit + history guard
  - start_watcher(): creates Observer, schedules handler, returns running Observer
  - main(): sb-watch CLI daemon entry point watching BRAIN_ROOT/files/
affects: [04-05, future-automation, file-drop-workflows]

tech-stack:
  added: [watchdog==6.0.0 (runtime dep for sb-watch daemon)]
  patterns:
    - threading.Timer cancel/restart debounce pattern
    - FSEvents history guard via ctime vs monotonic start time
    - RateLimiter.allow() gate before expensive AI call

key-files:
  created: []
  modified:
    - engine/watcher.py
    - tests/test_watcher.py

key-decisions:
  - "watchdog Observer not started in unit tests — handler class methods tested directly via on_created() and _fire() calls"
  - "FSEvents history guard uses (time.time() - (time.monotonic() - start_time) - 1s slack) to convert monotonic start to wall clock"
  - "RateLimiter reused from Phase 3 engine/ratelimit.py — no new AI infrastructure needed"

patterns-established:
  - "Debounce pattern: cancel pending timer for path, create new Timer, start it; only _fire() reaches rate limiter"
  - "Test isolation: patch threading.Timer to capture callbacks; invoke manually to simulate timer expiry without sleeping"

requirements-completed: [CAP-04]

duration: 5min
completed: 2026-03-14
---

# Phase 4 Plan 04: File Drop Watcher Summary

**watchdog-based FilesDropHandler daemon with threading.Timer debounce, RateLimiter gate, and FSEvents history guard for brain/files/ drop detection**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-14T18:18:50Z
- **Completed:** 2026-03-14T18:24:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Replaced stub `engine/watcher.py` with full FilesDropHandler implementation
- Debounce via `threading.Timer` cancel/restart — multiple rapid events for same path collapse to one callback
- FSEvents history guard — skips files whose ctime predates watcher start (prevents replaying Drive-synced history on macOS)
- Rate limiting via existing `RateLimiter(max_calls=1, window_seconds=5.0)` — gates AI categorization calls
- `start_watcher()` wires handler + Observer; `main()` provides `sb-watch` interactive CLI daemon
- All 4 xfail test stubs replaced with real passing unit tests; full suite 83 passed, 4 skipped, 1 xpassed

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement engine/watcher.py and tests** - `249c1fc` (feat)

## Files Created/Modified

- `engine/watcher.py` - Full FilesDropHandler, start_watcher, main implementation (replaces stub)
- `tests/test_watcher.py` - 4 real unit tests replacing xfail stubs

## Decisions Made

- watchdog Observer not started in unit tests — handler class methods tested directly via `on_created()` and `_fire()` calls (avoids real filesystem events in CI)
- FSEvents history guard uses `(time.time() - (time.monotonic() - start_time) - 1s slack)` formula to convert monotonic start to approximate wall clock for ctime comparison
- RateLimiter reused from Phase 3 `engine/ratelimit.py` — no new AI infrastructure needed for this plan

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `engine/watcher.py` fully implemented and tested — `sb-watch` entry point ready to wire into pyproject.toml
- Depends on `BRAIN_ROOT/files/` directory existing (created by `main()` via `mkdir(parents=True, exist_ok=True)`)
- watchdog must be added to pyproject.toml dependencies if not already present for the daemon to work outside `uv run --with watchdog`

---
*Phase: 04-automation*
*Completed: 2026-03-14*
