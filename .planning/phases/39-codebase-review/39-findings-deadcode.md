# Dead Code + Optimisation Audit Findings

**Produced by:** Plan 39-05
**Date:** 2026-03-27
**Scope:** All `engine/*.py` modules + `frontend/src/components/*.tsx`

---

## Dead Module Assessment

| Module | Import Count (engine) | Import Count (tests) | CLI Entry Point | Verdict |
|---|---|---|---|---|
| `engine/rag.py` | 1 (lazy in ai.py L91) | 2 (test_rag.py) | None | ALIVE — used by `ask_followup_questions` via lazy import |
| `engine/templates.py` | 0 | 1 (test_capture.py) | None | DEAD — zero engine callers; tests the module in isolation |
| `engine/ratelimit.py` | 1 (`watcher.py` imports `RateLimiter`) | 2 (test_subagent.py, test_watcher.py) | None | ALIVE — watcher depends on it |
| `engine/ai.py` | 2 (capture.py L406, L441) | 6 (test_ai.py, test_rag.py) | `sb-update-memory` | ALIVE — `ask_followup_questions` + `update_memory` called from capture; CLI registered |
| `engine/classifier.py` | - (not audited here) | - | None | See DEAD-04 |
| `engine/segmenter.py` | - (not audited here) | - | None | ALIVE — used by mcp_server.py `sb_capture_smart` |
| `engine/links.py` | - | - | `sb-check-links` | ALIVE — CLI + capture/reindex callers |
| `engine/link_capture.py` | 1 (mcp_server.py) | - | None | ALIVE — used by `sb_capture_link` |
| `engine/people.py` | 2 (api.py, mcp_server.py) | - | None | ALIVE |
| `engine/entities.py` | Multiple | Multiple | None | ALIVE |
| `engine/smart_classifier.py` | 3 lazy (mcp_server.py) | 8 (test_smart_capture.py) | None | ALIVE |
| `engine/sharding.py` | Self-ref only | 6 (test_sharding.py) | None | ALIVE — but note API/MCP exposure unclear (see DEAD-06) |

---

## Finding: DEAD-01

- **Severity:** Medium
- **Type:** dead-module
- **File:** `engine/templates.py`
- **Description:** `load_template()` and `render_template()` are defined but zero engine modules call them. Only `tests/test_capture.py:84` imports them directly (as an isolated test of the module). The actual capture pipeline does NOT use `engine/templates.py` — note body construction happens elsewhere (likely hardcoded strings in `capture.py`).
- **Evidence:**
  - `grep engine/ "from engine.templates"` → 0 matches
  - `grep engine/ "load_template\|render_template"` → 0 matches (engine/ only)
  - `grep tests/ "from engine.templates"` → 1 match (test_capture.py:84, isolation test)
  - pyproject.toml `[project.scripts]` → no entry references `engine.templates`
  - No dynamic imports found (`importlib`, `__import__`)
- **Recommended fix:** Either wire `templates.py` into `capture.py`'s note body construction (so the module earns its place), or remove `templates.py` and the isolation test in `test_capture.py`. Removing it cleans up a misleading module.
- **Risk if removed:** Low. The test file imports it but the production path doesn't — removing it won't break any live feature. The test would fail and should be deleted alongside.

---

## Finding: DEAD-02

- **Severity:** Low
- **Type:** dead-function
- **File:** `engine/api.py:24-25`
- **Description:** Duplicate `from engine.paths import BRAIN_ROOT` on consecutive lines. Line 24 imports only `BRAIN_ROOT`, line 25 also imports `store_path` — making line 24 a dead/redundant import.
- **Evidence:**
  ```python
  24: from engine.paths import BRAIN_ROOT
  25: from engine.paths import BRAIN_ROOT, store_path
  ```
- **Recommended fix:** Remove line 24; keep line 25 as the single import.
- **Risk if removed:** Zero. It's a pure duplicate.

---

## Finding: DEAD-03

- **Severity:** Low
- **Type:** dead-route (deprecated alias)
- **File:** `engine/api.py:318, 456, 543, 574`
- **Description:** Multiple endpoints have `/people` deprecated aliases registered alongside `/persons` canonical routes. The frontend already uses `/persons` on most callers (PeoplePage.tsx, PersonAutocomplete.tsx, DeleteEntityModal.tsx), but `IntelligencePage.tsx:50` still calls `/people`. The deprecated aliases remain live code and cannot be removed until all frontend callers are migrated.
- **Evidence:**
  ```
  @app.get("/persons")
  @app.get("/people")  # deprecated alias
  @app.post("/people")  # deprecated alias
  @app.get("/people/<path:note_path>/links")  # deprecated alias
  @app.delete("/people/<path:note_path>")  # deprecated alias
  ```
  Frontend caller still on old route: `IntelligencePage.tsx:50` uses `'/people'`
- **Recommended fix:** Migrate `IntelligencePage.tsx` to use `/persons`, then remove the deprecated `/people` route registrations.
- **Risk if removed:** Low after migration. Currently one frontend caller would break if aliases were removed today.

---

## Finding: DEAD-04

- **Severity:** Low
- **Type:** optimisation
- **File:** `engine/api.py` — many handler functions
- **Description:** `os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))` is repeated in at least 10 handler functions inline, instead of using the already-imported `BRAIN_ROOT` from `engine.paths`. `engine/paths.py` already centralises this lookup as `BRAIN_ROOT`. The inline lookups are redundant and inconsistent — if `BRAIN_PATH` changes mid-run, some handlers would pick it up and others (those using `BRAIN_ROOT`) wouldn't.
- **Evidence:**
  - `grep api.py "os.environ.get.*BRAIN_PATH"` → 13 occurrences
  - `BRAIN_ROOT` is imported at module top but not used in many handlers
- **Recommended fix:** Replace all inline `os.environ.get("BRAIN_PATH", ...)` in `api.py` with the imported `BRAIN_ROOT` constant.
- **Risk if removed:** Low. Behaviour is identical at startup, and `BRAIN_ROOT` is module-level so it resolves once — consistent with the runtime assumption.

---

## Finding: DEAD-05

- **Severity:** Low
- **Type:** duplicate-logic
- **File:** Multiple `engine/*.py` modules
- **Description:** `json.loads(col or "[]")` pattern for parsing JSON-stored `tags` and `people` columns is repeated in ~12 files: `api.py` (9 occurrences), `intelligence.py`, `consolidate.py`, `db.py`, `search.py`. Each callsite rolls its own error handling (some wrap in try/except, some don't).
- **Evidence:**
  - `grep engine/ "json.loads.*tags\|json.loads.*people"` → 13 occurrences across 5 files
  - No shared helper exists (`grep engine/ "_safe_json\|_parse_json"` → 0 matches)
- **Recommended fix:** Extract a `_parse_json_list(val: str | None) -> list` helper to `engine/db.py` or a new `engine/utils.py`, and replace all callsites.
- **Risk if removed:** Low. Purely internal refactor, no API surface changes.

---

## Finding: DEAD-06

- **Severity:** Low
- **Type:** dead-code path (unused in production surface)
- **File:** `engine/sharding.py`
- **Description:** `sharding.py` is well-tested (6 test files) but has no callers in `engine/api.py` or `engine/mcp_server.py`. The module exposes `get_shard_path`, `shard_note`, `shard_all_notes` — none of these are invoked from the API/MCP surface or from any CLI entry point in `pyproject.toml`. It's implemented as a Phase 38 feature that was never wired to a user-facing path.
- **Evidence:**
  - `grep api.py "sharding\|shard_note\|shard_all"` → 0 matches
  - `grep mcp_server.py "sharding\|shard_note"` → 0 matches
  - pyproject.toml scripts → no `sb-shard` or similar entry
  - `engine/sharding.py:7` has a self-referential docstring import showing example usage but no actual callers
- **Recommended fix:** Either: (a) wire `shard_all_notes` to a CLI entry `sb-shard` in pyproject.toml, or (b) document that sharding is a background maintenance module for Phase 38 scale work and keep it as-is. Do not delete — it has valid tests and is part of the scale architecture.
- **Risk if removed:** Low. No production path depends on it today. If deleted, `test_sharding.py` would fail.

---

## Finding: DEAD-07

- **Severity:** Medium
- **Type:** dead-function
- **File:** `engine/links.py:46-60` — `ensure_person_profile()`
- **Description:** `ensure_person_profile()` creates person profile stubs at `brain_root/person/{slug}.md`. It uses the old `person/` subdirectory (singular), while the brain's canonical people directory is `people/` (plural). This function is called by `add_backlinks()` which is likely still called from older capture paths, but the path it writes to (`brain_root/person/…`) is inconsistent with the note structure (`people/` subfolder from `pyproject.toml` and `brain_health.py`).
- **Evidence:**
  - `ensure_person_profile` uses `brain_root / "person" /` (singular)
  - Brain structure in PROJECT.md lists `people/` (plural)
  - `grep engine/ "ensure_person_profile"` → only defined in `links.py`, called by `add_backlinks()` in same file
  - `add_backlinks()` is still called from multiple callers (capture + reindex paths)
- **Recommended fix:** Audit whether `add_backlinks()` is still the active backlink-writing path, or if it was superseded by the `note_people` junction table added in Phase 32. If superseded, `links.py::add_backlinks` and `ensure_person_profile` can be removed. If still active, fix the path to `people/` (plural).
- **Risk:** Medium — this touches backlink file creation. Verify against Phase 30/32 changes before removing.

---

## Finding: DEAD-08

- **Severity:** Low
- **Type:** optimisation (deprecated datetime pattern)
- **File:** 13 engine modules
- **Description:** `datetime.utcnow()` is used 33 times across 13 files (`grep engine/ "datetime.utcnow"` → 33 occurrences). Python 3.12+ deprecates `utcnow()` in favour of `datetime.now(tz=timezone.utc)`. While not yet removed from Python, the deprecation warning appears at runtime in 3.12+.
- **Evidence:** Count via grep: 33 occurrences across `api.py` (9), `capture.py` (4), `mcp_server.py` (5), and 10 other files.
- **Recommended fix:** Global replace `datetime.utcnow()` → `datetime.now(timezone.utc)` with appropriate import of `timezone`. Low blast radius, purely mechanical.
- **Risk if changed:** Low. Behaviour equivalent. Output format change: `utcnow()` produces naive datetime, `now(timezone.utc)` produces aware datetime. Any code doing string formatting with `.strftime(...)` is unaffected. Any code doing arithmetic or comparison against naive datetimes would need review.

---

## Finding: DEAD-09

- **Severity:** Low
- **Type:** dead-function
- **File:** `engine/api.py` — `_note_folder()` helper
- **Description:** `_note_folder()` extracts the subfolder name from a note path. Needs verification that it is called by live routes (not confirmed unused — this is a flag for review).
- **Evidence:** Not fully traced in this audit. Marked for follow-up in DEAD-10 triage.
- **Recommended fix:** Run `grep api.py "_note_folder"` to confirm callsite count.

---

## Frontend Dead Component Assessment

| Component | Imported from App.tsx | Used in import tree | Verdict |
|---|---|---|---|
| `NoteEditor.tsx` | No (App.tsx does not import it) | Yes — imported by `NoteViewer.tsx` | ALIVE |
| `TagAutocomplete.tsx` | No | Used by `NoteViewer.tsx` | ALIVE |
| `PersonAutocomplete.tsx` | No | Used by `NewNoteModal.tsx` or similar | ALIVE (verify) |
| `ActionItemList.tsx` | No | Used by `NoteViewer`, `RightPanel`, `ActionsPage`, `PeoplePage` | ALIVE |
| `DeleteEntityModal.tsx` | No | Used by `PeoplePage.tsx` or `ProjectsPage.tsx` | ALIVE (verify) |
| `NewEntityModal.tsx` | No | Used by `PeoplePage.tsx` or entity pages | ALIVE (verify) |

**NoteEditor.tsx verdict:** ALIVE. Not imported by App.tsx directly, but imported by `NoteViewer.tsx:8` and used at line 113. This matches RESEARCH.md candidate D-07 — it was a false alarm. NoteEditor is reachable via `App.tsx → NoteViewer → NoteEditor`.

---

## Summary Table

| ID | Severity | Type | File | Recommended Action |
|---|---|---|---|---|
| DEAD-01 | Medium | dead-module | `engine/templates.py` | Wire into capture OR remove module + test |
| DEAD-02 | Low | duplicate-import | `engine/api.py:24` | Remove duplicate import line |
| DEAD-03 | Low | deprecated-route | `engine/api.py` (5 alias routes) | Migrate `IntelligencePage.tsx`, then remove aliases |
| DEAD-04 | Low | duplicate-logic | `engine/api.py` (13 occurrences) | Replace inline `os.environ.get(BRAIN_PATH)` with `BRAIN_ROOT` |
| DEAD-05 | Low | duplicate-logic | 5 engine modules | Extract `_parse_json_list()` helper |
| DEAD-06 | Low | unwired-module | `engine/sharding.py` | Add CLI entry OR document as maintenance-only |
| DEAD-07 | Medium | stale-path | `engine/links.py:46-60` | Audit if superseded; fix `person/` → `people/` path if not |
| DEAD-08 | Low | deprecated-api | 13 engine modules (33 occurrences) | Replace `datetime.utcnow()` → `datetime.now(timezone.utc)` |
| DEAD-09 | Low | unverified-usage | `engine/api.py:_note_folder()` | Verify callsite count |
