# Project Learnings

Rules derived from past bugs. Only kept if universally applicable and not already in CLAUDE.md.

---

## Frontend Deploy Pipeline

After any `frontend/src/**` change, run in order:
1. `npm run build` (in `frontend/`)
2. `uv tool install . --reinstall` (copies new static files)
3. Kill port 37491 + restart `sb-api`

**Why:** GUI is served from installed uv tool binary, not source tree. A stale `sb-api` on port 37491 silently serves old bundles even if source is correct (`gui/__init__.py` reuses existing port).

---

## API Endpoints — Single Source of Truth

The only note metadata endpoint is `/notes/<path>/meta` — returns `{ backlinks, related, people }`. No separate `/backlinks` or `/people` routes exist. Always verify routes in `engine/api.py` before wiring frontend.

---

## People Field Semantics

- `notes.people` column stores JSON array of **file paths**, not objects.
- May be `[]` for notes captured before entity extraction worked.
- `note_meta()` must detect people by **body-mention fallback** (match person note titles in body), not rely solely on `people` column.

---

## Reindex Must Purge Stale Rows

`reindex_brain()` must DELETE DB rows whose paths are absent from disk. Hidden directories (path component starting with `.`) must be excluded from the walk.

---

## Test Isolation — Patch Both DB_PATH Locations

Any test calling `get_connection()` without explicit path MUST patch **both** `engine.db.DB_PATH` and `engine.paths.DB_PATH`. MCP capture tests must also patch `engine.paths.BRAIN_ROOT` (not just `mcp_mod.BRAIN_ROOT`) — those functions re-import from `engine.paths` at call time.

---

## Capture Ordering — Entity Extraction Before build_post()

`extract_entities()` must run BEFORE `build_post()`. The `people` param to `build_post()` is written verbatim — it cannot be patched after without a second UPDATE.

---

## Upsert Semantics — Merge, Don't Replace

When coercing optional list params (tags, people) via helpers like `_to_list()`, capture "was it provided?" BEFORE coercion. Upsert paths must **merge** new + existing, not replace, unless caller explicitly wants replacement.

---

## SQL Migrations — Verify Column Exists

When adding columns to UPDATE/INSERT statements, verify the column exists in both CREATE TABLE schema AND the migration chain. Test with a fresh DB.
