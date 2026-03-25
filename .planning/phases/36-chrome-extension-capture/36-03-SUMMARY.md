---
phase: 36-chrome-extension-capture
plan: 03
subsystem: chrome-extension
tags: [chrome-extension, gmail, content-script, mutation-observer, context-menu]

requires:
  - phase: 36-02
    provides: content.js, background.js, popup.js scaffold with context menu and pendingCapture pattern
  - phase: 36-01
    provides: POST /notes backend with source_type support

provides:
  - Gmail MutationObserver that detects thread views on mail.google.com
  - "Save to Brain" button injected into Gmail thread header (no duplicates on SPA navigation)
  - extractGmailThread() extracting subject, sender, recipients, date, full body as markdown
  - Gmail context menu item "Capture thread to Brain" via background.js
  - open-popup-gmail message handler in background.js with openPopup fallback
  - showInPageNotification() fallback when openPopup() fails from injected button
  - popup.js capture-gmail case pre-filling form with thread data, type=meeting, tags=email
  - captureSourceType tracking so POST body sends source_type=gmail

affects: [36-04, chrome-extension]

tech-stack:
  added: []
  patterns:
    - "MutationObserver for SPA navigation: observe document.body childList+subtree, guard duplicate with #sb-gmail-btn id check"
    - "Content-script to background openPopup relay: sendMessage({action:'open-popup-gmail'}), background wraps openPopup() in try/catch and returns {ok:true/false}"
    - "In-page fallback notification: fixed-position div with auto-dismiss on pendingCapture already stored"
    - "captureSourceType variable in popup.js tracks source across different capture flows"

key-files:
  created: []
  modified:
    - chrome-extension/content.js
    - chrome-extension/background.js
    - chrome-extension/popup.js

key-decisions:
  - "Gmail content script runs at document_start (manifest Plan 02) so MutationObserver can start before thread renders"
  - "Button injected into threadView.querySelector('[role=toolbar]') with prepend fallback — Gmail DOM lacks stable injection points"
  - "extractGmailThread() uses .a3s CSS class fallback for message body — more reliable than nested data-* traversal for partial renders"
  - "capture-gmail context menu uses extract-gmail message to content script before storing pendingCapture — gesture is from contextMenus.onClicked (trusted)"
  - "Injected button path stores pendingCapture in content script, then relays open-popup-gmail to background — gesture chain is NOT guaranteed, fallback notification directs user to click icon"

patterns-established:
  - "Gmail-specific pendingCapture: menuItemId=capture-gmail, gmailData object, pageUrl for source_url"
  - "captureSourceType in popup.js controls source_type POST field — extend for future source types"

requirements-completed: [D-07, D-08]

duration: 2min
completed: 2026-03-25
---

# Phase 36 Plan 03: Gmail Integration Summary

**Gmail thread capture via injected button and context menu: MutationObserver, extractGmailThread(), showInPageNotification fallback, popup pre-fill with type=meeting**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-25T06:57:26Z
- **Completed:** 2026-03-25T06:59:39Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments

- Gmail MutationObserver injects "Save to Brain" button into thread views with duplicate guard
- extractGmailThread() extracts subject, sender, recipients, date, and full thread body as formatted markdown
- Two capture paths: injected button (open-popup-gmail relay with in-page notification fallback) and context menu (trusted gesture, direct openPopup)
- popup.js capture-gmail case pre-fills form with thread data, pre-selects "meeting" type and "email" tag
- source_type=gmail propagated through captureSourceType variable to POST body

## Task Commits

1. **Task 1: Gmail content script — MutationObserver, button injection, thread extraction** - `a844aee` (feat)

## Files Created/Modified

- `chrome-extension/content.js` — Added isGmail check, MutationObserver, injectGmailButton(), extractGmailThread(), showInPageNotification(), extract-gmail message handler
- `chrome-extension/background.js` — Added capture-gmail context menu item, capture-gmail click handler, open-popup-gmail message handler
- `chrome-extension/popup.js` — Added captureSourceUrl/captureSourceType vars, capture-gmail case in populateFromPendingCapture, updated handleSave payload

## Decisions Made

- `captureSourceType` variable added to popup.js to replace hardcoded `'web'` — allows future source types without changing save handler
- Gmail context menu click calls `chrome.tabs.sendMessage` to extract thread before storing — reliable because contextMenus.onClicked is a trusted gesture source
- Injected button stores pendingCapture in content script directly (chrome.storage accessible from content scripts), then sends open-popup-gmail to background — avoids double async on a potentially broken gesture chain

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Worktree was behind main and lacked chrome-extension directory — merged main before starting. Not a code issue.

## User Setup Required

None — no external service configuration required. Extension install instructions will be in Phase 36-04.

## Next Phase Readiness

- Gmail integration complete and committed
- Plan 36-04 (packaging, install docs, end-to-end testing) can proceed immediately
- All acceptance criteria for D-07 (Gmail capture surface) and D-08 (thread metadata extraction) met

---
*Phase: 36-chrome-extension-capture*
*Completed: 2026-03-25*
