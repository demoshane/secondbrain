---
plan: 42-01
status: complete
---

## Summary

Added `importance` field to the DB, capture pipeline, MCP tools, and typeclassifier.

**Task 1 — DB + capture pipeline:**
- `engine/db.py`: Added `migrate_add_importance_column()` (idempotent); called from `init_schema()` between `migrate_create_person_insights` and `_migrate_fk_cascade`.
- `engine/capture.py`: Added `importance: str = "medium"` to `build_post()`, `capture_note()`; added `importance` extraction and INSERT column in `write_note_atomic()`.
- `tests/test_capture.py`: 4 new tests — all pass.

**Task 2 — MCP tools + classify_importance:**
- `engine/typeclassifier.py`: Added `_IMPORTANCE_HIGH_PAT`, `_IMPORTANCE_LOW_PAT`, and `classify_importance(title, body) -> str` function.
- `engine/mcp_server.py`: Added `importance` param to `sb_capture`, `sb_capture_batch` (per-note), `sb_edit` (optional, preserves if None), `sb_capture_smart` (infers via `classify_importance`).
- `tests/test_mcp.py`: 6 new tests — all pass.

**Verification:** All tests pass, no regressions.
