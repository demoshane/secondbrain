---
phase: 36-chrome-extension-capture
plan: "04"
subsystem: chrome-extension, frontend, setup
tags: [chrome-extension, ux, badge, history, install]
dependency_graph:
  requires: [36-01, 36-02, 36-03]
  provides: [D-09, D-10, D-11, D-16, D-17]
  affects: [chrome-extension/manifest.json, chrome-extension/background.js, chrome-extension/popup.js, chrome-extension/popup.css, setup.sh, frontend/src/components/IntelligencePage.tsx]
tech_stack:
  added: []
  patterns: [chrome.alarms badge polling, localStorage capture history, AbortSignal.timeout ping check, React toggle state for install instructions]
key_files:
  created: []
  modified:
    - chrome-extension/manifest.json
    - chrome-extension/background.js
    - chrome-extension/popup.js
    - chrome-extension/popup.css
    - setup.sh
    - frontend/src/components/IntelligencePage.tsx
decisions:
  - "chrome.alarms used for badge polling (not setInterval) — service workers have no persistent timers"
  - "chrome:// URLs cannot be opened from web pages — install button shows inline instructions only"
  - "extensionApiReachable state fetches /ping in useEffect — same check as badge polling but from GUI context"
metrics:
  duration_seconds: 691
  completed_date: "2026-03-25"
  tasks_completed: 2
  files_modified: 6
---

# Phase 36 Plan 04: Rich UX + Installation Summary

Connection badge polling, capture history, and installation UX for the Chrome extension using chrome.alarms for reliable service worker polling and a React toggle section on the Intelligence page.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Connection badge polling + capture history in popup | 3b22709 | chrome-extension/manifest.json, background.js, popup.js, popup.css, popup.html, content.js |
| 2 | Installation UX — setup.sh + Intelligence page button | b7ec3b8 | setup.sh, IntelligencePage.tsx |

## What Was Built

### Task 1: Connection Badge + Capture History

**manifest.json:** `"alarms"` permission added (was already present in main repo — previous parallel agent had done this work; files copied from main repo and committed).

**background.js:** `checkApiStatus()` polls `GET /ping` every 30s via `chrome.alarms.create('api-status-check', { periodInMinutes: 0.5 })`. Sets red `!` badge when unreachable, clears badge and restores icon when reachable. Also runs on service worker start.

**popup.js:** `addToHistory()` stores up to `MAX_HISTORY=10` entries in `localStorage`. `renderHistory()` displays entries with relative time. `checkConnectivity()` sets `status-bar` class to `connected` or `disconnected`, disables Save button when offline.

**popup.css:** `#status-bar.connected` (green), `#status-bar.disconnected` (red), `.status-message` for offline text, `#history-section`/`#history-list`/`.history-title`/`.history-type`/`.history-time` layout.

### Task 2: Installation UX

**setup.sh:** New section after health check — detects `chrome-extension/` directory, prompts user `[y/N]`, shows 5-step installation guide, calls `open "chrome://extensions"` on macOS.

**IntelligencePage.tsx:** New Chrome Extension section added at end of page. States: `showExtensionInstructions` (toggle) and `extensionApiReachable` (live ping). `useEffect` fetches `/ping` with 2s timeout. Button toggles inline numbered instructions. Status dot (green/red) shows API reachability. Comment explains why chrome:// URL is not an href.

## Deviations from Plan

None — plan executed exactly as written. Note: chrome-extension files were already complete in the main repo (parallel agents 36-01 through 36-03 had built them); this plan's Task 1 committed those files to the worktree branch.

## Known Stubs

None — all features are fully wired.

## Self-Check: PASSED

All files present. Both commits verified (3b22709, b7ec3b8).
