---
phase: 28
slug: todo-and-gap-resolution
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-19
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

> **Wave 0 approach:** Wave 0 is embedded per-task via TDD-inline pattern. Each plan's `<action>` block
> explicitly instructs the executor to write the failing test FIRST before implementing. No separate
> Wave 0 plan file is needed.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + Playwright |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -q --ignore=tests/test_gui.py` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds (unit), ~90 seconds (with Playwright) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -q --ignore=tests/test_gui.py`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 28-01-01 | 01 | 1 | title-only dedup | unit | `uv run pytest tests/test_capture.py -q -k dedup` | ✅ | ⬜ pending |
| 28-02-01 | 02 | 1 | sb_capture_smart suggestions | unit | `uv run pytest tests/test_mcp.py -q -k capture_smart` | TDD-inline | ⬜ pending |
| 28-03-01 | 03 | 1 | sb_tag add/remove | unit | `uv run pytest tests/test_mcp.py -q -k sb_tag` | TDD-inline | ⬜ pending |
| 28-04-01 | 04 | 1 | sb_link / sb_unlink | unit | `uv run pytest tests/test_mcp.py -q -k "sb_link or sb_unlink"` | TDD-inline | ⬜ pending |
| 28-05-01 | 05 | 1 | sb_remind due_date | unit | `uv run pytest tests/test_mcp.py tests/test_intelligence.py -q -k "remind or due_date or overdue"` | TDD-inline | ⬜ pending |
| 28-06-01 | 06 | 1 | sb_person_context | unit | `uv run pytest tests/test_mcp.py -q -k person_context` | TDD-inline | ⬜ pending |
| 28-07-01 | 07 | 2 | Playwright session isolation | e2e | `uv run pytest tests/test_gui.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*TDD-inline: test written by executor at start of task (RED phase), before implementation*

---

## Wave 0 Requirements

Wave 0 is satisfied inline: each plan (28-01 through 28-06) instructs the executor to write the
failing test FIRST before implementing. This is the TDD-inline pattern — no separate stub file needed.

*Existing pytest + Playwright infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| sb_capture_smart suggestions UI flow | 28-02 | Requires conversational confirm before batch capture | Call sb_capture_smart, verify suggestions returned, then call sb_capture_batch to commit |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or TDD-inline Wave 0
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covered via TDD-inline pattern (embedded in each plan's action block)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending execution
