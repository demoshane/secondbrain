---
phase: 16
slug: semantic-search-and-digest
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 7.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_search.py tests/test_intelligence.py tests/test_digest.py -q -x` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_search.py tests/test_intelligence.py tests/test_digest.py -q -x`
- **After every plan wave:** Run `pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-??-01 | 01 | 1 | SRCH-01 | unit | `pytest tests/test_search.py::TestSemanticSearch -x` | ❌ Wave 0 | ⬜ pending |
| 16-??-02 | 01 | 1 | SRCH-01 | unit | `pytest tests/test_search.py::TestSemanticFallback -x` | ❌ Wave 0 | ⬜ pending |
| 16-??-03 | 02 | 2 | SRCH-02 | unit | `pytest tests/test_search.py::TestHybridSearch -x` | ❌ Wave 0 | ⬜ pending |
| 16-??-04 | 02 | 2 | SRCH-02 | unit | `pytest tests/test_search.py::TestKeywordFlag -x` | ❌ Wave 0 | ⬜ pending |
| 16-??-05 | 02 | 2 | SRCH-02 | unit | `pytest tests/test_search.py::TestHybridFallback -x` | ❌ Wave 0 | ⬜ pending |
| 16-??-06 | 03 | 2 | SRCH-03 | unit | `pytest tests/test_intelligence.py::TestRecapEntity -x` | ❌ Wave 0 | ⬜ pending |
| 16-??-07 | 03 | 2 | SRCH-03 | unit | `pytest tests/test_intelligence.py::TestRecapEntityEmpty -x` | ❌ Wave 0 | ⬜ pending |
| 16-??-08 | 03 | 2 | SRCH-04 | unit | `pytest tests/test_intelligence.py::TestRecapEntityPIIRouting -x` | ❌ Wave 0 | ⬜ pending |
| 16-??-09 | 04 | 3 | DIAG-01 | unit | `pytest tests/test_digest.py::TestDigestWrite -x` | ❌ Wave 0 | ⬜ pending |
| 16-??-10 | 04 | 3 | DIAG-01 | unit | `pytest tests/test_digest.py::TestDigestIdempotent -x` | ❌ Wave 0 | ⬜ pending |
| 16-??-11 | 04 | 3 | DIAG-02 | unit | `pytest tests/test_digest.py::TestDigestSections -x` | ❌ Wave 0 | ⬜ pending |
| 16-??-12 | 04 | 3 | DIAG-03 | unit | `pytest tests/test_read.py::TestDigestFlag -x` | ❌ Wave 0 | ⬜ pending |
| 16-??-13 | 04 | 3 | DIAG-03 | unit | `pytest tests/test_read.py::TestDigestFlagEmpty -x` | ❌ Wave 0 | ⬜ pending |
| 16-??-14 | 04 | 3 | DIAG-04 | unit | `pytest tests/test_digest.py::TestDigestPIIRouting -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_search.py` — add `TestSemanticSearch`, `TestSemanticFallback`, `TestHybridSearch`, `TestKeywordFlag`, `TestHybridFallback` classes (RED stubs)
- [ ] `tests/test_intelligence.py` — add `TestRecapEntity`, `TestRecapEntityEmpty`, `TestRecapEntityPIIRouting` classes (RED stubs)
- [ ] `tests/test_digest.py` — new file; covers `TestDigestWrite`, `TestDigestIdempotent`, `TestDigestSections`, `TestDigestPIIRouting`
- [ ] `tests/test_read.py` — add `TestDigestFlag`, `TestDigestFlagEmpty` classes
- [ ] `engine/digest.py` — new module (stub with `NotImplementedError` in Wave 0)
- [ ] `pyproject.toml` — register `sb-digest = "engine.digest:digest_main"` script entry point

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| launchd plist fires digest on Monday 08:00 | DIAG-04 | Requires real calendar wait | `launchctl list | grep sb-digest` + wait for trigger, or `launchctl start com.secondbrain.digest` to test immediately |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
