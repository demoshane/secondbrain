---
phase: 27
slug: search-quality-tuning
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | none — discovered automatically |
| **Quick run command** | `uv run pytest tests/test_search_regression.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_search_regression.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 27-01-01 | 01 | 0 | ENGL-02 | unit | `uv run pytest tests/test_search_regression.py -x -q` | ❌ W0 | ⬜ pending |
| 27-01-02 | 01 | 0 | ENGL-02 | unit | `uv run pytest tests/test_mcp.py::test_sb_edit_preserves_frontmatter -x` | ❌ W0 | ⬜ pending |
| 27-02-01 | 02 | 1 | ENGL-02 | unit | `uv run pytest tests/test_search_regression.py::test_precision_person_full_name -x` | ✅ W0 | ⬜ pending |
| 27-02-02 | 02 | 1 | ENGL-02 | unit | `uv run pytest tests/test_search_regression.py::test_precision_partial_name -x` | ✅ W0 | ⬜ pending |
| 27-02-03 | 02 | 1 | ENGL-02 | unit | `uv run pytest tests/test_search_regression.py::test_hybrid_title_wins -x` | ✅ W0 | ⬜ pending |
| 27-03-01 | 03 | 1 | ENGL-02 | unit | `uv run pytest tests/test_search_regression.py::test_recall_body_topic -x` | ✅ W0 | ⬜ pending |
| 27-04-01 | 04 | 1 | ENGL-02 | unit | `uv run pytest tests/test_mcp.py::test_sb_edit_preserves_frontmatter -x` | ✅ W0 | ⬜ pending |
| 27-05-01 | 05 | 2 | ENGL-02 | unit | `uv run pytest tests/ -q` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_search_regression.py` — 10 regression queries (5 precision + 5 recall) for ENGL-02
- [ ] `tests/test_mcp.py` — add `test_sb_edit_preserves_frontmatter` stub

*Existing infrastructure (pytest, seeded_db fixture, DB_PATH patching) covers all other phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Person→note sidebar chips render correctly | ENGL-02 | UI rendering requires browser | Open GUI, open any note with person mentions, verify chips appear in sidebar |
| sb-recap returns results for recent activity | ENGL-02 | Requires live brain data | Run `sb-recap`, verify recent notes appear |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
