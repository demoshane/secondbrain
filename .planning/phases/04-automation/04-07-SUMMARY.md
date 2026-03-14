---
phase: 04-automation
plan: "07"
subsystem: backlinks
tags: [links, people, profiles, capture, tdd]
dependency_graph:
  requires: [04-01]
  provides: [PEOPLE-03, PEOPLE-04, PEOPLE-05, SEARCH-03]
  affects: [engine/links.py, engine/capture.py, tests/test_links.py]
tech_stack:
  added: []
  patterns: [ensure-then-use, idempotent-file-creation, tdd-red-green]
key_files:
  created: []
  modified:
    - engine/links.py
    - tests/test_links.py
decisions:
  - "ensure_person_profile() creates skeleton on first access — eliminates silent skip for missing people profiles"
  - "Skeleton format: '# {Display Name}\n\n## Backlinks\n' where display name derives from slug via title-case"
  - "add_backlinks() calls ensure_person_profile() unconditionally — profile is always guaranteed to exist before backlink append"
metrics:
  duration_minutes: 5
  completed_date: "2026-03-14"
  tasks_completed: 2
  files_changed: 2
---

# Phase 4 Plan 07: Ensure Person Profile on Capture Summary

**One-liner:** Auto-create people/alice-smith.md with name heading and Backlinks section when missing, eliminating the silent skip in add_backlinks().

## What Was Built

Added `ensure_person_profile(slug, brain_root)` to `engine/links.py` and replaced the `if not matches: continue` guard in `add_backlinks()` with a call to it. This means `sb-capture --people 'Alice Smith'` now always creates the person profile when none exists, appends the backlink, and inserts the relationships row — satisfying PEOPLE-03, PEOPLE-04, PEOPLE-05.

Gap 3 (sb-search --type people 'Alice' returning alice-smith.md) resolves automatically since the file now exists on disk and is indexed by the existing search pipeline.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add ensure_person_profile() and fix add_backlinks() silent skip | 1d016ab | engine/links.py, tests/test_links.py |
| 2 | Verify add_backlinks is called from capture_note() | (no change) | engine/capture.py already correct |

## Decisions Made

- `ensure_person_profile()` creates the file unconditionally on first access (not deferred to a separate command)
- Skeleton is minimal: `# {Display Name}\n\n## Backlinks\n` — display name derived via `slug.replace('-', ' ').title()`
- Idempotent: if file already exists, returns path without reading or modifying content
- Task 2 required no code change — `capture_note()` already had the deferred import + `add_backlinks` call from plan 04-01

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

**Note:** `test_missing_person_skipped` was updated to assert the new auto-create behaviour (profile now created instead of silently skipped). The old assertion `result is None` was kept structurally but the new assertion `profile.exists()` replaces the skip expectation — this is correct per the plan spec.

## Verification

- `tests/test_links.py`: 10 passed, 1 xfail (work templates xfail — unrelated)
- `tests/test_capture.py` + `tests/test_search.py`: all pass
- Pre-existing failures in `test_paths.py`, `test_rag.py`, `test_watcher.py` were present before this plan (those files shown as modified in initial git status from other in-progress work)

## Self-Check: PASSED

- `engine/links.py` exists and contains `ensure_person_profile` and updated `add_backlinks`
- Commit `1d016ab` exists in git log
- `tests/test_links.py` contains all three new test functions
