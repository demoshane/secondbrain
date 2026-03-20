---
phase: 26
slug: intelligence-features
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` or `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 1 | ENGL-03 | unit | `uv run pytest tests/test_digest.py -x -q` | ❌ W0 | ⬜ pending |
| 26-01-02 | 01 | 1 | ENGL-03 | unit | `uv run pytest tests/test_digest.py -x -q` | ❌ W0 | ⬜ pending |
| 26-01-03 | 01 | 1 | ENGL-04 | unit | `uv run pytest tests/test_intelligence.py -x -q` | ❌ W0 | ⬜ pending |
| 26-02-01 | 02 | 1 | ENGL-05 | unit | `uv run pytest tests/test_brain_health.py -x -q` | ❌ W0 | ⬜ pending |
| 26-02-02 | 02 | 1 | ENGL-05 | unit | `uv run pytest tests/test_brain_health.py -x -q` | ❌ W0 | ⬜ pending |
| 26-03-01 | 03 | 2 | GUIF-02 | e2e | `uv run pytest tests/test_gui_intelligence.py -x -q` | ❌ W0 | ⬜ pending |
| 26-03-02 | 03 | 2 | GUIF-02 | e2e | `uv run pytest tests/test_gui_health.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_digest.py` — stubs for ENGL-03 (digest column fix + dedup)
- [ ] `tests/test_intelligence.py` — stubs for ENGL-04 (on-demand recap)
- [ ] `tests/test_brain_health.py` — stubs for ENGL-05 (brain health score)
- [ ] `tests/test_gui_intelligence.py` — stubs for GUIF-02 (recap button)
- [ ] `tests/test_gui_health.py` — stubs for GUIF-02 (health panel)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Recap spinner visible during generation | GUIF-02 | UI animation timing | Click "Generate Recap" and observe spinner appears before result |
| Health panel updates live after new note | GUIF-02 | Real-time UI state | Add orphan note, reload health panel, verify score changes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
