---
plan: 45-02
title: Performance GUI page + datetime deprecation fix
status: complete
completed_at: "2026-03-30"
---

# Plan 45-02 Summary

## What shipped

**PerformancePage (frontend)**
- New `PerformancePage.tsx` component with collapsible "Latest Run" table (6 columns: tool, latest, previous, delta, limit, status) and "30-Day Trend" sparkline grid
- Inline `Sparkline` SVG component (polyline, hsl primary colour)
- Client-side delta computation per D-18; fetches `/perf/results/latest` on mount
- Status colours: green=pass, amber=warn, red=error
- `TabBar.tsx`: Performance tab added after Intelligence (Gauge icon)
- `UIContext.tsx`: `'performance'` added to `View` union type
- `App.tsx`: render branch for `currentView === 'performance'`

**API routes (engine/api.py)**
- `GET /perf/results` → list of YYYY-MM-DD date strings
- `GET /perf/results/latest` → `{latest, previous}` for GUI delta display
- `GET /perf/results/<date>` → single result by date (404 on missing)

**datetime.datetime.utcnow() deprecation fix**
- 15 engine files migrated to `datetime.datetime.now(datetime.UTC).replace(tzinfo=None)`
- All arithmetic-adjacent callsites validated for naive/aware consistency

**sb-perf benchmark fixes**
- `_benchmark_read_tools`: relative DB paths resolved to absolute via `_abs()` helper
- `_benchmark_write_tools`: fixed `sb_capture_batch(notes=[...])`, `sb_edit(path=...)`, `sb_link/sb_unlink(source_path=..., target_path=...)`, `sb_remind(action_id=int)`, `sb_anonymize(path=..., tokens=[...])`, removed `sb_forget` (person-only); dropped `asyncio.run()` wrapper around sync `sb_capture`
- `_benchmark_ai_tools`: `sb_recap()` and `sb_digest()` called with no args
- `_time_tool`: rewritten to inspect return value (not function signature) — correctly handles FastMCP-decorated functions that return dicts synchronously
- `--verbose` / `-v` flag: prints error message in red under each failing row

## Final state

`sb-perf --verbose` result: **19/19 tools passing**, 0 warnings, 0 errors.

## Test coverage

- `tests/test_perf.py`: 21 tests, all pass
- `tests/test_api.py`: 4 new perf route tests, all pass
