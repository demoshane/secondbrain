---
phase: 42
slug: add-importance-field-to-notes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 42 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_capture.py tests/test_search.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_capture.py tests/test_search.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 42-01-01 | 01 | 1 | DB migration + capture pipeline | unit | `uv run pytest tests/test_capture.py -k importance -x -q` | ❌ W0 | ⬜ pending |
| 42-01-02 | 01 | 1 | MCP tools + classify_importance | unit | `uv run pytest tests/test_mcp.py -k importance -x -q` | ❌ W0 | ⬜ pending |
| 42-02-01 | 02 | 2 | API endpoints | unit | `uv run pytest tests/test_api.py -k importance -x -q` | ❌ W0 | ⬜ pending |
| 42-02-02 | 02 | 2 | Search filter | unit | `uv run pytest tests/test_search.py -k importance -x -q` | ❌ W0 | ⬜ pending |
| 42-03-01 | 03 | 3 | Frontend badges | manual | — | N/A | ⬜ pending |
| 42-03-02 | 03 | 3 | Importance dropdown | manual | — | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_capture.py` — add importance-specific test stubs (or extend existing)
- [ ] `tests/test_search.py` — add importance filter test stubs
- [ ] `tests/test_api.py` — add importance endpoint test stubs
- [ ] `tests/test_mcp.py` — add importance MCP tool test stubs (if file exists)

*Existing test infrastructure covers framework; only new test stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sidebar badges show [HIGH]/[MED]/[LOW] for all notes | D-11–D-13 | Frontend visual rendering | Open GUI, verify badges appear next to all note titles |
| Importance dropdown in detail panel works | D-15–D-16 | Frontend interaction | Open a note, change importance via dropdown, verify badge updates |
| sb_capture_smart infers importance from content | D-08 | Requires testing content heuristics end-to-end | Capture note with "URGENT" in body → verify importance=high in frontmatter |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
