---
phase: 39-codebase-review
plan: "03"
subsystem: performance-audit
tags: [audit, performance, wave-1, n+1, indexes, scale]
dependency_graph:
  requires: []
  provides: [39-findings-performance.md]
  affects: [39-triage]
tech_stack:
  added: []
  patterns: [performance-audit, scale-analysis, index-coverage-review]
key_files:
  created:
    - .planning/phases/39-codebase-review/39-findings-performance.md
  modified: []
decisions:
  - "PERF-01 backlink detection should use relationships table not LIKE scan"
  - "PERF-07 duplicate detection is O(n^2) — must replace with ANN-based approach from consolidate.py"
  - "PERF-08 recap_entity bypasses Phase 32 junction tables — oversight, not design decision"
  - "PERF-12 recap_main latent bug: queries closed connection when git context matches"
  - "notes(archived) and action_items(note_path) are the highest-priority missing indexes"
metrics:
  duration_seconds: 420
  completed_date: "2026-03-27"
  tasks_completed: 1
  files_created: 1
  files_modified: 0
---

# Phase 39 Plan 03: Performance Audit Summary

**One-liner:** Full performance audit producing 12 severity-ranked findings covering N+1 query patterns, missing DB indexes, O(n^2) duplicate detection, ANN cold-start cost, and scale-breaking operations at 100K notes.

## What Was Done

Systematically audited all performance-sensitive code paths across engine/api.py, engine/search.py, engine/ann_index.py, engine/intelligence.py, engine/brain_health.py, engine/reindex.py, engine/consolidate.py, engine/db.py, engine/health.py, and engine/digest.py.

## Findings Summary

| ID | Severity | Description |
|----|----------|-------------|
| PERF-01 | High | note_meta backlink scan uses LIKE on body — O(n) full table scan; should use relationships table |
| PERF-02 | High | Search tag post-filter issues one DB query per result — N+1 at scale |
| PERF-03 | High | reindex_brain walks filesystem twice (double rglob) |
| PERF-04 | Medium | get_missing_file_notes LIMIT 500 silently caps orphan detection at 100K notes |
| PERF-05 | Medium | ANN cold-start: index rebuilt from DB on first request after restart (10-30s at 100K) |
| PERF-06 | Medium | excerpt enrichment issues one DB query per search result — N+1 pattern |
| PERF-07 | Medium | get_duplicate_candidates is O(n^2) KNN scan — infeasible at 100K notes |
| PERF-08 | Medium | recap_entity uses LIKE on JSON people/tags columns — bypasses Phase 32 junction table indexes |
| PERF-09 | Low | list_people fetches all records then paginates in Python |
| PERF-10 | Low | get_stale_notes fetches 3x limit then filters in Python with disk reads |
| PERF-11 | Low | startup() uses glob.glob for disk count — slow at 100K files |
| PERF-12 | Low | recap_main queries closed connection (latent bug, Rule 1) |

## Pre-Identified P-01..P-04 Disposition

- **P-01** (N+1 on note_meta): Confirmed. Expanded to two findings — PERF-01 (LIKE body scan) and PERF-02 (per-result tag queries).
- **P-02** (rglob in capture): Confirmed in reindex_brain (double walk) → PERF-03. The smart-capture endpoint also calls rglob but that is a separate path not audited in this plan.
- **P-03** (FTS5 rebuild outside transaction): Verified correct. Both merge_notes and smart_merge_notes in brain_health.py rebuild FTS5 after the `with conn:` block exits. No finding needed.
- **P-04** (ANN fallback cost): Confirmed cold-start issue → PERF-05. Fallback to sqlite-vec is O(n) and infeasible at 100K scale.

## Missing Index Summary

Highest priority gaps not yet in init_schema:
- `notes(archived)` — used in WHERE archived=0 on every list query; unindexed means full scan
- `action_items(note_path)` — used in per-note action count subqueries in list_meetings/list_projects

Lower priority:
- `notes(created_at)` — ORDER BY without index (LIMIT keeps it manageable)
- `notes(updated_at)` — stale note detection ORDER BY

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] 39-findings-performance.md exists at correct path
- [x] 12 PERF-findings documented with severity, scale impact, and recommended fix
- [x] All pre-identified P-01..P-04 items addressed
- [x] Each finding includes scale impact estimate (note count threshold)
- [x] N+1 patterns identified with caller context
- [x] Commit 71cff3c exists
