---
phase: 21-live-refresh-sse
plan: "04"
subsystem: ui
tags: [sse, live-refresh, conflict-banner, status-dot, pywebview]

# Dependency graph
requires:
  - phase: 21-03
    provides: EventSource client, status dot, conflict banner, isDirty tracking
provides:
  - Human verification results for SSE live-refresh feature
  - Bug report: 3 issues found requiring follow-up fixes
affects: [21-05-or-followup, any phase touching note editor or SSE client]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified: []

key-decisions:
  - "Verification FAILED — 3 bugs found; phase 21 cannot be marked complete until fixed"
  - "Critical: conflict banner silently discards editor content on external change (data loss)"
  - "Bug: save_note response triggers false-positive 'note deleted' notification"

patterns-established: []

requirements-completed: []  # GUIX-01 NOT completed — verification failed

# Metrics
duration: 0min
completed: 2026-03-16
---

# Phase 21 Plan 04: Human Verification Summary

**SSE live-refresh verification FAILED — conflict banner causes silent data loss; save triggers false "note deleted" notification**

## Performance

- **Duration:** N/A (human checkpoint plan — no code executed)
- **Started:** 2026-03-16
- **Completed:** 2026-03-16
- **Tasks:** 0 (checkpoint only)
- **Files modified:** 0

## Verification Result

**FAILED** — 3 issues found during manual testing.

### Issue 1 — Minor: Status dot connection delay

- **Severity:** Minor / cosmetic
- **Check:** Check 1 (status dot)
- **Observed:** Status dot turned green after ~5 seconds instead of within 1-2 seconds
- **Expected:** Green within 1-2 seconds of launch
- **Impact:** Cosmetic; SSE does connect and function correctly

### Issue 2 — CRITICAL: Conflict banner does not appear; editor silently discarded

- **Severity:** Critical — data loss risk
- **Check:** Check 4 (conflict banner)
- **Observed:** When a note is open in the editor (with unsaved changes) and an external file change arrives via SSE, the editor is closed or refreshed without displaying the conflict banner. The user's in-progress edits are silently discarded.
- **Expected:** A banner with "Note was updated externally" plus Keep/Load buttons should appear; user must explicitly choose
- **Impact:** Any externally-triggered file change (e.g. watcher, sync tool, another terminal) silently destroys unsaved editor content — this is a data-loss bug
- **Likely cause:** SSE `note_updated` handler fires the viewer reload path even when `isDirty` is true and the editor is active; the `isDirty` / conflict-banner branch in `app.js` is either not reached or has a logic error

### Issue 3 — Bug: False-positive "note deleted" message on save

- **Severity:** Medium — incorrect UX, confusing
- **Check:** Check 5 (deleted note message) — observed during normal save flow
- **Observed:** When saving a note (clicking Save in the editor), a "note is deleted" notification appears. The note still exists and is navigable — the message is a false positive.
- **Expected:** A success/save confirmation, or no message; the "note deleted" message should only appear when SSE delivers a `note_deleted` event
- **Likely cause:** The `save_note` API response is being misinterpreted by the SSE event handler or notification logic; a `note_deleted` SSE event may be firing after save due to a transient file-system event (delete + rewrite pattern)

## Accomplishments

None — this was a verification-only checkpoint plan. No code was written.

## Task Commits

No task commits — checkpoint plan only.

## Files Created/Modified

None.

## Decisions Made

- Phase 21 cannot be marked complete until the two bugs (Issues 2 and 3) are resolved.
- Issue 2 (conflict banner / data loss) is blocking — must be fixed before any write features in subsequent phases.
- Issue 3 (false deletion message) is a medium-priority correctness bug — fix alongside Issue 2.
- Issue 1 (5s connection delay) is acceptable to defer; address if time allows.

## Deviations from Plan

None — plan was a human-verify checkpoint with no automated tasks.

## Issues Encountered

Three bugs discovered during verification:

1. **[Minor] Status dot slow to go green** — ~5s delay on initial connect. Likely the EventSource `onopen` fires late or the first heartbeat triggers the status update rather than the connection event itself.

2. **[Critical] Conflict banner not shown on external edit while editor dirty** — isDirty guard is not preventing silent reload. The `handleNoteChange` path in app.js needs to check `isEditing && isDirty` before refreshing content and must show the conflict banner instead of auto-reloading.

3. **[Bug] False "note deleted" on save** — The save flow (POST to `/api/notes/:id`) appears to trigger a filesystem `deleted` event (likely because the write-to-tmp-then-rename or direct overwrite causes a brief unlink event picked up by watchdog). The NoteChangeHandler or the frontend must debounce/suppress `note_deleted` events that immediately follow a `note_updated` for the same path.

## Next Phase Readiness

Phase 21 is **NOT complete**. Required follow-up:

- Fix conflict banner logic: show banner instead of auto-reload when `isDirty` is true and note matches current editor (app.js)
- Fix false deletion notification: suppress or debounce `note_deleted` SSE events that fire within ~500ms of a successful save for the same note path
- Optionally: investigate 5s status dot delay (lower priority)

After fixes are applied, re-run checks 1, 4, and 5 from the verification protocol.

GUIX-01 requirement remains **open**.

---
*Phase: 21-live-refresh-sse*
*Completed: 2026-03-16*
