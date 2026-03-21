---
phase: 32-architecture-hardening
plan: "02"
title: "FK cascade + connection safety + upload cap"
status: complete
started: 2026-03-21
completed: 2026-03-21
---

# Plan 32-02: FK Cascade + Connection Safety + Upload Cap — Summary

## What was built

- PRAGMA foreign_keys=ON on every get_connection() call (ARCH-02)
- All 30 get_connection/conn.close pairs in api.py wrapped in try/finally (ARCH-03)
- 50 MB upload cap with 413 error handler (ARCH-04)
- _SlashNormMiddleware removed (ARCH-04)
- suppress_next_delete upgraded to per-path Events with lock (ARCH-03)

## Key files

### Modified
- `engine/db.py` — PRAGMA foreign_keys=ON in get_connection()
- `engine/api.py` — try/finally wraps, MAX_CONTENT_LENGTH, 413 handler, middleware removed
- `engine/watcher.py` — per-path Event-based suppress

## Commits
- `7822251` feat(32-04): included FK pragma + try/finally wraps (scope leak from parallel agent)
- `fb3a709` feat(32-02): 50 MB upload cap, 413 handler, remove _SlashNormMiddleware
- `5fd5742` feat(32-02): thread-safe suppress_next_delete with per-path Events

## Deviations
- FK pragma and try/finally wraps were committed by the 32-04 agent (scope leak — both agents modified db.py/api.py concurrently)
- _SlashNormMiddleware didn't need fixture fixes — it was only a workaround and tests pass without it
- Orchestrator completed Tasks 2-3 directly after agent failed to commit

## Self-Check: PASSED
- [x] PRAGMA foreign_keys=ON on every connection
- [x] All connections wrapped in try/finally
- [x] 50 MB upload cap with 413 response
- [x] _SlashNormMiddleware removed
- [x] Thread-safe suppress with per-path Events
