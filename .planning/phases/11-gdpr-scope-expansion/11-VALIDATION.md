---
phase: 11
slug: gdpr-scope-expansion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run --no-project --with pytest pytest tests/test_export.py tests/test_anonymize.py tests/test_consent.py -q` |
| **Full suite command** | `uv run --no-project --with pytest pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run --no-project --with pytest pytest tests/test_export.py tests/test_anonymize.py tests/test_consent.py -q`
- **After every plan wave:** Run `uv run --no-project --with pytest pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-00-01 | 00 | 0 | GDPR-02 | unit stub | `pytest tests/test_export.py -q` | ❌ W0 | ⬜ pending |
| 11-00-02 | 00 | 0 | GDPR-03 | unit stub | `pytest tests/test_anonymize.py -q` | ❌ W0 | ⬜ pending |
| 11-00-03 | 00 | 0 | GDPR-06 | unit stub | `pytest tests/test_consent.py -q` | ❌ W0 | ⬜ pending |
| 11-01-01 | 01 | 1 | GDPR-02 | unit | `pytest tests/test_export.py::test_export_returns_note_count -x` | ✅ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | GDPR-02 | unit | `pytest tests/test_export.py::test_export_json_contains_all_fields -x` | ✅ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | GDPR-02 | unit | `pytest tests/test_export.py::test_export_includes_pii_notes -x` | ✅ W0 | ⬜ pending |
| 11-01-04 | 01 | 1 | GDPR-02 | unit | `pytest tests/test_export.py::test_export_audit_logged -x` | ✅ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | GDPR-03 | unit | `pytest tests/test_anonymize.py::test_anonymize_replaces_token_in_body -x` | ✅ W0 | ⬜ pending |
| 11-02-02 | 02 | 1 | GDPR-03 | unit | `pytest tests/test_anonymize.py::test_anonymize_case_insensitive -x` | ✅ W0 | ⬜ pending |
| 11-02-03 | 02 | 1 | GDPR-03 | unit | `pytest tests/test_anonymize.py::test_anonymize_updates_db_row -x` | ✅ W0 | ⬜ pending |
| 11-02-04 | 02 | 1 | GDPR-03 | unit | `pytest tests/test_anonymize.py::test_anonymize_downgrades_sensitivity -x` | ✅ W0 | ⬜ pending |
| 11-02-05 | 02 | 1 | GDPR-03 | unit | `pytest tests/test_anonymize.py::test_anonymize_audit_logged -x` | ✅ W0 | ⬜ pending |
| 11-03-01 | 03 | 1 | GDPR-06 | unit | `pytest tests/test_consent.py::test_consent_sentinel_written -x` | ✅ W0 | ⬜ pending |
| 11-03-02 | 03 | 1 | GDPR-06 | unit | `pytest tests/test_consent.py::test_check_consent_returns_true_when_sentinel -x` | ✅ W0 | ⬜ pending |
| 11-03-03 | 03 | 1 | GDPR-06 | unit | `pytest tests/test_consent.py::test_check_consent_returns_false_when_missing -x` | ✅ W0 | ⬜ pending |
| 11-03-04 | 03 | 1 | GDPR-06 | unit | `pytest tests/test_consent.py::test_yes_flag_skips_prompt -x` | ✅ W0 | ⬜ pending |
| 11-03-05 | 03 | 1 | GDPR-06 | manual | n/a — TTY prompt | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_export.py` — stubs for GDPR-02 expanded (4 tests)
- [ ] `tests/test_anonymize.py` — stubs for GDPR-03 expanded (6 tests)
- [ ] `tests/test_consent.py` — stubs for GDPR-06 expanded (5 tests)
- [ ] `engine/export.py` — `export_brain()` and `main()` stubs
- [ ] `engine/anonymize.py` — `anonymize_note()` and `main()` stubs
- [ ] `engine/init_brain.py` — add `prompt_consent()`, `check_consent()`, `write_consent_sentinel()`, `--yes` flag
- [ ] `pyproject.toml` — add `sb-export = "engine.export:main"` to `[project.scripts]`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Consent prompt displays and waits for user input on fresh init | GDPR-06 | TTY interaction not automatable | Run `sb-init` in a fresh tmp dir; verify prompt appears and blocks |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
