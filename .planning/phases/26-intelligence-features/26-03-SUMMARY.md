---
phase: 26-intelligence-features
plan: "03"
subsystem: brain-health
tags: [health, analytics, api, cli]
dependency_graph:
  requires: [26-01]
  provides: [brain-health-api, brain-health-cli]
  affects: [engine/api.py, engine/health.py]
tech_stack:
  added: []
  patterns: [lazy-import-in-route, argparse-subcommand, tdd-xfail-promotion]
key_files:
  created:
    - engine/brain_health.py
  modified:
    - engine/api.py
    - engine/health.py
decisions:
  - "compute_health_score() uses penalty weights: 40% broken links, 30% orphans, 20% duplicates — reflects relative data quality impact"
  - "get_duplicate_candidates() returns [] silently on any exception — sqlite-vec absence is expected on systems without embeddings"
  - "GET /brain-health always returns 200 with score — slow is acceptable, this endpoint is only called on explicit user request"
  - "sb-health --brain prints score and issue counts; system health checks unchanged when --brain absent"
metrics:
  duration: "10 min"
  completed_date: "2026-03-17"
  tasks_completed: 2
  files_modified: 3
requirements:
  - ENGL-04
  - ENGL-05
---

# Phase 26 Plan 03: Brain Health Module Summary

**One-liner:** Brain content health module with orphan/broken/duplicate checks, 0-100 score formula, REST endpoint, and CLI flag using TDD xfail promotion.

## What Was Built

### engine/brain_health.py (new)

Three functions for brain data quality analysis:

- `get_orphan_notes(conn)` — LEFT JOIN notes/relationships, excludes `type IN ('digest','memory')`, returns `[{path, title}]`
- `get_duplicate_candidates(conn, threshold=0.92)` — calls `find_similar()` per path from `note_embeddings`, deduplicates pairs by sorted tuple key, returns `[]` on any exception (graceful sqlite-vec absence)
- `compute_health_score(total_notes, orphans, broken, duplicates)` — returns 100 for zero notes; penalty formula `(orphan*30 + broken*40 + dup*20) * 100`; clamps to `[0, 100]`; returns `int`

### engine/api.py (modified)

New `GET /brain-health` endpoint added after `POST /intelligence/recap`:

- Returns `{"score": int, "total_notes": int, "orphans": [...], "broken_links": [...], "duplicate_candidates": [...]}` (max 20 items each)
- Always returns 200; 500 only on unexpected exception
- Lazy-imports `engine.brain_health`, `engine.links`, `engine.paths` inside route handler

### engine/health.py (modified, previously untracked)

Extended `main()` with `argparse` `--brain` flag:

- `--brain` path calls `_run_brain_health()`: connects to real DB, runs all three checks, prints score and counts, exits 0
- No-flag path: existing system health checks unchanged
- `_run_brain_health()` catches and prints any exception to stderr, never raises

## Test Results

All 7 `tests/test_brain_health.py` stubs promoted from `xfail` → `xpassed`:

| Test | Status |
|------|--------|
| test_get_orphan_notes_returns_notes_with_no_inbound_links | XPASS |
| test_get_orphan_notes_excludes_digest_and_memory_types | XPASS |
| test_get_duplicate_candidates_returns_pairs_above_threshold | XPASS |
| test_compute_health_score_returns_100_for_clean_brain | XPASS |
| test_compute_health_score_reduces_for_orphans | XPASS |
| test_compute_health_score_zero_notes_returns_100 | XPASS |
| test_brain_health_api_returns_score_and_checks | XPASS |

Full suite (excluding pre-existing failures in test_intelligence, test_mcp, test_precommit): **268 passed, 1 skipped, 1 xfailed, 8 xpassed**.

## Commits

| Hash | Message |
|------|---------|
| `7c4342e` | feat(26-03): add engine/brain_health.py with orphan, duplicate, and score checks |
| `d692cbf` | feat(26-03): add GET /brain-health endpoint and --brain flag to sb-health |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] engine/brain_health.py exists and importable
- [x] GET /brain-health route in engine/api.py
- [x] --brain flag in engine/health.py
- [x] All 7 tests xpassed
- [x] Both commits verified in git log
