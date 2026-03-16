---
phase: 18-gui-hub
plan: "00"
subsystem: gui
tags: [pywebview, api, tdd, scaffold]
dependency_graph:
  requires: []
  provides: [engine/gui package stub, tests/test_api_extensions.py, sb-gui entry point]
  affects: [pyproject.toml, uv.lock]
tech_stack:
  added: [pywebview>=5.0 (installed 6.1)]
  patterns: [TDD RED scaffold, Flask test client, package vs module resolution]
key_files:
  created:
    - engine/gui/__init__.py
    - tests/test_api_extensions.py
  modified:
    - pyproject.toml
    - uv.lock
decisions:
  - "engine/gui/ directory pre-existed as package from prior session; moved stub content to __init__.py rather than fighting Python module shadowing"
  - "Test URL construction uses f'/notes{p}' (not f'/notes/{p}') for absolute paths to avoid double-slash Flask 308 redirect"
  - "All 8 API endpoints were pre-implemented in engine/api.py from prior untracked session; tests serve as GREEN regression suite rather than RED scaffold"
metrics:
  duration: 251s
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_changed: 4
---

# Phase 18 Plan 00: GUI Hub Wave 0 RED Scaffold Summary

**One-liner:** pywebview dep added, sb-gui stub created, and 8-endpoint test suite established for Phase 18 GUI Hub with URL-double-slash bug fixed.

## What Was Built

- `engine/gui/__init__.py` — Desktop GUI entry point stub; `main()` raises `NotImplementedError`; `open_in_editor()` exposes OS shell open for JS bridge
- `tests/test_api_extensions.py` — 8 test classes covering all new GUI Hub API endpoints: `/ui`, `/notes/<path>` PUT, `/notes` POST, `/notes/<path>/meta`, `/files`, `/files/move`, `/actions/<id>/done`, `/intelligence`
- `pyproject.toml` — `pywebview>=5.0` added to deps; `sb-gui = "engine.gui:main"` entry point registered
- `uv.lock` — Updated with pywebview 6.1 and PyObjC framework wheels

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] engine/gui/ package directory shadows engine/gui.py**
- **Found during:** Task 1 verification
- **Issue:** Python's import system gives packages (`engine/gui/`) priority over modules (`engine/gui.py`). The directory existed as an untracked file from a prior session, causing `engine.gui.main` to raise `AttributeError`.
- **Fix:** Moved stub content from `engine/gui.py` to `engine/gui/__init__.py`. Removed `engine/gui.py`.
- **Files modified:** `engine/gui/__init__.py`, removed `engine/gui.py`
- **Commit:** ad2b87c

**2. [Rule 1 - Bug] Double-slash URL in test stubs causes Flask 308 redirect**
- **Found during:** Task 2 verification
- **Issue:** `f"/notes/{p}"` where `p` is an absolute path (e.g. `/var/folders/...`) produces `/notes//var/...`. Flask returns 308 redirect to strip the double-slash, but the test client does not follow redirects by default, so status is 308 not 200/404.
- **Fix:** Changed to `f"/notes{p}"` in `TestSaveNote` and `TestNoteMeta`.
- **Files modified:** `tests/test_api_extensions.py`
- **Commit:** ad2b87c

### State Deviation (Not a Bug)

The plan expected all 8 tests to fail (RED state) because the endpoints hadn't been implemented yet. However, a prior untracked session had already fully implemented all 8 endpoints in `engine/api.py` and created `engine/gui/` as a package with static assets. As a result, all 8 tests pass after the URL bug fix — the test suite acts as a GREEN regression suite rather than a RED scaffold. This is a positive deviation; the implementation contract is valid and all `must_haves` are satisfied.

## Success Criteria Check

- [x] `tests/test_api_extensions.py` has 8 test classes covering all new endpoints
- [x] All 8 tests pass (endpoints pre-implemented; URL bug fixed)
- [x] `engine/gui` package is importable; `main()` raises `NotImplementedError`
- [x] `pyproject.toml`: `pywebview>=5.0` in deps, `sb-gui` entry point registered
- [x] `uv.lock` updated with pywebview

## Self-Check: PASSED
