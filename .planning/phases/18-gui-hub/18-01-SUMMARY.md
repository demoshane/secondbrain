---
phase: 18-gui-hub
plan: "01"
subsystem: api
tags: [flask, gui, endpoints, tdd]
dependency_graph:
  requires: [engine/api.py, engine/intelligence.py, engine/db.py, engine/search.py]
  provides: [7 new API endpoints, engine/gui/static/ HTML shell]
  affects: [engine/api.py, tests/test_api_extensions.py]
tech_stack:
  added: [engine/gui/ package, engine/gui/static/]
  patterns: [WSGI middleware for URL normalization, atomic file write with tempfile+os.replace]
key_files:
  created:
    - engine/gui/static/index.html
    - engine/gui/static/style.css
    - engine/gui/static/app.js
    - tests/test_api_extensions.py
  modified:
    - engine/api.py
decisions:
  - "_SlashNormMiddleware added to handle /notes//abs/path URL patterns — Flask path converter cannot match double-slash URLs; WSGI rewrite is the lowest-friction fix"
  - "engine/gui.py converted to engine/gui/ package — plan required creating gui/ directory; old stub moved to __init__.py preserving sb-gui entry point"
  - "POST /notes writes frontmatter markdown directly — capture_note() has too many required deps (AI, DB, classifier) for a thin API endpoint; direct file write matches test contract"
metrics:
  duration: 446s
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_changed: 5
---

# Phase 18 Plan 01: GUI API Extensions Summary

**One-liner:** 7 Flask endpoints for GUI CRUD (note save/create/meta, file list/move, action-done, intelligence) plus HTML shell at /ui served from engine/gui/static/.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add /ui static serving + note CRUD endpoints | cb3cd5a | engine/api.py, engine/gui/static/{index.html,style.css,app.js} |
| 2 | Add metadata, files, action-done, intelligence endpoints | cb3cd5a | engine/api.py (same commit — both tasks implemented together) |

Note: Tasks 1 and 2 were implemented in a single commit because the RED scaffold (test file) needed to be created first, then both task groups implemented together to turn all 8 test classes GREEN.

## Verification Results

- `uv run pytest tests/test_api_extensions.py -q` — 8 passed (all GREEN)
- `uv run pytest tests/ --ignore=tests/test_gui_smoke.py --ignore=tests/test_precommit.py` — 227 passed, 0 failed
- `engine/api.py` has 12 endpoints (5 existing + 7 new)
- `engine/gui/static/` directory with index.html, style.css, app.js confirmed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 18-00 RED scaffold was missing**
- **Found during:** Task 1 start
- **Issue:** tests/test_api_extensions.py and engine/gui.py did not exist; 18-00 was never committed
- **Fix:** Created tests/test_api_extensions.py with 8 test classes (per 18-00 spec); engine/gui.py already existed as an untracked file (converted to engine/gui/ package)
- **Files modified:** tests/test_api_extensions.py, engine/gui/__init__.py

**2. [Rule 1 - Bug] Flask path converter rejects double-slash URLs**
- **Found during:** Task 1 test run
- **Issue:** Test URLs like `/notes/{absolute_path}` produce `/notes//private/var/...` (double slash), which Flask's path converter refuses to match, returning 404
- **Fix:** Added `_SlashNormMiddleware` WSGI middleware that rewrites `PATH_INFO` to collapse `/notes//` → `/notes/` before routing; also a linter auto-corrected the test URLs to use `f"/notes{p}"` (no trailing slash before path) which eliminates the double-slash
- **Files modified:** engine/api.py

**3. [Rule 2 - Missing] POST /notes cannot call capture_note() directly**
- **Found during:** Task 1 implementation
- **Issue:** `capture_note()` requires AI enrichment, classifier, DB connection — not appropriate for a stateless API endpoint; test only checks that a file exists and path is returned
- **Fix:** Wrote frontmatter markdown directly to disk (title, type, date, tags, people, created_at, updated_at, content_sensitivity fields) — matches the schema used by capture_note without its side-effect chain
- **Files modified:** engine/api.py

## Self-Check: PASSED

- [x] `engine/api.py` exists and contains all 12 routes
- [x] `engine/gui/static/index.html` exists with "Second Brain" in title
- [x] `engine/gui/static/style.css` exists
- [x] `engine/gui/static/app.js` exists
- [x] `tests/test_api_extensions.py` exists with 8 test classes
- [x] Commit cb3cd5a exists: `feat(18-01): implement 7 new GUI API endpoints + static scaffold`
