---
phase: 37
slug: housekeeping
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-25
---

# Phase 37 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -q -x` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -q -x`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 37-01 | 01 | 1 | sb_recap fix | unit | `uv run pytest tests/test_mcp_server.py -q -k recap` | yes | pending |
| 37-02 | 02 | 1 | Action item create in person view | compile | `npx tsc --noEmit` | yes | pending |
| 37-03 | 03 | 1 | People chips in NoteViewer | compile+manual | `npx tsc --noEmit` + manual per UI-SPEC.md | yes | pending |
| 37-04 | 04 | 2 | Cascade delete impact + orphan cleanup | unit | `uv run pytest tests/test_delete.py tests/test_forget.py -q` | yes | pending |
| 37-05 | 05 | 1 | install_subagent.py tests | unit | `uv run pytest tests/test_install_subagent.py -q` | W0 self-created | pending |
| 37-06 | 06 | 2 | Fix 3 Playwright tests | e2e | `uv run pytest tests/test_gui_playwright.py::test_title_sync tests/test_gui_playwright.py::test_delete_flow tests/test_gui_playwright.py::test_right_panel_people_mention -v` | yes | pending |
| 37-07 | 07 | 2 | Fix 4 embedding reindex tests | unit | `uv run pytest tests/test_embeddings.py::TestReindexGeneratesEmbeddings -v` | yes | pending |
| 37-08 | 08 | 1 | Drive sync setup + health check | unit+bash | `uv run pytest tests/test_brain_health.py -q -k drive` + `bash -n setup.sh` | W0 self-created | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `tests/test_install_subagent.py` — self-created by plan 05 Task 1 (TDD: test written before implementation)
- [x] `tests/test_brain_health.py` (extend) — self-created by plan 08 Task 1 (TDD: drive tests written before implementation)

*Both Wave 0 files are self-created by their respective plans as part of the TDD red-green cycle. No separate Wave 0 task needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| People chips add/remove in NoteViewer | 37-03 | React UI interaction with no backend-testable logic in Task 1; TypeScript compile verifies type correctness; visual layout verified per 37-UI-SPEC.md | Open a note, click +, add a person, confirm chip appears; click x to remove, confirm chip gone |
| Action item creation from person view | 37-02 | Frontend-only prop wiring to existing ActionItemList component | Open People page, select a person, create an action item, confirm it appears assigned |
| Drive sync health display in GUI | 37-08 | Requires Google Drive Desktop installed | Open Intelligence page, verify Drive sync section shows correct status |

**Nyquist exception:** Tasks 37-02 and 37-03 Task 1 are frontend-only (React component prop wiring and JSX rendering). TypeScript compile (`npx tsc --noEmit`) is the automated verify; behavioral verification is manual per UI-SPEC.md. This is acceptable because: (a) no backend logic is created or modified, (b) the API endpoint in 37-03 Task 2 has its own pytest verify, (c) Playwright e2e coverage for people chips is addressed in plan 06.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (both are self-created by TDD plans)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (with documented manual-only exception for frontend UI tasks)
