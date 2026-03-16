---
phase: 20-frontend-bug-fixes
plan: "01"
subsystem: api + gui
tags: [bug-fix, api, sqlite, frontmatter, tdd]
dependency_graph:
  requires: []
  provides: [GUIX-02, GUIX-03]
  affects: [engine/api.py, engine/gui/static/app.js, engine/gui/static/index.html]
tech_stack:
  added: [python-frontmatter]
  patterns: [TDD red-green, atomic SQLite update after file write]
key_files:
  created: []
  modified:
    - engine/api.py
    - engine/gui/static/app.js
    - engine/gui/static/index.html
    - tests/test_api.py
decisions:
  - "read_note returns body (stripped) by default; ?raw=true returns full content for editor"
  - "save_note parses frontmatter post-write to extract title for SQLite UPDATE"
  - "easyMDE value captured before exitEditMode() to avoid null reference in renderMarkdown"
metrics:
  duration: "3 minutes"
  completed: "2026-03-16"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 4
requirements: [GUIX-02, GUIX-03]
---

# Phase 20 Plan 01: Frontmatter Strip + Save Re-index Summary

**One-liner:** Fixed GUIX-02/03 by stripping YAML frontmatter from viewer response via python-frontmatter and running a SQLite title UPDATE after every save.

## What Was Built

Two coupled API bugs in `engine/api.py` fixed with full TDD coverage:

**GUIX-03 — Frontmatter visible in viewer:**
- `read_note` now calls `_fm.loads(raw).content` by default, returning `{"body": stripped_content}`
- `?raw=true` param added returning `{"content": full_raw}` for editor use

**GUIX-02 — Title not persisted to SQLite after save:**
- `save_note` now parses the just-written file with `_fm.loads` to extract `title`
- Runs `UPDATE notes SET title=?, updated_at=? WHERE path=?` immediately after `os.replace`

**GUI updates:**
- `openNote()` reads `body` key instead of `content`
- `enterEditMode()` fetches with `?raw=true` so editor shows full file including frontmatter
- `saveNote()` captures `easyMDE.value()` before `exitEditMode()`, calls `loadNotes()` to refresh sidebar, restores active state
- `index.html`: `<span id="save-error">` added to toolbar for inline error display

## Tasks

| # | Name | Status | Commit |
|---|------|--------|--------|
| 1 | Add test scaffolding (TDD RED) | Done | 77d5c79 |
| 2 | Fix read_note + save_note + app.js (TDD GREEN) | Done | 92d07e6 |

## Deviations from Plan

None - plan executed exactly as written.

## Test Results

```
uv run --extra dev pytest tests/test_api.py -x -q
18 passed
```

All 18 tests pass including 6 new tests covering GUIX-02 and GUIX-03.

## Self-Check: PASSED

- engine/api.py: FOUND
- engine/gui/static/app.js: FOUND
- engine/gui/static/index.html: FOUND
- tests/test_api.py: FOUND
- Commit 77d5c79 (RED tests): FOUND
- Commit 92d07e6 (GREEN implementation): FOUND
