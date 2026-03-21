---
phase: 32
slug: architecture-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 32 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -q --tb=short` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -q --tb=short`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 32-01-01 | 01 | 1 | ARCH-01 | unit+migration | `uv run pytest tests/test_db.py tests/test_paths.py -q` | ✅ / ❌ W0 | ⬜ pending |
| 32-02-01 | 02 | 1 | ARCH-02 | unit | `uv run pytest tests/test_db.py -q` | ✅ | ⬜ pending |
| 32-02-02 | 02 | 1 | ARCH-03 | unit | `uv run pytest tests/test_api.py -q` | ✅ | ⬜ pending |
| 32-02-03 | 02 | 1 | ARCH-04 | unit | `uv run pytest tests/test_api.py -q` | ✅ | ⬜ pending |
| 32-03-01 | 03 | 2 | ARCH-05 | unit+migration | `uv run pytest tests/test_db.py tests/test_capture.py -q` | ✅ / ❌ W0 | ⬜ pending |
| 32-03-02 | 03 | 2 | ARCH-15 | unit+migration | `uv run pytest tests/test_db.py tests/test_capture.py -q` | ✅ / ❌ W0 | ⬜ pending |
| 32-04-01 | 04 | 2 | ARCH-06 | unit | `uv run pytest tests/test_intelligence.py tests/test_health.py -q` | ✅ / ❌ W0 | ⬜ pending |
| 32-05-01 | 05 | 3 | ARCH-07 | unit | `uv run pytest tests/test_api.py -q` | ✅ | ⬜ pending |
| 32-05-02 | 05 | 3 | ARCH-08 | unit | `uv run pytest tests/test_forget.py -q` | ✅ | ⬜ pending |
| 32-05-03 | 05 | 3 | ARCH-09 | unit | `uv run pytest tests/test_capture.py tests/test_search.py -q` | ✅ | ⬜ pending |
| 32-05-04 | 05 | 3 | ARCH-14 | unit | `uv run pytest tests/test_api.py tests/test_mcp.py -q` | ✅ / ❌ W0 | ⬜ pending |
| 32-05-05 | 05 | 3 | ARCH-16 | unit | `uv run pytest tests/test_db.py tests/test_mcp.py -q` | ✅ | ⬜ pending |
| 32-06-01 | 06 | 3 | ARCH-10 | unit | `uv run pytest tests/test_people.py -q` | ❌ W0 | ⬜ pending |
| 32-06-02 | 06 | 3 | ARCH-11 | unit | `uv run pytest tests/test_people.py tests/test_mcp.py -q` | ❌ W0 | ⬜ pending |
| 32-06-03 | 06 | 3 | ARCH-12 | unit | `uv run pytest tests/test_reindex.py -q` | ❌ W0 | ⬜ pending |
| 32-06-04 | 06 | 3 | ARCH-13 | unit | `uv run pytest tests/test_api.py tests/test_mcp.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_paths.py` — stubs for resolve_path/store_path (ARCH-01)
- [ ] `tests/test_people.py` — stubs for shared service function, path+name matching (ARCH-10, ARCH-11)
- [ ] `tests/test_reindex.py` — stubs for entity merge on reindex (ARCH-12)
- [ ] `tests/test_health.py` — stubs for archive counts in health check (ARCH-06)

*Existing test files cover ARCH-02 through ARCH-05, ARCH-07 through ARCH-09, ARCH-13 through ARCH-16.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Migration runs on real brain DB | ARCH-01 | Production data patterns can't be mocked | Run `sb-health` after upgrade on host; verify note count unchanged |
| forget_person dry-run output | ARCH-08 | Interactive confirmation flow | Run `sb_forget` via MCP on test person; verify dry-run shows affected notes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
