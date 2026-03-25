---
status: partial
phase: 36-chrome-extension-capture
source: [36-VERIFICATION.md]
started: 2026-03-25T00:00:00Z
updated: 2026-03-25T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Extension loads without errors in Chrome developer mode
expected: Extension appears in chrome://extensions with no errors, icon visible in toolbar
result: [pending]

### 2. Readability.js article extraction fills popup body correctly
expected: Clicking icon on a news article opens popup with extracted article text in body field
result: [pending]

### 3. Selection and link context menu flows pre-fill popup correctly
expected: Right-click selected text → "Save Selection to Brain" opens popup with selection in body; right-click link → "Save Link to Brain" opens popup with URL as body
result: [pending]

### 4. Gmail "Save to Brain" button injects without duplicates on SPA navigation
expected: Button appears in Gmail thread header; navigating between threads doesn't create duplicate buttons
result: [pending]

### 5. Gmail context menu extracts thread metadata correctly
expected: Right-click in Gmail thread → "Save Gmail Thread to Brain" opens popup pre-filled with subject as title, thread body, type=meeting, tags=email
result: [pending]

### 6. Badge shows red "!" when sb-api is stopped
expected: When sb-api is not running, extension icon shows a red "!" badge; clears when api restarts
result: [pending]

### 7. Capture history persists across popup opens
expected: After saving a note, reopening popup shows the saved note in the Recent Captures list
result: [pending]

### 8. Options page saves and propagates API URL change
expected: Changing API URL in options page → saved → subsequent captures use the new URL
result: [pending]

### 9. setup.sh install prompt behaves correctly
expected: Running setup.sh shows Chrome extension install prompt (y/N); answering y prints instructions; n skips
result: [pending]

### 10. IntelligencePage Chrome Extension card shows correct connection status
expected: Intelligence page shows Chrome Extension section with green dot when sb-api running, red when not; Install button toggles instructions
result: [pending]

## Summary

total: 10
passed: 0
issues: 0
pending: 10
skipped: 0
blocked: 0

## Gaps
