# Phase 36: Chrome Extension Capture — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 36-chrome-extension-capture
**Areas discussed:** Use cases, Popup UI, Note type, Gmail, Sub-phase scope, Article extraction, Keyboard shortcut, Capture history/options, Connection status UX

---

## Use Cases

| Option | Description | Selected |
|--------|-------------|----------|
| Articles / blog posts | Readability.js extraction | ✓ |
| Selected text snippets | Highlight + source URL | ✓ |
| Gmail threads | Full thread with metadata | ✓ |
| URL + title (link) | Bookmark-style minimal capture | ✓ |

**User's choice:** All 4. Also explicitly requested right-click context menu for text selections and links.

---

## Popup UI

| Option | Description | Selected |
|--------|-------------|----------|
| Quick confirm — title + tags | AI pre-classifies, fast review | |
| Full edit — see & edit body too | Title, body preview, type, tags | ✓ |
| Silent capture — no popup on context menu | Saves immediately | |

**User's choice:** Full edit popup with title, body preview, type picker, and tags.

---

## Note Type Assignment

| Option | Description | Selected |
|--------|-------------|----------|
| Always 'link' for URL captures | Consistent with Phase 29 | |
| Let smart-capture decide | Auto-classify | |
| User picks in popup | Dropdown in popup | ✓ |

**User's choice:** User picks in popup. Pre-suggest based on context (link for URL-only, note for text, etc.).

---

## Gmail Capture Method

| Option | Description | Selected |
|--------|-------------|----------|
| Context menu only | Right-click, simpler | |
| Injected button in Gmail UI | More discoverable | |
| Both | Context menu + injected button | ✓ |

**User's choice:** Both — context menu AND injected button in Gmail thread header.

---

## Sub-phase Scope

| Option | Description | Selected |
|--------|-------------|----------|
| All 3 sub-phases must ship | 36-01 + 36-02 + 36-03 all in v4.0 | ✓ |
| 36-01 + 36-02, 36-03 optional | Polish deferred | |
| Only 36-01 must ship | Core only | |

**User's choice:** All 3 sub-phases in v4.0.

---

## Article Extraction Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Full readable article via Readability.js | Clean article text | ✓ |
| User-selected text only | Minimal and precise | |
| Readable article + user can trim in popup | Most flexible | |

**User's choice:** Full readable article via Readability.js.

---

## Keyboard Shortcut

| Option | Description | Selected |
|--------|-------------|----------|
| Cmd+Shift+B (from plan) | Conflicts — Chrome bookmarks bar | |
| Cmd+B | Conflicts — Chrome bookmarks bar | |
| Cmd+Shift+C | Conflicts — Chrome DevTools inspector | |
| No shortcut — icon + context menu | ✓ |

**User's choice:** No keyboard shortcut. Extension icon click → dropdown of actions. Right-click → context menu.
**Notes:** Multiple shortcuts considered (Cmd+B, Cmd+Shift+B, Cmd+Shift+C) all conflict with Chrome built-ins. User decided to drop shortcut entirely in favour of icon dropdown + context menu.

---

## Capture History & Options Page

| Option | Description | Selected |
|--------|-------------|----------|
| Both needed in v4.0 | History + options page | ✓ |
| Options page only | Port config, no history | |
| Defer both | Hard-code URL, no history UI | |

**User's choice:** Both needed — capture history (last 10, localStorage) and options page (sb-api URL config).

---

## Connection Status UX

| Option | Description | Selected |
|--------|-------------|----------|
| Badge on extension icon | Red badge when sb-api down | ✓ |
| Warning banner in popup only | Normal icon, red bar in popup | |
| Both — badge + banner | Full awareness | |

**User's choice:** Badge on extension icon. (Popup will also show inline message when trying to capture while api is down — implementation detail.)

---

## Claude's Discretion

- Exact popup layout/styling
- Readability.js content script integration approach
- localStorage schema for capture history
- Gmail DOM selectors for injected button
- DOMPurify sanitization level
- Frontmatter field ordering for source_url/source_type

## Deferred Ideas

- Firefox/Safari port
- Floating macOS capture widget (screenshot + OCR)
- Cloud sync / remote sb-api
- Auto-capture without user interaction
- Silent/instant capture (no popup)
