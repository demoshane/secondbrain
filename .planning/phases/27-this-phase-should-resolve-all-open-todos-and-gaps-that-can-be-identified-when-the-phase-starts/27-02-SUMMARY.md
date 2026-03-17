---
phase: 27-search-quality-tuning
plan: "02"
subsystem: search
tags: [search, bm25, ranking, recency, tdd]
dependency_graph:
  requires: [27-01]
  provides: [ENGL-02-implementation]
  affects: [engine/search.py]
tech_stack:
  added: []
  patterns: [BM25 column weighting, exponential recency decay, TDD red-green]
key_files:
  created:
    - tests/test_recency_multiplier.py
  modified:
    - engine/search.py
decisions:
  - "[27-02] BM25 column weights 10.0 (title) / 1.0 (body) — title match always beats body-only match"
  - "[27-02] Recency multiplier applied to BM25 leg only, not semantic leg — per RESEARCH.md resolution"
  - "[27-02] test_recall_mixed_content remains xfail — FTS5 phrase-quoted search finds 'Alice Bob' as phrase not independent tokens; acceptable given xfail(strict=False)"
metrics:
  duration: "4 min"
  completed: "2026-03-17"
  tasks: 2
  files: 2
---

# Phase 27 Plan 02: BM25 Column Weighting + Recency Multiplier Summary

BM25 column-weighted search (title 10.0, body 1.0) + exponential recency boost applied to `search_notes()`, promoting 9/10 regression tests from xfail to xpass.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add _recency_multiplier helper and apply in search_notes() | 77179ff | engine/search.py, tests/test_recency_multiplier.py |
| 2 | Apply BM25 column weights (10.0 title, 1.0 body) in search_notes() | 822879d | engine/search.py |

## What Was Built

**`_recency_multiplier(created_at_str, half_life_days=30) -> float`**

Exponential decay boost: new notes get ~1.1x, at 30 days ~1.05x, at 180+ days ~1.0x. Applied to every BM25 result score before returning from `search_notes()`. Exception-safe (returns 1.0 on any parse error).

**BM25 column weights in `search_notes()`**

Both SQL query variants (with and without `note_type` filter) updated to use `bm25(notes_fts, 10.0, 1.0)` in both SELECT and ORDER BY clauses. Title column weighted 10x vs body — satisfies ENGL-02 (title searches rank correctly).

## Verification Results

```
tests/test_search_regression.py: 9 xpassed, 1 xfailed (test_recall_mixed_content)
tests/test_search.py: 8 passed
tests/test_recency_multiplier.py: 7 passed
Total: 24 tests, all pass or acceptable xfail
```

**Precision tests (all 5 promoted to xpass):**
- `test_precision_person_full_name` — "Alice Johnson" ranks first
- `test_precision_partial_name` — "Alice Johnson" in top 3 for "Alice"
- `test_precision_meeting_title` — "Q3 Planning Session" ranks first
- `test_precision_partial_meeting` — "Q3 Planning Session" in top 3
- `test_precision_short_title` — "Python" ranks first

## Deviations from Plan

None — plan executed exactly as written. The 1 remaining xfail (`test_recall_mixed_content`) was anticipated: FTS5 phrase-quoted queries treat "Alice Bob" as an exact phrase, not independent tokens, so "Weekly Sync" (which contains both words separately) doesn't match. This is a known FTS5 characteristic, not a regression.

## Self-Check: PASSED

- engine/search.py exists and contains `_recency_multiplier`: confirmed
- engine/search.py contains `bm25(notes_fts, 10.0, 1.0)`: confirmed
- Commit 77179ff exists: confirmed
- Commit 822879d exists: confirmed
- All test assertions met
