---
phase: 36-chrome-extension-capture
plan: "02"
subsystem: chrome-extension
tags: [chrome-extension, manifest-v3, readability, capture, popup]
dependency_graph:
  requires: []
  provides:
    - chrome-extension/manifest.json (MV3 manifest, loadable in Chrome developer mode)
    - chrome-extension/background.js (context menus, pendingCapture, badge polling)
    - chrome-extension/content.js (Readability.js article extraction, selection extraction)
    - chrome-extension/popup.html/js/css (full edit form with save/cancel/history)
    - chrome-extension/options.html/js (API URL + default tags configuration)
    - chrome-extension/lib/ (Readability.js 0.6.0, DOMPurify 3.3.3 bundled)
    - chrome-extension/icons/ (16/48/128px PNG icons)
  affects: []
tech_stack:
  added:
    - "@mozilla/readability@0.6.0 (vendored)"
    - "DOMPurify@3.3.3 (vendored)"
  patterns:
    - "MV3 service worker + context menu → storage.session → popup flow"
    - "Content script message passing with return true for async responses"
    - "localStorage for capture history (max 10 entries)"
    - "chrome.storage.sync for user settings (apiUrl, defaultTags)"
    - "chrome.alarms for periodic API badge status polling"
key_files:
  created:
    - chrome-extension/manifest.json
    - chrome-extension/background.js
    - chrome-extension/content.js
    - chrome-extension/popup.html
    - chrome-extension/popup.js
    - chrome-extension/popup.css
    - chrome-extension/options.html
    - chrome-extension/options.js
    - chrome-extension/lib/Readability.js
    - chrome-extension/lib/purify.min.js
    - chrome-extension/icons/icon16.png
    - chrome-extension/icons/icon48.png
    - chrome-extension/icons/icon128.png
  modified: []
decisions:
  - "Used chrome.alarms (not setInterval) for badge polling — service worker has no persistent timer"
  - "Added alarms permission to manifest (auto-fix Rule 2 — required for badge polling)"
  - "Gmail content script entry uses document_start (not document_idle) per research recommendation"
  - "content.js gracefully handles missing Readability (Gmail path — lib not loaded)"
  - "POST /notes endpoint used (not /smart-capture) — user already selected type in dropdown"
metrics:
  duration_seconds: 226
  completed_date: "2026-03-25"
  tasks_completed: 2
  tasks_total: 2
  files_created: 13
  files_modified: 0
---

# Phase 36 Plan 02: Chrome Extension Scaffold Summary

**One-liner:** MV3 Chrome extension with Readability.js article extraction, context menu capture, full edit popup, and options page — loadable in Chrome developer mode.

## What Was Built

Complete `chrome-extension/` directory with all files needed to load in Chrome developer mode:

- **manifest.json**: MV3 manifest with contextMenus, activeTab, scripting, storage, alarms permissions. Content scripts for general pages (Readability + DOMPurify + content.js) and Gmail (content.js only, document_start). No keyboard shortcut (D-03).
- **background.js**: Three context menu items (capture-page, capture-selection, capture-link). pendingCapture stored in chrome.storage.session before openPopup() call. API badge polling via chrome.alarms every 30 seconds.
- **content.js**: Readability.js article extraction with DOMPurify sanitization. Selection extraction. Graceful fallback when Readability not available (Gmail path). Always returns true from onMessage listeners.
- **popup.html/js/css**: Full 400px edit form. Title, type picker (8 types), body textarea (scrollable, min 120px), tags, save/cancel buttons. Connectivity check against /ping disables Save button if sb-api unreachable. Form populates from pendingCapture context or active tab extraction. localStorage capture history (max 10 entries). POST to /notes endpoint.
- **options.html/js**: Save apiUrl and defaultTags to chrome.storage.sync.
- **Vendor libs**: Readability.js (89KB), DOMPurify (23KB) bundled in lib/.
- **Icons**: 16/48/128px PNGs generated with pure Python (no Pillow dependency).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added alarms permission to manifest**
- **Found during:** Task 2 (writing background.js)
- **Issue:** background.js uses chrome.alarms for badge polling (D-09 requirement), but alarms permission was not in the plan's manifest specification.
- **Fix:** Added "alarms" to permissions array in manifest.json before the Task 2 commit.
- **Files modified:** chrome-extension/manifest.json
- **Commit:** f8d0ef9

## Self-Check: PASSED
