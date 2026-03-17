---
phase: 26-intelligence-features
plan: "01"
subsystem: tests
tags: [tdd, xfail, brain-health, intelligence, digest]
dependency_graph:
  requires: []
  provides:
    - tests/test_brain_health.py (7 xfail stubs for ENGL-04/ENGL-05)
    - tests/test_intelligence.py (2 new xfail stubs for ENGL-03/GUIF-02)
    - tests/test_digest.py (1 new xfail stub for ENGL-03 column fix)
  affects:
    - engine/brain_health.py (Wave 2 implementation target)
    - engine/intelligence.py (Wave 2 implementation target)
    - engine/digest.py (Wave 2 fix target)
tech_stack:
  added: []
  patterns:
    - xfail(strict=False) for pre-implementation stubs — suite stays green before Wave 2 ships
    - local client fixture in test_brain_health.py patches both engine.db.DB_PATH and engine.paths.DB_PATH
key_files:
  created:
    - tests/test_brain_health.py
  modified:
    - tests/test_intelligence.py
    - tests/test_digest.py
decisions:
  - xfail(strict=False) used (not pytest.skip) — stubs are collected, counted, and auto-promote to pass once Wave 2 ships
  - Local client fixture in test_brain_health.py rather than shared conftest — conftest has no client fixture and scope is isolated to this feature
metrics:
  duration: "3 min"
  completed: "2026-03-17"
  tasks_completed: 2
  files_changed: 3
---

# Phase 26 Plan 01: Wave 0 xfail Test Stubs Summary

**One-liner:** Created 10 xfail test stubs across 3 files covering brain health checks, on-demand recap, action item dedup, and digest column name fix.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create tests/test_brain_health.py with xfail stubs | 6f705e4 | tests/test_brain_health.py |
| 2 | Add xfail stubs to test_intelligence.py and test_digest.py | 212825d | tests/test_intelligence.py, tests/test_digest.py |

## What Was Built

**tests/test_brain_health.py** (new, 7 stubs):
- `test_get_orphan_notes_returns_notes_with_no_inbound_links` — ENGL-04
- `test_get_orphan_notes_excludes_digest_and_memory_types` — ENGL-04
- `test_get_duplicate_candidates_returns_pairs_above_threshold` — ENGL-05
- `test_compute_health_score_returns_100_for_clean_brain` — ENGL-05
- `test_compute_health_score_reduces_for_orphans` — ENGL-05
- `test_compute_health_score_zero_notes_returns_100` — ENGL-05
- `test_brain_health_api_returns_score_and_checks` — ENGL-04/ENGL-05 (GET /brain-health endpoint)

**tests/test_intelligence.py** (2 stubs appended):
- `test_generate_recap_on_demand_returns_string` — ENGL-03/GUIF-02
- `test_extract_action_items_no_duplicate_on_recapture` — GUIF-02

**tests/test_digest.py** (1 stub appended):
- `test_generate_digest_open_actions_uses_correct_column` — ENGL-03 (column name bug: action_text -> text, status -> done)

## Verification

Final run: `1 failed, 24 passed, 9 xfailed, 1 xpassed`

- All 10 new stubs collected and xfail/xpass (none ERROR)
- 1 pre-existing failure (`TestClaudeMdHook::test_claude_md_contains_session_hook`) — not introduced by this plan

## Deviations from Plan

**1. [Rule 2 - Missing Functionality] Added local `client` fixture to test_brain_health.py**
- **Found during:** Task 1
- **Issue:** conftest.py has no `client` fixture for API testing; test_brain_health.py needs one for `test_brain_health_api_returns_score_and_checks`
- **Fix:** Added local `client` fixture that patches `engine.db.DB_PATH` and `engine.paths.DB_PATH` to tmp SQLite, inits schema, returns `app.test_client()`
- **Files modified:** tests/test_brain_health.py
- **Commit:** 6f705e4

## Self-Check: PASSED

- tests/test_brain_health.py: FOUND
- tests/test_intelligence.py: FOUND
- tests/test_digest.py: FOUND
- Commit 6f705e4: FOUND
- Commit 212825d: FOUND
