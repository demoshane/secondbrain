# Phase 50: Retrieval Reinforcement — Learning from Use

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Add access tracking to notes so the system learns which notes are valuable through use.
When a note is read, searched for, or referenced, that signal feeds back into future rankings.

Foundation phase — Phases 51 (temporal decay) and 53 (proactive surfacing) depend on the
access tracking infrastructure built here.

### Problem
Today, a note captured 2 years ago that's been read 50 times ranks identically to one
captured yesterday and never accessed. The audit_log tracks searches and reads, but that
signal is never fed back into ranking. Real brains strengthen neural pathways through
repeated retrieval — we don't.

### Scope
- Schema: add `last_accessed_at` and `access_count` columns to `notes` table
- Tracking: increment access on `sb_read`, `sb_search` result clicks, `sb_person_context`
- Ranking: add `_access_boost()` multiplier to hybrid search RRF pipeline
- MCP: `sb_read` and `sb_search` update access metadata as side effect
</domain>

<decisions>
## Implementation Decisions

### Access tracking granularity
Track at note level, not query level. We care about "note X was useful" not "query Y worked."
Increment `access_count` and update `last_accessed_at` whenever:
- `sb_read()` is called for a note
- A note appears in `sb_search()` results AND is subsequently read (tracked via sb_read)
- `sb_person_context()` resolves a person note
- API `/notes/<path>` endpoint serves a note to the GUI

### Boost formula
Similar pattern to existing `_recency_multiplier()`:
`1.0 + 0.15 * min(access_count, 20) / 20 * exp(-days_since_access / 60)`
- Caps at 20 accesses (diminishing returns)
- 60-day half-life on the access signal
- Max ~15% boost for frequently-accessed recently-used notes
- Decays to ~1.0 if note stops being accessed

### Where to inject
Post-RRF merge, same as recency boost — multiply each result's final score by access boost.
This keeps BM25 and semantic scoring pure, with boosts applied as post-processing.

### Migration safety
Add columns with DEFAULT values — no data loss, backward compatible. Existing notes start
with access_count=0 and last_accessed_at=NULL (treated as "never accessed" = boost of 1.0).
</decisions>

<canonical_refs>
## Canonical References

### Source files to modify
- `engine/db.py` — schema migration: add columns to `notes` table
- `engine/search.py` — add `_access_boost()` and inject into ranking pipeline
- `engine/mcp_server.py` — update `sb_read`, `sb_search`, `sb_person_context` to track access
- `engine/api.py` — update note-serving endpoints to track access

### Source files to read
- `engine/search.py` — understand `_recency_multiplier()` pattern and RRF merge
- `engine/db.py` — current schema, migration pattern (add-column functions)
- `engine/mcp_server.py` — current `sb_read`, `sb_search` implementations
</canonical_refs>

<deferred>
## Deferred Ideas

- Per-type access weighting (decision notes vs meeting notes) → Phase 51
- Access pattern analytics (most/least accessed notes dashboard) → future
- Search result click-through tracking (which rank position was clicked) → future
</deferred>

---

*Phase: 50-retrieval-reinforcement-learning-from-use*
*Context gathered: 2026-04-01*
