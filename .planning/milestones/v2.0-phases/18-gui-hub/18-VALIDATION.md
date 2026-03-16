---
phase: 18
slug: gui-hub
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `uv run pytest tests/ -x -q --ignore=tests/test_gui_smoke.py` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --ignore=tests/test_gui_smoke.py`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-00-01 | 00 | 0 | GUI-01 | unit | `uv run pytest tests/test_api_extensions.py -x -q` | ❌ W0 | ⬜ pending |
| 18-00-02 | 00 | 0 | GUI-02 | unit | `uv run pytest tests/test_api_extensions.py -x -q` | ❌ W0 | ⬜ pending |
| 18-00-03 | 00 | 0 | GUI-03 | unit | `uv run pytest tests/test_api_extensions.py -x -q` | ❌ W0 | ⬜ pending |
| 18-01-01 | 01 | 1 | GUI-01 | unit | `uv run pytest tests/test_api_extensions.py -x -q` | ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 1 | GUI-04 | unit | `uv run pytest tests/test_api_extensions.py::test_put_note -x -q` | ❌ W0 | ⬜ pending |
| 18-01-03 | 01 | 1 | GUI-05 | unit | `uv run pytest tests/test_api_extensions.py::test_post_note -x -q` | ❌ W0 | ⬜ pending |
| 18-01-04 | 01 | 1 | GUI-06 | unit | `uv run pytest tests/test_api_extensions.py::test_get_meta -x -q` | ❌ W0 | ⬜ pending |
| 18-01-05 | 01 | 1 | GUI-07 | unit | `uv run pytest tests/test_api_extensions.py::test_files -x -q` | ❌ W0 | ⬜ pending |
| 18-01-06 | 01 | 1 | GUI-08 | unit | `uv run pytest tests/test_api_extensions.py::test_action_done -x -q` | ❌ W0 | ⬜ pending |
| 18-01-07 | 01 | 1 | GUI-09 | unit | `uv run pytest tests/test_api_extensions.py::test_intelligence -x -q` | ❌ W0 | ⬜ pending |
| 18-02-01 | 02 | 1 | GUI-01 | manual | — | N/A | ⬜ pending |
| 18-02-02 | 02 | 1 | GUI-02 | manual | — | N/A | ⬜ pending |
| 18-02-03 | 02 | 1 | GUI-10 | manual | — | N/A | ⬜ pending |
| 18-03-01 | 03 | 2 | GUI-11 | manual | — | N/A | ⬜ pending |
| 18-03-02 | 03 | 2 | GUI-03 | manual | — | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_api_extensions.py` — stubs for GUI-01 through GUI-09 (new API endpoints)
- [ ] `tests/conftest.py` — add Flask test client fixture if not present
- [ ] Verify `pywebview` installable on Python 3.13 Intel Mac (`uv add pywebview` dry-run)
- [ ] Verify PyObjC wheel available for Python 3.13 Intel Mac

*GUI rendering tests (GUI-01..GUI-11 visual behavior) are manual-only — pywebview opens a real OS window and cannot be headlessly automated in standard CI.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Desktop window opens with sidebar | GUI-01 | Requires OS display / WKWebView | Run `sb-gui`; confirm window appears with folder sidebar |
| Sidebar lists notes by folder/type | GUI-01 | Visual rendering | Verify notes appear grouped in sidebar |
| Click note → renders in center panel | GUI-01 | UI interaction | Click any note; confirm Markdown renders |
| Keyword search updates center panel | GUI-02 | UI interaction | Type query; verify results update live |
| Semantic search returns relevant results | GUI-02 | Embedding-dependent | Type natural-language query; verify sensible results |
| Create note from GUI saves to disk | GUI-03 | File system + UI | Create note via GUI; confirm file in ~/SecondBrain |
| Right panel shows backlinks/metadata | GUI-04 | UI rendering | Open note with backlinks; confirm right panel |
| Action items panel marks items done | GUI-05 | State mutation + UI | Check off action item; confirm persisted |
| Intelligence panel shows recap/nudges | GUI-06 | AI layer integration | Verify recap and stale nudges appear |
| Browse binary files in GUI | GUI-07 | File browser UI | Navigate to binary subfolder; confirm listing |
| Move binary files between subfolders | GUI-07 | File mutation + UI | Drag or move file; confirm moved on disk |
| Open note in system default editor | GUI-08 | OS shell integration | Click "Open in editor"; confirm correct app opens |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
