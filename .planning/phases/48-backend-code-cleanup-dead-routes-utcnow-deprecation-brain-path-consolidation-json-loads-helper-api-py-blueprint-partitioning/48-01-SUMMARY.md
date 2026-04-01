---
phase: 48-backend-code-cleanup
plan: 01
status: complete
---

# Plan 48-01 Summary — Helpers + F-23 + F-30

## What was done

### Task 1: Added _json_list and _now_utc to engine/db.py
- Added `import datetime` and `import json` to db.py imports
- Added `_json_list(col)` after `_escape_like` — returns list from JSON column or [] for NULL/empty; passes through existing lists defensively
- Added `_now_utc()` — returns `datetime.datetime.now(datetime.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")`
- Created `tests/test_db_helpers.py` with 9 tests covering all edge cases — all pass

### Task 2: F-23 — consolidate.py comment fixed
- Added comment before lazy imports in `consolidate_main()`: "Lazy imports: deferred to avoid slow module-level load of brain_health (heavy dependencies). Reason is startup performance, not import ordering."
- `grep -c "circular import"` returns 0 ✓

### Task 2: F-30 — links.py person path verified (false positive)
- `ensure_person_profile()` already uses `brain_root / "person" / ...` — canonical per BRAIN_SUBDIRS
- Added comment confirming canonical path and closing the finding

## Artifacts produced
- `engine/db.py` — `_json_list`, `_now_utc` helpers (Plan 02 will use these)
- `engine/consolidate.py` — accurate lazy-import comment
- `engine/links.py` — canonical path comment
- `tests/test_db_helpers.py` — 9 tests, all passing

## Notes for Plan 02
- Import helpers as: `from engine.db import _json_list, _now_utc`
- `_now_utc()` produces `strftime` format (matches existing DB values)
- `_json_list` handles None, "", "[]", valid JSON arrays, and pass-through lists
