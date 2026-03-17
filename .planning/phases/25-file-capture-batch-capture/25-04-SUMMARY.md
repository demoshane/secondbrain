---
phase: 25-file-capture-batch-capture
plan: 04
subsystem: ui, database, api
tags: [sqlite, migrations, sse, file-upload, attachments, flask]

requires:
  - phase: 25-01
    provides: attachments table migration and save_attachment()
  - phase: 25-02
    provides: POST /files/upload endpoint
  - phase: 25-03
    provides: frontend attachment section and upload UI

provides:
  - DB migrations run on GUI server startup (no OperationalError on fresh deploys)
  - Live attachment list refresh via SSE attachment event after upload
  - Error string guard in tag chip renderer
  - Global file management modal wired to top toolbar File button

affects: [phase-26, any future phase touching api.py main()]

tech-stack:
  added: []
  patterns:
    - "_ensure_schema() called in main() before serving — always safe to add new migrations to init_schema()"
    - "SSE attachment event type: {type:'attachment', note_path} for targeted list refresh without full reload"
    - "Tag guard: skip chips >60 chars or matching error-sentence prefixes"

key-files:
  created: []
  modified:
    - engine/api.py
    - engine/gui/static/app.js
    - engine/gui/static/index.html

key-decisions:
  - "[25-04] _ensure_schema() in main() is the canonical fix — api.py was the only entry point that did not call init_schema() on an existing DB"
  - "[25-04] SSE attachment event is separate from note events so the sidebar does not reload on every upload"
  - "[25-04] Tag error guard uses length+prefix heuristic rather than allowlist — pragmatic since no schema enforcement on tags column exists"
  - "[25-04] Top toolbar File button opens file management modal (all files, all notes); viewer toolbar File button stays as note-specific uploader"

requirements-completed:
  - GUIF-01
  - ENGL-01

duration: 25min
completed: 2026-03-17
---

# Phase 25 Plan 04: Final Sign-off and Bug Fixes Summary

**Four GUI bugs fixed post-human-verify: missing attachments table on existing DBs, no live refresh after upload, AI error strings leaking into tag chips, and top File button with no handler**

## Performance

- **Duration:** 25 min
- **Started:** 2026-03-17T07:00:00Z
- **Completed:** 2026-03-17T07:25:00Z
- **Tasks:** 2 (Task 1 pre-completed; Task 2 required 4 bug fixes)
- **Files modified:** 3

## Accomplishments

- Fixed `sqlite3.OperationalError: no such table: attachments` — `api.py`'s `main()` was the only entry point not calling `init_schema()`, so existing DBs never got the migration
- Fixed live refresh after upload — `POST /files/upload` now broadcasts `{type:'attachment', note_path}` via SSE; `handleNoteEvent` handles it by calling `loadAttachments()` for the current note
- Fixed error strings appearing as tags — `renderTagChips` now skips entries longer than 60 chars or matching AI error sentence prefixes
- Implemented global file management modal for the top toolbar `+ File` button (all uploaded files, all notes)

## Task Commits

1. **Task 1: Full test suite sign-off** - `9875dca` (test — pre-completed)
2. **Fix Issue 1: DB migration on startup** - `a502ca4` (fix)
3. **Fix Issue 2: SSE broadcast + attachment event handler** - `12043c3` (fix — also includes tag guard)
4. **Fix Issue 4: Global file management modal** - `666211c` (feat)

## Files Created/Modified

- `engine/api.py` — Added `_ensure_schema()` helper; call it in `main()` before serving; added `_broadcast` after upload
- `engine/gui/static/app.js` — `handleNoteEvent` handles `attachment` type; `renderTagChips` error guard; `openFilesModal()` + files modal wiring; top upload button repurposed
- `engine/gui/static/index.html` — Added `#files-modal` markup; removed `disabled` from top `#upload-btn`

## Decisions Made

- `_ensure_schema()` is placed in `main()` rather than triggered per-request, since it runs idempotent `CREATE TABLE IF NOT EXISTS` — negligible cost and avoids per-request overhead
- SSE `attachment` event returns early after calling `loadAttachments()` — does not trigger `loadNotes()` sidebar reload since upload doesn't change the notes list
- Tag guard uses length + prefix heuristic: no DB schema enforcement on `tags` TEXT column exists, so a runtime filter is the pragmatic choice
- Top `+ File` button now opens a file management modal (global); viewer `+ File` still triggers the note-specific upload. Both are visible when a note is open — acceptable per user spec

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] DB migration not running on existing databases**
- **Found during:** Task 2 (human GUI verification)
- **Issue:** `api.py`'s `main()` never called `init_schema()`; every other CLI entry point did. Existing DBs had no `attachments` table.
- **Fix:** Added `_ensure_schema()` function that calls `init_schema()` on a fresh connection; called at server startup
- **Files modified:** `engine/api.py`
- **Verification:** Upload no longer raises `OperationalError`; 305 pytest tests still pass
- **Committed in:** a502ca4

**2. [Rule 1 - Bug] No SSE broadcast after file upload**
- **Found during:** Task 2 (human GUI verification)
- **Issue:** `POST /files/upload` returned the attachment JSON but never called `_broadcast`, so the frontend attachment list only updated if the client polled
- **Fix:** Added `_broadcast({"type": "attachment", "note_path": note_path})` after `save_attachment()`; added `attachment` event handler in `handleNoteEvent` to call `loadAttachments(currentPath)`
- **Files modified:** `engine/api.py`, `engine/gui/static/app.js`
- **Committed in:** 12043c3

**3. [Rule 1 - Bug] AI error string leaking into tag chip renderer**
- **Found during:** Task 2 (human GUI verification)
- **Issue:** `ron-3.png` triggered AI processing that stored an error sentence in the `tags` field; `renderTagChips` rendered it verbatim as `#The file 'ron-3.png' doesn't exist...`
- **Fix:** Guard added at top of `tagsCopy.forEach`: skip tags >60 chars or matching `/^(The |Could |Error|Failed|Unable )/i`
- **Files modified:** `engine/gui/static/app.js`
- **Committed in:** 12043c3

**4. [Rule 2 - Missing] Top File button had no handler**
- **Found during:** Task 2 (human GUI verification)
- **Issue:** `#upload-btn` in topbar fired `fileInput.click()` without `currentPath`, doing nothing when no note was open
- **Fix:** Repurposed button to open global file management modal listing all files via `GET /files`; added modal HTML, backdrop click, close button
- **Files modified:** `engine/gui/static/app.js`, `engine/gui/static/index.html`
- **Committed in:** 666211c

---

**Total deviations:** 4 auto-fixed (3 Rule 1 bugs, 1 Rule 2 missing functionality)
**Impact on plan:** All fixes required for the phase to meet its stated success criteria. No scope creep beyond user-approved Issue 4.

## Issues Encountered

- During pre-existing-failure check (stash test), `uv.lock` was modified by the pre-commit hook and blocked stash pop — resolved by resetting `uv.lock` first

## Next Phase Readiness

- Phase 25 requirements GUIF-01 and ENGL-01 are met: file upload works end-to-end, batch capture is functional, no critical errors in the GUI
- The tag error guard is a defensive fix; root cause (AI layer storing error strings in `tags`) remains in Phase 27 TODO backlog
- Phase 26 (RRF search) can proceed without blockers

---
*Phase: 25-file-capture-batch-capture*
*Completed: 2026-03-17*
