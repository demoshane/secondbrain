---
phase: 22
slug: note-deletion-security-hardening
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-16
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_delete.py tests/test_api.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_delete.py tests/test_api.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 0 | GUIX-06 | unit | `uv run pytest tests/test_delete.py -x -q` | ✅ | ✅ green |
| 22-02-01 | 02 | 1 | GUIX-06 | unit | `uv run pytest tests/test_delete.py::test_delete_note_removes_file -x` | ✅ | ✅ green |
| 22-02-02 | 02 | 1 | GUIX-06 | unit | `uv run pytest tests/test_delete.py::test_delete_note_removes_db_row -x` | ✅ | ✅ green |
| 22-02-03 | 02 | 1 | GUIX-06 | unit | `uv run pytest tests/test_delete.py::test_delete_note_removes_embedding -x` | ✅ | ✅ green |
| 22-02-04 | 02 | 1 | GUIX-06 | unit | `uv run pytest tests/test_delete.py::test_delete_note_removes_relationships -x` | ✅ | ✅ green |
| 22-02-05 | 02 | 1 | GUIX-06 | unit | `uv run pytest tests/test_delete.py::test_delete_note_removes_action_items -x` | ✅ | ✅ green |
| 22-02-06 | 02 | 1 | GUIX-06 | unit | `uv run pytest tests/test_delete.py::test_delete_note_audit_log -x` | ✅ | ✅ green |
| 22-02-07 | 02 | 1 | GUIX-06 | unit | `uv run pytest tests/test_delete.py::test_fts5_clean_after_delete -x` | ✅ | ✅ green |
| 22-03-01 | 03 | 1 | GUIX-06 | integration | `uv run pytest tests/test_delete.py::test_delete_endpoint_200 -x` | ✅ | ✅ green |
| 22-03-02 | 03 | 1 | GUIX-06 | integration | `uv run pytest tests/test_delete.py::test_delete_endpoint_404 -x` | ✅ | ✅ green |
| 22-03-03 | 03 | 1 | GUIX-06 | security | `uv run pytest tests/test_delete.py::test_delete_endpoint_path_traversal_403 -x` | ✅ | ✅ green |
| 22-03-04 | 03 | 1 | GUIX-06 | security | `uv run pytest tests/test_delete.py::test_get_note_path_traversal_403 -x` | ✅ | ✅ green |
| 22-03-05 | 03 | 1 | GUIX-06 | security | `uv run pytest tests/test_delete.py::test_save_note_path_traversal_403 -x` | ✅ | ✅ green |
| 22-04-01 | 04 | 2 | GUIX-06 | manual | — | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_delete.py` — all stubs for GUIX-06 unit, integration, and security tests
- [ ] `engine/delete.py` — `delete_note()` utility stub (importable by tests before implementation)

*conftest.py and test infrastructure are fully present — reuse `brain_root`, `db_conn`, `initialized_db`, `client`, and `tmp_note` fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Delete button appears in note toolbar; confirmation dialog shows note title | GUIX-06 | GUI interaction, no headless test harness | Open GUI, open a note, click Delete, verify dialog shows note title |
| Note disappears from sidebar immediately after confirm | GUIX-06 | DOM/SSE real-time behavior | Confirm delete, verify sidebar updates without page refresh |
| Watcher does not re-index the deleted note | GUIX-06 | Race condition between watcher and delete | Delete a note, wait 2s, verify note is absent from search results |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-03-16 — human verified
