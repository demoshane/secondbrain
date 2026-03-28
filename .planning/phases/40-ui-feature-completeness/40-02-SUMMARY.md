---
plan: 40-02
phase: 40-ui-feature-completeness
status: complete
---

## What was built

Weekly synthesis endpoint for the Intelligence page redesign.

## Changes

- **engine/intelligence.py**: Added `WEEKLY_SYNTHESIS_SYSTEM_PROMPT` constant and `generate_weekly_synthesis(conn) -> str` — 7-day window, up to 100 notes, enriched with top people and recent action items, PII-aware adapter routing, no caching.
- **engine/api.py**: Added `GET /intelligence/synthesis` — returns `{"synthesis": "..."}`, regenerated on every call.
- **tests/test_intelligence.py**: Added `test_synthesis_returns_string`, `test_synthesis_empty_db`, `test_synthesis_endpoint` — all passing.

## Verification

`uv run pytest tests/test_intelligence.py -x -q -k synthesis` → 3 passed (100%)
