---
phase: 7
slug: fix-path-format-split
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-15
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run --no-project --with pytest pytest tests/test_capture.py tests/test_rag.py tests/test_forget.py -x -q` |
| **Full suite command** | `uv run --no-project --with pytest pytest -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run --no-project --with pytest pytest tests/test_capture.py tests/test_rag.py tests/test_forget.py -x -q`
- **After every plan wave:** Run `uv run --no-project --with pytest pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-00-01 | 00 | 0 | SEARCH-01 | unit | `pytest tests/test_capture.py::test_write_note_atomic_stores_absolute_path -x` | ✅ | ✅ green |
| 7-00-02 | 00 | 0 | SEARCH-01 | unit | `pytest tests/test_capture.py::test_write_note_atomic_path_is_absolute -x` | ✅ | ✅ green |
| 7-00-03 | 00 | 0 | SEARCH-04 | unit | `pytest tests/test_rag.py::test_retrieve_context_reads_captured_note -x` | ✅ | ✅ green |
| 7-00-04 | 00 | 0 | GDPR-01 | unit | `pytest tests/test_forget.py::test_forget_removes_row_stored_by_capture -x` | ✅ | ✅ green |
| 7-01-01 | 01 | 1 | SEARCH-01 | unit | `pytest tests/test_capture.py::test_write_note_atomic_stores_absolute_path tests/test_capture.py::test_write_note_atomic_path_is_absolute -x` | ✅ | ✅ green |
| 7-01-02 | 01 | 1 | SEARCH-04 | unit | `pytest tests/test_rag.py::test_retrieve_context_reads_captured_note -x` | ✅ | ✅ green |
| 7-01-03 | 01 | 1 | GDPR-01 | unit | `pytest tests/test_forget.py::test_forget_removes_row_stored_by_capture -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_capture.py::test_write_note_atomic_stores_absolute_path` — stub for SEARCH-01 (path value in DB)
- [x] `tests/test_capture.py::test_write_note_atomic_path_is_absolute` — stub for SEARCH-01 (path format guard)
- [x] `tests/test_rag.py::test_retrieve_context_reads_captured_note` — stub for SEARCH-04
- [x] `tests/test_forget.py::test_forget_removes_row_stored_by_capture` — stub for GDPR-01

All 4 are new test functions in existing files. No new test files needed.

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
