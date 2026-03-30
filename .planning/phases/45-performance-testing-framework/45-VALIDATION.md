---
phase: 45
slug: performance-testing-framework
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 45 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7+ |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_perf.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_perf.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/test_perf.py tests/test_api.py -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 45-01 | perf-engine | 1 | PERF-01 | unit | `uv run pytest tests/test_perf.py::test_cleanup_test_notes -x` | W0 | pending |
| 45-02 | perf-engine | 1 | PERF-02 | unit | `uv run pytest tests/test_perf.py::test_save_result -x` | W0 | pending |
| 45-03 | perf-engine | 1 | PERF-03 | unit | `uv run pytest tests/test_perf.py::test_rotate_old_results -x` | W0 | pending |
| 45-04 | perf-engine | 1 | PERF-04 | unit | `uv run pytest tests/test_perf.py::test_delta_computation -x` | W0 | pending |
| 45-05 | perf-api | 2 | PERF-05 | unit | `uv run pytest tests/test_api.py::test_perf_list_results -x` | W0 | pending |
| 45-06 | perf-api | 2 | PERF-06 | unit | `uv run pytest tests/test_api.py::test_perf_latest -x` | W0 | pending |
| 45-07 | perf-engine | 1 | PERF-07 | unit | `uv run pytest tests/test_perf.py::test_cleanup_flag -x` | W0 | pending |
| 45-08 | perf-engine | 1 | PERF-08 | unit | `uv run pytest tests/test_perf.py::test_error_recovery -x` | W0 | pending |
| 45-09 | perf-engine | 1 | PERF-09 | unit | `uv run pytest tests/test_perf.py::test_full_suite_runs -x` | W0 | pending |
| 45-10 | perf-engine | 1 | PERF-10 | unit | `uv run pytest tests/test_perf.py::test_run_benchmarks_with_filter -x` | W0 | pending |
| 45-11 | perf-engine | 1 | PERF-11 | unit | `uv run pytest tests/test_perf.py::test_json_output -x` | W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_perf.py` — stubs for PERF-01 through PERF-11 (new file)
- [ ] `engine/perf.py` — module must exist before tests can import it
- [ ] `engine/test_utils.py` — cleanup utility (or extend existing conftest)

*Existing pytest infrastructure covers the framework — no install step needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `sb-perf` CLI terminal output (colors, icons, delta formatting) | PERF-CLI | Visual only — no assertion on ANSI output | Run `sb-perf`, verify table renders with pass/warn icons and delta column |
| GUI Performance page renders chart + history table | PERF-GUI | Playwright / host-only | Open `http://localhost:37491/ui`, navigate to Performance tab, verify chart and table visible |
| Performance tab position (after Intelligence, before Inbox) | D-16 | Visual tab ordering | Open GUI, verify tab ordering in TabBar |
| `sb-perf --cleanup` purges synthetic notes from brain | PERF-07 (integration) | Requires live brain | Run after full benchmark, check ~/SecondBrain for orphan perf-test-* files |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
