---
phase: 23-navigation-polish
verified: 2026-03-16T00:00:00Z
status: human_needed
score: 13/15 must-haves verified (2 require human)
re_verification: false
human_verification:
  - test: "Open the GUI; confirm sidebar shows a 'Recent (N)' section at the top, then folder sections (e.g. 'projects/ (3)') with type sub-groups beneath each"
    expected: "Two-level hierarchy rendered: Recent block first, then folder/ > type sub-sections. No flat list in default browse mode."
    why_human: "Pure JS DOM rendering — no automated test covers visual sidebar structure"
  - test: "Click a folder header to collapse it. Reload the page. Confirm the same folder is still collapsed."
    expected: "Collapsed state persists across reloads (server-side prefs via /ui/prefs)"
    why_human: "localStorage/prefs persistence requires a live browser session"
  - test: "Open a note with tags. Confirm tag chips appear below the note title (e.g. '#work #idea + Add tag'). Double-click a chip, type a new value, press Enter. Reopen the note — confirm new tag is saved."
    expected: "Inline edit works end-to-end: chip transforms to input, Enter commits, re-open shows persisted tag"
    why_human: "UI interaction flow with double-click event, inline DOM replacement, and async save"
  - test: "Click a tag chip (single-click) on an open note. Confirm the sidebar switches to a flat list of notes with that tag. Confirm a banner appears showing 'Filtering: #tagname ×'. Click × — confirm sidebar returns to hierarchy view."
    expected: "Tag filter activates, banner shows, × clears filter and restores hierarchy"
    why_human: "UI state machine — activeTagFilter, banner show/hide, renderFlatList vs renderHierarchySidebar"
  - test: "While a tag filter is active, type a search query. Confirm the results list is narrowed to only notes that match BOTH the text query AND the active tag."
    expected: "AND logic: results must satisfy text search AND tag filter simultaneously"
    why_human: "Combined filter behavior requires live interaction to verify the intersection"
---

# Phase 23: Navigation Polish — Verification Report

**Phase Goal:** Navigation polish — sidebar folder/type hierarchy, tag chips, tag filter mode
**Verified:** 2026-03-16
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | PUT /notes/<path> with only `tags` in body updates frontmatter file and DB without full reindex | VERIFIED | `api.py` lines 283-302: tags-only branch present, reads file with `_fm.loads`, writes via tempfile+os.replace, targeted `UPDATE notes SET tags=?`; 3/3 `TestTagsOnlySave` tests pass |
| 2 | POST /search with `tags` param returns only notes containing all specified tags (AND logic) | VERIFIED | `api.py` lines 163-191: both tags-only path and combined path implement `all(t in note_tags for t in tags_filter)`; `TestTagSearch` 3/3 pass |
| 3 | GET /notes returns `tags` as a parsed list, not a raw JSON string | VERIFIED | `api.py` line 150: `d["tags"] = json.loads(d.get("tags") or "[]")`; `TestListNotesTags` 2/2 pass |
| 4 | Sidebar shows a 'Recent' section at the top (last 10 notes, flat list, collapsible) | VERIFIED | `app.js` lines 161-164: `recentNotes = notes.slice(0, 10)`, `makeSection('recent', ...)`, appended first to list |
| 5 | Below Recent, notes are grouped by folder then by type within each folder | VERIFIED | `app.js` lines 166-205: `folderMap` built via `folderName()`, nested `makeTypeSection()` per type |
| 6 | Each folder/type header has an independent collapse/expand toggle | VERIFIED | `app.js` lines 107-131 and 133-158: separate `setCollapseState(key)` calls with distinct `folder` and `folderKey::typeName` keys |
| 7 | Collapse state persists and is restored on reload | VERIFIED (automated portion) | `app.js` lines 14-36: `_loadCollapseState()` reads from `GET /ui/prefs`, `setCollapseState()` writes to `PUT /ui/prefs`; `api.py` lines 239-258: `/ui/prefs` endpoints functional. **Live browser persistence needs human confirm — see human_verification #2** |
| 8 | Search results and tag-filtered results display as a flat list (no hierarchy) | VERIFIED | `app.js` line 580: `runSearch()` calls `renderFlatList()`; `app.js` line 549: `runTagFilter()` without query calls `renderFlatList()` |
| 9 | Tag chips appear below note title with '+ Add tag' button | VERIFIED | `index.html` line 34: `<div id="tag-chips" class="tag-chips-row"></div>` present between toolbar and viewer; `app.js` lines 270-304: `renderTagChips()` populates chips; `openNote()` line 420 calls `renderTagChips()` |
| 10 | Double-clicking a chip transforms it into an inline text input; Enter saves, Escape cancels | VERIFIED | `app.js` lines 306-338: `makeChipEditable()` with `chipEl.replaceWith(input)`, `input.focus()`, keydown handlers for Enter/Escape. **End-to-end UI flow needs human confirm — see human_verification #3** |
| 11 | Saving a tag edit updates frontmatter file and DB immediately (optimistic); chip turns red briefly on failure | VERIFIED | `app.js` lines 377-404: `saveTags()` sets `_suppressNextTagRefresh=true`, calls `renderTagChips()` optimistically, adds `tag-save-error` class on failure; backed by tested `PUT /notes/<path>` endpoint |
| 12 | Clicking a tag chip activates tag filter — sidebar switches to flat list | VERIFIED | `app.js` line 280: single-click calls `activateTagFilter(tag)`; `activateTagFilter()` lines 512-531 shows banner and calls `runTagFilter()`. **Sidebar visual switch needs human confirm — see human_verification #4** |
| 13 | A filter banner appears above the note list showing active tag; clicking x clears the filter | VERIFIED | `index.html` line 23: `<div id="filter-banner" style="display:none" class="filter-banner">` present; `app.js` lines 512-531: banner populated with XSS-safe textContent; `clearTagFilter()` lines 533-539 hides banner. **Visual confirm needs human — see human_verification #4** |
| 14 | When both text search and tag filter are active, results match both (AND logic) | VERIFIED | `app.js` lines 570-573: `if (activeTagFilter !== null) body.tags = [activeTagFilter]` appended to POST /search body; backend AND logic confirmed tested. **Live interaction needs human confirm — see human_verification #5** |
| 15 | All test classes (TestTagsOnlySave, TestTagSearch, TestListNotesTags) pass | VERIFIED | `uv run pytest tests/test_api_tags.py`: 8/8 pass in 1.00s |

**Score:** 13/15 truths verified programmatically; 2 fully verified by automated + code inspection but require live browser confirmation

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_api_tags.py` | Tags API tests | VERIFIED | 247 lines, 3 test classes, 8 tests all passing |
| `engine/api.py` | Tags-only PUT, tag-filtered search, tags parse | VERIFIED | All 3 endpoints implemented and tested |
| `engine/gui/static/app.js` | `renderHierarchySidebar()`, `renderFlatList()`, `folderName()`, `getCollapseState()`, `setCollapseState()`, `renderTagChips()`, `makeChipEditable()`, `saveTags()`, `activateTagFilter()`, `clearTagFilter()`, `runTagFilter()`, `activeTagFilter` | VERIFIED | All functions present and substantive (802 lines total) |
| `engine/gui/static/index.html` | `filter-banner` div above note list; `tag-chips` div below title | VERIFIED | Lines 23 and 34 confirmed |
| `engine/gui/static/style.css` | `.folder-header`, `.type-header`, `.collapse-toggle`, `.section-count`, `.tag-chip`, `.tag-chip-input`, `.tag-add-btn`, `.filter-banner`, `.filter-clear-btn`, `.tag-chips-row`, `.tag-save-error` | VERIFIED | All classes present, lines 59-234 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.js:loadNotes()` | `renderHierarchySidebar(notes)` | replaces old renderSidebar | WIRED | Line 60: `renderHierarchySidebar(notes)` called when no activeTagFilter |
| `app.js:runSearch()` | `renderFlatList(notes)` | search always flat | WIRED | Line 580: `renderFlatList(results.map(...))` |
| `app.js:openNote()` | `renderTagChips(note.tags, tagContainer)` | called after rendering body | WIRED | Line 420: `renderTagChips(cachedNote ? (cachedNote.tags || []) : [], path)` |
| `app.js:activateTagFilter(tag)` | POST /search with tags param | via runTagFilter → runSearch | WIRED | Lines 542-545: if search query present, delegates to `runSearch()` which injects `body.tags = [activeTagFilter]` at lines 571-573 |
| `app.js:runSearch()` | POST /search with tags param when activeTagFilter set | AND logic | WIRED | Lines 570-573: `if (activeTagFilter !== null) body.tags = [activeTagFilter]` |
| `engine/api.py:save_note()` | `UPDATE notes SET tags=? WHERE path=?` | targeted DB update | WIRED | Lines 296-300: exact pattern present |
| `engine/api.py:search()` | tags AND filter | `all(t in note_tags for t in tags_filter)` | WIRED | Lines 171 and 189: both code paths use this pattern |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GNAV-01 | 23-02, 23-04 | Sidebar shows collapsible section navigation by note type/folder | VERIFIED (automated) + HUMAN NEEDED | `renderHierarchySidebar()` implemented and wired; `folder-header`/`type-header` CSS present; collapse state persists via /ui/prefs; visual confirmation needed |
| GNAV-02 | 23-01, 23-03, 23-04 | User can edit note tags and metadata directly from the GUI | VERIFIED (automated) + HUMAN NEEDED | Backend: tags-only PUT endpoint tested 3/3; Frontend: `makeChipEditable()`, `saveTags()`, `addNewTag()` all implemented and wired into `openNote()`; visual interaction confirmation needed |
| GNAV-03 | 23-01, 23-03, 23-04 | User can filter notes by tag in search and browse | VERIFIED (automated) + HUMAN NEEDED | Backend: POST /search tags param tested 3/3; Frontend: `activateTagFilter()`, `runTagFilter()`, `clearTagFilter()`, filter banner, AND logic in runSearch() all wired; visual confirmation needed |

No orphaned requirements — all three GNAV IDs appear in plan frontmatter and are covered by implementation evidence.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app.js` | 352 | `input.placeholder = 'new tag'` | Info | Legitimate UX placeholder text on a new-tag input, not a stub |

No blocker anti-patterns found. No empty implementations, no `return null` stubs, no TODO/FIXME comments in phase-23 code.

---

## Test Suite Status

| Suite | Result | Notes |
|-------|--------|-------|
| `tests/test_api_tags.py` | 8/8 pass | Phase 23 backend contract fully tested |
| Full suite (265 tests) | 265 pass, 1 skip, 1 xfail | Excludes 2 pre-existing failures from earlier phases |
| `test_intelligence.py::TestClaudeMdHook::test_claude_md_contains_session_hook` | FAIL (pre-existing) | Expects `sb-recap` in `~/.claude/CLAUDE.md` — failure exists before phase 23 (commit `85b3dbe`) |
| `test_precommit.py::test_blocks_api_key` | FAIL (pre-existing) | Pre-existing failure from phase 1 (commit `0f137b5`) |

---

## Human Verification Required

### 1. Sidebar hierarchy renders correctly (GNAV-01)

**Test:** Start `uv run sb-gui`. Open the GUI. Confirm the sidebar shows a "Recent (N)" section at top, then folder sections such as "projects/ (3)", with type sub-groups (e.g. "note (2)") inside each folder.
**Expected:** Two-level folder > type hierarchy in default browse mode; not a flat list.
**Why human:** Pure JS DOM rendering — no server-side test covers what the browser actually renders.

### 2. Collapse state persists across reload (GNAV-01)

**Test:** Click a folder header to collapse it. Reload the page. Confirm the collapsed folder is still collapsed.
**Expected:** Collapse state survives reload via server-side `/ui/prefs` persistence.
**Why human:** Requires a live browser session to test localStorage/prefs round-trip.

### 3. Tag chip inline edit works end-to-end (GNAV-02)

**Test:** Open a note that has tags. Confirm chips appear below the title. Double-click a chip — it should transform into an inline input. Type a new tag name, press Enter. Click away and reopen the note — confirm the new tag name is saved.
**Expected:** Chip edits persist to file (frontmatter) and DB.
**Why human:** Double-click event, DOM replacement, async save, and re-render require live browser.

### 4. Tag filter banner and clear button work (GNAV-03)

**Test:** Single-click a tag chip. Confirm the sidebar switches to a flat list showing only notes with that tag. Confirm a banner appears above the list showing "Filtering: #tagname ×". Click ×. Confirm the sidebar returns to the hierarchy view.
**Expected:** Filter activates, banner shows, × clears and restores hierarchy.
**Why human:** UI state machine (activeTagFilter, banner visibility, sidebar re-render) requires live interaction.

### 5. Text search + tag filter AND logic (GNAV-03)

**Test:** With a tag filter active, type a search query in the search box. Confirm that results show only notes matching BOTH the text query AND the active tag.
**Expected:** Intersection of text search and tag filter — not a union.
**Why human:** Combined live state (activeTagFilter + search input value) requires browser interaction.

---

## Gaps Summary

No gaps found. All automated checks pass. The 5 human verification items are confirmations of visual/interactive behavior for which code evidence is strong — all wiring is correct and all backend contracts are tested. These are sign-off checks, not gap indicators.

---

_Verified: 2026-03-16_
_Verifier: Claude (gsd-verifier)_
