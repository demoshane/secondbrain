---
phase: 24
slug: playwright-gui-test-suite
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-playwright |
| **Config file** | `pyproject.toml` (Wave 0 adds deps) |
| **Quick run command** | `uv run pytest tests/test_gui.py -x -q` |
| **Full suite command** | `uv run pytest tests/test_gui.py -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_gui.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/test_gui.py -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 24-01-01 | 01 | 0 | TEST-01 | infra | `uv run pytest tests/test_gui.py --collect-only` | ❌ W0 | ⬜ pending |
| 24-01-02 | 01 | 0 | TEST-01 | infra | `uv run playwright install chromium` | ❌ W0 | ⬜ pending |
| 24-02-01 | 02 | 1 | TEST-01 | e2e | `uv run pytest tests/test_gui.py::test_markdown_renders_as_html -x` | ❌ W0 | ⬜ pending |
| 24-02-02 | 02 | 1 | TEST-01 | e2e | `uv run pytest tests/test_gui.py::test_viewer_scroll -x` | ❌ W0 | ⬜ pending |
| 24-02-03 | 02 | 1 | TEST-01 | e2e | `uv run pytest tests/test_gui.py::test_title_sync -x` | ❌ W0 | ⬜ pending |
| 24-03-01 | 03 | 2 | TEST-01 | e2e | `uv run pytest tests/test_gui.py::test_sse_live_refresh -x` | ❌ W0 | ⬜ pending |
| 24-03-02 | 03 | 2 | TEST-01 | e2e | `uv run pytest tests/test_gui.py::test_delete_flow -x` | ❌ W0 | ⬜ pending |
| 24-04-01 | 04 | 3 | TEST-01 | e2e | `uv run pytest tests/test_gui.py::test_tag_editing -x` | ❌ W0 | ⬜ pending |
| 24-04-02 | 04 | 3 | TEST-01 | e2e | `uv run pytest tests/test_gui.py::test_tag_filtering -x` | ❌ W0 | ⬜ pending |
| 24-04-03 | 04 | 3 | TEST-01 | e2e | `uv run pytest tests/test_gui.py::test_collapsible_sections -x` | ❌ W0 | ⬜ pending |
| 24-04-04 | 04 | 3 | TEST-01 | e2e | `uv run pytest tests/test_gui.py::test_path_traversal_guard -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_gui.py` — stub file with all 10 test functions (xfail stubs so suite is collectable)
- [ ] `pytest-playwright` added to `pyproject.toml` dev dependencies
- [ ] `playwright install chromium` — browser binary installed
- [ ] `engine/gui/__init__.py` or `engine/api.py` — `window.API_BASE` injection fix so Flask serves the correct port (critical blocker identified in research)
- [ ] `tests/conftest.py` — `gui_server` session-scoped fixture (threading.Thread, NOT pytest-flask live_server — teardown hang documented)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual appearance of rendered markdown | TEST-01 SC-2 | DOM checks pass even if styling is broken | Open note with `## heading`, `**bold**`, `- list` — confirm visual rendering |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
