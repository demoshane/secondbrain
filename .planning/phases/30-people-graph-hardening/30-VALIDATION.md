---
phase: 30
slug: people-graph-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` [tool.pytest] |
| **Quick run command** | `uv run pytest tests/test_entities.py tests/test_people.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_entities.py tests/test_people.py tests/test_mcp.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 30-01-01 | 01 | 1 | PEO-01 | unit | `uv run pytest tests/test_entities.py -x -q` | ✅ extend | ⬜ pending |
| 30-01-02 | 01 | 1 | PEO-01 | unit | `uv run pytest tests/test_entities.py::test_extract_compound_names -x` | ❌ W0 | ⬜ pending |
| 30-01-03 | 01 | 1 | PEO-01 | unit | `uv run pytest tests/test_entities.py::test_finnish_stopwords -x` | ❌ W0 | ⬜ pending |
| 30-01-04 | 01 | 1 | PEO-01 | unit | `uv run pytest tests/test_entities.py::test_extract_orgs -x` | ❌ W0 | ⬜ pending |
| 30-01-05 | 01 | 1 | PEO-02 | unit | `uv run pytest tests/test_capture.py::test_capture_people_writeback -x` | ❌ W0 | ⬜ pending |
| 30-02-01 | 02 | 1 | PEO-02 | unit | `uv run pytest tests/test_reindex.py::test_entities_flag -x` | ❌ W0 | ⬜ pending |
| 30-02-02 | 02 | 1 | PEO-02 | unit | `uv run pytest tests/test_api.py::test_note_meta_no_body_fallback -x` | ❌ W0 | ⬜ pending |
| 30-03-01 | 03 | 2 | PEO-03 | unit | `uv run pytest tests/test_mcp.py::test_person_context_column_lookup -x` | ❌ W0 | ⬜ pending |
| 30-03-02 | 03 | 2 | PEO-03 | unit | `uv run pytest tests/test_mcp.py::test_person_context_by_name -x` | ❌ W0 | ⬜ pending |
| 30-03-03 | 03 | 2 | PEO-03 | unit | `uv run pytest tests/test_mcp.py::test_sb_list_people -x` | ❌ W0 | ⬜ pending |
| 30-04-01 | 04 | 3 | PEO-04 | unit | `uv run pytest tests/test_people.py::test_list_people_enriched -x` | ❌ W0 | ⬜ pending |
| 30-04-02 | 04 | 3 | PEO-04 | unit (vitest) | `cd /workspace/frontend && npx vitest run` | ❌ W0 | ⬜ pending |
| 30-04-03 | 04 | 3 | PEO-04 | unit | `uv run pytest tests/test_people.py::test_person_type_isolation -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_entities.py` — add Unicode/Finnish/org/compound name test cases (file exists, extend)
- [ ] `tests/test_capture.py` — add `test_capture_people_writeback` test
- [ ] `tests/test_reindex.py` — add `test_entities_flag` test (check if file exists first)
- [ ] `tests/test_mcp.py` — add `test_person_context_column_lookup`, `test_person_context_by_name`, `test_sb_list_people`
- [ ] `tests/test_people.py` — add enriched fields tests and type isolation regression

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| People page shows Finnish names correctly | PEO-04 | Visual rendering check | Open GUI → People page → verify Ä/Ö characters render |
| Person right panel shows meetings + actions | PEO-04 | Visual layout check | Click person → verify sections present |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
