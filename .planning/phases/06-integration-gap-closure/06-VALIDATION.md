---
phase: 6
slug: integration-gap-closure
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-15
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run --no-project --with pytest pytest tests/test_capture.py tests/test_watcher.py tests/test_reindex.py tests/test_subagent.py -x` |
| **Full suite command** | `uv run --no-project --with pytest pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run --no-project --with pytest pytest tests/test_capture.py tests/test_watcher.py tests/test_reindex.py tests/test_subagent.py -x`
- **After every plan wave:** Run `uv run --no-project --with pytest pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-W0-01 | W0 | 0 | CAP-06 | unit stub | `pytest tests/test_capture.py::test_cap06_update_memory_called_after_capture -x` | ✅ | ✅ green |
| 6-W0-02 | W0 | 0 | CAP-06 | unit stub | `pytest tests/test_capture.py::test_cap06_update_memory_skipped_for_pii -x` | ✅ | ✅ green |
| 6-W0-03 | W0 | 0 | AI-02 | unit stub | `pytest tests/test_watcher.py::test_watcher_pii_routes_to_ollama -x` | ✅ | ✅ green |
| 6-W0-04 | W0 | 0 | AI-02 | unit stub | `pytest tests/test_watcher.py::test_watcher_binary_fallback_to_private -x` | ✅ | ✅ green |
| 6-W0-05 | W0 | 0 | SEARCH-01/AI-08 | unit stub | `pytest tests/test_reindex.py::test_reindex_stores_absolute_paths -x` | ✅ | ✅ green |
| 6-W0-06 | W0 | 0 | CAP-08 | unit stub | `pytest tests/test_subagent.py::test_subagent_documents_all_commands -x` | ✅ | ✅ green |
| 6-reindex | 01 | 1 | SEARCH-01/AI-08 | unit | `pytest tests/test_reindex.py -x` | ✅ (updated) | ✅ green |
| 6-watcher | 02 | 1 | AI-02 | unit | `pytest tests/test_watcher.py -x` | ✅ (updated) | ✅ green |
| 6-cap06 | 03 | 1 | CAP-06 | unit | `pytest tests/test_capture.py -x` | ✅ (updated) | ✅ green |
| 6-cap08 | 04 | 2 | CAP-08 | unit | `pytest tests/test_subagent.py -x` | ✅ (updated) | ✅ green |
| 6-cap09 | 05 | 2 | CAP-09 | manual | Manual inspection of `~/.claude/CLAUDE.md` | manual-only | manual-only |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_capture.py` — add `test_cap06_update_memory_called_after_capture` and `test_cap06_update_memory_skipped_for_pii` (failing stubs)
- [x] `tests/test_watcher.py` — add `test_watcher_pii_routes_to_ollama` and `test_watcher_binary_fallback_to_private` (failing stubs); update `test_main_on_new_file_no_input_on_ai_failure` closure shape
- [x] `tests/test_reindex.py` — add `test_reindex_stores_absolute_paths` (failing stub); note existing `test_reindex_parses_frontmatter_fields` and `test_reindex_idempotent` will break after reindex fix and must be updated
- [x] `tests/test_subagent.py` — add `test_subagent_documents_all_commands` (failing stub)

*Existing test infrastructure covers all phase requirements — no new framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `~/.claude/CLAUDE.md` contains "## Second Brain" proactive capture block | CAP-09 | File lives outside repo on host filesystem; cannot be reliably asserted in CI without host path assumptions | Open `~/.claude/CLAUDE.md`, verify "## Second Brain" section present with proactive offer phrasing and content-type guidance |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
