---
phase: 21
slug: live-refresh-sse
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 0 | GUIX-01 | unit | `uv run pytest tests/test_sse.py -x -q` | ❌ W0 | ⬜ pending |
| 21-01-02 | 01 | 1 | GUIX-01 | unit | `uv run pytest tests/test_sse.py::test_subscribe -x -q` | ❌ W0 | ⬜ pending |
| 21-01-03 | 01 | 1 | GUIX-01 | unit | `uv run pytest tests/test_sse.py::test_notify -x -q` | ❌ W0 | ⬜ pending |
| 21-01-04 | 01 | 1 | GUIX-01 | manual | — | — | ⬜ pending |
| 21-02-01 | 02 | 2 | GUIX-01 | manual | — | — | ⬜ pending |
| 21-02-02 | 02 | 2 | GUIX-01 | manual | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_sse.py` — stubs for SSE subscribe, notify, heartbeat (GUIX-01)
- [ ] `tests/conftest.py` — Flask test client fixture with SSE app

*Existing pytest infrastructure covers the rest.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Note appears in sidebar within 2s after `sb-capture` | GUIX-01 | Requires live pywebview GUI | Run `sb-capture`, observe sidebar refresh |
| Note content updates in viewer within 2s after CLI edit | GUIX-01 | Requires live GUI | Edit note via CLI, observe viewer update |
| SSE reconnects after connection drop | GUIX-01 | Requires network simulation | Kill server briefly, observe auto-reconnect |
| pywebview EventSource compatibility | GUIX-01 | Runtime environment | Open GUI, check browser console for SSE errors |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
