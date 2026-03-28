---
plan: 40-04
phase: 40-ui-feature-completeness
status: complete
---

## What was built

Linked meetings on project detail and participant objects on meeting detail.

## Changes

- **engine/api.py**: Added `_resolve_participant(conn, name) -> dict` helper. Updated `get_project()` to add `linked_meetings` array (path, title, meeting_date). Updated `get_meeting()` to return participants as `[{name, path}]` objects instead of plain strings; path is null when no person note matches.
- **tests/test_projects.py**: Added `test_linked_meetings`, `test_linked_meetings_empty`.
- **tests/test_meetings.py**: Added `BRAIN_ROOT` monkeypatch to fixture. Added `test_participant_objects_with_person`, `test_participant_objects_no_person`.

## Verification

`uv run pytest tests/test_projects.py tests/test_meetings.py -x -q -k "linked_meetings or participant_objects"` → 4 passed (100%)
