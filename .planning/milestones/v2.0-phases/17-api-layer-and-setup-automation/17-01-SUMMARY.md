---
phase: 17-api-layer-and-setup-automation
plan: "01"
subsystem: api
tags: [flask, waitress, flask-cors, api, tdd-green]
dependency_graph:
  requires:
    - 17-00 (RED scaffold — tests/test_api.py)
  provides:
    - engine/api.py (Flask sidecar with /health, /notes, /search, /notes/<path>, /actions)
    - engine.intelligence.list_actions (new helper function)
  affects:
    - Phase 18 (GUI calls engine/api.py exclusively)
tech_stack:
  added: []
  patterns:
    - Per-request sqlite3.Row row_factory — set on conn after get_connection() for dict serialization
    - Flask test client pattern with @pytest.fixture client
    - Waitress serve in main() — no app.run()
key_files:
  created:
    - engine/api.py
  modified:
    - engine/intelligence.py
decisions:
  - "list_actions(conn, done) added to intelligence.py — was missing, referenced in plan but not yet implemented"
  - "sqlite3.Row row_factory set per-request since get_connection() returns plain connection without row_factory"
metrics:
  duration: 240s
  completed: "2026-03-15"
  tasks_completed: 1
  files_modified: 2
---

# Phase 17 Plan 01: API Layer Implementation Summary

**One-liner:** Flask sidecar engine/api.py with 5 HTTP endpoints (health, notes, search, read, actions) using Waitress on 127.0.0.1:37491 with pywebview-compatible CORS.

## What Was Built

`engine/api.py` — the thin HTTP sidecar the GUI will call exclusively. Implements all 5 endpoints specified in the plan: `GET /health`, `GET /notes`, `POST /search`, `GET /notes/<path>`, `GET /actions`. CORS configured for `null`, `file://*`, and `http://127.0.0.1:*` origins. `main()` uses `waitress.serve()` on `127.0.0.1:37491` with 4 threads.

Also added `list_actions(conn, done=False)` to `engine/intelligence.py` — this function was referenced in the plan's interface spec but did not exist in the codebase. The equivalent DB query was present inside `actions_main()` and was extracted into a reusable helper.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement engine/api.py with all endpoints | 0796dd5 | engine/api.py, engine/intelligence.py |

## Verification

All 9 tests in `tests/test_api.py` pass GREEN:
- `TestHealthEndpoint`: 2 tests (200 status, body has "status": "ok")
- `TestNotesList`: 2 tests (200 status, "notes" key present)
- `TestSearch`: 2 tests (200 status, "results" key present)
- `TestReadNote`: 1 test (404 on missing note path)
- `TestActionItems`: 2 tests (200 status, "actions" key present)

Full suite (excluding pre-existing RED scaffolds): 206 passed, 1 skipped, 1 xfailed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Function] Added list_actions() to engine/intelligence.py**
- **Found during:** Task 1 — plan references `engine.intelligence.list_actions` but function did not exist
- **Issue:** `actions_main()` contained the equivalent DB query inline but there was no reusable `list_actions(conn, done)` function
- **Fix:** Added `list_actions(conn, done=False)` to intelligence.py extracting the query from `actions_main`
- **Files modified:** engine/intelligence.py
- **Commit:** 0796dd5

**2. [Rule 1 - Bug] Fixed sqlite3 row serialization with row_factory**
- **Found during:** Task 1 — first test run showed `ValueError: dictionary update sequence element #0 has length 83; 2 is required`
- **Issue:** `get_connection()` returns a plain sqlite3 connection without `row_factory=sqlite3.Row`; calling `dict(row)` on plain tuple rows fails
- **Fix:** Set `conn.row_factory = sqlite3.Row` immediately after `get_connection()` in each endpoint that converts rows to dicts
- **Files modified:** engine/api.py
- **Commit:** 0796dd5

## Self-Check: PASSED

- engine/api.py: FOUND
- engine/intelligence.py: FOUND
- Commit 0796dd5: FOUND
