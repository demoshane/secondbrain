---
phase: 20
slug: frontend-bug-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q --tb=short` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | GUIX-03 | unit | `uv run pytest tests/test_api.py::test_read_note_strips_frontmatter -x -q` | ❌ W0 | ⬜ pending |
| 20-01-02 | 01 | 1 | GUIX-03 | unit | `uv run pytest tests/test_api.py::test_read_note_body_only -x -q` | ❌ W0 | ⬜ pending |
| 20-01-03 | 01 | 1 | GUIX-04 | manual | — | — | ⬜ pending |
| 20-01-04 | 01 | 1 | GUIX-02 | unit | `uv run pytest tests/test_api.py::test_save_note_updates_sqlite -x -q` | ❌ W0 | ⬜ pending |
| 20-01-05 | 01 | 1 | GUIX-02 | unit | `uv run pytest tests/test_api.py::test_save_note_preserves_frontmatter -x -q` | ❌ W0 | ⬜ pending |
| 20-01-06 | 01 | 1 | GUIX-05 | unit | `uv run pytest tests/test_api.py::test_backlinks_title_match -x -q` | ❌ W0 | ⬜ pending |
| 20-01-07 | 01 | 1 | GUIX-05 | unit | `uv run pytest tests/test_api.py::test_backlinks_case_insensitive -x -q` | ❌ W0 | ⬜ pending |
| 20-01-08 | 01 | 1 | GUIX-05 | unit | `uv run pytest tests/test_api.py::test_backlinks_empty_returns_none -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_api.py` — stubs for GUIX-02, GUIX-03, GUIX-05 API-level tests
- [ ] `tests/conftest.py` — shared fixtures (Flask test client, temp brain directory, sample notes with frontmatter)

*Existing infrastructure: pytest already present in pyproject.toml. Wave 0 adds new test file only.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mouse wheel scrolls note content | GUIX-04 | CSS/pywebview scroll behavior not automatable | Open `sb-gui`, load a long note, attempt mouse wheel scroll in viewer panel |
| Sidebar title updates after edit+save | GUIX-02 | Requires live GUI interaction | Edit a note title in editor, Ctrl+S, verify sidebar item text changes without restart |
| No raw YAML visible in viewer | GUIX-03 | Visual rendering check | Open any note with frontmatter, verify no `---` or `type:` lines visible |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
