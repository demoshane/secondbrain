---
phase: 34
slug: gui-management-productivity
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 34 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -q --tb=short` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -q --tb=short`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 34-01-01 | 01 | 0 | GUI-01 | unit | `uv run pytest tests/test_action_items.py -q` | ❌ W0 | ⬜ pending |
| 34-01-02 | 01 | 1 | GUI-01 | unit | `uv run pytest tests/test_action_items.py -q` | ❌ W0 | ⬜ pending |
| 34-01-03 | 01 | 1 | GUI-02 | integration | `uv run pytest tests/test_api.py -k "action" -q` | ✅ | ⬜ pending |
| 34-02-01 | 02 | 0 | GUI-03 | unit | `uv run pytest tests/test_search.py -q` | ✅ | ⬜ pending |
| 34-02-02 | 02 | 1 | GUI-03 | manual | n/a — frontend UI | n/a | ⬜ pending |
| 34-03-01 | 03 | 0 | GUI-04 | unit | `uv run pytest tests/test_capture.py -k "person" -q` | ✅ | ⬜ pending |
| 34-03-02 | 03 | 1 | GUI-04 | integration | `uv run pytest tests/test_api.py -k "people" -q` | ✅ | ⬜ pending |
| 34-03-03 | 03 | 1 | GUI-07 | unit | `uv run pytest tests/test_mcp.py -k "create_person" -q` | ❌ W0 | ⬜ pending |
| 34-04-01 | 04 | 1 | GUI-05 | integration | `uv run pytest tests/test_api.py -k "intelligence" -q` | ✅ | ⬜ pending |
| 34-04-02 | 04 | 1 | GUI-06 | integration | `uv run pytest tests/test_api.py -k "tags" -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_action_items.py` — stubs for GUI-01 (ActionItemList toggle, source note link)
- [ ] `tests/test_mcp.py` — stub for GUI-07 (`sb_create_person` MCP tool)

*Existing infrastructure (pytest, conftest.py, test_api.py, test_capture.py, test_search.py) covers remaining requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cmd+K palette opens/closes, keyboard navigation works | GUI-03 | Frontend UI interaction | Open GUI → press Cmd+K → type query → verify results → press Escape |
| Tag autocomplete dropdown appears while typing | GUI-06 | Frontend UI interaction | Open note edit → type tag prefix → verify dropdown → select → verify tag added |
| Toast appears and auto-dismisses on success/error | GUI-05 | Frontend UI notification | Perform create/delete action → verify toast appears → verify dismissal after 3s |
| Inbox polish — visual layout and spacing | GUI-06 | Visual regression not automated | Open Inbox page → verify layout matches UI-SPEC spacing |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
