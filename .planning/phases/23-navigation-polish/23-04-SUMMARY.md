---
phase: 23-navigation-polish
plan: "04"
subsystem: gui
tags: [bug-fix, ux, persistence, autocomplete, sidebar]
dependency_graph:
  requires: [23-01, 23-02, 23-03]
  provides: [GNAV-01, GNAV-02, GNAV-03]
  affects: [engine/api.py, engine/gui/static/app.js, tests/test_api.py]
tech_stack:
  added: []
  patterns:
    - Server-side UI state persistence via GET/PUT /ui/prefs (JSON file in brain dir)
    - HTML5 datalist for native browser tag autocomplete (no new deps)
    - Immediate SQLite indexing on note creation (watcher-independent)
key_files:
  created: []
  modified:
    - engine/api.py
    - engine/gui/static/app.js
    - tests/test_api.py
decisions:
  - "[23-04] Collapse state stored server-side in .sb-gui-prefs.json — localStorage is unreliable in pywebview WKWebView on macOS"
  - "[23-04] POST /notes immediately INSERTs into SQLite; watcher remains as secondary sync"
  - "[23-04] Tag autocomplete uses <datalist> — native, zero deps, works in WKWebView"
  - "[23-04] Slug collision resolved by appending -1, -2 counter; path returned as absolute resolved string"
metrics:
  duration: 25 min
  completed: "2026-03-16T19:10:00Z"
  tasks_completed: 2
  files_modified: 3
---

# Phase 23 Plan 04: Human Verification and Gap Closure Summary

**One-liner:** Three post-verification bugs fixed: server-side collapse persistence, immediate new-note indexing, and HTML5 tag autocomplete from brain tags.

## What Was Built

Phase 23-04 resolved three issues discovered during the 17-step human verification of Phase 23 features.

### Bug 1 Fixed — Sidebar Collapse State Not Persisting (Step 4)

**Root cause:** `localStorage` is unreliable inside pywebview's WKWebView on macOS. Although the JavaScript logic was correct, the storage layer did not survive app restarts.

**Fix:** Added `GET/PUT /ui/prefs` endpoints to `engine/api.py`. Prefs are stored as `.sb-gui-prefs.json` in the brain directory. `app.js` now uses `_loadCollapseState()` (async fetch from `/ui/prefs`) at init time before the first `renderHierarchySidebar()` call, and `setCollapseState()` PUTs updates to the server (fire-and-forget).

### Bug 2 Fixed — New Notes Don't Appear in Sidebar (Step 17)

**Root cause:** `POST /notes` wrote the file to disk and returned, but never inserted the note into the SQLite `notes` table. `loadNotes()` called immediately after creation fetched from SQLite and found nothing.

**Fix:** `create_note()` now INSERTs the new note into `notes` table immediately after writing the file. Also added slug collision resolution: if a file with the generated slug already exists, a `-1`, `-2`, ... counter is appended.

### Enhancement — Tag Autocomplete (Additional UX Request)

**Implementation:** Added `_getAllUniqueTags()` (collects all tags from `_allNotes` cache) and `_attachTagDatalist(inputEl)` (builds/updates a shared `<datalist id="sb-tag-datalist">` and wires it to the input). Both `makeChipEditable()` and `addNewTag()` call `_attachTagDatalist()`. No new dependencies — uses standard HTML5 `datalist` which is supported natively in WKWebView.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] localStorage not persisting across pywebview restarts**
- **Found during:** Task 2 (human verification — Step 4)
- **Issue:** pywebview's WKWebView did not reliably persist `localStorage` for `http://127.0.0.1` origin across app restarts
- **Fix:** Added `GET/PUT /ui/prefs` API endpoints; switched collapse state to server-side JSON file
- **Files modified:** `engine/api.py`, `engine/gui/static/app.js`
- **Commit:** `4cd4019`

**2. [Rule 1 - Bug] New notes not indexed into SQLite on creation**
- **Found during:** Task 2 (human verification — Step 17)
- **Issue:** `POST /notes` wrote file to disk but skipped SQLite INSERT; `GET /notes` couldn't return the new note until the watchdog picked it up
- **Fix:** Added immediate INSERT into `notes` table after `target.write_text()`; added slug collision guard
- **Files modified:** `engine/api.py`
- **Commit:** `ac86381`

**3. [Rule 2 - Missing critical functionality] Tag autocomplete UX**
- **Found during:** Task 2 (human verification — additional feedback)
- **Issue:** No way to see or reuse existing brain tags when editing/adding chips
- **Fix:** HTML5 `<datalist>` populated from `_allNotes` cache, attached to all tag input elements
- **Files modified:** `engine/gui/static/app.js`
- **Commit:** `4cd4019`

## Test Results

- **259 passed**, 1 skipped, 1 xfailed
- 6 new tests added in `TestCreateNote` (4 tests) and `TestUIPrefs` (2 tests)
- 2 pre-existing failures excluded: `test_claude_md_contains_session_hook` (requires manual CLAUDE.md update) and `test_blocks_api_key` (detect-secrets config issue) — both pre-dated this plan

## Self-Check: PASSED

Files verified:
- `engine/api.py` — `_get_prefs_path`, `get_prefs`, `put_prefs`, updated `create_note` all present
- `engine/gui/static/app.js` — `_loadCollapseState`, `_attachTagDatalist`, `_getAllUniqueTags` all present
- `tests/test_api.py` — `TestCreateNote`, `TestUIPrefs` classes present

Commits verified:
- `ac86381` — new note indexing + slug collision
- `4cd4019` — server-side prefs + tag autocomplete
