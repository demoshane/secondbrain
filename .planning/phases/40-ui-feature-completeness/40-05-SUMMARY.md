---
phase: 40-ui-feature-completeness
plan: 05
status: complete
completed: 2026-03-28
---

# Plan 40-05 Summary — Grouped Actions Endpoint

## What was done

Added `GET /actions/grouped` endpoint to `engine/api.py` that returns action items grouped by source note. Also fixed a pre-existing regression in `TestNoteMeta` (introduced by plan 39's backlinks refactor from body LIKE scan to relationships table — the `tmp_note_pair` fixture was not seeding the relationships table).

## Changes

- **engine/api.py**: Added `get_actions_grouped()` endpoint after existing `/actions` route. Batches title lookup in one SQL IN query; groups actions by note_path using defaultdict; sorts alphabetically by note_title.
- **tests/test_api.py**: Added 4 tests — `test_actions_grouped_empty`, `test_actions_grouped_shape`, `test_actions_grouped_filter_done`, `test_actions_grouped_filter_assignee`. Fixed `tmp_note_pair` fixture to seed `relationships` rows for note_b and note_lower → note_a (backlinks), restoring `TestNoteMeta` tests that regressed in plan 39.

## Verification

- `uv run pytest tests/test_api.py -k grouped` — 4/4 green
- `uv run pytest tests/test_api.py` — all green (no regressions)

## Decisions

- No pagination on grouped endpoint — it's an aggregate view; total reflects all matching actions
- `list_actions` called unchanged (backward compatible)
- Groups sorted alphabetically by note_title for deterministic output
- `from collections import defaultdict` kept as lazy import inside function (consistent with other lazy imports in api.py)
