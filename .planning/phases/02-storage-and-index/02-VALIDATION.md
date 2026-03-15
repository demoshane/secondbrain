---
phase: 2
slug: storage-and-index
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-14
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `uv run pytest tests/test_capture.py tests/test_search.py tests/test_audit.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_capture.py tests/test_search.py tests/test_audit.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-00-01 | 00 | 0 | CAP-01,CAP-02,CAP-03,CAP-07,SEARCH-01,SEARCH-02,GDPR-03,GDPR-05,GDPR-06 | stub | `uv run pytest tests/test_capture.py tests/test_search.py tests/test_audit.py --collect-only` | ✅ | ✅ green |
| 2-01-01 | 01 | 1 | CAP-01,CAP-02 | unit | `uv run pytest tests/test_capture.py -x -q` | ✅ | ✅ green |
| 2-02-01 | 02 | 1 | CAP-03 | unit | `uv run pytest tests/test_capture.py::test_atomic_write -x -q` | ✅ | ✅ green |
| 2-03-01 | 03 | 2 | SEARCH-01,SEARCH-02 | unit | `uv run pytest tests/test_search.py -x -q` | ✅ | ✅ green |
| 2-04-01 | 04 | 2 | GDPR-03,GDPR-05 | unit | `uv run pytest tests/test_audit.py -x -q` | ✅ | ✅ green |
| 2-05-01 | 05 | 3 | CAP-07,GDPR-06 | integration | `uv run pytest tests/ -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_capture.py` — stubs for CAP-01, CAP-02, CAP-03
- [x] `tests/test_search.py` — stubs for SEARCH-01, SEARCH-02
- [x] `tests/test_audit.py` — stubs for GDPR-03, GDPR-05, GDPR-06
- [x] `tests/conftest.py` — extend with capture/search fixtures (tmp brain dir, sample notes)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Process-kill atomicity | CAP-03 | Requires SIGKILL between file write and DB commit | `kill -9` a running `/sb-capture` mid-flight, verify no partial note on disk |
| detect-secrets baseline | CAP-07 | Requires full scan of engine/ codebase | `uv run detect-secrets scan engine/ \| python3 -m json.tool` — confirm zero violations |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
