---
phase: 12
slug: micro-code-fixes
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-15
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_reindex.py tests/test_export.py tests/test_ai.py tests/test_anonymize.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_reindex.py tests/test_export.py tests/test_ai.py tests/test_anonymize.py -q`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-00-01 | 00 | 0 | GDPR-03 | unit | `uv run pytest tests/test_anonymize.py -q` | ✅ W0 | ✅ green |
| 12-00-02 | 00 | 0 | AI-06 | unit | `uv run pytest tests/test_ai.py -q` | ✅ W0 | ✅ green |
| 12-00-03 | 00 | 0 | GDPR-05 | unit | `uv run pytest tests/test_export.py -q` | ✅ W0 | ✅ green |
| 12-00-04 | 00 | 0 | GDPR-01 | unit | `uv run pytest tests/test_reindex.py tests/test_forget.py -q` | ✅ W0 | ✅ green |
| 12-00-05 | 00 | 0 | CAP-02 | unit | `uv run pytest tests/test_reindex.py -q` | ✅ W0 | ✅ green |
| 12-01-01 | 01 | 1a | GDPR-03 | unit | `uv run pytest tests/test_anonymize.py -q` | ✅ | ✅ green |
| 12-01-02 | 01 | 1a | AI-06 | unit | `uv run pytest tests/test_ai.py -q` | ✅ | ✅ green |
| 12-02-01 | 02 | 1b | GDPR-05 | unit | `uv run pytest tests/test_export.py -q` | ✅ | ✅ green |
| 12-03-01 | 03 | 1c | GDPR-01 | unit | `uv run pytest tests/test_reindex.py tests/test_forget.py -q` | ✅ | ✅ green |
| 12-03-02 | 03 | 1c | CAP-02 | unit | `uv run pytest tests/test_reindex.py -q` | ✅ | ✅ green |
| 12-04-01 | 04 | 2 | All | manual | See manual verifications below | — | ✅ manual-only |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_reindex.py` — add `test_reindex_preserves_people_column` and `test_reindex_stores_resolved_absolute_paths` (confirm `.resolve()`)
- [x] `tests/test_export.py` — add `test_export_main_initialises_schema_on_fresh_db`
- [x] `tests/test_anonymize.py` — add `test_sb_anonymize_entry_point_registered`
- [x] `tests/test_ai.py` — add `test_sb_update_memory_entry_point_registered` + `test_update_memory_main_argparse`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `sb-anonymize --help` runs without error | GDPR-03 | Entry point validation in installed env | Run `sb-anonymize --help` in terminal |
| `sb-update-memory --help` runs without error | AI-06 | Entry point validation in installed env | Run `sb-update-memory --help` in terminal |
| `sb-export` completes on fresh DB | GDPR-05 | Schema init path requires live DB | Remove DB, run `sb-export`, confirm no OperationalError |
| After `sb-reindex` then `sb-forget <person>`, DELETE matches > 0 | GDPR-01 | End-to-end flow | Run sequence, check output |
| After `sb-reindex`, notes retain `people` field | CAP-02 | End-to-end flow | Run `sb-reindex`, inspect DB |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-15
