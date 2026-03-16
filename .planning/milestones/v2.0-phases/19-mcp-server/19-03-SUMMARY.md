---
phase: 19-mcp-server
plan: "03"
subsystem: mcp-server
tags: [mcp, gdpr, two-step-confirmation, token-gate, init-brain]
dependency_graph:
  requires: [engine/forget.py, engine/anonymize.py, engine/init_brain.py]
  provides: [sb_forget token gate, sb_anonymize token gate, write_mcp_config]
  affects: [engine/mcp_server.py, engine/init_brain.py]
tech_stack:
  added: []
  patterns: [two-step token confirmation, threading.Lock token store, platform-conditional config write]
key_files:
  modified:
    - engine/mcp_server.py
    - engine/init_brain.py
    - tests/test_mcp.py
decisions:
  - "Two-step token uses 60s TTL stored in module-level dict under threading.Lock — no persistence needed (in-process only)"
  - "write_mcp_config accepts _cfg_path override param for test isolation — avoids monkeypatching platform.system()"
  - "Plan 01+02 work was already committed (1befab6); Plan 03 verification confirmed all 14 tests GREEN"
metrics:
  duration: 480s
  completed: "2026-03-15"
  tasks_completed: 2
  files_changed: 3
requirements_completed: [MCP-02, MCP-04]
---

# Phase 19 Plan 03: Two-Step Confirmation + MCP Config Write Summary

Two-step token gate for sb_forget and sb_anonymize (MCP-04) with 60s TTL thread-safe token store; write_mcp_config() added to sb-init for zero-config Claude Desktop onboarding (MCP-02).

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Two-step token confirmation for sb_forget and sb_anonymize | 1befab6 | engine/mcp_server.py, tests/test_mcp.py |
| 2 | write_mcp_config() in engine/init_brain.py + call from main() | 1befab6 | engine/init_brain.py |

## What Was Built

### Task 1: Two-Step Token Confirmation (MCP-04)

`engine/mcp_server.py` now implements `_issue_token()` and `_consume_token()` as free functions operating on the module-level `_pending: dict[str, float]` dict protected by `_pending_lock = threading.Lock()`.

- `sb_forget(slug, confirm_token="")`: without token → returns `{status: pending, confirm_token: <tok>, message: ...}`. With valid token → calls `forget_person()`, logs audit. With invalid/expired token → raises `ValueError("TOKEN_EXPIRED: ...")`.
- `sb_anonymize(path, tokens, confirm_token="")`: same pattern, calls `anonymize_note()` after token consumed.
- All 10 non-destructive tools (sb_search, sb_capture, sb_read, sb_edit, sb_recap, sb_digest, sb_connections, sb_actions, sb_actions_done, sb_files) are also fully implemented in the same commit.

### Task 2: write_mcp_config() (MCP-02)

`engine/init_brain.py` gains `write_mcp_config(sb_mcp_bin=None, _cfg_path=None)`:
- Resolves `sb-mcp-server` binary via `shutil.which` if not provided
- macOS → `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows → `%APPDATA%/Claude/claude_desktop_config.json`
- Linux → returns silently (no Claude Desktop)
- Reads existing JSON, merges `mcpServers["second-brain"]` entry, writes back with `json.dumps(indent=2)`
- `_cfg_path` param enables test isolation without patching `platform.system()`
- `main()` calls `write_mcp_config()` as last setup step

## Verification

```
pytest tests/test_mcp.py -v  →  14 passed in 3.84s
grep -n "print(" engine/mcp_server.py  →  (no output — zero stdout pollution)
python -c "from engine.init_brain import write_mcp_config; print('OK')"  →  OK
pytest --tb=no  →  1 failed (pre-existing test_precommit.py::test_blocks_api_key), 245 passed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] tenacity `reraise` not exported in tenacity 9.x**
- **Found during:** Task 1 — module import
- **Issue:** Plan action imported `reraise` from tenacity; tenacity 9.x does not export this name (it's a parameter, not a symbol)
- **Fix:** Removed `reraise` from import list; `reraise=True` on `@retry()` decorator is the correct API
- **Files modified:** engine/mcp_server.py
- **Commit:** 1befab6

**2. [Rule 3 - Blocking] Plans 01+02 work already committed**
- **Found during:** Initial file inspection
- **Issue:** `engine/mcp_server.py` and `tests/test_mcp.py` already existed and had full implementation from commit 1befab6; attempting to re-create would have been a no-op or regression
- **Fix:** Verified existing implementation matched all plan requirements, updated tests from stub-state to real-assertion state, proceeded to Plan 03 work
- **Commit:** Already present at 1befab6

## Self-Check: PASSED

- engine/mcp_server.py: FOUND
- engine/init_brain.py: FOUND
- tests/test_mcp.py: FOUND
- commit 1befab6: FOUND
- 14 MCP tests: ALL PASSED
