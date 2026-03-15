---
phase: 4
slug: automation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-14
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `uv run --no-project --with pytest python -m pytest tests/test_watcher.py tests/test_hooks.py tests/test_links.py tests/test_rag.py -x -q` |
| **Full suite command** | `uv run --no-project --with pytest --with watchdog python -m pytest -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-00-01 | 00 | 0 | CAP-04,CAP-05,PEOPLE-01..05,WORK-01..04,SEARCH-03,SEARCH-04 | stub | `pytest tests/test_watcher.py tests/test_hooks.py tests/test_links.py tests/test_rag.py -q` | ✅ | ✅ green |
| 4-01-01 | 01 | 1 | CAP-04 | unit | `pytest tests/test_watcher.py -q` | ✅ | ✅ green |
| 4-01-02 | 01 | 1 | CAP-05 | unit | `pytest tests/test_hooks.py -q` | ✅ | ✅ green |
| 4-02-01 | 02 | 2 | PEOPLE-01,PEOPLE-02,PEOPLE-03 | unit | `pytest tests/test_links.py -q` | ✅ | ✅ green |
| 4-02-02 | 02 | 2 | PEOPLE-04,PEOPLE-05,WORK-01..04 | unit | `pytest tests/test_links.py tests/test_capture.py -q` | ✅ | ✅ green |
| 4-03-01 | 03 | 3 | SEARCH-03,SEARCH-04 | unit | `pytest tests/test_rag.py tests/test_search.py -q` | ✅ | ✅ green |
| 4-04-01 | 04 | 4 | all | integration | `pytest -q` | ✅ existing | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_watcher.py` — stubs for CAP-04 (file watcher, debounce)
- [x] `tests/test_hooks.py` — stubs for CAP-05 (git post-commit hook)
- [x] `tests/test_links.py` — stubs for PEOPLE-01..05 (backlinks, orphan check)
- [x] `tests/test_rag.py` — stubs for SEARCH-03, SEARCH-04 (RAG-lite retrieval)
- [x] `tests/conftest.py` — extend fixtures: tmp brain dir, mock git repo

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PDF drop triggers prompt within 10s | CAP-04 | Requires live FSEvents/inotify + terminal interaction | Drop a PDF into ~/SecondBrain/files/ while `sb-watch` is running; confirm prompt appears |
| Bulk 20-file drop ≤1 prompt/5s | CAP-04 | Timing-dependent; debounce can't be reliably mocked | Copy 20 files rapidly; confirm only one prompt per 5s window |
| git commit fires hook + brain entry | CAP-05 | Requires real git repo + claude CLI on PATH | Commit in a project dir; confirm AI summary offered and entry written |
| /sb-check-links reports zero orphans | PEOPLE-03 | Requires populated brain state | Create meeting with 2 people; run /sb-check-links |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (automated coverage confirmed; live-env manual items annotated manual-only — not blocking nyquist sign-off)
