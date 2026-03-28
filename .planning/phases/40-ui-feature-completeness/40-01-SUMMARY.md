---
plan: 40-01
phase: 40-ui-feature-completeness
status: complete
---

## What was built

Per-person AI Brain Insight endpoint with 24h caching.

## Changes

- **engine/db.py**: Added `migrate_create_person_insights(conn)` — creates `person_insights(person_path PK, insight, generated_at)` table. Registered in `init_schema()` after `migrate_add_summary_column`.
- **engine/intelligence.py**: Added `PERSON_INSIGHT_SYSTEM_PROMPT` constant and `generate_person_insight(conn, person_path, force=False) -> str` — checks cache, returns within 24h, regenerates via Ollama adapter when stale/missing/forced, upserts result.
- **engine/api.py**: Added `GET /persons/<path:note_path>/insight` endpoint — returns `{"insight": "...", "person_path": "..."}`, supports `?force=1` to bypass cache, returns 403/404/400 on error cases.
- **tests/test_people.py**: Added `test_person_insight_cache`, `test_person_insight_regen`, `test_person_insight_fresh` — all passing.

## Verification

`uv run pytest tests/test_people.py -x -q -k insight` → 3 passed (100%)
