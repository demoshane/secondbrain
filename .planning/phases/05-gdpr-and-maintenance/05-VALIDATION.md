---
phase: 5
slug: gdpr-and-maintenance
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-14
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `uv run --no-project --with pytest pytest tests/test_forget.py tests/test_read.py -x -q` |
| **Full suite command** | `uv run --no-project --with pytest pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run --no-project --with pytest pytest tests/test_forget.py tests/test_read.py -x -q`
- **After every plan wave:** Run `uv run --no-project --with pytest pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-00-01 | 00 | 1 | GDPR-01 | unit | `uv run --no-project --with pytest pytest tests/test_forget.py --collect-only -q` | ✅ | ✅ green |
| 5-00-02 | 00 | 1 | GDPR-04 | unit | `uv run --no-project --with pytest pytest tests/test_read.py --collect-only -q` | ✅ | ✅ green |
| 5-01-01 | 01 | 2 | GDPR-01 | unit | `uv run --no-project --with pytest pytest tests/test_forget.py::test_forget_person_removes_markdown -x -q` | ✅ | ✅ green |
| 5-01-02 | 01 | 2 | GDPR-02 | unit | `uv run --no-project --with pytest pytest tests/test_forget.py::test_forget_rebuilds_fts -x -q` | ✅ | ✅ green |
| 5-01-03 | 01 | 2 | GDPR-01 | unit | `uv run --no-project --with pytest pytest tests/test_forget.py::test_forget_meeting_sole_ref -x -q` | ✅ | ✅ green |
| 5-02-01 | 02 | 2 | GDPR-04 | unit | `uv run --no-project --with pytest pytest tests/test_read.py::test_pii_gate_blocks_without_passphrase -x -q` | ✅ | ✅ green |
| 5-02-02 | 02 | 2 | GDPR-04 | unit | `uv run --no-project --with pytest pytest tests/test_read.py::test_pii_gate_allows_with_passphrase -x -q` | ✅ | ✅ green |
| 5-03-01 | 03 | 3 | GDPR-01 | unit | `uv run --no-project --with pytest pytest tests/test_forget.py -q` | ✅ | ✅ green |
| 5-03-02 | 03 | 3 | GDPR-01 | manual | `sb-forget <test-person>` + `sb-search <test-person>` | N/A | manual-only |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_forget.py` — stubs for GDPR-01, GDPR-02 (forget_person, FTS rebuild, sole-reference meeting deletion)
- [x] `tests/test_read.py` — stubs for GDPR-04 (PII passphrase gate)
- [x] `engine/forget.py` — importable module stub with `forget_person()` raising `NotImplementedError`
- [x] `engine/read.py` — importable module stub with `read_note()` raising `NotImplementedError`

*Existing pytest infrastructure covers the framework; Wave 0 adds the test and module stubs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `sb-forget <person>` end-to-end with real vault | GDPR-01 | Requires real filesystem + DB state | Create test person note, run `sb-forget`, verify `sb-search` returns 0 results |
| Passphrase prompt blocks TTY | GDPR-04 | Requires interactive terminal | Open PII note without env var; confirm prompt appears and blocks |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
