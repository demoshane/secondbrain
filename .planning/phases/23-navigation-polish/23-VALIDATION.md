---
phase: 23
slug: navigation-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, configured via pyproject.toml) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_api_tags.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_api_tags.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 0 | GNAV-02/03 | unit | `uv run pytest tests/test_api_tags.py -x -q` | ❌ W0 | ⬜ pending |
| 23-02-01 | 02 | 1 | GNAV-02 | unit | `uv run pytest tests/test_api_tags.py::TestTagsOnlySave -x -q` | ❌ W0 | ⬜ pending |
| 23-02-02 | 02 | 1 | GNAV-02 | unit | `uv run pytest tests/test_api_tags.py::TestListNotesTags -x -q` | ❌ W0 | ⬜ pending |
| 23-02-03 | 02 | 1 | GNAV-03 | unit | `uv run pytest tests/test_api_tags.py::TestTagSearch -x -q` | ❌ W0 | ⬜ pending |
| 23-03-01 | 03 | 2 | GNAV-01 | manual | — | — | ⬜ pending |
| 23-03-02 | 03 | 2 | GNAV-01 | manual | — | — | ⬜ pending |
| 23-04-01 | 04 | 2 | GNAV-02 | manual | — | — | ⬜ pending |
| 23-05-01 | 05 | 2 | GNAV-03 | manual | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_api_tags.py` — stubs for GNAV-02 (tags-only save), GNAV-03 (tag search filter), GET /notes tags array parsing
- [ ] No framework changes needed; `tests/conftest.py` fixtures (`client`, `tmp_path`, `monkeypatch`) already sufficient

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sidebar renders folder/type hierarchy with collapse/expand | GNAV-01 | Pure JS UI, no backend | Open GUI, check sidebar sections exist and toggle persists via localStorage |
| Tag chip click → inline edit → save updates frontmatter and DB | GNAV-02 | UI interaction flow | Click tag chip, edit inline, save; verify note frontmatter updated and no full reindex triggered |
| Tag filter in sidebar/search shows only matching notes | GNAV-03 | UI interaction flow | Click tag chip to filter; verify sidebar/results reflect tag filter correctly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
