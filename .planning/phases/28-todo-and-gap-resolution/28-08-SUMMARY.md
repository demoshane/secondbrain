---
phase: 28-todo-and-gap-resolution
plan: "08"
subsystem: intelligence
tags: [recap, overdue-actions, tdd]
dependency_graph:
  requires: []
  provides: [overdue-in-recap]
  affects: [engine/intelligence.py, tests/test_intelligence.py]
tech_stack:
  added: []
  patterns: [prepend-section-to-recap]
key_files:
  created: []
  modified:
    - engine/intelligence.py
    - tests/test_intelligence.py
decisions:
  - "[28-08] generate_recap_on_demand calls get_overdue_actions(conn) at the top of the try block before the notes query; overdue_section is empty string when no overdue items exist so no empty heading is emitted"
  - "[28-08] overdue_section is prepended to both the early-return (no recent notes) path and the final return path so overdue items always surface regardless of recent activity"
metrics:
  duration: "6 min"
  completed_date: "2026-03-19"
  tasks_completed: 2
  files_modified: 2
---

# Phase 28 Plan 08: Wire Overdue Actions into Recap Summary

**One-liner:** `generate_recap_on_demand()` now prepends a `## Overdue Actions` section by calling `get_overdue_actions(conn)` at the top of its try block, surfacing due items even when no recent notes exist.

## Objective

The only remaining Phase 28 gap: overdue action items were queryable via `get_overdue_actions()` but never shown in recap output. This plan wires the call site and fixes the test to assert integration rather than helper isolation.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Wire get_overdue_actions into generate_recap_on_demand + fix tests (TDD) | 4b3925e | engine/intelligence.py, tests/test_intelligence.py |
| 2 | Full unit suite green (verification) | — | — |

## Changes Made

### engine/intelligence.py

At the top of `generate_recap_on_demand()`'s try block, added:

```python
overdue = get_overdue_actions(conn)
overdue_section = ""
if overdue:
    lines = ["## Overdue Actions"]
    for item in overdue:
        due = item["due_date"]
        lines.append(f"- {item['text']} (due {due})")
    overdue_section = "\n".join(lines) + "\n\n"
```

Both the early return (no recent notes) and final return now prepend `overdue_section`.

### tests/test_intelligence.py

- `test_overdue_in_recap`: Changed from calling `get_overdue_actions()` directly to calling `generate_recap_on_demand(conn)` and asserting `"## Overdue Actions" in recap` and `"Overdue task" in recap`.
- `test_overdue_not_in_recap_when_none`: New test — seeds only a future-due item and asserts `"## Overdue Actions"` is absent from the recap.

## Verification

```
uv run pytest tests/ --ignore=tests/test_gui.py
388 passed, 1 skipped, 8 xfailed, 36 xpassed in 78.29s
```

Exit code 0. No regressions.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- engine/intelligence.py: modified (get_overdue_actions call wired in)
- tests/test_intelligence.py: modified (test_overdue_in_recap updated + test_overdue_not_in_recap_when_none added)
- Commit 4b3925e: verified present
- Full suite: 388 passed, 0 failed
