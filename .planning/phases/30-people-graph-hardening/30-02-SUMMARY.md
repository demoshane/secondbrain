---
phase: 30-people-graph-hardening
plan: "02"
subsystem: engine/api, engine/reindex
tags: [people-graph, entity-extraction, reindex, api]
dependency_graph:
  requires: [30-01]
  provides: [PEO-02-complete, clean-note-meta, entities-reindex-flag]
  affects: [engine/api.py, engine/reindex.py]
tech_stack:
  added: []
  patterns: [TDD red-green, body-scan removal, entities bulk rewrite]
key_files:
  modified:
    - engine/api.py
    - engine/reindex.py
    - tests/test_api.py
    - tests/test_reindex.py
decisions:
  - "Body-mention fallback removed entirely from note_meta() — people column is now the single source of truth"
  - "entities reindex pass uses disk_paths set (already built) to avoid a second rglob walk"
  - "Errors in entity re-extraction are collected into the existing errors list (non-fatal)"
metrics:
  duration: 8 min
  completed_date: "2026-03-20"
  tasks_completed: 2
  files_changed: 4
---

# Phase 30 Plan 02: Remove Body-Mention Fallback + --entities Reindex Flag Summary

People column is now the single source of truth for who appears in a note. Body-mention scanning is removed from `note_meta()` and `sb-reindex --entities` provides a one-shot migration path to populate people columns for all historical notes.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Remove body-mention fallback from note_meta() + regression tests | 0c973c6 |
| 2 | Add --entities flag to sb-reindex for bulk people column re-extraction | c938e6d |

## What Was Built

**Task 1 — Body-mention fallback removal (engine/api.py):**
- Deleted the entire `if note_body:` block (lines 729-740) that scanned all person notes and checked if their title appeared in the body of the queried note
- People list in `/notes/<path>/meta` now comes exclusively from the `people` DB column, resolved to `{path, title}` objects
- Added two regression tests:
  - `test_note_meta_no_body_fallback`: body mentions "John Doe" but people column is `[]` — asserts person does NOT appear
  - `test_note_meta_people_from_column`: people column contains a person path — asserts correct `{path, title}` resolution

**Task 2 — --entities flag (engine/reindex.py):**
- Added `entities: bool = False` parameter to `reindex_brain()`
- When `entities=True`: iterates all `disk_paths`, loads each note with python-frontmatter, calls `extract_entities(title, body)`, and overwrites `people` and `entities` columns (replace, not merge)
- Added `--entities` CLI argument to argparse; wires through to `reindex_brain()`
- Added two TDD tests:
  - `test_entities_flag_populates_people_column`: empty people column gets populated from body content
  - `test_entities_flag_overwrites_people_column`: stale "OldEntry" is replaced by fresh extraction

## Deviations from Plan

None — plan executed exactly as written.

## Verification

```
uv run pytest tests/test_api.py tests/test_reindex.py -v
# 34 passed, 4 xfailed, 1 xpassed
```

Success criteria confirmed:
- `grep "body_lower" engine/api.py` returns nothing
- People in `/notes/<path>/meta` come exclusively from people column
- `sb-reindex --entities` re-extracts and overwrites people column for all notes
- `--entities` flag is idempotent (running twice produces same result — pure overwrite)
- Full test suite green

## Self-Check: PASSED

Files confirmed present:
- `engine/api.py` — body-mention block removed
- `engine/reindex.py` — entities flag added
- `tests/test_api.py` — 2 new regression tests
- `tests/test_reindex.py` — 2 new TDD tests

Commits confirmed:
- `0c973c6` — feat(30-02): remove body-mention fallback from note_meta()
- `c938e6d` — feat(30-02): add --entities flag to sb-reindex for bulk people column re-extraction
