---
phase: 04-automation
plan: "11"
subsystem: automation
tags: [watcher, headless, ai-classify, capture, batch-processing]

# Dependency graph
requires:
  - phase: 04-automation
    provides: FilesDropHandler with _fire_batch batch design (04-04)
  - phase: 04-automation
    provides: capture_note, get_connection, init_schema (02-storage-and-index)
  - phase: 03-ai-layer
    provides: router.get_adapter, adapter.generate interface
provides:
  - headless on_new_file callback in engine/watcher.py main() with zero input() calls
  - AI-derived title (stem title-casing) and best-effort tag suggestion per dropped file
  - graceful AI failure fallback — empty tags, never blocks or aborts
  - two new unit tests confirming batch non-blocking and AI-failure fallback
affects:
  - sb-watch daemon operation
  - CAP-04 file drop automation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - closure-over-shared-resources: conn and adapter initialized once before on_new_file closure, closed after observer.join()
    - best-effort AI with silent fallback: try/except around adapter.generate, empty list on any exception

key-files:
  created: []
  modified:
    - engine/watcher.py
    - tests/test_watcher.py

key-decisions:
  - "on_new_file derives title from path.stem with hyphen/underscore->space and title-case — no user input needed"
  - "adapter and conn initialized once in main() before closure — not per-file — avoids repeated DB connection overhead"
  - "conn.close() moved to after observer.join() so connection stays alive for entire daemon lifetime"
  - "sensitivity hardcoded to 'private' for all file-drop captures — safe default for unclassified dropped files"

patterns-established:
  - "Headless watcher callback: derive metadata from filename, AI best-effort, capture directly — zero blocking calls"

requirements-completed: [CAP-04]

# Metrics
duration: 2min
completed: 2026-03-14
---

# Phase 04 Plan 11: Headless Watcher Callback Summary

**Replaced blocking input()-based on_new_file in sb-watch with headless AI-classify callback: title from stem, adapter.generate tags, direct capture_note call — zero user interaction per dropped file**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-14T19:47:47Z
- **Completed:** 2026-03-14T19:49:47Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Removed both `input()` calls from `on_new_file` in `main()` — watcher now fully headless
- Title derived automatically from `path.stem` (hyphens/underscores replaced with spaces, title-cased)
- AI tags via `adapter.generate` with graceful fallback to `[]` on any exception — never blocks
- `conn` and `adapter` set up once before closure and `conn.close()` deferred to after `observer.join()`
- Two new tests: direct `_fire_batch` with 3 injected paths (all 3 processed), AI-failure path (empty tags, no `input()` raised)
- Full suite 91 passed, 4 skipped, 1 xfailed

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace interactive on_new_file with headless AI-classify callback** - `ea3fcf5` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `engine/watcher.py` - Replaced blocking on_new_file; moved imports, conn, adapter setup before closure; conn.close() after join
- `tests/test_watcher.py` - Added test_batch_processes_all_files_direct and test_main_on_new_file_no_input_on_ai_failure

## Decisions Made
- `adapter` initialized with `"private"` sensitivity — safe default for unclassified dropped files matches the `capture_note` call's `content_sensitivity="private"` argument
- Used `import engine.router as router_mod` (module ref, not from-import) to stay consistent with the existing pattern established in Phase 3 for correct mock patching
- `conn.close()` placed after `observer.join()` rather than in the `KeyboardInterrupt` handler body — ensures connection is alive for entire watcher lifetime including final batch processing after stop

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- `uv run --no-project --with pytest tests/...` produced empty output (exit 0) — correct invocation is `uv run --with pytest pytest tests/...` (no `--no-project`). Discovered during verification; did not affect implementation.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- `sb-watch` daemon is now fully automated for file-drop capture — drops N files, all N get brain notes without any user interaction
- CAP-04 requirement fulfilled
- Phase 04 automation plans complete

---
*Phase: 04-automation*
*Completed: 2026-03-14*
