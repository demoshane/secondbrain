---
phase: 39
slug: codebase-review
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-27
closed: 2026-03-28
---

# Phase 39 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -q --tb=short -x` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every fix task commit:** Run `uv run pytest tests/ -q --tb=short -x`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 39-audit | 01 | 1 | quality gate | manual | reviewer agents produce FINDINGS.md | ⬜ pending |
| 39-triage | 02 | 2 | quality gate | manual | 39-FINDINGS.md exists with severity-ranked items | ⬜ pending |
| 39-fix-* | 03+ | 3 | quality gate | unit | `uv run pytest tests/ -q` after each fix | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements — no new test stubs needed before Wave 1 (audit runs against existing code).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Audit findings are complete | Quality gate | Requires human judgment on severity | Read 39-FINDINGS.md and verify no obvious issues were missed |
| Risky fix decisions | Quality gate | User must approve per-finding | User confirms each risky fix before execution |
| Dead code removal is safe | Quality gate | Static analysis may miss dynamic paths | Grep for usage before deleting any module |

---

## Validation Sign-Off

- [x] All fix tasks have `uv run pytest` verify commands
- [x] No regressions introduced by fixes — pre-existing failures confirmed via stash test (FK constraint issues in test_delete/test_inbox pre-date phase 39; test_preflight requires frontend build on host)
- [x] 39-FINDINGS.md produced by Wave 1 with severity rankings
- [x] All Critical/High/Medium findings resolved or explicitly deferred
- [x] Low severity findings added to STATE.md Pending Todos
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-03-28
