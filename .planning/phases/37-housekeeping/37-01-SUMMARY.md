---
phase: 37-housekeeping
plan: 01
status: complete
---

# 37-01 Summary — sb_recap routing fix

## What was done
Fixed `sb_recap` MCP tool to call `generate_recap_on_demand()` when invoked without a name argument, instead of returning "No recap available for this context."

## Changes
- `engine/mcp_server.py`: Added `days: int | None = None` param to `sb_recap`; replaced the early-return stub with a real call to `generate_recap_on_demand(conn, window_days=days)`.
- `tests/test_mcp.py`: Added 3 tests — `test_sb_recap_no_name_calls_generate_recap`, `test_sb_recap_with_name_calls_recap_entity`, `test_sb_recap_no_name_empty_recap`.

## Verification
- `uv run pytest tests/test_mcp.py -q -k recap` — 3 new tests pass
- `uv run pytest tests/test_mcp.py` — 60 passed, 2 xfailed (no regressions)
- Pre-existing failure in `test_api_tags.py::TestTagSearch::test_filter_returns_matching` is unrelated to this plan.

## Decisions
- Inline import of `generate_recap_on_demand` inside the `if name is None` block to match existing style (other tools do inline imports too).
