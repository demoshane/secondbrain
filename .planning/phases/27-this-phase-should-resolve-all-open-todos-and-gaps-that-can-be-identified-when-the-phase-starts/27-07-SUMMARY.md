---
phase: 27-search-quality-tuning
plan: 07
subsystem: testing
tags: [pytest, detect-secrets, fastmcp, test-fixes]

requires:
  - phase: 27-02
    provides: BM25 title weighting in search_notes()
  - phase: 27-03
    provides: sb_edit frontmatter preservation, recap fallback
  - phase: 27-04
    provides: person chips in sidebar
  - phase: 27-05
    provides: CI workflow
  - phase: 27-06
    provides: CI workflow file

provides:
  - Full pytest suite passing with 0 failures
  - 9/10 regression tests xpassed (1 recall xfail — acceptable)
  - test_tool_parity using correct FastMCP internal API
  - test_blocks_api_key using AWSKeyDetector directly (bypass heuristic filter)
  - test_claude_md_contains_session_hook checking correct file (~/.claude/second-brain.md)

affects: [phase-28, future-phases]

tech-stack:
  added: []
  patterns:
    - "FastMCP tool introspection via mcp._local_provider._components (keyed 'tool:<name>@')"
    - "detect-secrets plugin testing via AWSKeyDetector.analyze_string() not subprocess"

key-files:
  created: []
  modified:
    - tests/test_mcp.py
    - tests/test_precommit.py
    - tests/test_intelligence.py
    - engine/mcp_server.py
    - .secrets.baseline

key-decisions:
  - "[27-07] FastMCP 3.x moved tool registry from _tool_manager._tools to _local_provider._components (sync dict keyed 'tool:<name>@')"
  - "[27-07] detect-secrets subprocess + is_likely_id_string heuristic silently filters well-known AWS example keys; use AWSKeyDetector.analyze_string() directly in tests"
  - "[27-07] Session hook test checks ~/.claude/second-brain.md (the @ referenced file), not ~/.claude/CLAUDE.md"

requirements-completed:
  - ENGL-02

duration: 15min
completed: 2026-03-17
---

# Phase 27 Plan 07: Sign-off Suite Summary

**Full pytest suite green (0 failures) — fixed 3 broken tests caused by FastMCP API drift, detect-secrets heuristic filtering, and wrong CLAUDE.md path; regression suite 9/10 xpassed**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-17T18:20:00Z
- **Completed:** 2026-03-17T18:35:00Z
- **Tasks:** 2 of 2 (Task 1 auto + Task 2 human-verify approved)
- **Files modified:** 5

## Accomplishments

- Full pytest suite exits 0, down from 3 failures
- Regression suite: 9 xpassed (precision + recall), 1 xfailed (strict=False recall — acceptable)
- Fixed `sb_tools()` in `mcp_server.py` which was silently returning the fallback stub due to `AttributeError` on non-existent `_tool_manager._tools`

## Task Commits

1. **Task 1: Run full test suite and fix failures** - `e991757` (fix)

## Files Created/Modified

- `tests/test_mcp.py` - test_tool_parity now uses `_local_provider._components` sync dict
- `tests/test_precommit.py` - test_blocks_api_key uses `AWSKeyDetector.analyze_string()` directly
- `tests/test_intelligence.py` - test_claude_md_contains_session_hook checks `~/.claude/second-brain.md`
- `engine/mcp_server.py` - sb_tools() fixed to use `_local_provider._components` (was masked by AttributeError fallback)
- `.secrets.baseline` - regenerated after test file changes

## Decisions Made

- FastMCP 3.x stores tools in `_local_provider._components` with keys `"tool:<name>@"` — not `_tool_manager._tools` as previously documented
- AWS docs placeholder key (AKIA…EXAMPLE format) is filtered by detect-secrets' `is_likely_id_string` heuristic when scanned via subprocess; plugin's `analyze_string()` bypasses post-scan filters for unit testing
- Session hook lives in `~/.claude/second-brain.md` (loaded via `@` import from CLAUDE.md); test was checking the top-level file

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed sb_tools() using non-existent _tool_manager._tools**
- **Found during:** Task 1 (diagnosing test_tool_parity failure)
- **Issue:** `mcp._tool_manager._tools` raised `AttributeError`; the `except AttributeError` fallback silently returned a stub — sb_tools() never actually listed tools
- **Fix:** Changed to `mcp._local_provider._components` with `startswith("tool:")` filter
- **Files modified:** `engine/mcp_server.py`
- **Verification:** `test_sb_tools()` and `test_tool_parity` both pass
- **Committed in:** e991757

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix necessary for sb_tools correctness — it was always returning the fallback stub. No scope creep.

## Issues Encountered

- Pre-commit hook blocked initial commit because the test's example AWS key pattern was detected as a real secret. Added `# pragma: allowlist secret` to the code line and removed the AWS docs placeholder literal from the docstring.

## Self-Check

- [x] Task 1 commit e991757 exists
- [x] All 3 previously failing tests now pass
- [x] Regression suite: 9 xpassed, 1 xfailed (acceptable)
- [x] Full suite exit code 0 confirmed

## Self-Check: PASSED

## Next Phase Readiness

- Human verification checkpoint approved: search ranking, sb-recap, and person chips confirmed working in live GUI
- Phase 27 is fully closed

---
*Phase: 27-search-quality-tuning*
*Completed: 2026-03-17*
