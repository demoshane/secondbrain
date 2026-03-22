---
plan: 33-04
phase: 33-performance-scale-hardening
status: complete
completed_at: 2026-03-22
---

## Summary

Entity-based filter params wired through `_apply_filters` in search.py, Flask POST /search, and MCP `sb_search`.

## What was built

**engine/search.py:**
- `_apply_filters(results, conn, person, tag, note_type, from_date, to_date)` — Python post-filter with AND logic across all 5 dimensions. Tag lookup via `note_tags` junction table. Person lookup via `json.loads` on `people` column. Type/date are dict field comparisons.

**engine/api.py:**
- POST /search extracts `person`, `tag`, `note_type`, `from_date`, `to_date` from request JSON
- `_apply_filters` called after `search_hybrid()` + existing `tags_filter` list logic
- Backwards compatible — `tags_filter` (list) still works alongside new single `tag` param

**engine/mcp_server.py:**
- `sb_search` gains 5 optional params: `person`, `tag`, `note_type`, `from_date`, `to_date`
- `_apply_filters` called after search results returned

## Test results

**86 passed, 6 xfailed, 1 xpassed** — zero failures

- `test_apply_filters_*` in test_search.py — all filter dimensions covered
- `test_search_filter_by_type` in test_api.py — Flask integration test
- `test_sb_search_filter_by_type` in test_mcp.py — MCP integration test

## Key decisions

- Python post-filter (not SQL filter) — consistent with existing `tags_filter` pattern; semgrep-safe; works for both FTS5 and semantic/hybrid results
- `note_type` filter applied in post-filter for consistency even though `search_notes()` has a native param (keeps code paths uniform)
- Multiple tag support deferred to Phase 34 (CONTEXT.md: OUT OF SCOPE)

## Requirements satisfied

- PERF-06: Entity filter params on sb_search and POST /search with AND logic
