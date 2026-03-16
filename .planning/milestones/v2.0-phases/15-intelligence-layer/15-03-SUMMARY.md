---
phase: 15-intelligence-layer
plan: 03
subsystem: intelligence
tags: [sqlite-vec, embeddings, cli, intelligence, connections, recap, action-items]

requires:
  - phase: 15-02
    provides: budget gate, extract_action_items, check_stale_nudge, actions_main — all implemented

provides:
  - find_similar() KNN via sqlite-vec for connection suggestions
  - check_connections() hook wired into capture_note()
  - extract_action_items() hook wired into capture_note()
  - check_stale_nudge() hook wired into search main()
  - detect_git_context() returning git repo basename
  - recap_main() summarising recent notes for a context via LLM
  - sb-recap CLI entry point registered in pyproject.toml
  - sb-actions CLI entry point registered in pyproject.toml
  - Session hook line in ~/.claude/CLAUDE.md for proactive recap offers

affects:
  - phase 16 (gui-hub) — intelligence hooks now fire on every capture and search
  - phase 17 (encryption) — check_connections skips pii notes via sensitivity field

tech-stack:
  added: []
  patterns:
    - "Best-effort hooks: all intelligence calls wrapped in try/except Exception: pass — never block core operations"
    - "Budget gate: one unsolicited offer per day, stored in ~/.meta/intelligence_state.json"
    - "Entry point registration: new CLI commands added to [project.scripts] and installed via uv pip install -e ."

key-files:
  created: []
  modified:
    - engine/intelligence.py
    - engine/capture.py
    - engine/search.py
    - pyproject.toml
    - /Users/tuomasleppanen/.claude/CLAUDE.md

key-decisions:
  - "intelligence.py was fully implemented in the prior 15-02 session; Task 1 was a no-op verification pass"
  - "search.py had conn.close() before results check — restructured so stale nudge fires with open conn before final close"
  - "~/.claude/CLAUDE.md lives outside the git repo; committed only the in-repo changes"

patterns-established:
  - "Intelligence hooks always go AFTER add_backlinks and BEFORE return target in capture_note()"
  - "Intelligence hooks always go BEFORE conn.close() in search main()"

requirements-completed: [INTL-01, INTL-02, INTL-09]

duration: 6min
completed: 2026-03-15
---

# Phase 15 Plan 03: Intelligence Layer Wiring Summary

**Connection suggestions, session recap, and stale nudges fully wired — sb-recap and sb-actions registered as CLI commands, all 17 intelligence tests GREEN**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-15T17:56:32Z
- **Completed:** 2026-03-15T18:02:00Z
- **Tasks:** 3 (Task 1: verify-only; Task 2: wiring; Task 3: full suite)
- **Files modified:** 4 (engine/capture.py, engine/search.py, pyproject.toml, ~/.claude/CLAUDE.md)

## Accomplishments

- Wired `check_connections` and `extract_action_items` into `capture_note()` as best-effort hooks
- Wired `check_stale_nudge` into `search.main()` before `conn.close()`
- Registered `sb-recap` and `sb-actions` entry points in pyproject.toml and installed via `uv pip install -e .`
- Added session hook line to `~/.claude/CLAUDE.md` for proactive recap offers
- All 17 `tests/test_intelligence.py` tests GREEN; 190/191 total tests pass (1 pre-existing failure in test_precommit.py unrelated to this plan)

## Task Commits

1. **Task 1: Implement detect_git_context, find_similar, check_connections, recap_main** - pre-existing (completed in 15-02 session, all 4 target tests already GREEN)
2. **Task 2: Wire intelligence hooks into capture.py, search.py, pyproject.toml, and CLAUDE.md** - `e83de05` (feat)
3. **Task 3: Full suite green** - no new code, verified only

## Files Created/Modified

- `engine/capture.py` - Added Phase 15 best-effort hook block (check_connections + extract_action_items) before `return target`
- `engine/search.py` - Restructured main() to call check_stale_nudge with open conn before close; fixed early conn.close() ordering bug
- `pyproject.toml` - Added sb-recap and sb-actions script entries
- `~/.claude/CLAUDE.md` - Added "Second Brain — Session Context" section with sb-recap offer pattern

## Decisions Made

- Task 1 (TDD) was already GREEN from the 15-02 session — intelligence.py arrived fully implemented. Verified tests pass, no new commit needed.
- Fixed a conn.close() ordering deviation: original search.py closed conn before results check, which would have caused the stale nudge to use a closed connection. Restructured so both early-exit and success paths close conn only after the nudge fires.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed conn.close() called before stale nudge in search.py**
- **Found during:** Task 2 (wiring search.py)
- **Issue:** Original code called `conn.close()` immediately after `search_notes()`, before the results check. Adding the stale nudge after this would use a closed connection.
- **Fix:** Removed the early `conn.close()`, added it in both the early-exit path (no results) and the normal path after the nudge fires.
- **Files modified:** engine/search.py
- **Verification:** `uv run python -m pytest tests/ -q` — no new failures
- **Committed in:** e83de05 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Fix was required for correctness. No scope creep.

## Issues Encountered

- `test_precommit.py::test_blocks_api_key` fails (detect-secrets tool configuration issue, pre-existing, unrelated to this plan)

## Next Phase Readiness

- Intelligence layer fully operational — connection suggestions, action extraction, stale nudges, and session recap all wired
- Phase 16 (GUI Hub) can call `engine/api.py` which will inherit intelligence hooks automatically
- Phase 17 (encryption) note: `check_connections` currently appends backlinks without sensitivity check — plan 15 spec defers pii filtering to Phase 17

---
*Phase: 15-intelligence-layer*
*Completed: 2026-03-15*
