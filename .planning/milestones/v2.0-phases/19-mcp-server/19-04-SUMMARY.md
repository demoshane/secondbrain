---
phase: 19-mcp-server
plan: "04"
subsystem: infra
tags: [mcp, claude-desktop, fastmcp, init, config]

# Dependency graph
requires:
  - phase: 19-03
    provides: write_mcp_config() and sb-mcp-server entry point
provides:
  - Human-verified confirmation that Claude Desktop discovers the second-brain MCP server
  - Confirmed 12 MCP tools visible and callable from a live Claude Desktop session
  - Bug fix: venv-relative fallback in write_mcp_config() for uv run invocation
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "write_mcp_config() resolves binary via shutil.which first, then sys.executable parent as fallback"

key-files:
  created: []
  modified:
    - engine/init_brain.py

key-decisions:
  - "write_mcp_config() venv fallback: shutil.which fails under uv run because venv bin/ is not on PATH at invocation time; resolved by resolving Path(sys.executable).parent / 'sb-mcp-server'"

patterns-established:
  - "Binary path resolution: always chain shutil.which → venv-relative fallback → error message; never assume PATH is populated under uv run"

requirements-completed:
  - MCP-01
  - MCP-02

# Metrics
duration: 10min
completed: 2026-03-15
---

# Phase 19 Plan 04: Human Verification Summary

**Claude Desktop shows all 12 second-brain MCP tools; sb_search executed successfully against live brain data after venv-path fallback fix**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-15T21:41:53Z
- **Completed:** 2026-03-15T21:52:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Human-verified MCP server integration: Claude Desktop shows second-brain server with all 12 tools
- sb_search invoked from Claude Desktop and returned real results without error
- Fixed write_mcp_config() silent failure when sb-init is run via `uv run` — config now writes correctly

## Task Commits

1. **Task 1: Run sb-init and verify config file written** — verified in prior session (no separate commit; config confirmed at `~/Library/Application Support/Claude/claude_desktop_config.json`)
2. **Task 2: Human verification — Claude Desktop MCP tools** — approved by user; sb_search ran successfully
3. **Bug fix (Rule 1): venv-relative path fallback in write_mcp_config()** — `f79666f` (fix)

## Files Created/Modified

- `engine/init_brain.py` — Added `Path(sys.executable).parent / "sb-mcp-server"` fallback after `shutil.which` in `write_mcp_config()`

## Decisions Made

- venv fallback is the correct second step: under `uv run`, the venv `bin/` directory is not on PATH, so `shutil.which` always returns None. Resolving relative to `sys.executable` is reliable across all uv-managed invocations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed write_mcp_config() returning no binary path under uv run**
- **Found during:** Task 1 (Run sb-init and verify config file written)
- **Issue:** `shutil.which("sb-mcp-server")` returns None when `sb-init` is invoked via `uv run` — PATH does not include the venv `bin/` directory at that point, so the Claude Desktop config was not written
- **Fix:** Added a second resolution step: `Path(sys.executable).parent / "sb-mcp-server"` — resolves correctly since sys.executable is always the venv Python
- **Files modified:** `engine/init_brain.py`
- **Verification:** Human confirmed config was written with correct absolute binary path after fix; sb_search ran successfully from Claude Desktop
- **Committed in:** `f79666f`

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug)
**Impact on plan:** Required fix for the plan's core objective — without it the config write silently skipped. No scope creep.

## Issues Encountered

None beyond the auto-fixed bug above.

## User Setup Required

None — sb-init writes the Claude Desktop config automatically once the binary path is resolved.

## Next Phase Readiness

Phase 19 is complete. All MCP requirements (MCP-01 through MCP-10) delivered and verified:
- 12 tools registered and callable from Claude Desktop
- sb-init auto-writes config on first run
- Retry/resilience contracts (MCP-08) implemented via tenacity
- Two-step confirmation for destructive operations (MCP-09, MCP-10)

No blockers for future phases.

---
*Phase: 19-mcp-server*
*Completed: 2026-03-15*
