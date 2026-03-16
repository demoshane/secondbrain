---
phase: 24-playwright-gui-test-suite
plan: 02
subsystem: testing
tags: [playwright, pytest, flask, javascript, gui, sse, markdown]

# Dependency graph
requires:
  - phase: 24-playwright-gui-test-suite/24-01
    provides: gui_brain/live_server_url/seed_note_fn fixtures, 9 xfail stubs, Chromium installed
provides:
  - 3 green e2e tests: test_markdown_renders_as_html, test_viewer_scroll, test_title_sync
  - Documented pattern: PUT /notes/<path> expects "content" key (full frontmatter+body), not title+body
  - Documented pattern: SSE in test env requires POST /notes/refresh since watcher not started
affects: [24-03, 24-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Use .first on has_text locators to tolerate session-scoped DB accumulation across test runs"
    - "SSE broadcast in test env via POST /notes/refresh (watcher not running in daemon-thread server)"
    - "PUT /notes/<path> content= full frontmatter+body markdown string; no title/body keys"
    - "Viewer h1 comes from markdown body only — no automatic title injection; seed body must include # heading"

key-files:
  created: []
  modified: [tests/test_gui.py]

key-decisions:
  - "PUT /notes/<path> expects content key (full frontmatter+body string), not {title, body} as plan stated"
  - "SSE broadcast requires POST /notes/refresh in test env — start_note_observer() not called by daemon-thread Flask server"
  - "Viewer does not inject <h1> from frontmatter title — body must contain # heading for h1 assertion"
  - "Use .first on has_text locators — session-scoped DB accumulates notes across repeated test runs"

patterns-established:
  - "test_title_sync pattern: PUT content → POST /notes/refresh → wait sidebar locator → click → wait viewer h1"

requirements-completed: [TEST-01]

# Metrics
duration: 12min
completed: 2026-03-16
---

# Phase 24 Plan 02: Playwright GUI Test Wave 2 Summary

**3 green Playwright e2e tests: markdown-renders-as-html, viewer-scroll, and title-sync via PUT+SSE-refresh**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-16T20:36:00Z
- **Completed:** 2026-03-16T20:48:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Replaced 3 xfail stubs with real Playwright assertions covering markdown rendering, scroll regression, and title sync
- Verified `#viewer` renders `<h1>`, `<strong>`, `<li>` and contains no raw `#` or `**` characters
- Verified `viewer.scrollTop > 0` after programmatic set (scroll-lock regression guard)
- Verified sidebar and viewer h1 both reflect new title after PUT + SSE refresh

## Task Commits

1. **Task 1: Implement test_markdown_renders_as_html and test_viewer_scroll** - `7368940` (feat)
2. **Task 2: Implement test_title_sync** - `fdf9975` (feat)

## Files Created/Modified

- `tests/test_gui.py` - replaced 3 xfail Wave 2 stubs with working implementations

## Decisions Made

- PUT `/notes/<path>` uses `content` key (full frontmatter+body string) — plan specified `{title, body}` which is incorrect
- SSE broadcasts via `POST /notes/refresh` in test env — `start_note_observer()` is not called by the daemon-thread test server so watcher is absent
- `#viewer` only renders markdown body; frontmatter title is not injected as `<h1>` — seed body must include `# heading` for h1 assertions
- `.first` added to `has_text` locators — session-scoped DB accumulates notes across repeated test invocations causing strict-mode violations

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PUT route expects "content" key, not {"title", "body"}**
- **Found during:** Task 2 (test_title_sync)
- **Issue:** Plan specified `json={"title": "Updated Title", "body": "body content"}` but actual API reads `body.get("content", "")` — passing title/body silently wrote empty content to the file
- **Fix:** Changed to `json={"content": "---\ntitle: Updated Title\n...\n---\n\n# Updated Title\n\nbody content\n"}`
- **Files modified:** tests/test_gui.py
- **Verification:** PUT returns 200 and file content updated correctly
- **Committed in:** fdf9975 (Task 2 commit)

**2. [Rule 1 - Bug] SSE does not propagate in test env without watcher**
- **Found during:** Task 2 (test_title_sync)
- **Issue:** Plan assumed PUT triggers SSE via watcher; `start_note_observer()` is never called by the daemon-thread Flask server — browser SSE client gets no `note_updated` event
- **Fix:** Added `POST /notes/refresh` call after PUT to trigger `_broadcast()` inline; sidebar reloads via SSE `created` event
- **Files modified:** tests/test_gui.py
- **Verification:** Sidebar updates with new title within 5s; test passes
- **Committed in:** fdf9975 (Task 2 commit)

**3. [Rule 1 - Bug] Viewer h1 requires heading in body, not just frontmatter title**
- **Found during:** Task 2 (test_title_sync)
- **Issue:** Plan expected `#viewer h1` to reflect the frontmatter title; viewer renders `marked.parse(body)` only — frontmatter title is not injected as `<h1>`
- **Fix:** Changed seed body to `"# Original Title\n\nbody content"` and PUT content to include `# Updated Title\n\nbody content`
- **Files modified:** tests/test_gui.py
- **Verification:** Viewer h1 assertion passes after clicking updated note
- **Committed in:** fdf9975 (Task 2 commit)

**4. [Rule 1 - Bug] Strict mode violation on has_text locator across test runs**
- **Found during:** Task 1 (test_viewer_scroll)
- **Issue:** Session-scoped DB retains notes from prior runs; `has_text="Long Note"` matched 2 sidebar entries
- **Fix:** Added `.first` to all `has_text` locators
- **Files modified:** tests/test_gui.py
- **Verification:** No strict-mode playwright error; test passes
- **Committed in:** 7368940 (Task 1 commit)

---

**Total deviations:** 4 auto-fixed (all Rule 1 - bugs in plan's interface descriptions)
**Impact on plan:** All fixes necessary for correct behavior. No scope creep. The plan's interface comments for PUT were incorrect — actual API contract documented in decisions.

## Issues Encountered

None beyond the auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 2 complete: 3 green tests, 6 remaining stubs (Wave 3-4)
- Wave 3 (24-03): `test_sse_live_refresh`, `test_delete_flow` — will need `start_note_observer()` called in fixture or alternative SSE strategy
- Confirmed: POST /notes/refresh is the reliable SSE trigger in test env — use for Wave 3 as well

---
*Phase: 24-playwright-gui-test-suite*
*Completed: 2026-03-16*
