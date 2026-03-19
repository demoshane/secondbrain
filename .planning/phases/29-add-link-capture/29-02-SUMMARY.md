---
phase: 29-add-link-capture
plan: 02
subsystem: engine
tags: [link-capture, db-migration, capture-pipeline, metadata-fetch]
dependency_graph:
  requires:
    - 29-01  # xfail stubs established
  provides:
    - engine/link_capture.py with fetch_link_metadata()
    - notes.url column via migrate_add_url_column()
    - TYPE_TO_DIR["link"] = "links"
    - capture_note() url= kwarg + frontmatter write
  affects:
    - engine/capture.py
    - engine/db.py
tech_stack:
  added: []
  patterns:
    - urllib.request module-ref patching for testability
    - keyword-only url param with None default for backward compat
    - try/except OperationalError for idempotent ALTER TABLE migration
key_files:
  created:
    - engine/link_capture.py
    - tests/test_link_capture.py
  modified:
    - engine/db.py
    - engine/capture.py
decisions:
  - "Use urllib.request.urlopen via module reference (not direct import) so tests can monkeypatch urllib.request.urlopen"
  - "url param is keyword-only in both capture_note() and write_note_atomic() to prevent accidental positional arg breakage"
  - "migrate_add_url_column uses try/except OperationalError (not PRAGMA table_info check) — consistent with plan spec, both approaches are idempotent"
  - "Test file was rewritten by sb-hook pre-commit; adopted xfail(strict=False) pattern from hook version matching Phase 29-01 style"
metrics:
  duration: "21 min"
  completed: "2026-03-19"
  tasks: 2
  files_modified: 4
requirements:
  - LINK-01
  - LINK-02
---

# Phase 29 Plan 02: Engine Foundation for Link Capture Summary

One-liner: stdlib urllib metadata fetch with og:title/description, notes.url column migration, and url keyword threaded into capture pipeline.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | fetch_link_metadata() in engine/link_capture.py | a6002a6 | engine/link_capture.py |
| 2 | DB migration + TYPE_TO_DIR["link"] + url frontmatter | 01b71f2 | engine/db.py, engine/capture.py |

## Verification Results

- `test_fetch_metadata_returns_title`: xpassed — og:title extracted correctly
- `test_fetch_metadata_fallback_on_error`: xpassed — hostname returned on error
- `test_url_column_exists`: xpassed — notes table has url column after init_schema
- `fetch_link_metadata("https://invalid.x")` returns `{'title': 'invalid.x', 'description': ''}` — no exception
- Full non-GUI test suite: 85 passed, 9 xfailed, 6 xpassed — zero regressions

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test file replaced by sb-hook pre-commit with different patching approach**
- **Found during:** Task 1 RED phase
- **Issue:** The test file written for TDD RED was replaced by the sb-hook pre-commit, converting explicit mock patching to monkeypatch-based pattern and adding xfail(strict=False) wrappers consistent with Phase 29-01 style
- **Fix:** Updated engine/link_capture.py to use `urllib.request.urlopen` via module reference rather than direct import, making monkeypatch.setattr(urllib.request, "urlopen", ...) work correctly
- **Files modified:** engine/link_capture.py
- **Commit:** a6002a6

## Self-Check: PASSED

- engine/link_capture.py: FOUND
- engine/db.py: FOUND
- engine/capture.py: FOUND
- tests/test_link_capture.py: FOUND
- commit a6002a6: FOUND
- commit 01b71f2: FOUND
