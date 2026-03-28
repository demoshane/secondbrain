---
phase: 40
slug: ui-feature-completeness
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-28
completed: 2026-03-28
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
| 40-01-01 | 01 | 1 | person_insights table created on init | unit | `uv run pytest tests/test_db.py -x -q -k insight` | ✅ | ✅ green |
| 40-01-02 | 01 | 1 | GET /persons/<path>/insight returns cached insight if <24h | unit | `uv run pytest tests/test_people.py -x -q -k insight_cache` | ✅ | ✅ green |
| 40-01-03 | 01 | 1 | GET /persons/<path>/insight regenerates when cache stale | unit | `uv run pytest tests/test_people.py -x -q -k insight_regen` | ✅ | ✅ green |
| 40-02-01 | 02 | 1 | GET /intelligence/synthesis returns string | unit | `uv run pytest tests/test_intelligence.py -x -q -k synthesis` | ✅ | ✅ green |
| 40-03-01 | 03 | 1 | status column added to notes table | unit | `uv run pytest tests/test_db.py -x -q -k status` | ✅ | ✅ green |
| 40-03-02 | 03 | 1 | GET /projects includes status per row | unit | `uv run pytest tests/test_projects.py -x -q -k status` | ✅ | ✅ green |
| 40-03-03 | 03 | 1 | GET /projects/<path> includes status + related_notes_count + linked_meetings_count | unit | `uv run pytest tests/test_projects.py -x -q -k project_detail_stats` | ✅ | ✅ green |
| 40-03-04 | 03 | 1 | PUT /projects/<path>/status 200 + SSE broadcast | unit | `uv run pytest tests/test_projects.py -x -q -k update_status` | ✅ | ✅ green |
| 40-03-05 | 03 | 1 | PUT /projects/<path>/status invalid value → 400 | unit | `uv run pytest tests/test_projects.py -x -q -k status_invalid` | ✅ | ✅ green |
| 40-04-01 | 04 | 1 | GET /projects/<path> includes linked_meetings list | unit | `uv run pytest tests/test_projects.py -x -q -k linked_meetings` | ✅ | ✅ green |
| 40-04-02 | 04 | 1 | GET /meetings/<path> participants are [{name, path}] objects | unit | `uv run pytest tests/test_meetings.py -x -q -k participant_objects` | ✅ | ✅ green |
| 40-05-01 | 05 | 1 | GET /actions/grouped returns {groups, total} shape | unit | `uv run pytest tests/test_api.py -x -q -k grouped` | ✅ | ✅ green |
| 40-05-02 | 05 | 1 | GET /actions/grouped done/assignee filters work | unit | `uv run pytest tests/test_api.py -x -q -k grouped_filter` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_projects.py` — test stubs for status field, stats counts, linked_meetings, PUT status endpoint
- [x] `tests/test_meetings.py` — test stub for participant objects shape
- [x] `tests/test_api.py` — test stubs for grouped actions endpoint
- [x] `tests/test_intelligence.py` — test stub for synthesis endpoint
- [x] `tests/test_db.py` — stubs for person_insights table + status column migrations

---

## Known Pre-existing Failures (not phase 40)

These 4 failures exist in the baseline before phase 40 and are unrelated to this phase's work:

- `test_delete.py::test_delete_endpoint_404` — Flask returns 308 instead of 404 (routing regression from earlier phase)
- `test_smart_capture.py::test_bidirectional_relationships` — co-captured relationship logic broken
- `test_smart_capture.py::TestSimilarRelationshipAutoLink::test_similar_relationship_inserted_on_confirm` — similar link insertion broken
- `test_smart_capture.py::test_smart_capture_golden_path` — golden path assertion failure

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-03-28 — all 5 plans complete, 13/13 tasks green, 4 pre-existing failures documented
