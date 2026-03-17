---
phase: 25-file-capture-batch-capture
plan: 03
subsystem: ui
tags: [javascript, html, file-upload, drag-drop, attachments, batch-capture]

requires:
  - phase: 25-02
    provides: POST /files/upload, GET /notes/<path>/attachments, POST /batch-capture backend endpoints

provides:
  - Upload button in topbar and viewer toolbar that triggers OS file picker
  - Drag-and-drop onto #viewer uploads file to current note
  - Attachment list rendered below note body in #attachments-section (never overwrites #viewer)
  - Batch Capture button posts to /batch-capture and displays result in Intelligence panel

affects:
  - 25-04
  - 26-rrf-search

tech-stack:
  added: []
  patterns:
    - "loadAttachments() called inside openNote() after body renders — attachment section is always in sync with current note"
    - "Silent upload success — no toast/modal; only loadAttachments() + loadNotes() refresh"
    - "Batch capture result prepended into #recap-content via DOM prepend, not innerHTML overwrite"
    - "upload-btn starts disabled in HTML; openNote() enables it — guarantees no upload without active note"

key-files:
  created: []
  modified:
    - engine/gui/static/index.html
    - engine/gui/static/app.js

key-decisions:
  - "[25-03] viewer-upload-btn placed in #viewer-toolbar (after delete-btn); upload-btn in topbar (after new-note-btn) — dual entry points per CONTEXT.md"
  - "[25-03] #attachments-section div placed after #viewer div (sibling, not child) — prevents attachment list from being wiped when renderMarkdown() sets viewer.innerHTML"
  - "[25-03] Batch capture result written to #recap-content (existing element in Intelligence panel) via prepend — matches existing panel structure without adding new elements"
  - "[25-03] loadAttachments() called inside openNote() after all other panel loads — consistent with loadMeta/loadActions/loadIntelligence pattern"

patterns-established:
  - "loadAttachments(path) always called from openNote() — single responsibility, no manual wiring needed"

requirements-completed:
  - GUIF-01
  - ENGL-01

duration: 1min
completed: 2026-03-17
---

# Phase 25 Plan 03: File Capture Frontend Summary

**Upload button, drag-and-drop, attachment list below note body, and Batch Capture button with Intelligence panel result — all wired to the Wave 2 backend endpoints**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-17T06:41:34Z
- **Completed:** 2026-03-17T06:43:24Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Upload button (topbar + viewer toolbar) triggers OS file picker via hidden `#file-input`; `upload-btn` starts disabled and is enabled by `openNote()`
- Drag-and-drop onto `#viewer` area uploads file to currently-open note via `uploadFile()`
- `loadAttachments()` fetches `/notes/<path>/attachments` and renders entries in `#attachments-section` (sibling of `#viewer`, never overwrites viewer content) in "filename · date · size" format
- Batch Capture button posts to `/batch-capture` and prepends result message into Intelligence panel's `#recap-content`

## Task Commits

1. **Task 1: HTML — buttons, file input, attachment section** - `acc232e` (feat)
2. **Task 2: JS — upload handler, drag-drop, attachment list, batch capture** - `2c03254` (feat)

## Files Created/Modified

- `engine/gui/static/index.html` - Added upload-btn, batch-capture-btn, viewer-upload-btn, #file-input, #attachments-section
- `engine/gui/static/app.js` - Added uploadFile(), loadAttachments(), drag-drop events, batch capture handler; wired loadAttachments() into openNote()

## Decisions Made

- `#attachments-section` placed as sibling of `#viewer` (not child) so `renderMarkdown()` setting `viewer.innerHTML` never destroys the attachment list
- Batch capture result goes into `#recap-content` (existing Intelligence panel element) via `prepend` — no new DOM structure needed
- `upload-btn` starts `disabled` in HTML; `openNote()` enables it — enforces the invariant that uploads require an active note without JS initialization order concerns

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Full file capture frontend is complete; upload, drag-drop, attachments, and batch capture all wired to Wave 2 backend
- Phase 25 is now complete (all 3 plans done)
- Phase 26 (RRF search) can proceed

---
*Phase: 25-file-capture-batch-capture*
*Completed: 2026-03-17*
