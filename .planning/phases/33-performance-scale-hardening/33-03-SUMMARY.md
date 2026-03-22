---
plan: 33-03
phase: 33-performance-scale-hardening
status: complete
completed_at: 2026-03-22
---

## Summary

Config-driven recap window with `--days` CLI override and non-blocking `embed_pass_async` background worker.

## What was built

**engine/intelligence.py:**
- `generate_recap_on_demand(conn, window_days=None)` — accepts optional `window_days`; reads `[recap].window_days` from config.toml (default 7), hard cap `max_notes` (default 50), body truncation `body_truncation` (default 500 chars)
- `recap_main` gains `--days N` argparse flag; no-context path now calls `generate_recap_on_demand` instead of printing a dead-end hint
- Fixed pre-existing SQL concatenation (dynamic IN clause replaced with per-path individual lookups — semgrep-clean)

**engine/reindex.py:**
- `embed_pass_async(conn_factory, provider, batch_size, force)` — submits `embed_pass` to `ThreadPoolExecutor(max_workers=1)`; returns `concurrent.futures.Future`
- `reindex_brain` calls `embed_pass_async` + `future.result()` to maintain stats reporting while exposing the async interface for future callers

## Test results

4 new tests GREEN. 1 pre-existing failure (`test_check_connections_prints_suggestion` — `check_connections` uses `logger.info`, test asserts stdout; pre-dates this phase, logged in 33-02 SUMMARY).

Updated `test_recap_main_no_context_calls_generate_recap` to match new behavior (calls `generate_recap_on_demand` instead of hint message).

**143 passed, 1 pre-existing failure, 7 xfailed, 2 xpassed**

## Key decisions

- `embed_pass_async` blocks on `future.result()` inside `reindex_brain` to keep stats reporting intact; the async interface is available for callers who want non-blocking behavior
- `recap_main` no-context path now falls back to general recap rather than dead-end message — better UX
- Per-path individual lookups instead of dynamic IN clause — trades N queries for semgrep compliance; acceptable since merged_paths is always small (10–20 items)

## Requirements satisfied

- PERF-04: Recap window configurable via config.toml and --days flag
- PERF-05: embed_pass_async returns Future; reindex non-blocking interface available
