# Phase 48: Backend Code Cleanup — Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Eliminate 7 specific tech-debt items flagged in the Phase 39 audit:
- **F-27**: Remove 4 deprecated `/people` route aliases from api.py
- **F-28**: Replace 13× `os.environ.get("BRAIN_PATH", ...)` in api.py with `BRAIN_ROOT` from engine.paths
- **F-29**: Add `_json_list(col)` helper for the `json.loads(col or "[]")` pattern (18× across 6 files)
- **F-30**: Fix `ensure_person_profile()` — audit whether `person/` or `people/` is canonical and align
- **F-31**: Add `_now_utc()` helper to replace verbose `datetime.datetime.now(datetime.UTC).replace(tzinfo=None)` (11× in api.py; 0 raw `utcnow()` calls remain — F-31 is about the verbose idiom)
- **F-22**: Begin api.py Blueprint partitioning (2792 lines) — register Blueprint objects and move at least one logical group of routes into a separate module
- **F-23**: Fix misleading "circular import" comment in consolidate.py — actual reason is load-time deferral, not circular dependency

No new features. No user-facing changes.

</domain>

<decisions>
## Implementation Decisions

### All areas — Claude's Discretion
User chose to skip discussion. All implementation decisions are delegated to Claude's discretion. Downstream agents should use best judgment based on existing codebase conventions:

- **F-27 (/people removal)**: Safe to delete — no frontend references to `/people` found; IntelligencePage and all other components already use `/persons`.
- **F-28 (BRAIN_PATH consolidation)**: Replace inline `os.environ.get("BRAIN_PATH", ...)` calls in api.py with the already-imported `BRAIN_ROOT` from `engine.paths`. For read-at-call-time uses (where dynamic env var reading is intentional), keep as-is and add a comment. Also cover `watcher.py` if it has the same pattern.
- **F-29 (json.loads helper)**: Put `_json_list(col)` in `engine/db.py` alongside other DB utilities. Keep it private (`_` prefix). Use across all 6 files.
- **F-30 (person/ path)**: Verify which directory is canonical by checking TYPE_TO_DIR, BRAIN_SUBDIRS, and existing DB rows. `person/` is the current canonical (TYPE_TO_DIR fallback, BRAIN_SUBDIRS entry). `ensure_person_profile()` is already correct — confirm this and close the finding, or align if discrepancy found.
- **F-31 (_now_utc helper)**: Add `_now_utc()` → returns `datetime.datetime.now(datetime.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")` in `engine/db.py` or `engine/paths.py`. Replace all occurrences in api.py and any other engine files.
- **F-22 (Blueprint partitioning)**: Register a Flask Blueprint for one logical group (e.g. config routes: `/config/*`, `/ui/prefs`) in a new `engine/api_config.py`. Keep `app = Flask(...)` in `api.py`. One group only — this is "begin", not a full rewrite.
- **F-23 (consolidate.py comment)**: Update the comment from "circular import" to accurately describe load-time deferral.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source files to modify
- `engine/api.py` — primary file: F-27, F-28, F-29, F-31, F-22 (2792 lines)
- `engine/links.py` — `ensure_person_profile()` at line 46 (F-30)
- `engine/consolidate.py` — lazy import comment (F-23)
- `engine/db.py` — target location for `_json_list()` and `_now_utc()` helpers
- `engine/watcher.py` — may have BRAIN_PATH pattern (line 164)

### Audit findings
- `.planning/phases/39-codebase-review/39-FINDINGS.md` — F-22, F-23, F-27, F-28, F-29, F-30, F-31

### Reference for Blueprint pattern
- No existing Blueprint usage in codebase — use standard Flask Blueprint docs. Keep `app` in `api.py`, new Blueprint registered via `app.register_blueprint(...)`.

### Path constants
- `engine/paths.py` — `BRAIN_ROOT`, `store_path()`, `BRAIN_SUBDIRS`

</canonical_refs>

<code_context>
## Existing Code Insights

### F-27: /people aliases
Four deprecated routes in api.py:
- Line 366: `@app.get("/people")` → alias for `/persons`
- Line 731: `@app.post("/people")` → alias for `/persons`
- Line 818: `@app.get("/people/<path:note_path>/links")` → alias for `/persons/<path>/links`
- Line 872: `@app.delete("/people/<path:note_path>")` → alias for `/persons/<path>`
No frontend references to `/people` found — safe to delete.

### F-28: BRAIN_PATH pattern
api.py already has `from engine.paths import BRAIN_ROOT, store_path` at line 27.
13 inline `os.environ.get("BRAIN_PATH", ...)` reads remain — most can be replaced with `BRAIN_ROOT`.
Some are inside functions that may need call-time resolution (e.g. `_resolve_note_path` at line 298 — already uses `.resolve()` dynamically).

### F-31: Current timestamp idiom
Current pattern (already correct, no utcnow() left):
`datetime.datetime.now(datetime.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")`
Used 11× in api.py, and in other engine files (strftime and isoformat variants).
Helper should produce the strftime format (matching existing DB values).

### F-22: Blueprint candidate
Config routes (`/config/*`, `/ui/prefs`, `/ui/prefs`) are self-contained, no cross-route dependencies,
and represent a natural domain boundary. Good first Blueprint target.
`app.register_blueprint(config_bp)` in api.py after Blueprint is defined in `engine/api_config.py`.

</code_context>

<deferred>
## Deferred Ideas

None — user confirmed no scope additions.

</deferred>

---

*Phase: 48-backend-code-cleanup*
*Context gathered: 2026-03-30*
