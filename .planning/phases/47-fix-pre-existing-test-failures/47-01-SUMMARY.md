# Phase 47-01 Summary: Fix Pre-existing Test Failures

**Completed:** 2026-03-30

## What was fixed

### test_delete_endpoint_404 (tests/test_delete.py)
- **Test fix:** Stripped leading `/` from the absolute ghost path before passing to `client.delete()`. Flask's `<path:>` route captures everything after `/notes/`, so a leading slash created a double-slash URL (`/notes//var/...`) that Flask normalised with a 308 redirect.
- **Production fix:** Added `if not p.exists(): return 404` in `delete_note_endpoint` (engine/api.py) after `_resolve_note_path`. Deleting a non-existent path now returns 404 instead of silently succeeding or erroring.

### 3 xfailed tests in tests/test_smart_capture.py
Root cause: macOS `/var` → `/private/var` symlink mismatch, combined with relationship inserts using absolute unresolved paths while `notes.path` stores relative paths (FK constraint on `relationships` table).

**Fixture fix:** `isolated_brain` now uses `tmp_path.resolve() / "brain"` — resolves the symlink at fixture creation so `BRAIN_ROOT` and all derived paths are consistent.

**Production pipeline fix (engine/mcp_server.py):**
- Added `store_path` to imports from `engine.paths`
- `sb_capture` similar relationship insert: source path normalised via `store_path(path.resolve())`; target normalised defensively if absolute
- `sb_capture_smart` co-captured insert: all paths normalised to relative before `itertools.combinations`
- `sb_capture_smart` save_complementary insert: source path normalised

**Test assertion fix (`test_similar_relationship_inserted_on_confirm`):**
- Mock now returns relative `first_rel` (simulating real `check_capture_dedup` behaviour — it returns `note_embeddings.note_path` which is relative)
- DB query uses `second_rel` (normalised) to match stored relative paths

**Removed:** All three `@pytest.mark.xfail` markers.

## Files changed
- `engine/api.py` — `p.exists()` 404 guard in `delete_note_endpoint`
- `engine/mcp_server.py` — `store_path` import + 3 relationship insert normalisation fixes
- `tests/test_delete.py` — strip leading `/` from ghost URL
- `tests/test_smart_capture.py` — fixture `.resolve()`, xfail removals, assertion normalisation
