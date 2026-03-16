---
phase: 20-frontend-bug-fixes
plan: "03"
subsystem: ui
tags: [css, flex, scroll, easymde, markdown, pywebview]

# Dependency graph
requires:
  - phase: 20-frontend-bug-fixes
    provides: GUI base layout with flex #center panel
provides:
  - "Scrollable note viewer in #center flex panel via min-height: 0"
  - "EasyMDE editor scroll fix (EasyMDEContainer/CodeMirror flex chain)"
  - "Bundled marked.min.js for client-side markdown rendering"
  - "Null-safe renderMarkdown in app.js"
affects: [21-sse-backbone, 22-note-management, 18-gui-hub]

# Tech tracking
tech-stack:
  added: [marked.min.js (vendored)]
  patterns: [flex child scroll via min-height 0 on every ancestor, null-check before marked.parse]

key-files:
  created: [engine/gui/static/vendor/marked.min.js]
  modified:
    - engine/gui/static/style.css
    - engine/gui/static/index.html
    - engine/gui/static/app.js

key-decisions:
  - "min-height: 0 on flex container (#center) is canonical fix for flex child overflow-scroll not triggering — do not remove overflow: hidden from grid parent"
  - "Apply min-height: 0 to entire EasyMDE flex chain (EasyMDEContainer, CodeMirror) not just #center"
  - "Vendor marked.min.js rather than CDN — GUI runs offline in pywebview"

patterns-established:
  - "Flex scroll pattern: any scrollable flex child needs min-height: 0 on itself AND all ancestor flex containers up to the fixed-height root"
  - "renderMarkdown null-check: always guard marked.parse() with a null/undefined check on input"

requirements-completed: [GUIX-04]

# Metrics
duration: 15min
completed: 2026-03-16
---

# Phase 20 Plan 03: CSS Scroll Fix Summary

**Fixed note viewer scroll via min-height: 0 on flex chain, vendored marked.min.js for offline markdown rendering, and null-guarded renderMarkdown**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-16
- **Completed:** 2026-03-16
- **Tasks:** 2 (1 auto + 1 human-verify)
- **Files modified:** 4

## Accomplishments

- Note viewer (#viewer) is now scrollable with mouse wheel in pywebview GUI
- EasyMDE editor still fills available height after the scroll fix
- Markdown rendering restored by vendoring marked.min.js (was failing silently)
- renderMarkdown in app.js no longer throws on null/undefined input

## Task Commits

Each task was committed atomically:

1. **Task 1: Apply min-height: 0 CSS scroll fix** - `b7fb2f9` (fix)
2. **Task 2: Verify scroll and editor layout in live GUI** - human-verify checkpoint, approved by user

**Plan metadata:** (docs commit — see state update below)

## Files Created/Modified

- `engine/gui/static/style.css` - Added `min-height: 0` to `#center`, `#viewer`, `.EasyMDEContainer`, `.CodeMirror`
- `engine/gui/static/vendor/marked.min.js` - Vendored marked.js for offline markdown rendering
- `engine/gui/static/index.html` - Load marked.min.js before easymde in script order
- `engine/gui/static/app.js` - Null-check guard in renderMarkdown before calling marked.parse()

## Decisions Made

- Vendor marked.min.js rather than use CDN — pywebview GUI runs fully offline, CDN scripts fail silently
- Apply min-height: 0 to entire flex chain (not just #center) — EasyMDEContainer and CodeMirror also need it to scroll correctly
- Do not remove `overflow: hidden` from `#center` — it prevents layout bleed into the grid; `min-height: 0` alone is the correct fix

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Vendored marked.min.js for offline markdown rendering**
- **Found during:** Task 2 verification (human-verify)
- **Issue:** Markdown was not rendering in the viewer — marked.js was loaded from CDN which is unavailable in pywebview offline context
- **Fix:** Downloaded and vendored `marked.min.js` to `engine/gui/static/vendor/`, updated `index.html` to load it before easymde
- **Files modified:** `engine/gui/static/vendor/marked.min.js`, `engine/gui/static/index.html`
- **Verification:** Markdown renders correctly in live GUI after fix
- **Committed in:** b7fb2f9 (part of task 1 commit / additional fix during verification)

**2. [Rule 2 - Missing Critical] Extended flex scroll fix to EasyMDE component chain**
- **Found during:** Task 2 verification
- **Issue:** Plan specified min-height: 0 only on #center and #viewer; EasyMDE editor (EasyMDEContainer, CodeMirror) also needed min-height: 0 to maintain correct height in flex layout
- **Fix:** Added `min-height: 0` to `.EasyMDEContainer` and `.CodeMirror` rules in style.css
- **Files modified:** `engine/gui/static/style.css`
- **Verification:** Editor fills available height correctly after fix; confirmed by human in live GUI
- **Committed in:** b7fb2f9

**3. [Rule 1 - Bug] Null-check in renderMarkdown prevents crash on empty/null note body**
- **Found during:** Task 2 verification
- **Issue:** `marked.parse(undefined)` throws; renderMarkdown called before note body loaded
- **Fix:** Added null/undefined guard before calling `marked.parse()` in `app.js`
- **Files modified:** `engine/gui/static/app.js`
- **Verification:** No console errors when switching notes quickly or opening empty notes
- **Committed in:** b7fb2f9

---

**Total deviations:** 3 auto-fixed (1 blocking, 1 missing critical, 1 bug)
**Impact on plan:** All fixes necessary for correct operation. Vendoring marked.js was essential for offline pywebview context. EasyMDE chain fix prevents editor height regression. Null-check prevents runtime crash.

## Issues Encountered

- Markdown rendering was silently broken due to CDN dependency in offline context — resolved by vendoring

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- GUI scroll and markdown rendering are stable
- Ready for Phase 21 SSE backbone (note: WebKit/pywebview SSE compatibility should be validated with proof-of-concept at phase start — existing blocker in STATE.md)

---
*Phase: 20-frontend-bug-fixes*
*Completed: 2026-03-16*
