---
phase: 39-codebase-review
plan: "05"
subsystem: dead-code-audit
tags: [audit, dead-code, optimisation, refactoring]
dependency_graph:
  requires: []
  provides: [39-findings-deadcode.md]
  affects: [engine/templates.py, engine/api.py, engine/links.py]
tech_stack:
  added: []
  patterns: [import-graph analysis, grep-evidence methodology]
key_files:
  created:
    - .planning/phases/39-codebase-review/39-findings-deadcode.md
  modified: []
decisions:
  - "templates.py is dead — zero engine callers, only isolated test import"
  - "NoteEditor.tsx is alive — reachable via NoteViewer.tsx import chain"
  - "rag.py is alive — used via lazy import in ai.py ask_followup_questions"
  - "ratelimit.py is alive — watcher.py depends on RateLimiter"
  - "sharding.py is implemented but unwired from any user-facing surface"
metrics:
  duration_seconds: 900
  completed_date: "2026-03-27"
  tasks_completed: 1
  files_changed: 1
---

# Phase 39 Plan 05: Dead Code + Optimisation Audit Summary

Dead code and optimisation audit across backend (39 Python modules) and frontend (24 React/TS components). Produces 9 severity-ranked findings covering dead modules, duplicate imports, stale patterns, and duplicate logic.

## What Was Done

Systematically audited all dead code candidates from RESEARCH.md using import graph evidence:

1. Grepped all `engine/` and `tests/` for each candidate module's import
2. Cross-referenced `pyproject.toml [project.scripts]` for CLI entry points
3. Checked for dynamic imports (`importlib`, `__import__`, lazy imports in function bodies)
4. Traced `NoteEditor.tsx` through the full `App.tsx` import tree
5. Identified duplicate logic patterns (BRAIN_PATH inline lookups, json.loads pattern)
6. Flagged deprecated Python API usage (`datetime.utcnow()`)

## Key Findings

### Dead (DEAD-01)
- `engine/templates.py` — zero engine callers, only an isolated test. Not wired into the capture pipeline despite being purpose-built for per-type note body templates.

### Alive (not dead, despite research candidates)
- `engine/rag.py` — used via lazy import in `ai.py:91` inside `ask_followup_questions()`
- `engine/ratelimit.py` — `watcher.py` imports `RateLimiter`; alive and tested
- `engine/ai.py` — called from `capture.py` and has `sb-update-memory` CLI entry
- `frontend/src/components/NoteEditor.tsx` — not in App.tsx directly, but reachable via `NoteViewer.tsx:8`

### Optimisation Opportunities
- `engine/api.py`: duplicate `BRAIN_ROOT` import on line 24+25; 13 inline `os.environ.get(BRAIN_PATH)` calls that should use the imported `BRAIN_ROOT` constant
- `engine/api.py`: 5 deprecated `/people` route aliases still live; one frontend caller (`IntelligencePage.tsx`) still uses the old route
- `json.loads(col or "[]")` duplicated 13x across 5 modules — no shared helper exists
- `datetime.utcnow()` used 33x across 13 modules — deprecated in Python 3.12+
- `engine/sharding.py` — implemented and tested but unwired from any CLI/API surface
- `engine/links.py::ensure_person_profile()` — writes to `brain_root/person/` (singular) but canonical path is `people/` (plural)

## Deviations from Plan

None — plan executed exactly as written. All acceptance criteria met:
- 39-findings-deadcode.md created with dead module assessment table
- All 4 RESEARCH.md candidates (rag.py, templates.py, ratelimit.py, ai.py) assessed with grep evidence
- NoteEditor.tsx verdict documented (alive, not dead)
- No module marked dead without checking pyproject.toml scripts
- Each finding includes import count evidence

## Known Stubs

None. This plan produces a findings document only — no code changes, no stubs.

## Self-Check: PASSED

- [x] `.planning/phases/39-codebase-review/39-findings-deadcode.md` exists (12655 bytes)
- [x] grep -c "DEAD-" returns 21 (9 findings with multiple references)
- [x] Commit verified: file present in git history (`71cff3c` — parallel agent staging)
- [x] Dead module assessment table covers all 4 RESEARCH.md candidates
