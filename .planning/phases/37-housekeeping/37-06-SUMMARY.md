---
phase: 37-housekeeping
plan: 06
status: complete
---

# 37-06 Summary — Fix 3 Failing Playwright Tests

## Outcome
All 3 previously-failing Playwright tests now pass:
- `test_title_sync` ✅
- `test_delete_flow` ✅
- `test_right_panel_people_mention` ✅

No regressions in the full test suite.

## Root Cause (all 3 shared the same bug)

`conftest.py` `gui_brain` and `seed_note_fn` fixtures stored note paths as **absolute paths** in the SQLite DB (e.g. `/private/var/.../gui_brain0/ideas/note-to-delete.md`).

The API's `store_path()` converts paths to **relative paths** (e.g. `ideas/note-to-delete.md`) before all DB lookups. This mismatch meant every `UPDATE`, `DELETE`, and `SELECT WHERE path=?` in the API silently touched 0 rows.

Consequence per test:
| Test | Symptom |
|------|---------|
| `test_title_sync` | PUT updated file, but DB title row unchanged → GET /notes still returned old title |
| `test_delete_flow` | DELETE removed file, but DB row survived → GET /notes still listed deleted note |
| `test_right_panel_people_mention` | `/meta` found no note row → `people = []` → no badges |

## Fix — `tests/conftest.py`

1. **`gui_brain` fixture**: All 7 DB `INSERT` statements switched from `str(path)` to `str(path.relative_to(brain))`.

2. **Mention note**: Added `people: ["Test Person"]` to frontmatter and DB insert (the `/meta` endpoint resolves `people` from the DB column, not from body text scanning).

3. **`seed_note_fn` fixture**: Single DB `INSERT` switched from `str(note_file)` to `str(note_file.relative_to(brain))`.

## Files Changed
- `tests/conftest.py` — path storage in test fixtures only; no production code changed
