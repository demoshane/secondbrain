---
phase: 33-performance-scale-hardening
verified: 2026-03-22T12:00:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 33: Performance & Scale Hardening Verification Report

**Phase Goal:** Keep system fast at thousands of notes — paginate all list endpoints, gate expensive O(n) operations, optimise reindex, cap LLM context
**Verified:** 2026-03-22
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Requirements Coverage

PERF-01 through PERF-07 are defined in ROADMAP.md against Phase 33. They are **not** listed in REQUIREMENTS.md (which tracks only v3.0 requirements). REQUIREMENTS.md has no PERF-* IDs for any phase — this is expected; the v4.0 milestone requirements live in ROADMAP.md only. No orphaned requirement IDs found.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PERF-01 | 33-01 | Pagination on all list endpoints + MCP page param | SATISFIED | api.py: all list endpoints return `{data, total, limit, offset}`; mcp_server.py: sb_search/sb_files/sb_actions return `{results, total, page, total_pages}` |
| PERF-02 | 33-02 | check_connections 30-min cooldown gate | SATISFIED | intelligence.py lines 18–19, 382–401: `_check_connections_last_run`, `_CHECK_CONNECTIONS_COOLDOWN_SECS = 30*60`, cooldown as first guard |
| PERF-03 | 33-02 | Incremental reindex via mtime comparison | SATISFIED | reindex.py lines 131–143: mtime-vs-updated_at skip loop with `skipped` counter; `--full` bypasses |
| PERF-04 | 33-03 | Config-driven recap window + --days CLI flag | SATISFIED | intelligence.py lines 530–625: `window_days` param, config lookup, `--days` argparse, `max_notes` hard cap |
| PERF-05 | 33-03 | Background embedding worker (embed_pass_async) | SATISFIED | reindex.py lines 78–92: `_embed_executor = ThreadPoolExecutor(max_workers=1)`, `embed_pass_async` returns Future |
| PERF-06 | 33-04 | Entity-based filter params on sb_search + POST /search | SATISFIED | search.py:241 `_apply_filters`; api.py:222 wired; mcp_server.py:159 wired |
| PERF-07 | 33-05 | sb_person_context query consolidation (4→3 roundtrips) | SATISFIED | mcp_server.py:1210–1251: COUNT+JOIN fast path replacing 2x json_each, fallback preserved |

---

## Observable Truths Verification

### PERF-01: Pagination

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /notes returns `{notes, total, limit, offset}` not a bare list | VERIFIED | api.py:157 `return jsonify({"notes": notes, "total": total, "limit": limit, "offset": offset})` |
| 2 | GET /actions returns `{actions, total, limit, offset}` | VERIFIED | api.py:500 same shape |
| 3 | GET /people, /meetings, /projects return paginated shape | VERIFIED | api.py:287, 321, 377 all return `{data_key, total, limit, offset}` |
| 4 | MCP sb_search, sb_files, sb_actions accept `page` and return `total_pages` | VERIFIED | mcp_server.py:172–174, 634–636, 678–680 all return `{..., total, page, total_pages}` with `math.ceil` |
| 5 | Omitting limit/offset returns first 50 (default bounded) | VERIFIED | api.py:140 `int(request.args.get("limit", 50))`; mcp_server.py:125 `limit: int = 10` |
| 6 | Max limit capped at 200 | VERIFIED | api.py:140 `min(..., 200)`; mcp_server.py:149 `min(limit, 200)` |

### PERF-02: Cooldown Gate

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | check_connections skips if called within 30 min of last run | VERIFIED | intelligence.py:385–387 `if (now - _check_connections_last_run) < _CHECK_CONNECTIONS_COOLDOWN_SECS: return` |
| 2 | check_connections runs normally if 30 min elapsed | VERIFIED | same logic — passes through when `_check_connections_last_run == 0.0` or cooldown expired |
| 3 | Cooldown check fires BEFORE budget_available | VERIFIED | intelligence.py:386 cooldown is first guard, budget_available at line 388 |

### PERF-03: Incremental Reindex

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Default (no flags) skips files where mtime <= DB updated_at | VERIFIED | reindex.py:131–143 UTC mtime vs fromisoformat(updated_at) comparison, `continue` on unchanged |
| 2 | `--full` processes all files regardless of mtime | VERIFIED | reindex.py:131 `if not full:` gate — full=True bypasses entirely |
| 3 | Orphan pruning still runs in incremental mode | VERIFIED | reindex.py:116–121 `disk_paths` collection loop is separate from the incremental skip loop |
| 4 | `skipped` count in return dict | VERIFIED | reindex.py:270 `"skipped": skipped` |

### PERF-04: Config-Driven Recap Window

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | generate_recap_on_demand respects window_days from config.toml | VERIFIED | intelligence.py:545–547 `window_days = recap_cfg.get("window_days", 7)` |
| 2 | `sb-recap --days N` overrides config for that call | VERIFIED | intelligence.py:609 `--days` argparse; 625 `generate_recap_on_demand(conn, window_days=args.days)` |
| 3 | Hard cap of 50 notes max | VERIFIED | intelligence.py:547 `max_notes = recap_cfg.get("max_notes", 50)`; passed as LIMIT to SQL query:567 |
| 4 | Body truncation at 500 chars | VERIFIED | intelligence.py:548 `body_trunc = recap_cfg.get("body_truncation", 500)`; used at line 575 `body[:body_trunc]` |

### PERF-05: Background Embedding Worker

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | embed_pass_async submits to background thread, returns Future | VERIFIED | reindex.py:78–91: `_embed_executor.submit(_run)` returns `concurrent.futures.Future` |
| 2 | embed_pass_async uses its own DB connection | VERIFIED | reindex.py:83–90: inner `_run()` calls `conn_factory()` and `conn.close()` |
| 3 | reindex_brain calls embed_pass_async (not embed_pass) | VERIFIED | reindex.py:261 `future = embed_pass_async(get_connection, ...)` |

### PERF-06: Entity Search Filters

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | sb_search accepts person, tag, type, from_date, to_date params | VERIFIED | mcp_server.py:127–131 all 5 params declared; 159–166 passed to `_apply_filters` |
| 2 | Multiple filters combine with AND logic | VERIFIED | search.py:267–295: all filters in sequence with `continue` on mismatch |
| 3 | person filter matches people column | VERIFIED | search.py:290–295: json.loads on people column, `any(person in p ...)` check |
| 4 | tag filter uses note_tags junction table | VERIFIED | search.py:278–285: `SELECT tag FROM note_tags WHERE note_path=?` |
| 5 | POST /search accepts same filter params | VERIFIED | api.py:24 `from engine.search import _apply_filters`; api.py:222 called after search |
| 6 | Filters work with empty query string (browse mode) | VERIFIED | search.py:267 `if not any([person, tag, note_type, from_date, to_date]): return results` (passthrough when no filters) |

### PERF-07: sb_person_context Query Consolidation

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Fast path uses note_people JOIN notes (single query for meetings+mentions) | VERIFIED | mcp_server.py:1215–1229: `SELECT DISTINCT n.path, n.title, n.type, n.created_at FROM note_people np JOIN notes n ...` |
| 2 | Python splits by type (not two separate queries) | VERIFIED | mcp_server.py:1228–1229 `meeting_rows = [r for r in all_note_rows if r["type"] == "meeting"]` |
| 3 | Fallback to json_each when note_people empty | VERIFIED | mcp_server.py:1230–1251: else branch preserves both json_each queries |
| 4 | Roundtrips reduced: COUNT + 1 JOIN + action items = 3 (was 4) | VERIFIED | COUNT at 1210, JOIN at 1217, assignee query at 1260 |

---

## Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `engine/api.py` | VERIFIED | Paginated Flask list endpoints; filter params on POST /search |
| `engine/mcp_server.py` | VERIFIED | Paginated MCP tools; sb_search filter params; sb_person_context fast path |
| `engine/intelligence.py` | VERIFIED | Cooldown gate; config-driven recap window; --days flag |
| `engine/reindex.py` | VERIFIED | Incremental mtime skip; embed_pass_async |
| `engine/search.py` | VERIFIED | `_apply_filters` with AND logic across 5 dimensions |
| `tests/test_api.py` | VERIFIED | Pagination tests; filter_by_type integration test |
| `tests/test_mcp.py` | VERIFIED | Pagination shape tests; filter_by_type; person_context fast path test |
| `tests/test_intelligence.py` | VERIFIED | Cooldown gate tests; window_days tests |
| `tests/test_reindex.py` | VERIFIED | Incremental skip tests; embed_pass_async Future test |
| `tests/test_search.py` | VERIFIED | _apply_filters unit tests for all 5 filter dimensions |

---

## Key Link Verification

| From | To | Via | Status |
|------|-----|-----|--------|
| GET /notes (api.py:list_notes) | COUNT(*) + LIMIT/OFFSET SELECT | request.args limit/offset | WIRED |
| MCP sb_files (mcp_server.py) | page → offset computation | `(page-1)*limit`, `math.ceil` | WIRED |
| check_connections (intelligence.py) | `_check_connections_last_run` module variable | `time.monotonic()` comparison | WIRED |
| reindex_brain loop (reindex.py) | mtime-vs-updated_at comparison | `Path.stat().st_mtime` + UTC conversion | WIRED |
| generate_recap_on_demand (intelligence.py) | config.toml [recap].window_days | `load_config(CONFIG_PATH)` | WIRED |
| recap_main (intelligence.py) | `--days` arg → window_days param | argparse + function call | WIRED |
| reindex_brain embed call (reindex.py) | embed_pass_async | ThreadPoolExecutor submit | WIRED |
| POST /search (api.py) | search_hybrid + _apply_filters | request.json filter fields | WIRED |
| sb_search (mcp_server.py) | _apply_filters in search.py | person/tag/note_type/from_date/to_date params | WIRED |
| sb_person_context (mcp_server.py) | note_people JOIN notes | COUNT gate + single JOIN query | WIRED |

---

## Test Results

Ran: `uv run pytest tests/test_api.py tests/test_mcp.py tests/test_search.py tests/test_intelligence.py tests/test_reindex.py`

**Result: 1 failed, 144 passed, 7 xfailed, 2 xpassed**

### Failing test

`tests/test_intelligence.py::TestConnectionSuggestion::test_check_connections_prints_suggestion`

**Status: PRE-EXISTING FAILURE — not introduced by Phase 33.**

This test asserts `check_connections` writes to stdout (`capsys.readouterr().out`). The implementation uses `logger.info` which writes to the log stream, not stdout. This mismatch predates Phase 33 and is documented in the 33-02 SUMMARY:

> `test_check_connections_prints_suggestion` was already failing before this plan (confirmed by stash-test). The test asserts on `captured.out` but `check_connections` uses `logger.info` — nothing goes to stdout.

This failure does not block any phase 33 goal. No phase 33 must-have depends on stdout output from `check_connections`.

---

## Anti-Pattern Scan

Scanned all modified files (engine/api.py, engine/mcp_server.py, engine/intelligence.py, engine/reindex.py, engine/search.py) for stubs and placeholders introduced by this phase.

| Pattern | Result |
|---------|--------|
| TODO/FIXME/PLACEHOLDER comments in new code | None found in phase 33 additions |
| Empty return `null / {} / []` in new functions | None — all new functions return substantive data |
| Console.log-only handlers | N/A (Python project) |
| Fetch without response handling | N/A |

Pre-existing semgrep warnings on unrelated lines (HTML construction, path traversal at lines 499, 653, 855 of api.py) noted in 33-01 SUMMARY — out of scope for this phase.

---

## Human Verification Required

### 1. Incremental reindex — second run skips all unchanged files

**Test:** Run `uv run sb-reindex` twice in sequence (no brain content changes between runs)
**Expected:** Second run prints `0 indexed, N skipped — unchanged`
**Why human:** Requires live brain data and launchd service interaction; can't mock filesystem mtime reliably in a unit test without writing actual files and waiting

### 2. check_connections cooldown — process restart clears cooldown

**Test:** Trigger check_connections (via capture), restart sb-api, trigger again
**Expected:** Second trigger runs the similarity scan (cooldown cleared on restart — module-level variable)
**Why human:** Requires process kill/restart cycle; noted in VALIDATION.md as manual-only

### 3. sb-recap --days 3 output scope

**Test:** Run `uv run sb-recap --days 3` with notes older than 3 days in brain
**Expected:** Recap output covers only the last 3 days of notes; older notes absent
**Why human:** Depends on actual brain content; not reproducible in isolation without seeded data

---

## Gaps Summary

No gaps. All 7 requirements (PERF-01 through PERF-07) are implemented and wired. All automated tests pass (excluding one pre-existing failure unrelated to this phase). Phase goal is achieved.

---

_Verified: 2026-03-22_
_Verifier: Claude (gsd-verifier)_
