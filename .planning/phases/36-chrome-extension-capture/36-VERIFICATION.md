---
phase: 36-chrome-extension-capture
verified: 2026-03-25T10:00:00Z
status: human_needed
score: 17/17 must-haves verified
human_verification:
  - test: "Load extension in Chrome developer mode"
    expected: "Extension loads without errors; three context menu items appear on right-click; icon badge is visible"
    why_human: "Requires Chrome browser, cannot verify manifest parsing or UI loading programmatically"
  - test: "Click extension icon on any web page"
    expected: "Popup opens with title pre-filled, body contains extracted article text (not blank), type=note pre-selected, save/cancel buttons present"
    why_human: "Readability.js extraction and popup rendering require live Chrome environment"
  - test: "Right-click a text selection and choose 'Save Selection to Brain'"
    expected: "Popup opens with selected text in body and page title in title field"
    why_human: "Context menu trigger and pendingCapture flow require live Chrome interaction"
  - test: "Right-click a hyperlink and choose 'Save Link to Brain'"
    expected: "Popup opens with link URL pre-filled, type=link pre-selected"
    why_human: "Link context menu flow requires live Chrome interaction"
  - test: "Open a Gmail thread; verify 'Save to Brain' button is injected in thread header"
    expected: "Button appears; clicking it stores capture and either opens popup or shows in-page notification directing user to click extension icon; no duplicate buttons on SPA navigation"
    why_human: "MutationObserver injection, Gmail DOM interaction, and openPopup gesture chain require live Gmail session"
  - test: "Right-click in Gmail thread and choose 'Capture thread to Brain'"
    expected: "Popup opens pre-filled with subject as title, thread body in body, type=meeting, tags=email"
    why_human: "Gmail context menu flow requires live Gmail session"
  - test: "Stop sb-api (kill service) and open popup"
    expected: "Red status bar visible, Save button disabled, error message shown. Extension icon shows red '!' badge."
    why_human: "Connection badge and popup offline state require live service interaction"
  - test: "Save a note, close popup, reopen popup"
    expected: "Capture history section shows the saved note with title, type badge, and relative time"
    why_human: "localStorage persistence in Chrome extension popup context cannot be tested without Chrome"
  - test: "Visit Options page (chrome://extensions -> Options)"
    expected: "API URL and default tags fields shown; changing and saving API URL is reflected on next popup open"
    why_human: "Options page UI and chrome.storage.sync require live extension context"
  - test: "Run setup.sh on a clean install"
    expected: "Chrome Extension section appears, prompts y/N, on 'y' prints 5-step instructions and opens chrome://extensions on macOS"
    why_human: "Interactive shell prompt requires manual execution; open command behavior is macOS-specific"
---

# Phase 36: Chrome Extension Capture — Verification Report

**Phase Goal:** Capture web content directly from Chrome into the second brain via a browser extension — full article extraction, text selection, Gmail threads, URL bookmarks, with edit-before-save popup and connection status awareness
**Verified:** 2026-03-25
**Status:** human_needed (all automated checks pass; 10 behaviors require live Chrome/browser verification)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

All 17 truths verified at the code level. Behavioral verification requires a live Chrome environment (see Human Verification Required section).

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /ping returns 200 with {ok: true} | VERIFIED | `engine/api.py:147-148` — `@app.get("/ping")` returns `jsonify({"ok": True})` |
| 2 | CORS allows chrome-extension:// origins | VERIFIED | `engine/api.py:64` — `CORS(app, origins=[..., "chrome-extension://*"])` |
| 3 | POST /smart-capture accepts source_url and source_type, writes to frontmatter | VERIFIED | `engine/api.py:1512-1526` — extracted from request body and passed to `capture_note(url=..., source_type=...)` |
| 4 | POST /notes accepts source_url, writes to frontmatter | VERIFIED | `engine/api.py:909,929` — `body.get("source_url")` written as `url:` in frontmatter string |
| 5 | capture_note() accepts source_type param and writes to frontmatter | VERIFIED | `engine/capture.py:459,522-523` — `source_type: str \| None = None` kwarg; `post["source_type"] = source_type` |
| 6 | Extension loads in Chrome developer mode without errors | VERIFIED (code) | manifest.json valid JSON, MV3 structure correct, all referenced files exist |
| 7 | Clicking extension icon opens popup with edit form (title, body, type, tags, save/cancel) | VERIFIED (code) | `popup.html` contains all required elements: `sb-title`, `sb-body`, `sb-type`, `sb-tags`, `save-btn`, `cancel-btn` |
| 8 | Right-click context menu shows all three items | VERIFIED | `background.js:11-31` — capture-page, capture-selection, capture-link created in onInstalled |
| 9 | Context menu click opens popup pre-filled with extracted content | VERIFIED (code) | `background.js:36-87` — stores `pendingCapture` in session storage then calls `openPopup()`; `popup.js:52-126` — reads and populates form |
| 10 | Full article extraction via Readability.js fills popup body | VERIFIED (code) | `content.js:31-86` — `new Readability(docClone).parse()` with DOMPurify sanitization; `popup.js:57-65` fills form |
| 11 | Selection capture fills popup with highlighted text + source URL | VERIFIED | `popup.js:79-86` — uses `pending.selectionText` + page URL |
| 12 | URL/link capture fills popup with page title and URL | VERIFIED | `popup.js:89-96` — uses `linkUrl`, type pre-set to `link` |
| 13 | Gmail thread capture: injected button, context menu, metadata extraction | VERIFIED (code) | `content.js:115-260` — MutationObserver, injectGmailButton(), extractGmailThread(); `background.js:27-31,37-62` Gmail menu + handler |
| 14 | Extension icon shows red badge when sb-api unreachable | VERIFIED (code) | `background.js:142-155` — `chrome.alarms` polls every 30s; `setOfflineBadge()` sets `!` badge |
| 15 | Popup shows inline connection status | VERIFIED | `popup.js:172-197` — `checkConnectivity()` sets connected/disconnected class, disables Save button |
| 16 | Last 10 captures visible in popup history | VERIFIED | `popup.js:258-291` — `addToHistory()`, `renderHistory()`, `MAX_HISTORY=10`, localStorage |
| 17 | Options page allows configuring sb-api URL and default tags | VERIFIED | `options.html:77,83`, `options.js:6-22` — `chrome.storage.sync.get/set` for `apiUrl` and `defaultTags` |

**Score:** 17/17 truths verified at code level

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/api.py` | /ping, CORS, source_url/source_type | VERIFIED | Line 64 CORS, line 146-148 ping, lines 909/1512-1526 source fields |
| `engine/capture.py` | source_type param | VERIFIED | Line 459 signature, lines 522-523 frontmatter write |
| `tests/test_api.py` | 4 tests for new endpoints | VERIFIED | test_ping, test_cors_extension_origin, test_smart_capture_source_url, test_create_note_source_url all present |
| `chrome-extension/manifest.json` | MV3, permissions, content scripts | VERIFIED | Valid JSON, manifest_version=3, all required permissions including alarms, no `commands` key (D-03 satisfied) |
| `chrome-extension/background.js` | Context menus, pendingCapture, badge polling | VERIFIED | All four menu items, gmail handler, badge polling via chrome.alarms |
| `chrome-extension/content.js` | Readability, selection, Gmail | VERIFIED | All handlers present: extract-article, extract-selection, extract-gmail, Gmail MutationObserver |
| `chrome-extension/popup.html` | Full edit form | VERIFIED | All required elements: sb-title, sb-body, sb-type, sb-tags, save-btn, cancel-btn, history-section |
| `chrome-extension/popup.js` | Form population, API POST, history | VERIFIED | pendingCapture handling, /notes POST, localStorage history, /ping connectivity check |
| `chrome-extension/popup.css` | 400px width, min-height textarea | VERIFIED | width:400px, max-height:600px, textarea min-height:120px, status-bar.connected/disconnected rules |
| `chrome-extension/options.html` | API URL + default tags form | VERIFIED | id="apiUrl", id="defaultTags" inputs present |
| `chrome-extension/options.js` | chrome.storage.sync read/write | VERIFIED | loadOptions(), saveOptions() with chrome.storage.sync.get/set |
| `chrome-extension/lib/Readability.js` | >10KB vendored library | VERIFIED | 89,980 bytes (2786 lines) |
| `chrome-extension/lib/purify.min.js` | >10KB vendored library | VERIFIED | 23,274 bytes — NOTE: minified to 3 lines, but 23KB is well above 10KB threshold |
| `chrome-extension/icons/icon16.png` | 16px icon | VERIFIED | 131 bytes |
| `chrome-extension/icons/icon48.png` | 48px icon | VERIFIED | 270 bytes |
| `chrome-extension/icons/icon128.png` | 128px icon | VERIFIED | 606 bytes |
| `setup.sh` | Chrome extension install prompt | VERIFIED | EXTENSION_DIR detection, y/N prompt, 5-step instructions, `open "chrome://extensions"` |
| `frontend/src/components/IntelligencePage.tsx` | Chrome Extension card with install button | VERIFIED | showExtensionInstructions state, extensionApiReachable state, /ping useEffect, "Install Chrome Extension" button, chrome://extensions instructions |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `engine/api.py` | `engine/capture.py` | `capture_note(source_type=)` | VERIFIED | Line 1526 passes `source_type=source_type or None` |
| `background.js` | `popup.js` | `chrome.storage.session pendingCapture` | VERIFIED | background.js sets, popup.js reads and removes on DOMContentLoaded |
| `popup.js` | `content.js` | `chrome.tabs.sendMessage extract-article` | VERIFIED | popup.js sendToContentScript() sends `{action: 'extract-article'}`; content.js handles it |
| `popup.js` | `http://127.0.0.1:37491` | `fetch POST /notes` | VERIFIED | popup.js:230 — `fetch(\`${currentApiUrl}/notes\`, {method: 'POST', ...})` |
| `content.js` | `background.js` | `chrome.runtime.sendMessage open-popup-gmail` | VERIFIED | content.js:164 sends; background.js:92 handles `msg.action === 'open-popup-gmail'` |
| `background.js` | `/ping` | `fetch polling every 30s via chrome.alarms` | VERIFIED | background.js:148 alarm named `api-status-check`, checkApiStatus() fetches `/ping` |
| `IntelligencePage.tsx` | user | inline instructions (chrome://extensions not openable) | VERIFIED | Line 313 comment: "chrome:// URLs cannot be opened from web pages"; instructions shown as text |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `popup.js` | `sb-body` textarea | `sendToContentScript` → `content.js extract-article` → Readability.js | Yes — Readability.parse() on live DOM | FLOWING |
| `popup.js` | `captureHistory` localStorage | `addToHistory()` called on successful save | Yes — actual save titles/types | FLOWING |
| `IntelligencePage.tsx` | `extensionApiReachable` | `fetch(/ping)` in useEffect | Yes — live HTTP response | FLOWING |
| `background.js` | badge state | `checkApiStatus()` via chrome.alarms fetching `/ping` | Yes — live HTTP response | FLOWING |

---

### Behavioral Spot-Checks

Step 7b: SKIPPED — Chrome extension requires a Chrome browser runtime to execute. No entry point is runnable without Chrome. Backend tests cover the engine side; extension-side behavior requires live Chrome verification (see Human Verification Required).

---

### Requirements Coverage

Phase 36 uses internal decision IDs (D-01 through D-17) defined in 36-CONTEXT.md. These are not present in REQUIREMENTS.md (which covers v3.0 GUI requirements). This is consistent with Phase 36 being part of the v4.0 milestone. The D-XX IDs are phase-internal requirements that are fully satisfied.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| D-01 | 36-02 | Four capture types: article, selection, Gmail, URL | SATISFIED | content.js + background.js + popup.js handle all four |
| D-02 | 36-02 | Icon click + context menu triggers only (no keyboard shortcut) | SATISFIED | manifest.json has no `commands` key; background.js creates menus in onInstalled |
| D-03 | 36-02 | No keyboard shortcut | SATISFIED | `commands` key absent from manifest.json |
| D-04 | 36-02 | Full-edit popup with title, body, type picker, tags, save/cancel | SATISFIED | popup.html and popup.js implement all fields with pre-suggestions |
| D-05 | 36-02 | Always show popup before saving (no silent capture) | SATISFIED | All flows go through popup; no background-only save path |
| D-06 | 36-02 | Full readable article via Readability.js, scrollable body | SATISFIED | content.js Readability extraction; popup.css textarea min-height:120px with scroll |
| D-07 | 36-03 | Gmail: context menu + injected button trigger surfaces | SATISFIED | background.js capture-gmail menu; content.js injectGmailButton() with MutationObserver |
| D-08 | 36-03 | Gmail: sender, recipients, subject, date, full body, source_url preserved | SATISFIED | extractGmailThread() in content.js; captureSourceType='gmail' in popup.js; pageUrl stored |
| D-09 | 36-04 | Badge on extension icon (red when unreachable) | SATISFIED | background.js setBadgeText('!') via chrome.alarms polling |
| D-10 | 36-04 | Popup inline status when sb-api down | SATISFIED | popup.js checkConnectivity() sets disconnected class, disables Save |
| D-11 | 36-04 | Capture history in popup, last 10 | SATISFIED | popup.js addToHistory/renderHistory, MAX_HISTORY=10, localStorage |
| D-12 | 36-02 | Options page: sb-api URL + default tags | SATISFIED | options.html + options.js with chrome.storage.sync |
| D-13 | 36-01 | CORS: add chrome-extension://* to Flask CORS | SATISFIED | engine/api.py:64 |
| D-14 | 36-01 | /smart-capture and /notes: accept source_url and source_type | SATISFIED | engine/api.py + engine/capture.py |
| D-15 | 36-01 | GET /ping health endpoint | SATISFIED | engine/api.py:146-148 |
| D-16 | 36-04 | setup.sh detects extension dir and prompts install | SATISFIED | setup.sh:90-111 |
| D-17 | 36-04 | GUI Intelligence page: install button + connection status | SATISFIED | IntelligencePage.tsx:285-324 |

**REQUIREMENTS.md note:** D-01 through D-17 are phase-internal decisions, not tracked in the global REQUIREMENTS.md traceability table. This is expected — they are the design decisions for Phase 36, defined in 36-CONTEXT.md, not versioned requirements from the v3.0/v4.0 requirements system. No orphaned requirements found.

---

### Anti-Patterns Found

Scanning was performed on all modified/created files. No blockers or critical stubs found.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `chrome-extension/popup.js` | 12 | `captureSourceType = 'web'` initial default | Info | Default value is overwritten for every real capture flow; only relevant if populateFromActiveTab() completes without setting type (acceptable fallback) |
| `chrome-extension/content.js` | 34-43 | Returns fallback `body.innerText.slice(0, 5000)` when Readability unavailable | Info | Intentional graceful fallback for Gmail path; not a stub |
| `chrome-extension/popup.js` | 63-74 | Falls back to page title + error message when article extraction fails | Info | Intentional fallback path; user can still save manually |

All three are intentional, documented fallback behaviors — not stubs. No blockers or warnings.

---

### Human Verification Required

The following behaviors cannot be verified without a live Chrome browser environment:

#### 1. Extension Load Verification

**Test:** Navigate to `chrome://extensions`, enable Developer mode, click "Load unpacked", select `chrome-extension/` directory in the project root.
**Expected:** Extension loads with no errors in the error log; "Second Brain Capture" appears in the extension list.
**Why human:** Chrome extension parsing, permission validation, and service worker startup require the Chrome browser runtime.

#### 2. Full Article Extraction via Readability.js

**Test:** Open any article page (e.g., a news article), click the extension icon.
**Expected:** Popup opens with article title in the title field and clean article text in the body (not raw HTML, not empty).
**Why human:** Readability.js DOM parsing, content script injection, and popup message passing require a live browser page.

#### 3. Selection Capture Flow

**Test:** Highlight text on any web page, right-click, select "Save Selection to Brain".
**Expected:** Popup opens with the selected text in the body field and the page title in the title field.
**Why human:** Context menu user gesture, selectionText forwarding, and popup pre-fill require live interaction.

#### 4. Link Capture Flow

**Test:** Right-click any hyperlink, select "Save Link to Brain".
**Expected:** Popup opens with the link URL in the body, type picker pre-set to "link".
**Why human:** Link context menu context requires live browser.

#### 5. Gmail Button Injection

**Test:** Open a Gmail thread. Observe the thread header area.
**Expected:** "Save to Brain" button appears. On SPA navigation to another thread, a fresh button appears with no duplicates.
**Why human:** Gmail MutationObserver, DOM injection, and SPA navigation require live Gmail session.

#### 6. Gmail Context Menu Capture

**Test:** Right-click inside a Gmail thread, select "Capture thread to Brain".
**Expected:** Popup opens pre-filled with email subject as title, formatted thread messages in body, type=meeting, tags=email.
**Why human:** Gmail DOM selectors (data-legacy-message-id, .a3s, [email] attributes) need live Gmail DOM to verify extraction quality.

#### 7. Connection Status Badge and Popup Inline Status

**Test:** Stop sb-api (run `launchctl stop com.secondbrain.api`), then click the extension icon.
**Expected:** Extension icon shows red "!" badge. Popup shows red status bar and "sb-api unreachable" message with Save button disabled.
**Why human:** badge polling, AbortSignal timeout behavior, and DOM disable state require live Chrome extension runtime.

#### 8. Capture History Persistence

**Test:** Save a note via the popup, close the popup, reopen it.
**Expected:** "Recent Captures" section visible with the just-saved entry including title, type badge, and "just now" timestamp.
**Why human:** localStorage in Chrome extension popup context persists per-extension-origin; cannot test without Chrome.

#### 9. Options Page

**Test:** Open extension Options page, change API URL, save. Open popup.
**Expected:** Popup uses the new API URL for the /ping check and for POST /notes.
**Why human:** chrome.storage.sync propagation to popup.js requires live extension context.

#### 10. setup.sh Install Prompt

**Test:** Run `./setup.sh` in the project root.
**Expected:** After other setup steps, "Chrome Extension" section appears; entering "y" prints 5-step instructions and opens chrome://extensions on macOS.
**Why human:** Interactive shell prompt and macOS `open` command behavior require manual execution.

---

### Gaps Summary

No code gaps found. All 17 requirements have full implementation evidence:

- Backend (D-13, D-14, D-15): /ping, CORS, source fields — all wired end-to-end with 4 tests
- Extension scaffold (D-01 to D-06, D-12): manifest, background, content, popup, options — all files exist, substantive, and wired
- Gmail integration (D-07, D-08): MutationObserver, button injection, thread extraction, context menu — all code present
- Rich UX (D-09, D-10, D-11): badge polling, popup status, history — all code present
- Installation UX (D-16, D-17): setup.sh section, IntelligencePage card — both present

The `human_needed` status is due to the nature of Chrome extensions: correctness of DOM extraction, gesture chains, and UI rendering cannot be verified by static code analysis alone. The code is complete; the extension needs loading in Chrome to confirm runtime behavior.

---

_Verified: 2026-03-25_
_Verifier: Claude (gsd-verifier)_
