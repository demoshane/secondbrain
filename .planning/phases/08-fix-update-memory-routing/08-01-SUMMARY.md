---
phase: 08-fix-update-memory-routing
plan: "01"
subsystem: ai
tags: [model-router, claude-adapter, memory-update, ai-05]

requires:
  - phase: 08-fix-update-memory-routing
    provides: RED stub test_update_memory_routing_uses_config (08-00)
  - phase: 03-ai-layer
    provides: ModelRouter (_router.get_adapter) and ClaudeAdapter

provides:
  - update_memory() routes through ModelRouter — config.toml public_model drives adapter selection
  - ClaudeAdapter direct import removed from engine/ai.py
  - AI-05 gap closed for memory update path

affects: [engine/ai.py consumers, capture.py, any test patching update_memory adapter]

tech-stack:
  added: []
  patterns:
    - "update_memory() uses _router.get_adapter('public', config_path) — same pattern as ask_followup_questions()"

key-files:
  created: []
  modified:
    - engine/ai.py

key-decisions:
  - "update_memory() hardcodes sensitivity='public' internally — call site in capture.py already guards PII before calling this function"
  - "ClaudeAdapter import removed — engine/ai.py now uses only engine.router module ref for all adapter access"

patterns-established:
  - "All AI adapter calls in ai.py go through _router.get_adapter(sensitivity, config_path) — no direct adapter instantiation"

requirements-completed: [AI-05]

duration: 5min
completed: 2026-03-15
---

# Phase 08 Plan 01: Fix update_memory() Routing Summary

**`update_memory()` now routes through ModelRouter via `_router.get_adapter("public", config_path)` — config.toml public_model controls adapter selection, closing AI-05 gap**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-15T09:40:00Z
- **Completed:** 2026-03-15T09:45:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Fixed `update_memory()` to call `_router.get_adapter("public", config_path)` instead of hardcoded `ClaudeAdapter()`
- Updated `config_path` docstring to reflect its active role in AI-05 routing
- Removed unused `ClaudeAdapter` import from `engine/ai.py`
- Full test suite: 128 passed, 5 skipped, 1 xfailed — zero regressions

## Task Commits

1. **Task 1: Fix update_memory() to route through ModelRouter** - `75465d0` (feat)
2. **Task 2: Full suite smoke check** - no commit (no code changes)

## Files Created/Modified

- `engine/ai.py` - Replaced `ClaudeAdapter()` with `_router.get_adapter("public", config_path)`; removed `ClaudeAdapter` import; updated docstring

## Decisions Made

- Hardcoded `"public"` sensitivity in `update_memory()` — the call site in `capture.py` already guards PII via `if sensitivity != "pii"` before invoking this function, so no sensitivity parameter needed on `update_memory()` itself.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- AI-05 fully closed: both `ask_followup_questions()` and `update_memory()` now route through ModelRouter
- `engine/ai.py` contains no direct adapter instantiation — all adapter calls go via `_router.get_adapter`
- Phase 08 complete

---
*Phase: 08-fix-update-memory-routing*
*Completed: 2026-03-15*
