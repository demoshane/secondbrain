---
phase: 20-frontend-bug-fixes
plan: "02"
subsystem: api
tags: [backlinks, sqlite, bug-fix, tdd]
dependency_graph:
  requires: []
  provides: [accurate-backlinks-query]
  affects: [engine/api.py, tests/test_api.py]
tech_stack:
  added: []
  patterns: [LOWER(body) LIKE LOWER(?), tdd-red-green]
key_files:
  created: []
  modified:
    - engine/api.py
    - tests/test_api.py
decisions:
  - "Use LOWER(body) LIKE LOWER(?) for case-insensitive body content search"
  - "Fetch title_row once at top of note_meta; reuse for both backlinks and related queries"
metrics:
  duration: 4 minutes
  completed: 2026-03-16
  tasks_completed: 2
  files_changed: 2
---

# Phase 20 Plan 02: Backlinks Query Fix Summary

**One-liner:** Fixed `note_meta` backlinks to search note body content with `LOWER(body) LIKE LOWER(title)` instead of filename path matching.

## What Was Built

Replaced the broken backlinks query in `engine/api.py::note_meta` that matched notes by filename path characters with a case-insensitive body content search. Added `TestNoteMeta` test class with 4 tests covering correct match, false-positive exclusion, empty result, and case-insensitive scenarios.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add TestNoteMeta test class (RED) | 9d6b322 | tests/test_api.py |
| 2 | Fix note_meta backlinks query (GREEN) | 92d07e6 | engine/api.py |

**Note:** The api.py fix was committed as part of `92d07e6 feat(20-01)` in the same session (pre-commit hook stash/unstash cycle caused the explicit fix(20-02) commit attempt to find nothing new to stage). The fix is present and verified in HEAD.

## Changes Made

### engine/api.py — note_meta function

**Before (buggy):**
```python
fname = p.name
rows = conn.execute(
    "SELECT path, title FROM notes WHERE path != ? AND path LIKE '%' || ? || '%'",
    (str(p), fname[:20]),
).fetchall()
backlinks = [dict(r) for r in rows]
title_row = conn.execute("SELECT title FROM notes WHERE path=?", (str(p),)).fetchone()
```

**After (fixed):**
```python
title_row = conn.execute(
    "SELECT title FROM notes WHERE path=?", (str(p),)
).fetchone()
if title_row and title_row["title"]:
    rows = conn.execute(
        "SELECT path, title FROM notes "
        "WHERE path != ? AND LOWER(body) LIKE LOWER(?)",
        (str(p), f"%{title_row['title']}%"),
    ).fetchall()
    backlinks = [dict(r) for r in rows]
else:
    backlinks = []
```

### tests/test_api.py — TestNoteMeta class

Added `tmp_note_pair` fixture (5 notes: correct match, false-positive, unique title, lowercase variant) and `TestNoteMeta` class with:
- `test_backlinks_content_match` — note_b body mentions "Alice Smith", must appear in backlinks
- `test_backlinks_no_false_positive` — note_c filename has "alice" but body doesn't mention title, must NOT appear
- `test_backlinks_empty_when_no_mentions` — unique title with no mentions returns empty list
- `test_backlinks_case_insensitive` — lowercase body mention still matches

## Verification

```
python -m pytest tests/test_api.py -x -q
18 passed in <1s
```

## Deviations from Plan

### Pre-existing fix in 92d07e6

**Found during:** Task 2 commit
**Issue:** The `note_meta` body search fix was already committed in `92d07e6 feat(20-01)` from the same session. When attempting the explicit `fix(20-02)` commit, the pre-commit hook stash/unstash cycle left nothing staged.
**Impact:** None — the fix is in HEAD and all tests pass GREEN. The fix commit simply has a different message (feat(20-01)) than expected.

## Decisions Made

- `LOWER(body) LIKE LOWER(?)` chosen for case-insensitive SQLite search without requiring FTS (simpler, no index needed for this query pattern)
- `title_row` fetched once at top of function to avoid duplicate DB round-trip

## Self-Check: PASSED

- engine/api.py: FOUND
- tests/test_api.py: FOUND
- 20-02-SUMMARY.md: FOUND
- commit 9d6b322 (RED tests): FOUND
- commit 92d07e6 (GREEN fix): FOUND
