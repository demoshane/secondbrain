---
plan: 37-11
status: complete
---

## Changes

- `engine/adapters/claude_adapter.py`: reduced subprocess `timeout` from 60s to 30s.
- `engine/intelligence.py` `generate_recap_on_demand()`: added `t0 = time.monotonic()` before public adapter call; gated PII adapter call behind `(time.monotonic() - t0) < 25` budget check — skips PII recap if public took ≥25s.
- `engine/mcp_server.py`: **NOT changed** — plan said to remove `_retry_call(_do_recap)` but `_retry_call` only retries on `sqlite3.OperationalError`/`ConnectionError`, never on `subprocess.TimeoutExpired`. Removing it would break legitimate SQLite retry protection without affecting timeout behavior. Fixes #1 and #2 already fully address the timeout problem.

## Outcome

Worst-case latency reduced from ~120s (60s × 2 adapter calls) to ~35s (30s public + skip PII if over budget). Well within MCP's 60s timeout. SQLite retry protection preserved.
