---
status: partial
phase: 36-chrome-extension-capture
source: [36-VERIFICATION.md]
started: 2026-03-25T00:00:00Z
updated: 2026-03-25T12:00:00Z
---

## Current Test

UAT complete — all 10 tests passed on Vivaldi (Chromium fork).

## Tests

### 1. Extension loads without errors in Chrome developer mode
expected: Extension appears in chrome://extensions with no errors, icon visible in toolbar
result: pass

### 2. Readability.js article extraction fills popup body correctly
expected: Clicking icon on a news article opens popup with extracted article text in body field
result: pass

### 3. Selection and link context menu flows pre-fill popup correctly
expected: Right-click selected text → "Save Selection to Brain" opens popup with selection in body; right-click link → "Save Link to Brain" opens popup with URL as body
result: pass

### 4. Gmail "Save to Brain" button injects without duplicates on SPA navigation
expected: Button appears in Gmail thread header; navigating between threads doesn't create duplicate buttons
result: pass

### 5. Gmail context menu extracts thread metadata correctly
expected: Right-click in Gmail thread → "Save Gmail Thread to Brain" opens popup pre-filled with subject as title, thread body, type=meeting, tags=email
result: pass

### 6. Badge shows red "!" when sb-api is stopped
expected: When sb-api is not running, extension icon shows a red "!" badge; clears when api restarts
result: pass

### 7. Capture history persists across popup opens
expected: After saving a note, reopening popup shows the saved note in the Recent Captures list
result: pass

### 8. Options page saves and propagates API URL change
expected: Changing API URL in options page → saved → subsequent captures use the new URL
result: pass

### 9. setup.sh install prompt behaves correctly
expected: Running setup.sh shows Chrome extension install prompt (y/N); answering y prints instructions; n skips
result: pass

### 10. IntelligencePage Chrome Extension card shows correct connection status
expected: Intelligence page shows Chrome Extension section with green dot when sb-api running, red when not; Install button toggles instructions
result: pass

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
