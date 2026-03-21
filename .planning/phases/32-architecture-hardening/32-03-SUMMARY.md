---
phase: 32-architecture-hardening
plan: "03"
title: "Tags + people junction tables"
status: complete
started: 2026-03-22
completed: 2026-03-22
---

# Plan 32-03: Tags + People Junction Tables — Summary

## What was built

- `note_tags(note_path, tag)` junction table with index on both columns (ARCH-05)
- `note_people(note_path, person)` junction table with index on both columns (ARCH-15)
- Dropped useless `idx_notes_people` B-tree index on JSON text column (ARCH-15)
- Migration: converts existing JSON tags/people into junction table rows
- Dual-write: capture_note() and update_note() write to both junction tables AND JSON columns
- Read queries in api.py switched from json_each to indexed JOIN on note_tags
- All registered in init_schema() after path migration (locked order)

## Key files

### Modified
- `engine/db.py` — junction table DDL, migration, drop old index
- `engine/capture.py` — dual-write to note_tags + note_people
- `engine/api.py` — tag filter queries use JOIN note_tags
- `tests/test_db.py` — junction table and migration tests
- `tests/test_capture.py` — dual-write verification tests

## Commits
- `404a9e0` feat(32-03): junction table DDL + data migration
- `6f7552b` feat(32-03): dual-write junction tables + read queries via indexed joins

## Self-Check: PASSED
- [x] Junction tables created with indexes
- [x] Migration populates from existing JSON
- [x] Dual-write on capture and update
- [x] Read queries use junction table
- [x] JSON columns kept for backward compat
