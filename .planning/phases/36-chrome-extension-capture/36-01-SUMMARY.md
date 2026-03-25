---
phase: 36-chrome-extension-capture
plan: "01"
subsystem: backend-api
tags: [api, cors, capture, chrome-extension]
dependency_graph:
  requires: []
  provides: [ping-endpoint, chrome-extension-cors, source_url-frontmatter, source_type-frontmatter]
  affects: [engine/api.py, engine/capture.py]
tech_stack:
  added: []
  patterns: [flask-cors-origin-list, kwarg-extension-pattern]
key_files:
  created: []
  modified:
    - engine/api.py
    - engine/capture.py
    - tests/test_api.py
decisions:
  - "source_type added as kwarg to capture_note() — consistent with existing url kwarg pattern; no schema migration needed"
  - "create_note() writes url to manual frontmatter string via url_line interpolation — consistent with existing manual-string approach in that function (does not use capture_note)"
metrics:
  duration: 176
  completed: "2026-03-25"
  tasks: 1
  files: 3
---

# Phase 36 Plan 01: Backend API Chrome Extension Support Summary

Backend API now supports Chrome extension capture: `/ping` health check, CORS for `chrome-extension://` origins, and `source_url`/`source_type` fields written to note frontmatter via both `/smart-capture` and `/notes` endpoints.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Backend API changes — /ping, CORS, source_url/source_type | 54eb50e | engine/api.py, engine/capture.py, tests/test_api.py |

## What Was Built

### /ping endpoint
GET `/ping` returns `{"ok": true}` with 200. Used by extension to verify sb-api is reachable before attempting capture.

### CORS for chrome-extension://
Added `"chrome-extension://*"` to Flask-CORS origins list. Extension popup makes cross-origin XHR requests to `127.0.0.1:37491` — without this, all requests are blocked.

### source_url and source_type on /smart-capture
Extracted from request body, passed to `capture_note()` via `url=source_url or None, source_type=source_type or None`. Both land in frontmatter via the existing `url` kwarg and new `source_type` kwarg.

### source_url on /notes
Extracted from request body. Written into the manual frontmatter string as `url: {source_url}` line, inserted between `content_sensitivity` and the `---` closing marker.

### capture_note() source_type parameter
New `source_type: str | None = None` kwarg added to `capture_note()` in `capture.py`. Written to frontmatter as `post["source_type"] = source_type` after the existing `url` block.

## Test Coverage

4 new tests added to `tests/test_api.py`:
- `TestPingEndpoint.test_ping` — GET /ping returns 200 + `{"ok": True}`
- `TestCORSExtension.test_cors_extension_origin` — OPTIONS with chrome-extension origin gets CORS header
- `TestSmartCaptureSourceUrl.test_smart_capture_source_url` — source_url and source_type appear in saved frontmatter
- `TestCreateNoteSourceUrl.test_create_note_source_url` — source_url appears as `url:` in saved frontmatter

All 38 tests pass (4 xfailed pre-existing, 1 xpassed pre-existing).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All fields are fully wired: source_url and source_type are extracted from request body and written to disk frontmatter.

## Self-Check: PASSED

- `engine/api.py` contains `"chrome-extension://*"` in CORS list: confirmed
- `engine/api.py` contains `def ping():`: confirmed
- `engine/api.py` contains `return jsonify({"ok": True})`: confirmed
- `engine/api.py` smart_capture contains `data.get("source_url"`: confirmed
- `engine/api.py` smart_capture contains `data.get("source_type"`: confirmed
- `engine/api.py` create_note contains `body.get("source_url"`: confirmed
- `engine/capture.py` capture_note signature contains `source_type: str | None = None`: confirmed
- `engine/capture.py` contains `post["source_type"] = source_type`: confirmed
- `tests/test_api.py` contains `def test_ping`: confirmed
- `tests/test_api.py` contains `def test_cors_extension_origin`: confirmed
- Commit `54eb50e` exists: confirmed
