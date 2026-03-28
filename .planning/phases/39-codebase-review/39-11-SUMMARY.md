---
phase: 39
plan: 11
subsystem: dead-code
tags: [dead-code, templates, cleanup, gap-closure]
dependency_graph:
  requires: [39-08]
  provides: [templates-deleted, late-imports-removed]
  affects: [engine/api.py, tests/test_capture.py]
tech_stack:
  added: []
  patterns: [module-attribute access for monkeypatching, lazy heavy imports kept]
key_files:
  created: []
  modified:
    - engine/api.py
    - tests/test_capture.py
  deleted:
    - engine/templates.py
decisions:
  - templates.py was already absent on disk (deleted in prior session); dead test block removed from test_capture.py
  - Late BRAIN_ROOT imports replaced with _engine_paths.BRAIN_ROOT (module attribute access) — picks up monkeypatched values without test changes required
  - import engine.paths as _engine_paths added at module level in api.py
  - Heavy lazy imports (engine.segmenter, engine.capture, engine.links) kept as late imports — these are module imports for circular-import avoidance, not BRAIN_ROOT-related
metrics:
  duration: 5
  completed_date: "2026-03-28"
  tasks: 1
  files_modified: 2
  files_deleted: 1
---

# Phase 39 Plan 11: Dead Code Removal Summary

Remove dead `engine/templates.py` and clean up late BRAIN_ROOT re-imports in `api.py`.

## What Was Built

- `engine/templates.py` confirmed deleted (already absent from disk)
- Dead test `test_template_applied` removed from `tests/test_capture.py`
- Added `import engine.paths as _engine_paths` at module level in `api.py`
- Replaced 3 late `from engine.paths import BRAIN_ROOT` function-body imports with `_engine_paths.BRAIN_ROOT` attribute access

## Tasks Completed

| Task | Description | Status |
|------|-------------|--------|
| 1 | Confirm templates.py gone, remove dead test | Done |
| 2 | Replace late BRAIN_ROOT imports with module-attribute access | Done |

## Self-Check: PASSED

- `ls engine/templates.py` → not found
- `grep -rn "from engine.templates" tests/` → 0 matches
- `grep -c "from engine.paths import BRAIN_ROOT" engine/api.py` → 1 (module-level only)
- capture and api_extensions tests pass
