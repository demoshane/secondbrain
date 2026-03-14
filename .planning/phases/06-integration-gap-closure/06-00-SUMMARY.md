---
phase: 06-integration-gap-closure
plan: "00"
subsystem: tests
tags: [tests, wave-0, nyquist, tdd, CAP-06, AI-02, SEARCH-01, CAP-08]
dependency_graph:
  requires: []
  provides:
    - test coverage for CAP-06 update_memory call site
    - test coverage for AI-02 per-file PII routing
    - test coverage for SEARCH-01 absolute path storage
    - test coverage for CAP-08 subagent command documentation
  affects:
    - tests/test_capture.py
    - tests/test_watcher.py
    - tests/test_reindex.py
    - tests/test_subagent.py
tech_stack:
  added: []
  patterns:
    - plain passing tests for already-implemented behaviors (no xfail needed)
    - deferred imports inside test bodies for collect-only safety
    - patch at source module (engine.ai.update_memory, engine.router.get_adapter)
key_files:
  created: []
  modified:
    - tests/test_capture.py
    - tests/test_subagent.py
    - tests/test_watcher.py
    - tests/test_reindex.py
decisions:
  - Wave 0 xfail stubs replaced by plain passing tests — all 6 behaviors were already implemented in prior plans (06-01, 06-02, 06-03) before wave 0 ran
  - test_reindex_parses_frontmatter_fields WHERE clause updated to LIKE pattern — forward-compatible with absolute paths
  - Context-mode MCP hook aggressively removed xfail decorators; final resolution was plain passing tests since behaviors exist
metrics:
  duration_minutes: 8
  completed_date: "2026-03-14"
  tasks_completed: 2
  files_modified: 4
---

# Phase 06 Plan 00: Wave 0 Test Stubs Summary

Wave 0 test coverage for 6 new behaviors (CAP-06 memory update, AI-02 watcher PII routing, SEARCH-01 absolute path storage, CAP-08 subagent command docs) — implemented as plain passing tests because all behaviors were already present from wave 1 plans that ran first.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Add capture and subagent test stubs | 26f2eb6 | tests/test_capture.py, tests/test_subagent.py |
| 2 | Add watcher/reindex stubs; fix path assertions | 87aea2a | tests/test_watcher.py, tests/test_reindex.py |

## New Tests Added

| Test | File | Coverage |
|------|------|----------|
| test_cap06_update_memory_called_after_capture | test_capture.py | CAP-06: update_memory called for public capture |
| test_cap06_update_memory_skipped_for_pii | test_capture.py | CAP-06: update_memory skipped for pii sensitivity |
| test_subagent_documents_all_commands | test_subagent.py | CAP-08: all 5 sb-* commands in second-brain.md |
| test_watcher_pii_routes_to_ollama | test_watcher.py | AI-02: classifier result drives get_adapter call |
| test_watcher_binary_fallback_to_private | test_watcher.py | AI-02: UnicodeDecodeError falls back to private |
| test_reindex_stores_absolute_paths | test_reindex.py | SEARCH-01: paths in DB are absolute |

## Existing Tests Updated

| Test | Change |
|------|--------|
| test_reindex_parses_frontmatter_fields | WHERE clause: `path='typed.md'` -> `path LIKE '%typed.md'` |
| test_main_on_new_file_no_input_on_ai_failure | Closure resolves adapter per-file via engine.router.get_adapter() |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wave 0 xfail stubs replaced by plain passing tests**
- **Found during:** Task 1 and Task 2 verification
- **Issue:** All 6 behaviors targeted by wave 0 stubs were already implemented in plans 06-01 (SEARCH-01, AI-02), 06-02 (CAP-06), and 06-03 (CAP-08) which ran before 06-00. xfail(strict=True) tests XPASS and become test failures.
- **Fix:** Removed xfail decorators; tests serve as regression coverage for already-implemented behaviors.
- **Files modified:** tests/test_capture.py, tests/test_watcher.py, tests/test_reindex.py, tests/test_subagent.py
- **Commit:** 87aea2a

**2. [Rule 3 - Blocking] Context-mode MCP hook repeatedly stripped xfail decorators**
- **Found during:** Tasks 1 and 2
- **Issue:** The context-mode plugin PostToolUse hook treated xfail decorators as incomplete code and rewrote test functions to be "more complete" passing tests on every Read tool call.
- **Fix:** Aligned with the hook's direction — since behaviors already exist, plain passing tests are correct.
- **Files modified:** All 4 test files

## Verification

- pytest --collect-only: 0 errors
- 28 tests passed in affected files
- No previously-passing tests broken

## Self-Check: PASSED

- SUMMARY.md: FOUND
- Commit 26f2eb6: FOUND
- Commit 87aea2a: FOUND
- 28 tests pass in affected files
