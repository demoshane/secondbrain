---
phase: 29-add-link-capture
plan: "03"
subsystem: mcp-server, api
tags: [link-capture, mcp, flask-api, tdd]
dependency_graph:
  requires:
    - 29-02  # engine/link_capture.py, url column in DB
  provides:
    - sb_capture_link MCP tool
    - GET /links Flask endpoint
    - GET /links/<path> Flask endpoint
  affects:
    - engine/mcp_server.py
    - engine/api.py
tech_stack:
  added: []
  patterns:
    - duplicate-url-check before capture (SELECT url= LIMIT 1)
    - urlparse domain extraction in both MCP and API layers
    - xfail(strict=False) stubs promoted to xpass once implementation ships
key_files:
  created: []
  modified:
    - engine/mcp_server.py
    - engine/api.py
decisions:
  - "[29-03] sb_capture_link uses fetch_link_metadata then capture_note(note_type='link', url=url) — url is keyword-only per Phase 29-02 decision"
  - "[29-03] Duplicate URL check queries notes WHERE url=? BEFORE capture; saves anyway and returns duplicate_url_warning — no blocking on re-capture"
  - "[29-03] GET /links/<path> returns 403 for path-traversal attempts and 404 when path not found as type='link'"
metrics:
  duration: 8 min
  completed: 2026-03-19
  tasks_completed: 2
  files_modified: 2
---

# Phase 29 Plan 03: Link Capture — MCP Tool and Flask API Summary

Wire `sb_capture_link` MCP tool and `/links` Flask API endpoints using the `engine/link_capture` and `url` column foundation from Plan 02.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | sb_capture_link MCP tool | ec32658 | engine/mcp_server.py |
| 2 | Flask GET /links and GET /links/<path> | 7f07733 | engine/api.py |

## What Was Built

### Task 1 — sb_capture_link MCP tool (engine/mcp_server.py)

Added `sb_capture_link(url, tags, people, notes)` as an `@mcp.tool()`:

- Imports `fetch_link_metadata` from `engine.link_capture`
- Extracts hostname via `urlparse(url).hostname`
- Calls `fetch_link_metadata(url)` — uses og:title/description with fallback to hostname
- Builds body from description + optional annotation notes
- Checks `notes WHERE url=? LIMIT 1` before capture — if found, returns `duplicate_url_warning` status but saves new copy anyway
- Calls `capture_note(note_type="link", url=url, ...)` with keyword-only `url` param
- Returns `{"status": "created", "path", "title", "domain", "message"}` on first capture
- Returns `{"status": "duplicate_url_warning", "existing_path", "path", "message"}` on re-capture

### Task 2 — Flask /links endpoints (engine/api.py)

Added two routes after `/projects/<path>`:

**GET /links** — lists all link-type notes:
- SELECT WHERE type='link' ORDER BY created_at DESC
- Extracts domain from url via urlparse
- Returns `{"links": [{path, title, url, domain, date, tags, description}]}`

**GET /links/<path:note_path>** — fetches single link note:
- Path-traversal guard via `_resolve_note_path()` → 403 on escape
- SELECT WHERE path=? AND type='link' → 404 if not found
- Returns `{"path", "title", "url", "domain", "body", "date", "tags"}`

## Verification

All 6 tests in `tests/test_link_capture.py` xpass:
- `test_url_column_exists` — xpass (from 29-02)
- `test_fetch_metadata_returns_title` — xpass (from 29-02)
- `test_fetch_metadata_fallback_on_error` — xpass (from 29-02)
- `test_sb_capture_link_registered` — xpass (Task 1)
- `test_links_api_returns_list` — xpass (Task 2)
- `test_capture_link_duplicate_warn` — xpass (Task 1)

MCP tool confirmed: `sb_capture_link` present in `mcp._local_provider._components`.

Full non-GUI test suite: 35 passed, 4 xfailed, 9 xpassed.

## Deviations from Plan

None — plan executed exactly as written. Both implementations were pre-staged in the working tree from prior work; this plan validated, tested, and committed them with proper per-task commits.

## Self-Check: PASSED

- engine/mcp_server.py: FOUND (modified, committed ec32658)
- engine/api.py: FOUND (modified, committed 7f07733)
- `sb_capture_link` in MCP registry: CONFIRMED
- GET /links: CONFIRMED (test_links_api_returns_list xpass)
- Duplicate URL warning: CONFIRMED (test_capture_link_duplicate_warn xpass)
