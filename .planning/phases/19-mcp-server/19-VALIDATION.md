---
phase: 19
slug: mcp-server
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (pinned in pyproject.toml `[project.optional-dependencies].dev`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]` |
| **Quick run command** | `pytest tests/test_mcp.py -x -q` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_mcp.py -x -q`
- **After every plan wave:** Run `pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 0 | MCP-01 | unit | `pytest tests/test_mcp.py::test_sb_search -x` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 0 | MCP-02 | unit | `pytest tests/test_mcp.py::test_init_writes_mcp_config -x` | ❌ W0 | ⬜ pending |
| 19-01-03 | 01 | 0 | MCP-03 | unit | `pytest tests/test_mcp.py::test_tool_parity -x` | ❌ W0 | ⬜ pending |
| 19-01-04 | 01 | 0 | MCP-04 | unit | `pytest tests/test_mcp.py::test_two_step_confirmation -x` | ❌ W0 | ⬜ pending |
| 19-01-05 | 01 | 0 | MCP-04 | unit | `pytest tests/test_mcp.py::test_token_expiry -x` | ❌ W0 | ⬜ pending |
| 19-02-01 | 02 | 1 | MCP-05 | unit | `pytest tests/test_mcp.py::test_pii_routing -x` | ❌ W0 | ⬜ pending |
| 19-02-02 | 02 | 1 | MCP-06 | unit | `pytest tests/test_mcp.py::test_structured_error -x` | ❌ W0 | ⬜ pending |
| 19-02-03 | 02 | 1 | MCP-07 | unit | `pytest tests/test_mcp.py::test_path_traversal_rejected -x` | ❌ W0 | ⬜ pending |
| 19-02-04 | 02 | 1 | MCP-08 | unit | `pytest tests/test_mcp.py::test_retry_on_db_locked -x` | ❌ W0 | ⬜ pending |
| 19-02-05 | 02 | 1 | MCP-09 | unit | `pytest tests/test_mcp.py::test_audit_log_written -x` | ❌ W0 | ⬜ pending |
| 19-02-06 | 02 | 1 | MCP-10 | unit | `pytest tests/test_mcp.py::test_capture_idempotent -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_mcp.py` — test stubs for all 11 behaviors (MCP-01 through MCP-10)
- [ ] `engine/mcp_server.py` — stub with `FastMCP("second-brain")` and empty tool stubs
- [ ] `uv add fastmcp tenacity` — neither present in `pyproject.toml` yet

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Claude Desktop discovers MCP server and tools appear in sidebar | MCP-01 | Requires running Claude Desktop app | Run `sb-init`, open Claude Desktop, verify tools listed in MCP sidebar |
| Claude.ai web MCP connection (if in scope) | MCP-01 | Requires hosted bridge not in scope | Out of scope for Phase 19 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
