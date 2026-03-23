# Phase 36: Chrome Extension Capture - Research

**Researched:** 2026-03-23
**Domain:** Chrome Extension Manifest V3, Readability.js, Flask-CORS, Gmail DOM injection
**Confidence:** HIGH (core MV3 patterns), MEDIUM (Gmail DOM selectors)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- D-01: Four capture types: full article (Readability.js), selected text, Gmail thread, URL+title
- D-02: Trigger model — icon click dropdown + right-click context menu only (no keyboard shortcut)
- D-03: Keyboard shortcut removed from scope entirely
- D-04: Full-edit popup — title, body preview, type picker dropdown, tags, save/cancel
- D-05: No silent/instant capture — always popup for confirmation before saving
- D-06: Readability.js full readable article (not truncated); scrollable body preview in popup
- D-07: Gmail — both context menu AND injected button in thread header
- D-08: Gmail extract: sender, recipients, subject, date, full thread body. Preserve Gmail URL as source_url
- D-09: Badge on extension icon — red/greyed when sb-api unreachable
- D-10: Popup inline status message when sb-api down
- D-11: Capture history in popup — last 10 captures in localStorage
- D-12: Options page — configure sb-api URL (default: localhost:37491), default tags
- D-13: CORS — add chrome-extension://* to Flask CORS origins in api.py
- D-14: /smart-capture and /capture endpoints: accept optional source_url and source_type → frontmatter
- D-15: Add GET /ping lightweight health endpoint
- D-16: setup.sh detect built extension dir, prompt to install, open chrome://extensions with instructions
- D-17: GUI Intelligence page gets "Install Chrome Extension" button + connection status display

### Claude's Discretion

- Exact popup layout/styling (vanilla CSS, no framework)
- Readability.js integration approach (content script vs. background)
- localStorage schema for capture history
- Gmail DOM selectors for injected button (implementation detail)
- DOMPurify sanitization level
- Exact frontmatter field ordering for source_url/source_type

### Deferred Ideas (OUT OF SCOPE)

- Firefox / Safari port
- Floating macOS capture widget (screenshot + OCR)
- Cloud sync / remote sb-api
- Auto-capture without user interaction
- Silent/instant capture
</user_constraints>

---

## Summary

This phase builds a Chrome Manifest V3 extension with no build system (vanilla JS, bundled vendor files). The extension posts to the existing sb-api at localhost:37491, extended with CORS and two new endpoints. Three sub-phases: scaffold+core capture, Gmail integration, rich UX (history, options, badges).

The dominant MV3 architectural pattern is: content script extracts page data → message to service worker → service worker opens popup (or popup polls service worker for pre-extracted data) → popup POSTs to sb-api. The key gotcha is `chrome.action.openPopup()` only works in response to user gestures — context menu clicks qualify, icon clicks are inherently user gestures.

Gmail DOM scraping is the highest-risk area. Gmail's DOM uses non-semantic class names that change without notice; the safest approach is to extract visible text via well-known structural attributes (`data-legacy-message-id`, `role="listitem"` for messages) rather than fragile class chains. A small MutationObserver is needed because Gmail is a SPA that swaps content without full page navigation.

**Primary recommendation:** No build toolchain. Download Readability.js and DOMPurify minified files into `chrome-extension/lib/`, declare in manifest content_scripts list. Popup is a plain HTML/CSS/JS file — no React, no bundler.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Chrome MV3 APIs | built-in | Extension platform | Only option for Chrome |
| @mozilla/readability | 0.6.0 | Article extraction from DOM | Mozilla's official library, industry standard for reader-mode |
| DOMPurify | 3.3.3 | Sanitize extracted HTML before display | Recommended by Readability.js docs; prevents XSS in popup |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| flask-cors | existing (in pyproject.toml) | Add chrome-extension://* origin | Already used in api.py line 64 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vanilla JS popup | React/Preact | React adds 100KB+ to extension, requires bundler, no benefit for ~3 screens |
| Bundled vendor files | npm + rollup | Rollup adds dev complexity; no CI for this sub-project; 2 vendor files is trivial |
| Custom article extractor | Readability.js | Readability handles 200+ edge cases; worth the ~100KB |

**Installation (no npm required — manual file copy at scaffold time):**
```bash
# Download into chrome-extension/lib/
curl -o chrome-extension/lib/Readability.js \
  https://cdn.jsdelivr.net/npm/@mozilla/readability@0.6.0/Readability.js
curl -o chrome-extension/lib/purify.min.js \
  https://cdn.jsdelivr.net/npm/dompurify@3.3.3/dist/purify.min.js
```

Alternatively: `npm pack @mozilla/readability dompurify` and copy from package contents — no node_modules left behind.

**Version verification (confirmed 2026-03-23):**
- `@mozilla/readability`: 0.6.0 (npm view)
- `dompurify`: 3.3.3 (npm view)

---

## Architecture Patterns

### Recommended Project Structure
```
chrome-extension/
├── manifest.json           # MV3 manifest
├── background.js           # Service worker — context menu setup, openPopup()
├── content.js              # Content script — page extraction, Gmail injection
├── popup.html              # Popup UI shell
├── popup.js                # Popup logic — fetch data, POST to sb-api
├── popup.css               # Popup styles (vanilla CSS)
├── options.html            # Options page
├── options.js              # Options logic (save/load from chrome.storage.sync)
├── icons/
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── lib/
    ├── Readability.js      # Vendor — bundled directly
    └── purify.min.js       # Vendor — bundled directly
```

### Pattern 1: MV3 Manifest Structure
**What:** manifest.json declares permissions, content scripts, service worker, popup
**When to use:** Always — this is the required entrypoint

```json
// Source: https://developer.chrome.com/docs/extensions/develop/migrate/what-is-mv3
{
  "manifest_version": 3,
  "name": "Second Brain Capture",
  "version": "1.0.0",
  "permissions": ["contextMenus", "activeTab", "scripting", "storage"],
  "host_permissions": ["http://127.0.0.1/*", "https://mail.google.com/*"],
  "background": { "service_worker": "background.js" },
  "action": {
    "default_popup": "popup.html",
    "default_icon": { "16": "icons/icon16.png", "48": "icons/icon48.png" }
  },
  "options_page": "options.html",
  "content_scripts": [{
    "matches": ["<all_urls>"],
    "js": ["lib/Readability.js", "lib/purify.min.js", "content.js"],
    "run_at": "document_idle"
  }],
  "web_accessible_resources": [{
    "resources": ["lib/*"],
    "matches": ["<all_urls>"]
  }]
}
```

**Gmail content script needs separate entry with `"run_at": "document_start"`** and matches `"https://mail.google.com/*"` so the MutationObserver is registered before Gmail's SPA boots.

### Pattern 2: Context Menu → Popup Flow (the critical MV3 pattern)

**What:** Context menu click triggers data extraction then opens popup with pre-fetched data
**Why this matters:** `chrome.action.openPopup()` requires a user gesture — context menu click qualifies. Popup cannot fetch data itself because by the time it opens, the original context is gone.

```javascript
// background.js (service worker)
// Source: https://developer.chrome.com/docs/extensions/develop/ui/context-menu

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "capture-page",
    title: "Save Page to Brain",
    contexts: ["page"]
  });
  chrome.contextMenus.create({
    id: "capture-selection",
    title: "Save Selection to Brain",
    contexts: ["selection"]
  });
  chrome.contextMenus.create({
    id: "capture-link",
    title: "Save Link to Brain",
    contexts: ["link"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  // Store capture context BEFORE opening popup
  await chrome.storage.session.set({
    pendingCapture: {
      menuItemId: info.menuItemId,
      selectionText: info.selectionText,
      linkUrl: info.linkUrl,
      pageUrl: tab.url,
      pageTitle: tab.title,
    }
  });
  // Then open popup — this works because context menu click IS a user gesture
  await chrome.action.openPopup();
});
```

```javascript
// popup.js — reads pending capture on open
document.addEventListener('DOMContentLoaded', async () => {
  const { pendingCapture } = await chrome.storage.session.get('pendingCapture');
  if (pendingCapture) {
    await chrome.storage.session.remove('pendingCapture');
    populateForm(pendingCapture);
  } else {
    // icon click — extract current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    await requestExtraction(tab);
  }
});
```

### Pattern 3: Content Script Data Extraction

**What:** Content script runs Readability.js in page context, returns structured data to popup via message passing.
**When to use:** For full article capture; selection capture uses `window.getSelection()` directly.

```javascript
// content.js
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'extract-article') {
    const docClone = document.cloneNode(true);
    const reader = new Readability(docClone);
    const article = reader.parse();
    sendResponse({
      title: article?.title || document.title,
      textContent: article?.textContent || '',
      excerpt: article?.excerpt || '',
      url: location.href,
    });
  }
  return true; // keep message channel open for async sendResponse
});
```

**Note:** Readability.js must be listed BEFORE content.js in manifest content_scripts array — it loads in order, so `Readability` global is available when content.js runs.

### Pattern 4: Extension Icon Badge for API Status

```javascript
// background.js — poll sb-api every 30s
async function checkApiStatus() {
  try {
    const res = await fetch('http://127.0.0.1:37491/ping', { signal: AbortSignal.timeout(2000) });
    if (res.ok) {
      chrome.action.setBadgeText({ text: '' });
      chrome.action.setIcon({ path: 'icons/icon48.png' });
    } else { setOfflineBadge(); }
  } catch { setOfflineBadge(); }
}

function setOfflineBadge() {
  chrome.action.setBadgeText({ text: '!' });
  chrome.action.setBadgeBackgroundColor({ color: '#cc0000' });
}
```

### Pattern 5: localStorage History Schema

```javascript
// popup.js
const MAX_HISTORY = 10;
function addToHistory(entry) {
  const history = JSON.parse(localStorage.getItem('captureHistory') || '[]');
  history.unshift({ ...entry, savedAt: new Date().toISOString() });
  localStorage.setItem('captureHistory', JSON.stringify(history.slice(0, MAX_HISTORY)));
}
```

**Note:** localStorage is popup-context only. Popup gets a fresh context each time it opens, but localStorage persists across popup opens. This is appropriate for capture history per D-11.

### Anti-Patterns to Avoid

- **Service worker global state:** Variables in `background.js` are lost when service worker sleeps (every 5 min idle). Use `chrome.storage.session` (cleared on browser restart) or `chrome.storage.local` (persists) for any state that must survive. The `pendingCapture` approach above uses `chrome.storage.session`.
- **Direct fetch() in service worker to non-HTTPS:** Works because it's localhost but note that `fetch` in service workers has no DOM context — no `document`, no `window`. Always verify CORS headers are returned correctly by sb-api.
- **Injecting Readability into page context:** Do NOT use `scripting.executeScript` to inject Readability into the actual page DOM — that breaks page isolation. Run it in the content script isolated context via the content_scripts manifest declaration.
- **Synchronous chrome API calls:** All chrome.* APIs in MV3 are async/Promise-based. Never assume callbacks; use `await`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Article extraction | Custom DOM scraper | Readability.js | Handles ads, nav, sidebar, lazy-load, pagination, 200+ site quirks |
| HTML sanitization | Custom regex strip | DOMPurify | Regex misses mutation XSS, nested tags, SVG/MathML vectors |
| Gmail DOM parsing | Custom attribute walking | MutationObserver + data-legacy-message-id | Gmail re-renders constantly; need observer pattern |

**Key insight:** Readability.js is ~130KB but battle-tested across millions of pages. Custom article extractors always fail on edge cases within the first week of real use.

---

## Runtime State Inventory

> Phase is greenfield (new chrome-extension/ directory). No renames or migrations.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — new extension, no prior data | None |
| Live service config | sb-api on port 37491 — already running | Add /ping endpoint, update CORS origins |
| OS-registered state | launchd plist `second-brain.api` — runs sb-api | No change; sb-api gets new endpoints |
| Secrets/env vars | None | None |
| Build artifacts | No prior extension build artifacts | None |

---

## Common Pitfalls

### Pitfall 1: chrome.action.openPopup() Silently Fails
**What goes wrong:** `openPopup()` called outside user gesture context → no error thrown, popup just doesn't open.
**Why it happens:** Chrome restricts programmatic popup opening to user gesture scope. Service worker context menu handler IS a user gesture scope, but any subsequent async await before calling openPopup() can break the gesture chain in older Chrome versions.
**How to avoid:** Call `chrome.action.openPopup()` as the LAST thing in the context menu handler, after storing pendingCapture data. Don't chain awaits before it if avoidable.
**Warning signs:** Popup opens when clicking icon but not from context menu.

### Pitfall 2: Service Worker Wakes Up Without Context
**What goes wrong:** User right-clicks, context menu fires, but service worker was sleeping → it restarts, but event handlers registered at module scope are re-registered via `onInstalled` only at install time. Context menu items need to be re-created.
**Why it happens:** `onInstalled` fires once at install, not on service worker wake. Context menu `create()` calls must be idempotent (use `update()` if item exists, or wrap in try-catch).
**How to avoid:** Always use `chrome.contextMenus.create()` inside `onInstalled`. Context menus persist in Chrome's registry — they survive service worker sleep cycles. Only the in-memory event listener registration (`.onClicked.addListener`) needs to be at module scope (top-level of background.js), which re-runs on every service worker wake.
**Warning signs:** Context menu items appear twice, or clicks do nothing after browser restart.

### Pitfall 3: Gmail DOM Selectors Break Without Warning
**What goes wrong:** Gmail pushes a UI update, injected button disappears or script errors.
**Why it happens:** Gmail uses obfuscated class names that change on deploy. No public DOM API guarantee.
**How to avoid:** Target structural/semantic attributes: `data-legacy-message-id` for message containers, `role="main"` for the thread view, `[data-thread-id]` on the thread root. Avoid `.a3s`, `.g6`, etc. — those are minified and will change.
**Warning signs:** `querySelector` returns null; MutationObserver fires but button injection silently no-ops.

### Pitfall 4: Content Script Multiple Registration
**What goes wrong:** Navigating within Gmail triggers content script re-injection, multiple "Save to Brain" buttons appear in thread header.
**Why it happens:** Gmail is a SPA — navigation doesn't reload the page. content.js is injected once per page load, but the MutationObserver fires on every thread open. Button injection logic doesn't guard against existing buttons.
**How to avoid:** Before injecting the button, check `document.querySelector('#sb-gmail-btn')` and skip if already present. Use a sentinel attribute.
**Warning signs:** Multiple "Save to Brain" buttons stacked in thread header.

### Pitfall 5: CORS with chrome-extension:// Origin
**What goes wrong:** Extension fetch to sb-api returns CORS error even after adding origin to Flask.
**Why it happens:** `chrome-extension://` is a valid origin but each extension install gets a unique extension ID. The origin looks like `chrome-extension://abcdef1234567890...` — exact ID varies by machine.
**How to avoid:** Use `"chrome-extension://*"` wildcard in Flask CORS origins (D-13 decision). Flask-CORS supports wildcard matching. Since sb-api is localhost-only, the security tradeoff is acceptable.
**Warning signs:** Network tab shows CORS preflight failing; `Access-Control-Allow-Origin` missing from response.

### Pitfall 6: `return true` in content script message listener
**What goes wrong:** Popup sends message to content script and never gets a response; popup hangs.
**Why it happens:** Chrome closes the message channel after the listener returns. If response is async, must return `true` to keep channel open.
**How to avoid:** Always `return true` in any `onMessage` listener that calls `sendResponse` asynchronously (including any async function body).
**Warning signs:** Console error "The message port closed before a response was received."

---

## Code Examples

### /ping Endpoint (Flask)
```python
# engine/api.py — add near /health endpoint
@app.get("/ping")
def ping():
    return jsonify({"ok": True})
```

### CORS Update (api.py line 64)
```python
# Before:
CORS(app, origins=["null", "file://*", "http://127.0.0.1:*"])
# After:
CORS(app, origins=["null", "file://*", "http://127.0.0.1:*", "chrome-extension://*"])
```

### smart-capture with source_url/source_type (api.py)
```python
# In smart_capture() — extract new optional fields from request body
source_url = data.get("source_url", "")
source_type = data.get("source_type", "")  # "article" | "selection" | "gmail" | "link"

# Pass to capture_note() — needs url= param, and source_type in frontmatter
path = capture_note(
    note_type=seg["type"], title=seg["title"], body=seg["body"],
    tags=[], people=seg.get("entities", {}).get("people", []),
    content_sensitivity="public", brain_root=BRAIN_ROOT, conn=conn,
    url=source_url or None,
    # source_type written as extra frontmatter — requires capture.py extension
)
```

**Note:** `capture_note()` already has a `url=` parameter (written to frontmatter as `url:`). `source_type` is a new field — `build_post()` or the caller will need to set it on the frontmatter post object.

### Gmail MutationObserver for thread detection
```javascript
// content.js (gmail section)
const observer = new MutationObserver(() => {
  const threadView = document.querySelector('[data-thread-id]');
  if (threadView && !document.querySelector('#sb-gmail-btn')) {
    injectGmailButton(threadView);
  }
});
observer.observe(document.body, { childList: true, subtree: true });

function injectGmailButton(threadView) {
  const btn = document.createElement('button');
  btn.id = 'sb-gmail-btn';
  btn.textContent = 'Save to Brain';
  btn.onclick = () => {
    chrome.runtime.sendMessage({ action: 'capture-gmail', threadId: threadView.dataset.threadId });
  };
  // Target: thread header toolbar area
  const toolbar = threadView.querySelector('[role="toolbar"]') || threadView;
  toolbar.prepend(btn);
}
```

### Options Page Storage Pattern
```javascript
// options.js
const DEFAULT_API_URL = 'http://127.0.0.1:37491';

async function loadOptions() {
  const { apiUrl, defaultTags } = await chrome.storage.sync.get({
    apiUrl: DEFAULT_API_URL,
    defaultTags: '',
  });
  document.getElementById('apiUrl').value = apiUrl;
  document.getElementById('defaultTags').value = defaultTags;
}

async function saveOptions() {
  await chrome.storage.sync.set({
    apiUrl: document.getElementById('apiUrl').value.trim() || DEFAULT_API_URL,
    defaultTags: document.getElementById('defaultTags').value.trim(),
  });
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| background.js persistent page (MV2) | background.js as Service Worker (MV3) | Chrome 88+, enforced 2023 | No global state between events; must use chrome.storage |
| `chrome.browserAction` | `chrome.action` (unified) | MV3 | Single API for toolbar button |
| Remote code execution allowed | All code must be in extension bundle | MV3 | No CDN script tags; must bundle vendor files |
| `chrome.tabs.executeScript` | `chrome.scripting.executeScript` | MV3 | New API, stricter permissions model |

**Deprecated/outdated:**
- `"manifest_version": 2`: Chrome stopped accepting MV2 extensions in Chrome Web Store (June 2024). Local developer installs still work but MV3 is required.
- `"browser_action"` / `"page_action"` manifest keys: replaced by `"action"` in MV3.
- XMLHttpRequest in service workers: use `fetch()` instead.

---

## Open Questions

1. **source_type in capture.py frontmatter**
   - What we know: `capture_note()` has `url=` param; `build_post()` writes it as `url:` frontmatter field
   - What's unclear: Is there a clean hook to pass arbitrary extra frontmatter fields, or does `build_post()` need a new `source_type=` param?
   - Recommendation: Add `source_type: str | None = None` param to `capture_note()` and `build_post()` — same pattern as existing `url=`. Minimal change.

2. **Gmail: exact toolbar selector stability**
   - What we know: `role="toolbar"` and `[data-thread-id]` are semantic attributes that tend to be more stable
   - What's unclear: Gmail may have changed thread header structure since mid-2025; actual selector needs live verification when implementing
   - Recommendation: Plan 36-02 (Gmail) should include a manual verification step: open Gmail, inspect DOM, confirm selector before coding.

3. **chrome.action.openPopup() in Chrome 120+**
   - What we know: The API exists and works in response to user gestures (confirmed by multiple sources)
   - What's unclear: Exact Chrome version floor for reliable behavior — some sources mention Chrome 99+ for initial availability, wider reliability post-Chrome 108
   - Recommendation: Add a manifest `"minimum_chrome_version": "108"` to be safe. This is well below current stable (Chrome 120+).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | npm view for versions | ✓ | v22.22.1 | — |
| npm | package downloads | ✓ | 11.12.0 | — |
| Chrome browser | Extension testing | assumed ✓ | unknown | Cannot test without |
| sb-api (port 37491) | Extension → API | assumed ✓ | — | Extension shows offline badge |

**Missing dependencies with no fallback:**
- Chrome browser must be available on host for any manual testing/install verification.

**Missing dependencies with fallback:**
- sb-api not running → extension shows red badge (designed behavior).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pyproject.toml (existing) |
| Quick run command | `uv run pytest tests/test_api.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

Backend changes (Plans 36-01 and part of 36-03) are testable with pytest. The extension itself (JS) has no automated test framework — manual testing and Playwright are the verification path.

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| GET /ping returns 200 {"ok": true} | unit | `uv run pytest tests/test_api.py -k "test_ping" -x` | ❌ Wave 0 |
| CORS allows chrome-extension:// origin | unit | `uv run pytest tests/test_api.py -k "test_cors_extension" -x` | ❌ Wave 0 |
| POST /smart-capture accepts source_url field | unit | `uv run pytest tests/test_api.py -k "test_smart_capture_source_url" -x` | ❌ Wave 0 |
| POST /notes accepts source_url, writes to frontmatter | unit | `uv run pytest tests/test_api.py -k "test_notes_source_url" -x` | ❌ Wave 0 |
| Extension popup renders — visual check | manual | open popup in Chrome | N/A |
| Context menu items appear on right-click | manual | right-click in Chrome | N/A |
| Gmail button injects into thread header | manual | open Gmail thread | N/A |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_api.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api.py` — add test cases: `test_ping`, `test_cors_extension_origin`, `test_smart_capture_source_url`, `test_notes_source_url`

---

## Sources

### Primary (HIGH confidence)
- https://developer.chrome.com/docs/extensions/develop/migrate/what-is-mv3 — MV3 architecture overview
- https://developer.chrome.com/docs/extensions/develop/ui/context-menu — context menu API
- https://developer.chrome.com/docs/extensions/reference/api/action — chrome.action.openPopup()
- https://developer.chrome.com/docs/extensions/reference/api/contextMenus — contextMenus API
- https://github.com/mozilla/readability — Readability.js 0.6.0 (verified via npm)
- https://github.com/cure53/DOMPurify — DOMPurify 3.3.3 (verified via npm)
- engine/api.py — CORS config at line 64, /smart-capture at line 1483, /notes at line 889
- engine/capture.py — capture_note() url= param at line 458, TYPE_TO_DIR at line 15

### Secondary (MEDIUM confidence)
- https://developer.chrome.com/docs/extensions/develop/migrate/to-service-workers — service worker migration guide
- https://github.com/KartikTalwar/gmail.js — Gmail DOM patterns (data-legacy-message-id, MutationObserver approach)
- https://www.extension.ninja/blog/post/solved-this-function-must-be-called-during-a-user-gesture/ — openPopup user gesture

### Tertiary (LOW confidence)
- WebSearch findings on Gmail DOM selectors — selectors need live verification at implementation time; Gmail DOM changes without announcement

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified via npm registry
- Architecture: HIGH — based on official Chrome developer docs
- Flask backend changes: HIGH — based on direct code reading of api.py and capture.py
- Gmail DOM patterns: MEDIUM — structural attributes more stable than class names, but unverified against current Gmail
- Pitfalls: HIGH — based on MV3 official docs + known patterns

**Research date:** 2026-03-23
**Valid until:** 2026-06-23 (MV3 APIs stable; Gmail DOM LOW confidence item re-verify before Plan 36-02)
