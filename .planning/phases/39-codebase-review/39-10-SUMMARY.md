---
phase: 39
plan: 10
subsystem: performance
tags: [performance, queries, junction-tables, gap-closure]
dependency_graph:
  requires: [39-08]
  provides: [recap-entity-optimized, backlinks-optimized, tag-filter-batched, orphan-cap]
  affects: [engine/intelligence.py, engine/api.py, engine/brain_health.py]
key_files:
  modified:
    - engine/intelligence.py
    - engine/api.py
    - engine/brain_health.py
decisions:
  - F-03 recap_entity replaced with note_people JOIN (partial name LIKE) + note_tags JOIN (exact tag)
  - F-04 recap_main conn lifecycle was already correct in current code — no change needed
  - F-05 note_meta backlinks now use relationships table with rel_type='backlink'
  - F-15 get_missing_file_notes uses _ORPHAN_CHECK_CAP=10000 with logger.warning on truncation
  - F-16 both tag filter paths (tags-only and FTS post-filter) use batch IN-clause
metrics:
  duration: 10
  completed_date: "2026-03-28"
  tasks: 2
  files_modified: 3
---

# Phase 39 Plan 10: Performance Query Optimization Summary

Replace 5 inefficient query patterns with indexed/batched alternatives.

## What Was Built

- **F-03**: `recap_entity` LIKE scan on JSON columns → `note_people` JOIN + `note_tags` JOIN
- **F-04**: `recap_main` conn lifecycle already correct — no change needed
- **F-05**: `note_meta` backlinks body LIKE scan → `relationships` table lookup (`rel_type='backlink'`)
- **F-15**: `get_missing_file_notes` LIMIT 500 → configurable `_ORPHAN_CHECK_CAP=10000` with `logger.warning`
- **F-16**: N+1 tag filter in both search paths → batch `IN` clause with path→tags dict

## Self-Check: PASSED

- `grep "note_people" engine/intelligence.py` → match
- `grep "rel_type.*backlink" engine/api.py` → match
- `grep "LOWER(body) LIKE" engine/api.py` → 0 matches
- `grep "note_path IN" engine/api.py` → 2 matches (both filter paths)
- `grep "LIMIT 500" engine/brain_health.py` → 0 matches
- `grep "logger.warning" engine/brain_health.py` → match
- api_tags, brain_health, api_extensions tests pass
