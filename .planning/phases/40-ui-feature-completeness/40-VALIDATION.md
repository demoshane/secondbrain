---
phase: 40
slug: ui-feature-completeness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 40 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none (uv run pytest) |
| **Quick run command** | `uv run pytest tests/test_projects.py tests/test_meetings.py tests/test_api.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_projects.py tests/test_meetings.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Capability | Test Type | Automated Command | File Exists | Status |
|---------|------|------|------------|-----------|-------------------|-------------|--------|
| 40-01-01 | 01 | 1 | person_insights table created on init | unit | `uv run pytest tests/test_db.py -x -q -k insight` | ✅ | ⬜ pending |
| 40-01-02 | 01 | 1 | GET /persons/<path>/insight returns cached insight if <24h | unit | `uv run pytest tests/test_people.py -x -q -k insight_cache` | ✅ | ⬜ pending |
| 40-01-03 | 01 | 1 | GET /persons/<path>/insight regenerates when cache stale | unit | `uv run pytest tests/test_people.py -x -q -k insight_regen` | ✅ | ⬜ pending |
| 40-02-01 | 02 | 1 | GET /intelligence/synthesis returns string | unit | `uv run pytest tests/test_intelligence.py -x -q -k synthesis` | ✅ | ⬜ pending |
| 40-03-01 | 03 | 1 | status column added to notes table | unit | `uv run pytest tests/test_db.py -x -q -k status` | ✅ | ⬜ pending |
| 40-03-02 | 03 | 1 | GET /projects includes status per row | unit | `uv run pytest tests/test_projects.py -x -q -k status` | ✅ | ⬜ pending |
| 40-03-03 | 03 | 1 | GET /projects/<path> includes status + related_notes_count + linked_meetings_count | unit | `uv run pytest tests/test_projects.py -x -q -k project_detail_stats` | ✅ | ⬜ pending |
| 40-03-04 | 03 | 1 | PUT /projects/<path>/status 200 + SSE broadcast | unit | `uv run pytest tests/test_projects.py -x -q -k update_status` | ✅ | ⬜ pending |
| 40-03-05 | 03 | 1 | PUT /projects/<path>/status invalid value → 400 | unit | `uv run pytest tests/test_projects.py -x -q -k status_invalid` | ✅ | ⬜ pending |
| 40-04-01 | 04 | 1 | GET /projects/<path> includes linked_meetings list | unit | `uv run pytest tests/test_projects.py -x -q -k linked_meetings` | ✅ | ⬜ pending |
| 40-04-02 | 04 | 1 | GET /meetings/<path> participants are [{name, path}] objects | unit | `uv run pytest tests/test_meetings.py -x -q -k participant_objects` | ✅ | ⬜ pending |
| 40-05-01 | 05 | 1 | GET /actions/grouped returns {groups, total} shape | unit | `uv run pytest tests/test_api.py -x -q -k grouped` | ✅ | ⬜ pending |
| 40-05-02 | 05 | 1 | GET /actions/grouped done/assignee filters work | unit | `uv run pytest tests/test_api.py -x -q -k grouped_filter` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_projects.py` — add test stubs for: status field, stats counts, linked_meetings, PUT status endpoint (40-03-xx, 40-04-01)
- [ ] `tests/test_meetings.py` — add test stub for participant objects shape (40-04-02)
- [ ] `tests/test_api.py` — add test stubs for grouped actions endpoint (40-05-xx)
- [ ] `tests/test_intelligence.py` — add test stub for synthesis endpoint (40-02-01)
- [ ] `tests/test_db.py` — confirm/add stubs for person_insights table + status column migrations (40-01-01, 40-03-01)

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
