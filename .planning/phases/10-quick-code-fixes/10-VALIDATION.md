---
phase: 10
slug: quick-code-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via uv run --no-project --with pytest) |
| **Config file** | none (standard discovery) |
| **Quick run command** | `uv run --no-project --with pytest --with python-frontmatter tests/test_forget.py -x -q` |
| **Full suite command** | `uv run --no-project --with pytest --with python-frontmatter tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run --no-project --with pytest --with python-frontmatter tests/test_forget.py -x -q`
- **After every plan wave:** Run `uv run --no-project --with pytest --with python-frontmatter tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-00-01 | 00 | 1 | tech debt | manual | n/a (docstring review) | ✅ | ⬜ pending |
| 10-00-02 | 00 | 1 | tech debt | integration | `uv run --no-project --with pytest --with python-frontmatter tests/test_forget.py::test_forget_removes_row_stored_by_capture -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| update_memory docstring accuracy | tech debt | No automated test for comment correctness | Read engine/ai.py:122-125, verify docstring matches Phase 8 routing behaviour |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
