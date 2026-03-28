---
plan: 42-02
status: complete
---

## Summary

Added importance to API layer and search filter.

**Changes:**
- `engine/api.py`: Added `VALID_IMPORTANCE_VALUES = frozenset({"low","medium","high"})`. Added `PUT /notes/<path>/importance` endpoint (updates DB + frontmatter via `write_note_atomic`). Updated both GET /notes SELECT queries to include `importance`. Added `importance` extraction in POST /search handler and passed to `_apply_filters`.
- `engine/search.py`: Added `importance: str | None = None` to `_apply_filters()` signature, early-return guard, and DB-lookup filter block.
- `engine/mcp_server.py`: Added `importance: str | None = None` to `sb_search` and passed to `_apply_filters`.
- `tests/test_api.py`: 4 new tests in `TestNoteImportance` — valid/invalid/notfound/list. All pass.
- `tests/test_search.py`: 2 new tests — importance high filter, importance=None passthrough. All pass.

**Verification:** `uv run pytest tests/test_api.py tests/test_search.py -x -q` — all tests pass, no regressions.
