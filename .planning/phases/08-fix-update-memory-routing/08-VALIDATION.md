---
phase: 8
slug: fix-update-memory-routing
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-15
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run --no-project --with pytest tests/test_ai.py -x` |
| **Full suite command** | `uv run --no-project --with pytest tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run --no-project --with pytest tests/test_ai.py -x`
- **After every plan wave:** Run `uv run --no-project --with pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-00-01 | 00 | 0 | AI-05 | unit | `pytest tests/test_ai.py::test_update_memory_routing_uses_config -x` | ✅ | ✅ green |
| 08-01-01 | 01 | 1 | AI-05 | unit | `pytest tests/test_ai.py::test_update_memory_routing_uses_config -x` | ✅ after W0 | ✅ green |
| 08-01-02 | 01 | 1 | AI-05 | unit | `pytest tests/test_ai.py::test_cap06_memory_update_uses_write_tool -x` | ✅ existing | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_ai.py` — add `test_update_memory_routing_uses_config` asserting `get_adapter` is called with `("public", config_path)`

*Existing test `test_cap06_memory_update_uses_write_tool` covers the subprocess/Write tool assertion — no new infrastructure needed.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
