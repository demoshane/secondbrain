---
phase: 46-universal-capture-enrichment
plan: 01
status: completed
---

## What was done

Wired person stub creation into `capture_note()` so every capture path builds person memories, not only `sb_capture_smart`.

### Changes

**engine/capture.py**
- Added `_entities = entities` and `_skip_stubs = note_type in {"coding", "link", "files"} or not entities.get("people")` closure variables before thread spawn (two-layer gate, zero overhead when gate fires)
- Added Task 3 block inside `_run_intelligence_hooks()`: calls `resolve_entities(_entities, _conn3, _brain_root)` on a fresh connection, iterates `new_stubs`, calls `capture_note()` recursively for each stub with `body=""`, commits after each

**tests/test_capture.py**
- Added `_SyncThread` helper (runs thread target synchronously — eliminates race conditions)
- Added `TestPersonStubCreation` class with 7 tests:
  1. `test_stub_created_for_meeting_with_people` — resolve called, stub file created
  2. `test_stub_skipped_for_coding_type` — gate fires, resolve not called
  3. `test_stub_skipped_for_link_type` — gate fires, resolve not called
  4. `test_stub_skipped_for_files_type` — gate fires, resolve not called
  5. `test_stub_skipped_when_no_people` — no people extracted, gate fires
  6. `test_stub_no_recursive_loop` — stub with empty body → no people → no loop
  7. `test_stub_thread_error_silent` — resolve raises → capture still returns valid Path

### Verification

```
uv run pytest tests/test_capture.py -v
# 28 passed, 2 xpassed — all new tests green, zero regressions
```

### Design notes

- `_skip_stubs` computed before thread spawn (D-01: two-layer gate)
- `_conn3` is a fresh connection via `get_connection()` — never reuses caller's conn (avoids WAL conflicts)
- Triple try/except mirrors existing silent-catch pattern for `check_connections` and `extract_action_items`
- Recursive loop impossible: stub captures have `body=""` → `extract_entities` returns empty people → `_skip_stubs = True`
