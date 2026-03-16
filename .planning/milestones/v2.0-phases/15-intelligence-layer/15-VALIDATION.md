---
phase: 15
slug: intelligence-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/test_intelligence.py -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_intelligence.py -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 0 | INTL-01–10 | unit stubs | `python -m pytest tests/test_intelligence.py -q` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 1 | INTL-03/04/05 | unit (in-memory DB) | `python -m pytest tests/test_intelligence.py::TestExtractActionItems tests/test_intelligence.py::TestActionsList tests/test_intelligence.py::TestActionsDone -x` | ❌ W0 | ⬜ pending |
| 15-02-02 | 02 | 1 | INTL-01/02 | unit (mock LLM + mock git) | `python -m pytest tests/test_intelligence.py::TestClaudeMdHook tests/test_intelligence.py::TestRecap tests/test_intelligence.py::TestRecapNoContext -x` | ❌ W0 | ⬜ pending |
| 15-02-03 | 02 | 1 | INTL-06/07/08 | unit (in-memory DB + tmp files) | `python -m pytest tests/test_intelligence.py::TestStaleNudge tests/test_intelligence.py::TestEvergreenExempt tests/test_intelligence.py::TestStaleSnooze -x` | ❌ W0 | ⬜ pending |
| 15-02-04 | 02 | 1 | INTL-09 | unit (mock find_similar) | `python -m pytest tests/test_intelligence.py::TestConnectionSuggestion tests/test_intelligence.py::TestConnectionSuggestionEmpty -x` | ❌ W0 | ⬜ pending |
| 15-02-05 | 02 | 1 | INTL-10 | unit (mock state file) | `python -m pytest tests/test_intelligence.py::TestBudgetGate tests/test_intelligence.py::TestExplicitCommandsAlwaysWork -x` | ❌ W0 | ⬜ pending |
| 15-03-01 | 03 | 2 | INTL-01–10 | integration | `python -m pytest tests/ -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_intelligence.py` — test stubs for all INTL-01 through INTL-10
- [ ] `engine/intelligence.py` — new module with stub function bodies (`pass`) for RED phase
- [ ] `engine/db.py` — `migrate_add_action_items_table()` migration function added
- [ ] `engine/db.py` — `action_items` DDL added to `SCHEMA_SQL` constant

*Wave 0 creates failing tests (RED) before any implementation work.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `sb-recap` output reads naturally in a real Claude Code session | INTL-02 | LLM output quality is subjective | Run `sb-recap` in a project dir; verify summary is coherent and relevant |
| Session hook triggers exactly once per session | INTL-01 | Requires live Claude Code session lifecycle | Start fresh Claude Code session; verify recap offered once, not on next command |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
