---
phase: 20-frontend-bug-fixes
verified: 2026-03-16T14:00:00Z
status: human_needed
score: 7/8 must-haves verified
re_verification: false
human_verification:
  - test: "Open a long note in the GUI and scroll with the mouse wheel"
    expected: "Note content scrolls in the viewer panel; no clipping or stuck scroll"
    why_human: "CSS scroll behavior (min-height: 0 on flex chain) cannot be verified without a live browser/pywebview render"
  - test: "Click Edit on a note — EasyMDE editor should fill available height"
    expected: "Editor fills center panel height; no layout breakage or clipped toolbar"
    why_human: "EasyMDE flex-chain fix (.EasyMDEContainer, .CodeMirror min-height: 0) requires visual inspection in pywebview"
  - test: "Open any note — confirm markdown renders as HTML (headings, bold, lists visible)"
    expected: "Formatted HTML output in viewer, no raw markdown or YAML frontmatter visible"
    why_human: "marked.js rendering (vendored offline) confirmed by human in plan 03, but cannot be re-verified programmatically"
---

# Phase 20: Frontend Bug Fixes — Verification Report

**Phase Goal:** The GUI viewer is fully usable — note content renders as HTML, scrolls normally, displays correct backlinks, and title changes reflect without restart
**Verified:** 2026-03-16
**Status:** human_needed (all automated checks pass; 3 visual/UX items need human sign-off)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Opening a note in the viewer shows formatted HTML — no YAML frontmatter block visible | ? HUMAN | `read_note` returns `body` via `_fm.loads(raw).content` (api.py:86-87); marked.js vendored and loaded (index.html:67, vendor/marked.min.js 36KB); null-guard in renderMarkdown (app.js:69-74); human confirmed in plan 03 |
| 2 | After editing and saving a note title, the sidebar reflects the new title without restart | ✓ VERIFIED | `save_note` runs `UPDATE notes SET title=?, updated_at=?` (api.py:126-131); `saveNote()` calls `loadNotes()` then restores active state (app.js:128-132); `TestSaveNote.test_save_note_updates_sqlite_title` passes |
| 3 | Saving a note does not lose its frontmatter (title, tags, type fields survive round-trip) | ✓ VERIFIED | editor fetches `?raw=true` → full content in EasyMDE (app.js:87-88); PUT sends full `easyMDE.value()` (app.js:124); `TestSaveNote.test_save_note_preserves_frontmatter` passes |
| 4 | SQLite notes.title is updated immediately after a PUT save | ✓ VERIFIED | `save_note` parses saved file via `_fm.loads`, extracts title, executes UPDATE before returning (api.py:121-131); `test_save_note_updates_sqlite_title` confirms title == "New Title" |
| 5 | Backlinks shown are notes whose body text actually mentions the current note's title | ✓ VERIFIED | `note_meta` uses `LOWER(body) LIKE LOWER(?)` with `f"%{title_row['title']}%"` (api.py:169-173); `test_backlinks_content_match` and `test_backlinks_case_insensitive` pass |
| 6 | No false positives — notes not shown as backlinks due to filename similarity alone | ✓ VERIFIED | query matches body column only, not path column; `test_backlinks_no_false_positive` confirms note_c (filename contains "alice") is excluded |
| 7 | User can scroll a long note in the viewer panel using the mouse wheel | ? HUMAN | `#center` has `min-height: 0` (style.css:14); `#viewer` has `min-height: 0` + `overflow-y: auto` (style.css:17); plan 03 human checkpoint approved — cannot re-verify without live GUI |
| 8 | EasyMDE editor layout is not broken by the scroll fix | ? HUMAN | `.EasyMDEContainer` and `.CodeMirror` both have `min-height: 0` (style.css:20-21); plan 03 human checkpoint approved — visual check required |

**Score:** 5/8 truths fully automated-verified + 3 human-confirmed in plan 03 = 7/8 effectively verified (1 truth split across human items 1 and 3 above)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/api.py` | `read_note` strips frontmatter; `save_note` updates SQLite; `?raw=true` param | ✓ VERIFIED | Contains `import frontmatter as _fm`; `_fm.loads(raw)` in `read_note` (line 86); `UPDATE notes SET title` in `save_note` (line 127); `request.args.get("raw")` branch (line 84) |
| `engine/api.py` | `note_meta` uses `LOWER(body) LIKE LOWER` instead of path match | ✓ VERIFIED | Lines 169-173: `LOWER(body) LIKE LOWER(?)` with title bind param; old `fname = p.name` / `path LIKE` pattern fully replaced |
| `engine/gui/static/app.js` | `openNote` reads `body` key; `enterEditMode` fetches `?raw=true`; `saveNote` calls `loadNotes()` | ✓ VERIFIED | Line 56: `const { body }` from default fetch; line 87: `?raw=true` fetch; line 88: `const { content }`; lines 128-132: `loadNotes()` + active state restore |
| `engine/gui/static/style.css` | `min-height: 0` on `#center` and `#viewer` | ✓ VERIFIED | Line 14: `#center { ... min-height: 0; }`; line 17: `#viewer { ... min-height: 0; ... }` |
| `engine/gui/static/style.css` | `min-height: 0` on `.EasyMDEContainer` and `.CodeMirror` | ✓ VERIFIED | Line 20: `.EasyMDEContainer { ... min-height: 0; ... }`; line 21: `.CodeMirror { ... min-height: 0; ... }` |
| `engine/gui/static/vendor/marked.min.js` | Vendored marked.js for offline rendering | ✓ VERIFIED | File exists at 36,054 bytes |
| `engine/gui/static/index.html` | `save-error` span; loads marked.min.js before easymde | ✓ VERIFIED | Line 29: `<span id="save-error" ...>`; line 67: `/ui/vendor/marked.min.js` loaded |
| `tests/test_api.py` | `TestReadNote` (body key, raw param), `TestSaveNote`, `TestNoteMeta` classes | ✓ VERIFIED | All three classes present; `tmp_note` and `tmp_note_pair` fixtures present; 18/18 tests pass |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `engine/api.py read_note` | `python-frontmatter` | `_fm.loads(raw).content` | ✓ WIRED | `import frontmatter as _fm` (line 14); `post = _fm.loads(raw)` (line 86); `post.content` returned as `body` |
| `engine/api.py save_note` | SQLite notes table | `UPDATE notes SET title=?, updated_at=? WHERE path=?` | ✓ WIRED | Lines 126-131: conn.execute with UPDATE pattern; conn.commit() called |
| `engine/gui/static/app.js enterEditMode` | `engine/api.py read_note` | `fetch with ?raw=true` | ✓ WIRED | Line 87: `fetch(\`${API}/notes/${encodeURIComponent(currentPath)}?raw=true\`)` |
| `engine/api.py note_meta` | SQLite notes table body column | `LOWER(body) LIKE LOWER('%' || title || '%')` | ✓ WIRED | Lines 169-173: parameterized query with `f"%{title_row['title']}%"` bind |
| `style.css #center` | `#viewer scroll behavior` | `min-height: 0 allows flex child to scroll` | ✓ WIRED | Both `#center` and `#viewer` have `min-height: 0`; `#viewer` has `overflow-y: auto` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GUIX-02 | 20-01-PLAN.md | Title edits made in the GUI are reflected immediately without restart | ✓ SATISFIED | `save_note` runs SQLite UPDATE; `saveNote()` calls `loadNotes()`; `test_save_note_updates_sqlite_title` passes |
| GUIX-03 | 20-01-PLAN.md | Note content renders as formatted HTML (not raw markdown text) | ✓ SATISFIED | `read_note` strips frontmatter and returns `body`; marked.js vendored; `renderMarkdown` uses `marked.parse()`; `test_read_note_returns_body_key` passes |
| GUIX-04 | 20-03-PLAN.md | User can scroll the note content area with the mouse wheel | ? HUMAN | CSS fix applied and committed (b7fb2f9); human checkpoint approved in plan 03 execution |
| GUIX-05 | 20-02-PLAN.md | Backlinks display correctly in the note viewer | ✓ SATISFIED | `note_meta` uses body content search; false-positive exclusion confirmed; `TestNoteMeta` all 4 tests pass |

All 4 requirement IDs declared across plans are accounted for. No orphaned requirements found.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No TODOs, FIXMEs, placeholders, stub returns, or console.log-only implementations found in any modified file.

---

## Human Verification Required

### 1. Note viewer scroll

**Test:** Start the GUI (`sb-gui`), open a note longer than the viewer panel height, hover over the viewer panel, scroll with the mouse wheel.
**Expected:** Note content scrolls; viewer does not clip or remain stuck.
**Why human:** CSS `min-height: 0` flex scroll fix cannot be validated without a live pywebview or browser render. Automated grep confirms CSS is present; behavior requires live GUI.

### 2. EasyMDE editor height after scroll fix

**Test:** Click "Edit" on any note after the scroll fix is applied.
**Expected:** EasyMDE editor fills the center panel's available height; toolbar and editor body are fully visible; no overflow or clipping.
**Why human:** The `.EasyMDEContainer` and `.CodeMirror` `min-height: 0` fix prevents height regression but requires visual confirmation that the editor layout was not affected.

### 3. Markdown rendering (vendored marked.js)

**Test:** Open a note with markdown formatting (headings, bold text, bullet lists).
**Expected:** Content renders as formatted HTML — headings are large, bold text is bold, lists have bullets. No raw `#` or `**` characters visible. No YAML `---` frontmatter block visible.
**Why human:** `marked.parse()` call path is wired but actual HTML rendering in pywebview requires a live render to confirm. (Note: plan 03 human checkpoint was already approved by user during execution.)

---

## Gaps Summary

No gaps found. All automated truths are verified. The 3 human verification items above were already approved by the user during plan 03 execution (human-verify checkpoint gate was passed). They are listed here as required documentation for visual/UX items that cannot be re-verified programmatically.

---

_Verified: 2026-03-16T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
