---
phase: 35
slug: brain-consolidation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 35 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via uv) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_brain_health.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_brain_health.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 35-01-W0 | 01 | 0 | CONS-01 | unit stub | `uv run pytest tests/test_brain_health.py -x -q` | ❌ W0 | ⬜ pending |
| 35-01-01 | 01 | 1 | CONS-01 | unit | `uv run pytest tests/test_brain_health.py::test_merge_copies_body_tags_relationships -x` | ❌ W0 | ⬜ pending |
| 35-01-02 | 01 | 1 | CONS-01 | unit | `uv run pytest tests/test_brain_health.py::test_merge_deletes_discard_note -x` | ❌ W0 | ⬜ pending |
| 35-01-03 | 01 | 1 | CONS-01 | unit | `uv run pytest tests/test_mcp.py::test_merge_confirm_requires_token -x` | ❌ W0 | ⬜ pending |
| 35-02-01 | 02 | 1 | CONS-02 | unit | `uv run pytest tests/test_brain_health.py::test_get_stub_notes_word_count -x` | ❌ W0 | ⬜ pending |
| 35-02-02 | 02 | 1 | CONS-02 | unit | `uv run pytest tests/test_mcp.py::test_find_stubs_with_matches -x` | ❌ W0 | ⬜ pending |
| 35-02-03 | 02 | 1 | CONS-03 | unit | `uv run pytest tests/test_brain_health.py::test_delete_dangling_relationships -x` | ❌ W0 | ⬜ pending |
| 35-02-04 | 02 | 1 | CONS-03 | unit | `uv run pytest tests/test_brain_health.py::test_bidirectional_gap_detection -x` | ❌ W0 | ⬜ pending |
| 35-03-01 | 03 | 1 | CONS-04 | unit | `uv run pytest tests/test_brain_health.py::test_health_snapshots_migration -x` | ❌ W0 | ⬜ pending |
| 35-03-02 | 03 | 1 | CONS-04 | unit | `uv run pytest tests/test_brain_health.py::test_take_health_snapshot -x` | ❌ W0 | ⬜ pending |
| 35-03-03 | 03 | 1 | CONS-04 | unit | `uv run pytest tests/test_brain_health.py::test_cleanup_old_snapshots -x` | ❌ W0 | ⬜ pending |
| 35-03-04 | 03 | 1 | CONS-05 | unit | `uv run pytest tests/test_consolidate.py::test_consolidate_main_runs_clean -x` | ❌ W0 | ⬜ pending |
| 35-03-05 | 03 | 1 | CONS-05 | unit | `uv run pytest tests/test_install_native.py::test_write_consolidate_plist -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_brain_health.py` — add Phase 35 test stubs for CONS-01 through CONS-04 (extend existing file)
- [ ] `tests/test_mcp.py` — add `test_merge_confirm_requires_token` and `test_find_stubs_with_matches` stubs
- [ ] `tests/test_consolidate.py` — new file for `consolidate_main` integration test stub
- [ ] `tests/test_install_native.py` — add `test_write_consolidate_plist` stub (extend existing file)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GUI merge button visible in health panel | CONS-01 | Frontend rendering requires browser | Open GUI → Intelligence/Health tab → verify duplicate pair shows Merge button |
| launchd consolidate job fires on next wake | CONS-05 | Requires system sleep simulation | `launchctl list | grep consolidate` → verify loaded; check log after sleep/wake cycle |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
