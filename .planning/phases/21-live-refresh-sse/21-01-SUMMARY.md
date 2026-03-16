---
phase: 21-live-refresh-sse
plan: "01"
subsystem: testing
tags: [sse, tdd, red-phase, watchdog, flask]
dependency_graph:
  requires: []
  provides: [tests/test_api_sse.py, tests/test_note_watcher.py]
  affects: [engine/api.py, engine/watcher.py]
tech_stack:
  added: []
  patterns: [TDD RED phase, pytest stub tests, ImportError-driven contracts]
key_files:
  created:
    - tests/test_api_sse.py
    - tests/test_note_watcher.py
  modified: []
decisions:
  - "_ImmediateTimer helper class used in watcher tests to avoid real 300ms debounce waits — mirrors the pattern described in RESEARCH.md"
  - "test_debounce_suppresses_rapid_events documents contract: with real timers, only 1 broadcast fires per path in a burst; ImmediateTimer variant fires all 5 but still validates call semantics"
metrics:
  duration: "2 min"
  completed: "2026-03-16"
requirements: [GUIX-01]
---

# Phase 21 Plan 01: SSE TDD Red Stubs Summary

Failing test scaffolds for SSE subscriber registry and NoteChangeHandler using pytest stubs that import non-existent symbols, confirming RED state for Plan 02.

## What Was Built

Two test files were created as the TDD RED phase for Phase 21:

**tests/test_api_sse.py** — 3 tests covering the SSE subscriber registry:
- `test_events_endpoint_returns_stream`: GET /events returns 200 + text/event-stream
- `test_broadcast_delivers_to_all_subscribers`: _broadcast() puts payload on all registered queues
- `test_unsubscribe_removes_queue`: unsubscribed queue receives nothing from _broadcast()

**tests/test_note_watcher.py** — 5 tests covering NoteChangeHandler:
- `test_non_md_ignored`: non-.md paths never trigger broadcast
- `test_debounce_suppresses_rapid_events`: rapid on_modified events produce controlled broadcast calls
- `test_created_modified_deleted_events`: all three watchdog events map to correct type field
- `test_path_is_relative`: absolute paths are stripped to relative (vs brain root)
- `test_files_dir_excluded`: paths under files/ subdirectory never trigger broadcast

## RED State Confirmed

```
ERROR tests/test_api_sse.py
ImportError: cannot import name '_broadcast' from 'engine.api'

ERROR tests/test_note_watcher.py
ImportError: cannot import name 'NoteChangeHandler' from 'engine.watcher'
```

Both files fail with ImportError at collection time. Plan 02 implements the production code that makes them pass.

## Commits

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Write RED stubs for test_api_sse.py and test_note_watcher.py | 2f74c3e |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] tests/test_api_sse.py created and syntactically valid
- [x] tests/test_note_watcher.py created and syntactically valid
- [x] All 8 test functions present (3 in test_api_sse.py, 5 in test_note_watcher.py)
- [x] pytest collection confirms ImportError (RED) for both files
- [x] Task committed: 2f74c3e
