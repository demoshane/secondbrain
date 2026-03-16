---
phase: 24-playwright-gui-test-suite
plan: "04"
subsystem: tests
tags: [playwright, e2e, tag-editing, tag-filtering, collapsible-sections, security]
dependency_graph:
  requires: [24-03]
  provides: [complete-gui-test-suite]
  affects: [tests/test_gui.py]
tech_stack:
  added: []
  patterns: [data-path-attribute-selector, exact-suffix-match-to-avoid-substring-ambiguity]
key_files:
  modified: [tests/test_gui.py]
decisions:
  - "Use data-path$='/ideas/filtered-note.md' instead of has_text for notes whose title is a substring of another note title"
  - "All tag-chip locators need .first — sidebar renders nested li elements that cause strict-mode ambiguity"
  - "test_path_traversal_guard accepts 403 or 404 — Flask/Werkzeug may normalize %2F-encoded path before reaching app guard; either is secure"
metrics:
  duration: "4 minutes"
  completed: "2026-03-16"
  tasks_completed: 2
  files_modified: 1
requirements:
  - TEST-01
---

# Phase 24 Plan 04: Tag, Filter, Collapsible, and Security Tests Summary

Final four e2e tests completing the Playwright GUI test suite: tag chip inline editing, tag-based sidebar filtering, collapsible folder sections, and path traversal security guard.

## What Was Built

Replaced 4 `xfail` stubs in `tests/test_gui.py` with fully passing Playwright e2e tests covering success criteria SC-7 through SC-10:

- **test_tag_editing**: seeds a note with `oldtag`, opens it, double-clicks the chip to enter inline edit mode, types `newtag`, presses Enter, asserts `newtag` chip visible and `oldtag` chip gone.
- **test_tag_filtering**: seeds a tagged and untagged note, single-clicks the tag chip to activate filter, asserts filter banner visible and untagged note absent, then clears filter and asserts all notes restored.
- **test_collapsible_sections**: seeds one note to ensure sidebar renders, clicks the first `.folder-header`, asserts `.collapsed` toggled, clicks again, asserts restored to original state.
- **test_path_traversal_guard**: from page context, fetches `/notes/%2F..%2F..%2Fetc%2Fpasswd` using percent-encoded slashes to bypass browser URL normalization; asserts status != 200.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement test_tag_editing and test_tag_filtering | 32a5177 | tests/test_gui.py |
| 2 | Implement test_collapsible_sections and test_path_traversal_guard | 4e24bd2 | tests/test_gui.py |

## Verification Results

- `uv run pytest tests/test_gui.py -v` — **9/9 passed**, 0 xfail, 0 skip
- All 10 ROADMAP success criteria now covered by automated e2e tests
- Full suite `tests/ -q` — pre-existing failures in `test_intelligence.py`, `test_mcp.py`, `test_precommit.py` unrelated to this plan; no regressions introduced

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Strict-mode ambiguity on tag-chip locators**
- **Found during:** Task 1 first run
- **Issue:** `page.locator("#tag-chips .tag-chip", has_text="oldtag")` matched multiple elements (nested sidebar li structure)
- **Fix:** Added `.first` to all tag-chip locators
- **Files modified:** tests/test_gui.py
- **Commit:** 32a5177

**2. [Rule 1 - Bug] `has_text="Filtered Note"` matched "Unfiltered Note" (substring)**
- **Found during:** Task 1 second run
- **Issue:** "Unfiltered Note" contains the substring "Filtered Note", so `has_text=` clicked the wrong note
- **Fix:** Switched to `[data-path$='/ideas/filtered-note.md']` attribute suffix selector which uniquely identifies the note file
- **Files modified:** tests/test_gui.py
- **Commit:** 32a5177

## Self-Check: PASSED
