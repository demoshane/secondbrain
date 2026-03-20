# Phase 30: People Graph Hardening - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix entity extraction for non-ASCII names, consolidate people detection to a single source of truth (people column), remove body-mention fallback, enhance sb_person_context, and update PeoplePage to reflect improvements. Requirements: PEO-01, PEO-02, PEO-03, PEO-04.

</domain>

<decisions>
## Implementation Decisions

### Unicode Entity Extraction (PEO-01)
- Replace ASCII-only `[A-Z][a-z]+` regex with Unicode-aware pattern covering Extended Latin (Finnish, Nordic, French, Spanish, Portuguese, German)
- Support compound names: van/von/de/di/la/el prefixes, O' prefix, hyphens (e.g., Mäki-Petäjä)
- Two-word minimum for extraction; single-word names resolve silently against existing person notes (best-effort, no user prompts)
- No abbreviated name matching (T. Leppänen, Tuomas L.) — too ambiguous
- Add Finnish stop words to reduce false positives alongside existing English stop words
- Add organization name extraction to entities.py while touching the file (new entity type alongside people, places, topics)
- Title and body processed separately (preserve Phase 27.1 decision — no cross-boundary bigrams)

### People Column Write-Back (PEO-02)
- People column populated from entity extraction at capture time (replaces manual-only population)
- Full reindex of all existing notes — replace people column with fresh extraction results (not merge)
- Also update entities JSON column during reindex (full re-extraction: people, places, topics, orgs)
- Extend `sb-reindex` command with `--entities` flag for reusable entity re-extraction
- Body-mention fallback in `note_meta()` (api.py:729-740) removed entirely — people column is the single source of truth
- Body-mention scan in `sb_person_context` (mcp_server.py) also removed — use people column lookups
- Add a generated column + index on people column for faster JSON LIKE queries

### sb_person_context Enhancements (PEO-03)
- All sections ordered chronologically: meetings by date (newest first), mentions by created_at, actions by due_date then created_at
- Switch from body-scan to people-column lookup for finding mentions (consistent single source of truth)
- Accept both name string and path as input — if input contains `/`, use path lookup; otherwise fuzzy-match against person note titles
- Add organization field (extracted from person note entities) and last_interaction timestamp (max created_at of mentioning notes)
- Add relationship metrics: total_meetings, total_mentions, total_actions, last_interaction_date
- New `sb_list_people` MCP tool — returns all person notes with open_actions, org, last_interaction, mention_count

### Frontend & API Updates (PEO-04)
- Update PeoplePage to reflect extraction improvements
- Fix meeting detection (currently fragile path string match `/meetings/`)
- Enrich `/people` API: add org, last_interaction, mention_count fields
- PeoplePage left pane table columns: Name, Org, Last Interaction, Open Actions
- Regression tests for person type isolation and people column accuracy

### Claude's Discretion
- Exact Unicode regex pattern (as long as it covers Extended Latin + compound names)
- Finnish stop word list composition (derive from brain content analysis)
- Organization extraction heuristics (regex patterns, known-org list approach)
- Generated column implementation details for people index
- PeoplePage detail pane layout adjustments

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/entities.py`: `extract_entities()` (line 13-34) — main target for Unicode fix; `_extract_people()` (line 37-45) needs regex rewrite
- `engine/capture.py`: `capture_note()` (line 375-472) and `write_note_atomic()` (line 187-203) — people write path exists, needs extraction integration
- `engine/mcp_server.py`: `sb_person_context()` (line 798-879) — already functional, needs column-based lookup swap and enrichment
- `engine/reindex.py`: `sb-reindex` command — extend with `--entities` flag
- `frontend/src/components/PeoplePage.tsx` — split-pane layout ready, needs column additions

### Established Patterns
- `json.dumps()/json.loads()` with `[]` fallback for people column (capture.py, intelligence.py)
- `get_connection(db_path)` for test isolation (Phase 27.1 pattern)
- `ALTER TABLE ADD COLUMN` migrations in db.py with try/except for idempotency
- `conn.row_factory = sqlite3.Row` set locally per function (Phase 28 pattern)
- xfail(strict=False) for TDD stubs that auto-promote

### Integration Points
- `api.py` `note_meta()` (line 658-743): remove body-mention fallback (lines 729-740)
- `api.py` `list_people()` (line 249-259): add org, last_interaction, mention_count
- `db.py` `init_schema()`: add generated column migration for people index
- `mcp_server.py`: add `sb_list_people` tool alongside existing `sb_person_context`
- `frontend/src/types.ts`: extend PersonSummary type with new fields

</code_context>

<specifics>
## Specific Ideas

- People column becomes THE source of truth — no fallbacks, no body scanning
- sb_person_context should feel like a CRM lookup: "tell me everything about this person"
- PeoplePage table should give CRM-like overview: who, where they work, when you last interacted, what's pending
- Organization extraction enables future features (company pages, org charts)

</specifics>

<deferred>
## Deferred Ideas

- `sb_person_edit` MCP tool (direct person note editing) — future phase
- People merge/dedup tool (handle duplicate person notes) — future phase
- Company/organization pages in GUI — future phase
- Relationship graph visualization — future phase
- People extraction from calendar events — out of scope (no calendar sync)

</deferred>

---

*Phase: 30-people-graph-hardening*
*Context gathered: 2026-03-20*
