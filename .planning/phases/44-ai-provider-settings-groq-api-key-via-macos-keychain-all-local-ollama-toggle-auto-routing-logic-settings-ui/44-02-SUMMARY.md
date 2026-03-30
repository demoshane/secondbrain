---
phase: 44-ai-provider-settings
plan: "02"
subsystem: api
tags: [groq, keychain, flask, api-endpoints, ask-brain, provider-routing]
dependency_graph:
  requires:
    - phase: "44-01"
      provides: GroqAdapter, FallbackAdapter.used_fallback, router get_adapter feature param
  provides:
    - Flask Keychain endpoints (GET/POST/DELETE /config/groq)
    - Groq connection test endpoint (POST /config/groq/test)
    - Groq settings persistence (GET/PUT /config/groq-settings)
    - ask_brain() returns provider field in response dict
  affects: [engine/api.py, engine/intelligence.py, frontend-settings-ui]
tech-stack:
  added: []
  patterns: [lazy-import-keyring, provider-detection-tuple-return, tdd-red-green]
key-files:
  created: []
  modified:
    - engine/api.py
    - engine/intelligence.py
    - tests/test_api.py
key-decisions:
  - "GET/PUT /config/groq-settings patches engine.paths.CONFIG_PATH only (not engine.config_loader.CONFIG_PATH — that module has no such attribute)"
  - "ask_brain _call_adapter returns (answer, provider) tuple; provider precedence: groq > fallback > default"
  - "feature='ask_brain' only passed for public sensitivity path — PII still uses existing routing"
requirements-completed: [D-08, D-09, D-12]
duration: 18min
completed: "2026-03-30"
---

# Phase 44 Plan 02: Flask API Groq Endpoints + ask_brain Provider Wiring Summary

**Six Flask endpoints for Groq Keychain management and settings persistence, plus ask_brain() provider detection surfaced in /ask response for frontend toast logic.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-03-30T15:00:00Z
- **Completed:** 2026-03-30T15:18:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- 6 new Flask endpoints: GET/POST/DELETE /config/groq, POST /config/groq/test, GET/PUT /config/groq-settings
- ask_brain() `_call_adapter` refactored to return `(answer, provider)` tuple with Groq/fallback/default detection
- `feature="ask_brain"` passed to router for public sensitivity path only
- /ask response gains `"provider"` key automatically via existing `return jsonify(result)` passthrough
- 13 new tests, all passing; total 95 pass / 4 xfailed across api+router+adapters

## Task Commits

1. **Task 1 (RED):** Failing tests for Groq endpoints and ask_brain provider - `b07034f` (test)
2. **Task 1 (GREEN):** 6 Groq Flask endpoints - `ee4a4c4` (feat)
3. **Task 2:** Wire ask_brain() feature param and provider field - `dd75ce8` (feat)

## Files Created/Modified

- `engine/api.py` - 6 new Groq config endpoints added after `/config/me` block
- `engine/intelligence.py` - `_call_adapter` refactored to `tuple[str, str]`, provider detection logic, `ask_brain` return gains `provider` key
- `tests/test_api.py` - `TestGroqConfig` (12 tests) and `TestAskBrainProvider` (1 test) added

## Decisions Made

- `GET /config/groq-settings` and `PUT /config/groq-settings` use `from engine.paths import CONFIG_PATH` inside function body (lazy import) — consistent with existing `/config/me` pattern
- Test for groq-settings only patches `engine.paths.CONFIG_PATH` — `engine.config_loader` does not expose CONFIG_PATH as module attribute, so patching the paths module is sufficient
- `_call_adapter` returns `(answer, provider)` tuple; provider precedence: `groq` (FallbackAdapter with GroqAdapter primary that succeeded) > `fallback` (used_fallback=True) > `default`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test patching engine.config_loader.CONFIG_PATH caused AttributeError**

- **Found during:** Task 1 GREEN phase (test run)
- **Issue:** Test template patched `engine.config_loader.CONFIG_PATH` but that attribute doesn't exist on the module. The endpoint uses `from engine.paths import CONFIG_PATH` lazily, so only `engine.paths.CONFIG_PATH` needs patching.
- **Fix:** Removed `monkeypatch.setattr(_cl, "CONFIG_PATH", fake_config)` line from both groq-settings tests.
- **Files modified:** `tests/test_api.py`
- **Verification:** 12 groq tests all pass
- **Committed in:** ee4a4c4

---

**Total deviations:** 1 auto-fixed (Rule 1 - test bug)
**Impact on plan:** One-line test fix. No scope change.

## Issues Encountered

None beyond the one test deviation above.

## Self-Check: PASSED

- engine/api.py: GET/POST/DELETE /config/groq endpoints FOUND
- engine/api.py: POST /config/groq/test endpoint FOUND
- engine/api.py: GET/PUT /config/groq-settings endpoints FOUND
- engine/api.py: allowed_groq_keys allowlist FOUND
- engine/api.py: gsk_ prefix check FOUND
- engine/api.py: PasswordDeleteError catch FOUND
- engine/intelligence.py: feature assigned "ask_brain" for public path FOUND (line 1165: `feature = "ask_brain" if sensitivity == "public" else ""`)
- engine/intelligence.py: adapter.used_fallback check FOUND
- engine/intelligence.py: "provider" key in return dict FOUND
- Commits b07034f, ee4a4c4, dd75ce8: all present in git log

## Known Stubs

None — all endpoints are fully wired. Provider detection in ask_brain() is live.

## Next Phase Readiness

- All API contracts Plan 03 (Settings UI) needs are now available
- Provider field in /ask response ready for frontend toast logic
- No blockers

---
*Phase: 44-ai-provider-settings*
*Completed: 2026-03-30*
