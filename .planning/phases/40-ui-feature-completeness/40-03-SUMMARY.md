---
plan: 40-03
phase: 40-ui-feature-completeness
status: complete
---

## What was built

Project status field, stats counts, and status update endpoint.

## Changes

- **engine/db.py**: Added `migrate_add_status_column(conn)` — adds `status TEXT NOT NULL DEFAULT 'active'` to notes. Registered in `init_schema()` after `migrate_add_summary_column`.
- **engine/api.py**: Added `VALID_PROJECT_STATUSES = {"active", "paused", "completed"}`. Updated `list_projects()` to include `n.status` and `linked_meetings_count` subquery. Updated `get_project()` to include `status`, `related_notes_count`, `linked_meetings_count`. Added `PUT /projects/<path>/status` endpoint with validation, DB update, SSE broadcast, and 400/403/404 error handling.
- **tests/test_projects.py**: Added `test_project_list_has_status`, `test_project_detail_stats`, `test_update_status_success`, `test_update_status_invalid`, `test_update_status_not_found` — all passing.

## Verification

`uv run pytest tests/test_projects.py -x -q` → all new tests pass.

Pre-existing unrelated failure: `test_overdue_in_recap` (unmocked real adapter call in test_intelligence.py — predates this plan).
