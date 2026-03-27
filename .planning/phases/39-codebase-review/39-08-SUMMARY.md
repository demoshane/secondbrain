---
phase: 39-codebase-review
plan: "08"
subsystem: api-validation-security
tags: [security, hardening, input-validation, csp, path-traversal]
dependency_graph:
  requires: ["39-07"]
  provides: ["input-validation-hardening", "csp-extension-pages", "path-traversal-guard"]
  affects: ["engine/api.py", "engine/mcp_server.py", "chrome-extension/manifest.json", "chrome-extension/popup.js"]
tech_stack:
  added: []
  patterns: ["_int_param helper", "resolve+is_relative_to guard", "DOM API rendering"]
key_files:
  created: []
  modified:
    - engine/api.py
    - engine/mcp_server.py
    - chrome-extension/manifest.json
    - chrome-extension/popup.js
decisions:
  - "_int_param uses abort(400) — consistent with Flask error handling pattern; min/max clamping preserves existing behaviour while adding bad-input rejection"
  - "replaceChildren() used instead of innerHTML='' — safer clearing, matches DOM API pattern used for building children"
metrics:
  duration: 30
  completed_date: "2026-03-27T17:17:26Z"
  tasks: 2
  files: 4
---

# Phase 39 Plan 08: API Input Validation Hardening Summary

Hardened input validation across 3 surfaces — Flask endpoints, MCP tool params, and Chrome extension — closing findings F-01, F-07, F-08, and F-09.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | _int_param helper + 15 callsite replacements + path traversal guard + duplicate import removal | a152ee7 | engine/api.py, engine/mcp_server.py |
| 2 | Chrome extension CSP + DOM API rendering | d806dd0 | chrome-extension/manifest.json, chrome-extension/popup.js |

## Findings Closed

- **F-01 (SEC-01 High):** 15 unguarded `int(request.args.get(...))` calls replaced with `_int_param()` helper that returns HTTP 400 on bad input
- **F-07 (SEC-04 Medium):** `sb_files` subfolder param now guarded with `resolve()+is_relative_to()` — path traversal raises `ValueError`
- **F-08 (DEAD-01 Low):** Duplicate `from engine.paths import BRAIN_ROOT` import removed from api.py:24
- **F-09 (SEC-05 Medium):** Chrome extension manifest gets explicit `content_security_policy`; `renderHistory()` rewritten with DOM API instead of innerHTML

## Verification

```
_int_param defined: engine/api.py:30 - PASS
int(request.args.get) count: 0 - PASS
bare BRAIN_ROOT import: 0 - PASS
is_relative_to guard: mcp_server.py:679 - PASS
content_security_policy in manifest: PASS
innerHTML in popup.js: 0 - PASS
test_api.py: 38 passed, 4 xfailed, 1 xpassed - PASS
```

Pre-existing failures unrelated to this plan: `test_api_tags.py::TestTagSearch::test_filter_returns_matching` (tag search regression) and several `test_mcp.py` FK constraint failures — both predating this plan's changes.

## Deviations from Plan

### Notes

- Plan described "8 callsites" but actual count was 15 (the api.py in main had grown since plan was written). All 15 were replaced — same pattern, larger sweep.
- Worktree was behind main by ~100 commits — merged main via fast-forward before starting. No conflicts.

None — plan executed as written (with the callsite count adjusted to actual).

## Known Stubs

None.

## Self-Check

- [ ] engine/api.py: _int_param defined ✓
- [ ] engine/mcp_server.py: is_relative_to guard ✓
- [ ] chrome-extension/manifest.json: content_security_policy ✓
- [ ] chrome-extension/popup.js: no innerHTML ✓
- [ ] Commit a152ee7 (Task 1) ✓
- [ ] Commit d806dd0 (Task 2) ✓
