---
phase: 33
slug: performance-scale-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 33 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, no install needed) |
| **Config file** | none — run via `uv run pytest` |
| **Quick run command** | `uv run pytest tests/test_intelligence.py tests/test_reindex.py tests/test_search.py tests/test_mcp.py tests/test_api.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_intelligence.py tests/test_reindex.py tests/test_search.py tests/test_mcp.py tests/test_api.py -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 33-01-01 | 01 | 1 | PERF-01 | unit | `uv run pytest tests/test_api.py -k pagination -x` | ❌ Wave 0 | ⬜ pending |
| 33-01-02 | 01 | 1 | PERF-01 | unit | `uv run pytest tests/test_mcp.py -k pagination -x` | ❌ Wave 0 | ⬜ pending |
| 33-01-03 | 01 | 1 | PERF-01 | unit | `uv run pytest tests/ -q` | ✅ | ⬜ pending |
| 33-02-01 | 02 | 1 | PERF-02 | unit | `uv run pytest tests/test_intelligence.py -k cooldown -x` | ❌ Wave 0 | ⬜ pending |
| 33-02-02 | 02 | 1 | PERF-03 | unit | `uv run pytest tests/test_reindex.py -k incremental -x` | ❌ Wave 0 | ⬜ pending |
| 33-02-03 | 02 | 1 | PERF-03 | unit | `uv run pytest tests/test_reindex.py -k full -x` | ✅ | ⬜ pending |
| 33-03-01 | 03 | 2 | PERF-04 | unit | `uv run pytest tests/test_intelligence.py -k window_days -x` | ❌ Wave 0 | ⬜ pending |
| 33-03-02 | 03 | 2 | PERF-04 | unit | `uv run pytest tests/test_intelligence.py -k recap_days -x` | ❌ Wave 0 | ⬜ pending |
| 33-03-03 | 03 | 2 | PERF-05 | unit | `uv run pytest tests/test_reindex.py -k embed_async -x` | ❌ Wave 0 | ⬜ pending |
| 33-04-01 | 04 | 2 | PERF-06 | unit | `uv run pytest tests/test_search.py -k filter -x` | ❌ Wave 0 | ⬜ pending |
| 33-05-01 | 05 | 2 | PERF-07 | unit | `uv run pytest tests/test_mcp.py -k person_context -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_api.py` — pagination test stubs (PERF-01): `test_list_notes_pagination`, `test_list_notes_offset`
- [ ] `tests/test_mcp.py` — pagination test stubs (PERF-01): `test_sb_files_page2`, `test_sb_actions_pagination`
- [ ] `tests/test_intelligence.py` — cooldown stubs (PERF-02): `test_check_connections_cooldown`; recap stubs (PERF-04): `test_recap_window_days`, `test_recap_days_cli_override`
- [ ] `tests/test_reindex.py` — incremental stubs (PERF-03): `test_reindex_skips_unchanged`; embed async stub (PERF-05): `test_embed_pass_async_nonblocking`
- [ ] `tests/test_search.py` — entity filter stubs (PERF-06): `test_search_filter_by_person`, `test_search_filter_by_tag`, `test_search_filter_by_type`, `test_search_filter_date_range`

*These stubs must be created before the plan that implements their behavior executes.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| check_connections cooldown resets on process restart | PERF-02 | Requires process kill/restart cycle | Start sb-api, trigger check_connections, restart sb-api, verify cooldown is cleared |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
