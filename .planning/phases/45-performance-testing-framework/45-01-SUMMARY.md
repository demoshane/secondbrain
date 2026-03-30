---
plan: 45-01
phase: 45-performance-testing-framework
status: complete
completed_at: 2026-03-30
commit: ca7d5bf
---

## What was built

Performance testing engine for second-brain MCP tools.

**engine/test_utils.py** — `cleanup_test_notes(prefix)` cascades deletes through note_embeddings, note_chunks, relationships, action_items, audit_log, notes, and physical .md files on disk. Returns count deleted.

**engine/perf.py** — Full benchmark engine:
- `SOFT_LIMITS` dict mapping 20 MCP tool names to ms thresholds (per D-02)
- `PERF_DIR = META_DIR / "perf_results"` (env-isolated via engine.paths)
- Storage: `save_result`, `load_result`, `list_result_dates`, `get_result_by_date`, `get_latest_with_previous`, `rotate_old_results` (30-day TTL, always keep last)
- Delta: `compute_delta`, `_determine_status`
- Benchmark runner: `_time_tool`, `_benchmark_read_tools`, `_benchmark_write_tools`, `_benchmark_ai_tools`, `run_benchmarks(tool_filter)`
- CLI: `main()` with `--tool`, `--json`, `--cleanup`; always exits 0

**tests/test_perf.py** — 21 unit tests covering all core functions including PERF-09 (full suite), PERF-10 (--tool filter), PERF-11 (--json output).

**pyproject.toml** — `sb-perf = "engine.perf:main"` entry point added.

## Key decisions

- `sb_tag` benchmarked with `action="remove"` on a non-existent tag — idempotent, no side effects
- Write tools use two-step confirm_token pattern for `sb_forget`/`sb_anonymize`
- `ask_brain` benchmarked via `httpx.post` to localhost; `ConnectError` recorded as status="error" not a suite failure

## Self-Check: PASSED

- 21/21 tests pass
- All acceptance criteria met
- pyproject.toml entry registered
