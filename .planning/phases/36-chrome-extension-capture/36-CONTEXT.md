# Phase 36: Chrome Extension Capture — Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a Chrome Manifest V3 extension that captures web pages (full article via Readability.js), selected text snippets, Gmail threads, and bare URL+title links directly into the second brain via the existing sb-api. All three sub-phases (scaffold+capture, Gmail, rich UX) ship in v4.0.

</domain>

<decisions>
## Implementation Decisions

### A — Use Cases & Capture Surfaces

- **D-01:** Four capture types in scope:
  1. **Full article** — Readability.js extraction of readable page content
  2. **Selected text snippet** — highlighted passage + source URL
  3. **Gmail thread** — sender, recipients, subject, date, full thread body
  4. **URL / link** — page title + URL only (bookmark-style)
- **D-02:** Trigger model — **no keyboard shortcut**. Two surfaces only:
  - **Extension icon click** → dropdown of actions (capture page, capture selection, open options)
  - **Right-click context menu** → "Save to Brain" appears on: text selection, links (right-click on a hyperlink), and page background (capture whole page)
- **D-03:** Keyboard shortcut removed from 36-03 scope entirely (conflict risk with Chrome built-ins Cmd+Shift+B/C etc.).

### B — Popup UI

- **D-04:** Full-edit popup — user sees and can edit before saving:
  - Title (pre-filled from page `<title>` or selection/thread subject)
  - Body preview (truncated, editable)
  - **Type picker dropdown** — user selects note type; pre-suggest based on context:
    - URL-only capture → pre-suggest `link`
    - Text selection → pre-suggest `note`
    - Gmail thread → pre-suggest `meeting` or `note`
    - Full article → pre-suggest `note`
  - Tags field
  - Save / Cancel buttons
- **D-05:** No silent/instant capture — always open popup for user confirmation before saving.

### C — Article Extraction

- **D-06:** Full readable article via Readability.js — clean article text as note body. Not truncated or meta-only. User sees full extracted content in popup (scrollable body preview).

### D — Gmail Capture

- **D-07:** Both trigger surfaces for Gmail:
  - Context menu (right-click in Gmail → "Capture thread to Brain")
  - Injected "Save to Brain" button in the Gmail thread header UI
- **D-08:** Extract: sender, recipients, subject, date, full thread body (multi-message). Preserve Gmail URL as `source_url` in frontmatter.

### E — Connection Status

- **D-09:** Badge on extension icon — red badge / greyed icon when sb-api unreachable, normal when connected. Visible without opening popup.
- **D-10:** Popup also shows inline status message if sb-api is down when user tries to capture.

### F — Capture History & Options

- **D-11:** Capture history in popup — last 10 captures (stored in localStorage).
- **D-12:** Options page — configure sb-api URL (default: `localhost:37491`), default tags if desired.

### G — Backend Changes

- **D-13:** CORS: add `chrome-extension://*` to Flask CORS origins in `api.py` (currently: `"null", "file://*", "http://127.0.0.1:*"`).
- **D-14:** `/smart-capture` and `/capture` endpoints: accept optional `source_url` and `source_type` fields → write to note frontmatter.
- **D-15:** Add `GET /ping` lightweight health endpoint for extension connection check.

### H — Setup & Installation

- **D-16:** `setup.sh` should detect the built extension directory and prompt the user to install it in Chrome developer mode. If user agrees, open `chrome://extensions` and display step-by-step instructions (can't auto-install — Chrome security prevents it). Installation steps: enable Developer Mode → "Load unpacked" → point to `chrome-extension/` directory.
- **D-17:** GUI (Settings or Intelligence page) gets an "Install Chrome Extension" button that opens `chrome://extensions` and shows the same step-by-step instructions inline. Should also show current connection status (sb-api reachable from browser context) so the user can confirm the extension will work after install.

### Claude's Discretion

- Exact popup layout/styling (vanilla CSS, no framework)
- Readability.js integration approach (content script vs. background)
- localStorage schema for capture history
- Gmail DOM selectors for injected button (implementation detail)
- DOMPurify sanitization level
- Exact frontmatter field ordering for `source_url`/`source_type`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend API
- `engine/api.py` — Flask API; CORS config at line 64; `/smart-capture` at line 1483; add `/ping` here
- `engine/capture.py` — `capture_note()` entry point; all captures go through here

### Existing patterns
- `.planning/phases/29-add-link-capture/29-CONTEXT.md` — `link` note type decisions: `url:` frontmatter field, `links/` subfolder, filename pattern
- `engine/paths.py` — `BRAIN_ROOT`, `DB_PATH` canonical paths

### Extension
- No external specs — requirements fully captured in decisions above

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `/smart-capture` endpoint (`engine/api.py:1483`) — accepts `content`, returns segmented notes. Extend with `source_url`, `source_type`.
- `/capture` endpoint — standard single-note capture. Also needs `source_url`.
- Phase 29's `link` note type — already has `url:` frontmatter and `links/` folder mapping; extension should reuse this.

### Established Patterns
- CORS via `flask_cors.CORS` — already in place, just add `chrome-extension://*` to origins list.
- `source_url` concept exists in link notes (Phase 29) — consistent with storing origin URL in frontmatter.

### Integration Points
- Extension POSTs to `localhost:37491/smart-capture` (segmented/classified) or `/capture` (typed directly)
- New `GET /ping` endpoint needed — not currently present in `api.py`

</code_context>

<specifics>
## Specific Ideas

- Extension icon dropdown (not a traditional popup-on-icon) as the primary action surface
- Pre-suggest note type in popup based on what was captured — user still has final say
- Gmail injected button goes in thread header (not a floating overlay)

</specifics>

<deferred>
## Deferred Ideas

- Firefox / Safari port — future phase
- Floating macOS capture widget (screenshot + OCR from any app) — future phase
- Cloud sync / remote sb-api — would require auth, separate phase
- Auto-capture without user interaction — explicitly out of scope
- Silent/instant capture (no popup) — decided against for v4.0

</deferred>

---

*Phase: 36-chrome-extension-capture*
*Context gathered: 2026-03-23*
