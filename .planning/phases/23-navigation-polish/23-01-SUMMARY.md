---
phase: 23-navigation-polish
plan: "01"
subsystem: api
tags: [tdd, tags, api, search, backend]
dependency_graph:
  requires: []
  provides: [tags-only-save, tag-search-filter, tags-list-parsing]
  affects: [engine/api.py, tests/test_api_tags.py]
tech_stack:
  added: []
  patterns: [tags-only-put-branch, fts5-empty-query-fallback, python-side-and-filter]
key_files:
  created:
    - tests/test_api_tags.py
  modified:
    - engine/api.py
decisions:
  - "Tags-only PUT reads frontmatter with python-frontmatter, mutates metadata['tags'], writes back via tempfile+os.replace — consistent with existing save_note pattern"
  - "Empty query + tags_filter in POST /search bypasses FTS5 (which rejects empty queries) and does a direct SELECT with Python-side AND filter"
  - "GET /notes now selects tags column and json.loads it before jsonify — no breaking change to callers since they were getting None before"
metrics:
  duration: 6 min
  completed: 2026-03-16
  tasks_completed: 2
  files_modified: 2
---

# Phase 23 Plan 01: Tags API Extensions Summary

**One-liner:** Tags-only PUT endpoint, tag-filtered POST /search (AND logic), and tags parsed as list on GET /notes — all driven by TDD with 8 passing tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Test scaffold (RED) | c994c22 | tests/test_api_tags.py (+241 lines) |
| 2 | Backend extension (GREEN) | 04d459a | engine/api.py (+62/-3) |

## What Was Built

### GET /notes — tags parsed as list
`list_notes()` now selects the `tags` column and runs `json.loads()` on each row before jsonify. Previously the column was not selected at all, so `tags` was absent from the response.

### PUT /notes/<path> — tags-only branch
New branch inserted before the existing content-save path in `save_note()`:
- Triggers when `"tags"` key is present and `"content"` key is absent
- Reads file with `_fm.loads`, sets `post.metadata["tags"] = tags_val`, writes back with `_fm.dumps` via tempfile+os.replace
- Calls `suppress_next_delete()` before `os.replace()` to prevent false SSE delete event
- Issues targeted `UPDATE notes SET tags=?, updated_at=? WHERE path=?` — no full reindex

### POST /search — tags AND filter
Two code paths added after existing `search_notes()` call:
1. **Empty query + tags**: direct `SELECT` all notes from DB, Python-side `all(t in note_tags for t in tags_filter)` filter. Needed because FTS5 rejects empty-string queries.
2. **Non-empty query + tags**: use FTS5 results then post-filter each result with a per-row DB lookup for tags column.

## Test Coverage

All 8 tests in `tests/test_api_tags.py` pass:
- `TestListNotesTags`: tags returned as list, all notes have list tags
- `TestTagsOnlySave`: file frontmatter updated, DB updated, body unchanged
- `TestTagSearch`: filter returns matching only, AND logic excludes non-matching, no-param is backward compat

Full suite: 259 passed, 1 skipped, 1 xfailed (pre-existing failures unrelated to this plan).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] FTS5 rejects empty-string query in tags-only search**
- **Found during:** Task 2 (GREEN phase, first test run)
- **Issue:** `search_notes(conn, "")` triggers FTS5 with an empty match string, returning no results. The tag filter then has nothing to filter, so `test_filter_returns_matching` failed with empty results.
- **Fix:** Added a separate code path in `search()`: when `tags_filter` is set and `query` is empty, skip FTS5 entirely and query all notes directly from DB with Python-side AND tag filter.
- **Files modified:** engine/api.py
- **Commit:** 04d459a

## Self-Check

### Files created/modified
- [x] tests/test_api_tags.py — exists
- [x] engine/api.py — modified (62 lines added)

### Commits
- [x] c994c22 — test(23-01): add failing tests for tags API extensions
- [x] 04d459a — feat(23-01): extend api.py with tags-only save, tag search filter, tags parsing

## Self-Check: PASSED
