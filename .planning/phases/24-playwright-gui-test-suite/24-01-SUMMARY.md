---
phase: 24-playwright-gui-test-suite
plan: 01
subsystem: testing
tags: [playwright, pytest, flask, javascript, gui]

# Dependency graph
requires:
  - phase: 23-navigation-polish
    provides: completed GUI with tag chips, collapsible sections, create-note flow
provides:
  - pytest-playwright 0.5+ installed with Chromium headless binary
  - 9 xfail stub tests in tests/test_gui.py (collectable, Wave 2-4)
  - gui_brain / live_server_url / base_url / seed_note_fn session fixtures in conftest.py
  - window.API_BASE injection in /ui route + app.js fallback pattern
affects: [24-02, 24-03, 24-04]

# Tech tracking
tech-stack:
  added: [pytest-playwright>=0.5.0, Chrome Headless Shell 145 (playwright chromium)]
  patterns: [session-scoped Flask daemon-thread server, window.API_BASE injection via host_url]

key-files:
  created: [tests/test_gui.py]
  modified: [engine/gui/static/app.js, engine/api.py, tests/conftest.py, pyproject.toml]

key-decisions:
  - "window.API_BASE injected by /ui route using request.host_url.rstrip('/'); app.js uses || fallback so production pywebview is unchanged"
  - "engine._db does not exist; DB_PATH lives in engine.paths and is imported by engine.db — patch both modules for session-scoped isolation"
  - "Flask server started via daemon thread (not pytest-flask live_server) to avoid playwright teardown hang"
  - "gui_brain fixture patches engine.db.DB_PATH + engine.paths.DB_PATH as Path objects (not strings)"

patterns-established:
  - "GUI test isolation: set os.environ['BRAIN_PATH'] + patch engine.db.DB_PATH + engine.paths.DB_PATH before Flask starts"
  - "Random port selection: bind to port 0, read getsockname()[1], close, then Flask.run(port=port)"
  - "Server readiness: poll /health with urllib.request up to 2 seconds before yielding fixture"

requirements-completed: [TEST-01]

# Metrics
duration: 15min
completed: 2026-03-16
---

# Phase 24 Plan 01: Playwright GUI Test Infrastructure Summary

**pytest-playwright + Chromium installed; /ui route injects window.API_BASE; 9 collectable xfail stubs + session fixtures ready for Wave 2**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-16T20:10:00Z
- **Completed:** 2026-03-16T20:25:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Patched `app.js` to use `window.API_BASE || 'http://127.0.0.1:37491'` and `/ui` route to inject the correct base URL, so browser fetch() calls hit the test server port instead of production port
- Installed pytest-playwright 0.7.2 + Chrome Headless Shell 145 via `playwright install chromium`
- Created session-scoped conftest fixtures: `gui_brain` (isolated tmp brain + DB), `live_server_url` (Flask daemon thread on random port), `base_url` (pytest-playwright override), `seed_note_fn` (write .md + INSERT into SQLite)
- Created `tests/test_gui.py` with 9 xfail stubs covering SC-2 through SC-10, all collectable and exiting 0

## Task Commits

1. **Task 1: Patch app.js + /ui route to inject window.API_BASE** - `b21f4cb` (feat)
2. **Task 2: Add pytest-playwright to pyproject.toml dev deps and install browser** - `7b8e048` (chore)
3. **Task 3: Add GUI fixtures to conftest.py and create stub test_gui.py** - `fb8b705` (feat)

## Files Created/Modified

- `engine/gui/static/app.js` - line 2: `const API = window.API_BASE || 'http://127.0.0.1:37491'`
- `engine/api.py` - `/ui` route now injects `<script>window.API_BASE = "...";</script>` before `</head>`
- `pyproject.toml` - added `pytest-playwright>=0.5.0` to dev optional-dependencies
- `tests/conftest.py` - appended Phase 24 GUI fixtures block (gui_brain, live_server_url, base_url, seed_note_fn)
- `tests/test_gui.py` - created with 9 xfail stub tests (SC-2 through SC-10)

## Decisions Made

- Used `request.host_url.rstrip("/")` for API_BASE injection — correct for any port, identical to production behavior on 37491
- Flask started via `threading.Thread(daemon=True)` instead of pytest-flask `live_server` to avoid playwright teardown hang
- Patched both `engine.db.DB_PATH` and `engine.paths.DB_PATH` as `Path` objects; `engine._db` does not exist (plan's comment was incorrect — `engine.db` is the correct module)
- Random port via `socket.bind(("127.0.0.1", 0))` + `getsockname()[1]` — avoids port conflicts between test runs

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] engine._db module does not exist**
- **Found during:** Task 3 (conftest fixtures)
- **Issue:** Plan specified `import engine._db as _db` and `_db.DB_PATH = tmp_db` — `engine._db` does not exist; `DB_PATH` is defined in `engine.paths` and imported into `engine.db`
- **Fix:** Changed to `import engine.db as _db` and `import engine.paths as _paths`; patched both `_db.DB_PATH` and `_paths.DB_PATH` as `Path` objects to ensure `get_connection()` uses the tmp db
- **Files modified:** tests/conftest.py
- **Verification:** `pytest tests/test_api.py` passes all 24 tests; `pytest tests/test_gui.py --collect-only` collects 9 tests
- **Committed in:** fb8b705 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in plan's module reference)
**Impact on plan:** Essential fix — without it, conftest would raise ModuleNotFoundError for every test in the project.

## Issues Encountered

None beyond the auto-fixed deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 9 test stubs collectable; Wave 2 (plans 24-02 through 24-04) can implement them
- `gui_brain`, `live_server_url`, `base_url`, `seed_note_fn` fixtures available to all test_gui.py tests
- Chromium binary cached at `/Users/tuomasleppanen/Library/Caches/ms-playwright/chromium_headless_shell-1208`
- No blockers for Wave 2

---
*Phase: 24-playwright-gui-test-suite*
*Completed: 2026-03-16*
