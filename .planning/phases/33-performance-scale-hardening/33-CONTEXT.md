# Phase 33: Performance & Scale Hardening - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Keep the system fast at thousands of notes: paginate all list endpoints, gate expensive O(n) operations, optimise reindex speed, cap LLM context for recap/digest, and expose entity-based filtering in search. Scope is backend + API + MCP only. GUI settings UI for configurable values is Phase 34.

</domain>

<decisions>
## Implementation Decisions

### Pagination (PERF-01)
- Default limit: 50, max: 200 (already specified in 33-01-PLAN.md)
- Backwards compatible: omitting limit/offset returns first 50 (not all)
- Response shape: adds `total`, `limit`, `offset` alongside existing list key
- MCP tools (sb_search, sb_files, sb_actions): add `page` param (1-based); add `page`, `total_pages`, `total` to response

### check_connections gate (PERF-02)
- Gate type: time-based cooldown — skip check_connections if it ran within the last 30 minutes
- Storage: in-memory only (process-level timestamp); cooldown resets on process restart
- Threshold: existing similarity score 0.8 stays unchanged — no additional cap on result count
- This replaces/augments the existing `budget_available()` guard — both guards apply

### Reindex strategy (PERF-03)
- "Unchanged" detection: file mtime vs DB `updated_at` — OS-level check, no per-file I/O
- Default behaviour: **incremental by default** — only reindex changed files
- Add `--full` flag for guaranteed clean state (force all files)
- Orphan handling: DB rows with no corresponding file are **pruned** during incremental reindex
- Embeddings: incremental too — only regenerate embeddings for notes that changed (slowest step)

### Recap/digest token cap (PERF-04)
- Primary strategy: **time window** — only include notes from last N days
- Default window: **7 days** — configurable in `config.toml` (key: `recap.window_days`)
- CLI arg: `sb-recap --days N` overrides config for that call
- Body truncation: **500 chars per note** (current recap truncation, kept consistent)
- Hard cap: **50 notes max** even if all fall within the time window
- Deferred: GUI settings page to change window_days — Phase 34 territory

### Entity filtering API (PERF-06)
- Scope: add filter params to `sb_search` only — list endpoints stay simple
- Filter dimensions (all four, AND logic when combined):
  - `person` — match notes where person appears in `people` column; exact path OR name LIKE (same pattern as sb_person_context)
  - `tag` — filter by one or more tags (existing tag column)
  - `type` — filter by note type: meeting, person, project, idea, coding, etc.
  - `from_date` / `to_date` — ISO date strings; filters on `created_at`
- AND logic when multiple filters provided — narrowing, not broadening
- MCP: add as optional params on `sb_search` tool
- Flask API: add as query params on `GET /notes/search` (or equivalent search endpoint)
- Deferred: faceted search UI — Phase 34/36 will build on top of these filter params

### Claude's Discretion
- Exact cooldown state management (module-level variable vs class vs functools.lru_cache style)
- SQL query structure for combined AND filters (JOIN vs WHERE EXISTS vs json_each)
- config.toml key naming and section structure for recap settings
- Embedding staleness detection logic (mtime comparison approach)
- Which batched embedding worker pattern to use for PERF-05 (asyncio vs thread pool)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/intelligence.py:375` — `check_connections()`: has `budget_available()` guard; add cooldown check here
- `engine/intelligence.py:check_stale_nudge` — similar pattern for per-run gating; reference for cooldown impl
- `engine/embeddings.py:32` — `embed_texts()`: already accepts `batch_size=32`; incremental logic wraps this
- `engine/search.py` — `search_hybrid()`: extend with filter params here
- `engine/api.py` — all list endpoints; 33-01-PLAN.md already specifies pagination shape
- `engine/mcp_server.py:1126` — `sb_person_context()`: person match pattern (exact path OR name LIKE) to reuse for person filter

### Established Patterns
- `budget_available()` / `consume_budget()` in intelligence.py — proactive budget guard pattern
- `json_each(COALESCE(n.people, '[]'))` — people column lookup pattern (Phase 30)
- `config.toml` via `engine/paths.py CONFIG_PATH` — existing config layer for tunables
- Phase 30 decision: people column is single source of truth; json_each for all people lookups

### Integration Points
- `engine/intelligence.py` `check_connections()`: add cooldown timestamp at module level
- `engine/search.py` `search_hybrid()`: add person/tag/type/date params; build SQL WHERE clauses
- `engine/mcp_server.py` `sb_search`: expose new filter params; thread through to search_hybrid
- `engine/api.py` search endpoint: expose filter params as query strings
- `config.toml`: add `[recap]` section with `window_days = 7`
- `sb-reindex` entry point: switch default to incremental, add --full flag

</code_context>

<specifics>
## Specific Ideas

- GUI settings page for `recap.window_days` — user explicitly wants this, goes in Phase 34
- Chrome extension and future Claude cowork will call the same filter API/MCP params — design them as composable building blocks
- "Both filters apply" for check_connections: budget guard + cooldown are independent guards; either can block

</specifics>

<deferred>
## Deferred Ideas

- Faceted search UI — Phase 34 GUI work; builds on top of PERF-06 filter params
- GUI settings page for recap window_days — Phase 34 (PERF-04 configurable via config.toml in Phase 33)
- Chrome extension capture — Phase 36; will consume the filter API built here
- Note count threshold for check_connections — simple fallback if cooldown proves insufficient; decide after observing behaviour

</deferred>

---

*Phase: 33-performance-scale-hardening*
*Context gathered: 2026-03-22*
