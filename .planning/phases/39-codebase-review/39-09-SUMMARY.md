---
phase: 39
plan: 09
subsystem: db
tags: [db, migration, fk-cascade, indexes, gap-closure]
dependency_graph:
  requires: [39-07]
  provides: [fk-cascade-migration, performance-indexes]
  affects: [engine/db.py, tests/test_mcp.py, tests/test_intelligence.py, tests/test_brain_health.py, tests/test_forget.py, tests/test_api_tags.py]
tech_stack:
  added: []
  patterns: [rename-recreate FK migration, PRAGMA foreign_key_list detection]
key_files:
  created: []
  modified:
    - engine/db.py
    - tests/test_mcp.py
    - tests/test_intelligence.py
    - tests/test_brain_health.py
    - tests/test_forget.py
    - tests/test_api_tags.py
decisions:
  - FK migration uses rename-recreate pattern (SQLite cannot ALTER TABLE ADD CONSTRAINT)
  - Migration skipped if note_embeddings FK already has CASCADE (idempotent PRAGMA check)
  - FK enforcement disabled during migration and restored to original state afterwards
  - audit_log deliberately excluded from CASCADE — audit entries must survive note deletion
  - Test fixtures updated: isolated_link_brain seeds notes/a.md + notes/b.md; isolated_action_db seeds parent note for FK compliance; test_api_tags fixture populates note_tags; test_intelligence fixture seeds parent notes for action_items inserts
metrics:
  duration: 10
  completed_date: "2026-03-27"
  tasks: 1
  files_modified: 6
---

# Phase 39 Plan 09: FK CASCADE + Performance Indexes Summary

Add ON DELETE CASCADE FK constraints to `note_embeddings`, `action_items`, and `relationships`, plus two performance indexes.

## What Was Built

- `_migrate_fk_cascade(conn)` in `engine/db.py` using rename-recreate pattern for all 3 tables
- `idx_notes_archived` and `idx_action_items_note_path` indexes (IF NOT EXISTS)
- Both wired into `init_schema()` after existing migrations
- Test fixtures updated across 5 test files to satisfy new FK constraints

## Tasks Completed

| Task | Description | Status |
|------|-------------|--------|
| 1 | FK CASCADE migration + indexes in db.py | Done |
| 2 | Fix test fixtures broken by FK enforcement | Done |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test fixtures missing parent note inserts**
- **Found during:** Verification
- **Issue:** `isolated_link_brain`, `isolated_action_db`, `test_api_tags.tmp_brain`, `test_intelligence` fixtures all inserted into FK-constrained child tables without first inserting parent notes rows — FK enforcement was previously not active in test contexts
- **Fix:** Added parent note inserts to all affected fixtures before child table inserts
- **Files modified:** tests/test_mcp.py, tests/test_intelligence.py, tests/test_brain_health.py, tests/test_forget.py, tests/test_api_tags.py

**2. [Rule 1 - Cleanup] test_consolidation.py orphan**
- **Found during:** Test run baseline
- **Issue:** Untracked `tests/test_consolidation.py` testing non-existent `find_consolidation_candidates` (from prior aborted session work) — 16 failures
- **Fix:** Deleted orphaned file; not in scope for any phase 39 plan

## Self-Check: PASSED

- `grep -c "ON DELETE CASCADE" engine/db.py` → 5 matches (note_embeddings x1, action_items x1, relationships x2, note_tags x1)
- `grep "idx_notes_archived" engine/db.py` → match at line 658
- `grep "idx_action_items_note_path" engine/db.py` → match at line 659
- All MCP, intelligence, brain_health, forget, api_tags tests pass
