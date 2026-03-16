---
phase: 17
slug: api-layer-and-setup-automation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini or pyproject.toml |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | SETUP-03 | integration | `python -m pytest tests/test_api.py -x -q` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | SETUP-03 | integration | `python -m pytest tests/test_api.py -x -q` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 1 | SETUP-01 | unit | `python -m pytest tests/test_init.py::test_drive_detection -x -q` | ❌ W0 | ⬜ pending |
| 17-02-02 | 02 | 1 | SETUP-02 | unit | `python -m pytest tests/test_init.py::test_ollama_detection -x -q` | ❌ W0 | ⬜ pending |
| 17-03-01 | 03 | 2 | SETUP-04 | integration | `python -m pytest tests/test_api.py::test_health_endpoint -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_api.py` — stubs for SETUP-03, SETUP-04 (API endpoints and health check)
- [ ] `tests/test_init.py` — stubs for SETUP-01, SETUP-02 (Drive detection, Ollama automation)
- [ ] `tests/conftest.py` — shared fixtures (test client, mock Drive paths)
- [ ] `pip install waitress flask flask-cors` — if not already installed

*If existing conftest.py covers fixtures, Wave 0 only needs test stubs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Ollama auto-install on fresh machine | SETUP-02 | Requires real machine without Ollama; can't mock binary absence reliably | Run `sb-init` on VM with no Ollama installed; verify it installs and starts |
| Google Drive path not found error | SETUP-01 | Requires machine without Google Drive mounted | Run `sb-init` without Drive mounted; verify non-zero exit + readable message |
| Drive size warning before download | SETUP-02 | Interactive prompt requires human to confirm | Run `sb-init` with no embedding model; verify ~800 MB warning appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
