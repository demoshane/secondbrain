---
phase: 19-mcp-server
verified: 2026-03-15T22:30:00Z
status: human_needed
score: 3/4 must-haves verified
human_verification:
  - test: "Open Claude Desktop after running sb-init; check that second-brain MCP server appears in the sidebar and all 12 tools are listed"
    expected: "All 12 tools (sb_search, sb_capture, sb_read, sb_edit, sb_recap, sb_digest, sb_connections, sb_actions, sb_actions_done, sb_files, sb_forget, sb_anonymize) visible and callable"
    why_human: "Requires a running Claude Desktop session; cannot verify MCP sidebar presence programmatically"
---

# Phase 19: MCP Server Verification Report

**Phase Goal:** Users can use brain commands from Claude Desktop and Claude.ai via MCP tools with the same capabilities as the CLI
**Verified:** 2026-03-15T22:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After `sb-init`, Claude Desktop is automatically configured; user can invoke all listed tools | ? HUMAN NEEDED | `write_mcp_config()` implemented and called from `main()` in `init_brain.py`; binary path resolution via `shutil.which` + venv fallback confirmed (commit f79666f); config write tested by `test_init_writes_mcp_config_creates_file`; actual Claude Desktop sidebar discovery requires human |
| 2 | `sb_forget` / `sb_anonymize` require two-step confirmation with 60s token | ✓ VERIFIED | `_issue_token()` / `_consume_token()` implemented with `threading.Lock`; `test_two_step_confirmation` and `test_token_expiry` GREEN (14/14 tests pass) |
| 3 | PII notes from `sb_read` are routed through Ollama; MCP never bypasses ModelRouter | ✓ VERIFIED | `sb_read` queries `notes.sensitivity`, calls `get_adapter("pii", CONFIG_PATH).summarize(content)` on PII rows; `test_pii_routing` GREEN with mock assertions |
| 4 | All inputs validated; transient failures retry with backoff; every call audit-logged; write tools idempotent | ✓ VERIFIED | Size limits enforced (`_MAX_QUERY_LEN=500`, `_MAX_TITLE_LEN=200`, `_MAX_BODY_LEN=50_000`); `_retry_call` uses tenacity with `wait_exponential`, 4 attempts, `reraise=True`; `_log_mcp_audit` called at end of every tool; `test_retry_on_db_locked_retry`, `test_audit_log_written`, `test_path_traversal_rejected`, `test_body_too_large` all GREEN |

**Score:** 3/4 truths verified (1 requires human confirmation)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/mcp_server.py` | FastMCP server with 12 tools | VERIFIED | 347 lines; 12 `@mcp.tool()` functions; full implementations (no stubs); no TODOs or placeholders |
| `tests/test_mcp.py` | 14 tests covering all MCP behaviors | VERIFIED | 14 tests, all GREEN (`pytest tests/test_mcp.py -v` → 14 passed in 4.49s) |
| `engine/init_brain.py` — `write_mcp_config()` | Writes Claude Desktop config on `sb-init` | VERIFIED | Function present at line 247; called from `main()` at line 386; macOS/Windows/Linux branches; `_cfg_path` test-isolation param |
| `sb-mcp-server` entry point | Registered in pyproject.toml | VERIFIED | `sb-mcp-server = "engine.mcp_server:main"` in `[project.scripts]` |
| `fastmcp>=3.1.1`, `tenacity>=9.1.4` | In project dependencies | VERIFIED | Both present in `pyproject.toml` `[project.dependencies]` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `sb_search` | `search_hybrid` / `search_semantic` / `search_notes` | `_retry_call(...)` + `get_connection()` | WIRED | Import at line 24; called in `sb_search` body |
| `sb_read` | `get_adapter("pii", CONFIG_PATH).summarize()` | `notes.sensitivity == "pii"` gate | WIRED | `from engine.router import get_adapter`; conditional call in `sb_read` |
| `sb_forget` | `forget_person()` | `_consume_token()` gate | WIRED | Import at line 19; called after token consumed in `sb_forget` |
| `sb_anonymize` | `anonymize_note()` | `_consume_token()` gate | WIRED | Import at line 20; called after token consumed in `sb_anonymize` |
| `sb_recap` | `recap_entity()` | `_retry_call(_do_recap)` with self-import | WIRED | Self-import (`import engine.mcp_server as _self`) ensures monkeypatch visibility; `test_retry_on_db_locked_retry` GREEN |
| `write_mcp_config()` | `claude_desktop_config.json` | `shutil.which` + `sys.executable` venv fallback | WIRED | Two-step binary resolution; merge-writes JSON; called from `main()` |
| `_log_mcp_audit` | `log_audit(conn, event, path)` | Fresh `get_connection()` per call | WIRED | All 12 tools call `_log_mcp_audit` after execution |

---

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| MCP-01 | User can connect brain to Claude Desktop via `sb-mcp-server` | ? HUMAN NEEDED | Server runs on stdio transport; config write verified; Claude Desktop discovery requires live test |
| MCP-02 | `sb-init` auto-writes Claude Desktop MCP config | ✓ SATISFIED | `write_mcp_config()` called from `init_brain.main()`; path resolution bug fixed (f79666f); `test_init_writes_mcp_config_creates_file` GREEN |
| MCP-03 | MCP exposes full feature parity: search, capture, read, edit, recap, digest, connections, actions, files, forget | ✓ SATISFIED | 12 tools verified in `test_tool_parity` via `asyncio.run(mcp.list_tools())`; all delegate to existing engine functions |
| MCP-04 | Destructive tools require two-step confirmation with 60s token | ✓ SATISFIED | `_issue_token()` / `_consume_token()` with `threading.Lock`; `test_two_step_confirmation` and `test_token_expiry` GREEN |
| MCP-05 | PII routing inherited from ModelRouter; no bypass | ✓ SATISFIED | `sb_read` calls `get_adapter("pii", CONFIG_PATH).summarize()`; `test_pii_routing` GREEN with mock |
| MCP-06 | Structured errors with error codes; never silent | ✓ SATISFIED | All tools raise `ValueError("ERROR_CODE: ...")` with machine-readable prefix; `test_structured_error` GREEN |
| MCP-07 | All inputs validated before execution | ✓ SATISFIED | `_MAX_QUERY_LEN`, `_MAX_TITLE_LEN`, `_MAX_BODY_LEN` enforced; `_safe_path()` path traversal guard; `test_path_traversal_rejected` and `test_body_too_large` GREEN |
| MCP-08 | Transient failures retry with exponential backoff | ✓ SATISFIED | `_retry_call` uses `wait_exponential(multiplier=1, min=1, max=8)`, `stop_after_attempt(4)`, `reraise=True`; `test_retry_on_db_locked_retry` confirms `call_count >= 2` |
| MCP-09 | Write tools idempotent — no duplicate captures | ✓ SATISFIED | `sb_capture` checks `notes WHERE title=?` before calling `capture_note()`; `test_capture_idempotent` GREEN |
| MCP-10 | All tool calls recorded in audit log | ✓ SATISFIED | Every tool calls `_log_mcp_audit(event, path)` after successful execution; `test_audit_log_written` GREEN |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None | — | — | No TODOs, placeholders, stub returns, or empty handlers found in `engine/mcp_server.py` |

---

### Human Verification Required

#### 1. Claude Desktop MCP Integration (MCP-01)

**Test:** Run `sb-init` on a machine with Claude Desktop installed. Open Claude Desktop and look for the "second-brain" server in the MCP sidebar.
**Expected:** Second-brain server listed with all 12 tools visible (sb_search, sb_capture, sb_read, sb_edit, sb_recap, sb_digest, sb_connections, sb_actions, sb_actions_done, sb_files, sb_forget, sb_anonymize). Invoke `sb_search` with a test query and confirm real brain results are returned.
**Why human:** Requires a running Claude Desktop application with MCP sidebar. Cannot verify GUI sidebar presence, tool listing, or live invocation programmatically. (Per 19-04-SUMMARY.md, this was already performed and approved by the user — recording here for completeness.)

---

### Summary

Phase 19 is substantively complete. All automated checks pass:

- 14/14 tests GREEN (`pytest tests/test_mcp.py -v`, 4.49s)
- All 10 requirements (MCP-01 through MCP-10) have implementation evidence in `engine/mcp_server.py`
- No stubs, no placeholders, no anti-patterns found
- `write_mcp_config()` wired into `sb-init` with binary path fallback fix (f79666f)
- Two-step confirmation, PII routing, retry, audit logging, size guards all verified by dedicated tests

The single human-needed item (MCP-01 Claude Desktop sidebar discovery) was already performed and approved by the user per 19-04-SUMMARY.md — Claude Desktop showed all 12 tools and `sb_search` ran successfully against live brain data. This item is recorded here for audit completeness.

---

_Verified: 2026-03-15T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
