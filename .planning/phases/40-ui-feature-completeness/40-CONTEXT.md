# Phase 40: UI Feature Completeness - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Add the backend API capabilities required by the Visily designs that don't exist yet. This is **pure backend work** — no frontend changes. Phase 41 (Visual Redesign) consumes these endpoints.

Five capability gaps to close:
1. Per-person AI Brain Insight endpoint
2. Weekly Synthesis endpoint
3. Project status field + stats (status, related_notes_count, linked_meetings_count)
4. Linked meetings on projects + participant objects on meetings
5. Action items grouped-by-source endpoint + Links markdown body (already returned as raw text — frontend renders)

</domain>

<decisions>
## Implementation Decisions

### 40-01: Per-person AI Brain Insight
- **D-01:** New endpoint `GET /persons/<path>/insight`
- **D-02:** AI-generated narrative via **Ollama** (local, free tokens) — same adapter pattern as recap/digest
- **D-03:** Content: overview summary of the person + their recent activity (meetings, notes, action items)
- **D-04:** Cache: **24h TTL** stored in DB (new `person_insights` table or a cached column). Regenerate on view if cache is stale.
- **D-05:** Always regenerate on request — check cache age first; if < 24h, return cached; otherwise call Ollama and update cache.

### 40-02: Weekly Synthesis
- **D-06:** New endpoint `GET /intelligence/synthesis`
- **D-07:** AI-generated weekly synthesis — similar to recap but weekly scope
- **D-08:** Use existing `_router.get_adapter('public')` pattern (consistent with `generate_recap_on_demand`)
- **D-09:** No caching requirement specified — same as recap (on-demand, regenerated each call)

### 40-03: Project status field + stats
- **D-10:** Add `status TEXT NOT NULL DEFAULT 'active'` column to `notes` table via DB migration (idempotent `ALTER TABLE ADD COLUMN` pattern)
- **D-11:** Valid values: `'active'`, `'paused'`, `'completed'`
- **D-12:** `GET /projects` response adds `status` field per row
- **D-13:** `GET /projects/<path>` response adds `status`, `related_notes_count` (notes referencing this project via relationships table), `linked_meetings_count` (meeting-type notes linked via relationships)
- **D-14:** New `PUT /projects/<path>/status` endpoint to update status — accepts `{"status": "active|paused|completed"}`, validates value, updates DB, broadcasts `notes_changed` SSE event

### 40-04: Linked meetings on projects + participant objects on meetings
- **D-15:** `GET /projects/<path>` adds `linked_meetings: [{path, title, meeting_date}]` — queried from `relationships` table where source or target is the project path AND the linked note has `type='meeting'`
- **D-16:** `GET /meetings/<path>` changes `participants` from `["name"]` to `[{name, path}]` — path resolved via best-effort `SELECT path FROM notes WHERE type='person' AND title=?` query; `path` is **nullable** (null if no person note exists for that name)
- **D-17:** Write endpoint `POST /projects/<path>/meetings` (to link a meeting to a project) is **deferred to Phase 41** — Phase 40 is read-only for this feature

### 40-05: Action items grouped-by-source
- **D-18:** New **separate endpoint** `GET /actions/grouped` — always returns grouped shape, not a query param on existing `/actions`
- **D-19:** Response shape: `{"groups": [{"note_title": "...", "note_path": "...", "actions": [...]}], "total": N}`
- **D-20:** Same filter support as `/actions` — accepts `done`, `assignee` query params
- **D-21:** Links body: `GET /links/<path>` already returns `body` as raw markdown text — this is correct; the frontend renders it. No backend change needed.

### Claude's Discretion
- Cache storage for person insights: Claude decides whether to add a `person_insights` table or use a `insight_cache` column on `notes`. A separate table is cleaner (avoids polluting the notes schema further).
- SQL for `related_notes_count`: use the `relationships` table counting rows where source or target matches the project path.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing API patterns
- `engine/api.py` — all existing routes; follow established patterns for error handling, `_int_param`, `_resolve_note_path`, `store_path`, `_broadcast`
- `engine/db.py` — schema + migration pattern (`migrate_add_*` idempotent functions called from `init_schema`)

### Intelligence/AI patterns
- `engine/intelligence.py` — `generate_recap_on_demand()` pattern for Ollama calls; use `_router.get_adapter('public')` for AI calls
- `engine/api.py:1456` — `/intelligence/recap` endpoint — model for new synthesis endpoint

### Relationships table
- `engine/db.py:52` — `relationships(source_path, target_path)` schema — used for linked meetings query
- `engine/api.py:1571` — `POST /relationships` — shows how relationships are created

### Phase 41 deferred items
- `POST /projects/<path>/meetings` write endpoint — to be added in Phase 41

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_resolve_note_path(note_path)` — path validation + traversal guard; use in all new `/<path>` endpoints
- `store_path(abs_path)` — converts absolute path to DB-stored relative path
- `_broadcast({"type": "notes_changed"})` — SSE broadcast after writes
- `_int_param(name, default, min_val, max_val)` — validated int query param helper
- `list_actions(conn, done, assignee, note_path)` — existing action query function in `api.py`
- `_router.get_adapter('public')` — Ollama adapter for AI generation (in intelligence.py)

### Established Patterns
- DB migrations: idempotent `ALTER TABLE ADD COLUMN IF NOT EXISTS` via column list check
- Participant JSON: `people` column is `TEXT NOT NULL DEFAULT '[]'`, parsed with `json.loads(row["people"] or "[]")`
- Pagination: applied in Python after query (`actions[offset:offset + limit]`) for filtered endpoints
- Error handling: `return jsonify({"error": "forbidden"}), 403` for path traversal; `404` for not found; `400` for bad input

### Integration Points
- `GET /projects/<path>` at line 444 — extend response with status, stats, linked_meetings
- `GET /meetings/<path>` at line 388 — extend participants to be objects
- `GET /actions` at line 752 — new sibling endpoint `GET /actions/grouped`
- `init_schema()` at end of `db.py` — add status migration and person_insights table migration calls here

</code_context>

<specifics>
## Specific Ideas

- Person insight narrative should cover: who the person is (from profile note body) + recent meeting activity + recent notes mentioning them + open action items count
- The Visily design shows project status as an **inline editable badge** — the PUT endpoint needs to be lightweight (status-only update, not full note update)
- `linked_meetings_count` in project list (`GET /projects`) can be a subquery COUNT for efficiency

</specifics>

<deferred>
## Deferred Ideas

- `POST /projects/<path>/meetings` — write endpoint to link a meeting to a project. Deferred to Phase 41 (UI will need this to let users create links from the Projects detail panel).

</deferred>

---

*Phase: 40-ui-feature-completeness*
*Context gathered: 2026-03-28*
