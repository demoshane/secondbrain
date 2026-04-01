---
phase: 48-backend-code-cleanup
plan: 02
status: complete
---

# Plan 48-02 Summary — F-27/F-28/F-29/F-31 Applied

## What was done

### F-27: Removed 4 /people deprecated aliases
Removed decorator-only aliases from api.py: `/people` GET, `/people` POST, `/people/<path>/links` GET, `/people/<path>` DELETE. The canonical `/persons` routes are unchanged.

### F-28: Consolidated BRAIN_PATH in api.py (12/14 replaced)
Replaced 12 `os.environ.get("BRAIN_PATH", ...)` calls with `_engine_paths.BRAIN_ROOT` (module attribute ref, picks up monkeypatch in tests). Two intentionally kept for call-time resolution:
- `_resolve_note_path()` — tests set env var after import; comment added
- `_get_prefs_path()` — explicitly designed for call-time test isolation; comment added
- Deleted unused `_PREFS_FILE` module constant
- Also fixed `engine/watcher.py` line 164

### F-29: Replaced json.loads(col or "[]") pattern across 8 files
All 18+ occurrences replaced with `_json_list(col)`. Files touched:
`api.py`, `brain_health.py`, `capture.py`, `forget.py`, `mcp_server.py`, `search.py`, `db.py` (2 migration functions).
Removed now-unused lazy `import json as _json` in `db.py` migration functions and `import json` in `mcp_server.sb_tag`.

### F-31: Replaced verbose datetime idiom across 9 files
All `datetime.datetime.now(datetime.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")` replaced with `_now_utc()`. Files touched:
`api.py`, `capture.py`, `forget.py`, `search.py`, `links.py`, `delete.py`, `perf.py`, `export.py`, `anonymize.py`.
`export.py` filename-format variant (`%Y%m%dT%H%M%S`) replaced via `_now_utc().translate(...)`.
`db.py:30` is the `_now_utc()` definition itself — intentionally not replaced.

### Test fix
`tests/test_api.py` upload test updated to also `monkeypatch.setattr(_paths, "BRAIN_ROOT", tmp_path)` — required since `upload_file` now uses `_engine_paths.BRAIN_ROOT`.

## Verification
- `grep -c '"/people"' engine/api.py` → 0 ✓
- `grep -rn 'json.loads.*or.*\[\]' engine/*.py` → 0 ✓
- `grep -rn 'datetime.UTC.*replace.*strftime' engine/*.py | grep -v _now_utc` → 0 ✓
- `grep -c 'os.environ.get.*BRAIN_PATH' engine/api.py` → 2 (intentional keeps) ✓
- All focused tests pass (test_api, test_capture, test_search, test_db_helpers) ✓
