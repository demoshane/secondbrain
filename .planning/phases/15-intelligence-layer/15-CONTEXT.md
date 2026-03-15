# Phase 15: Intelligence Layer - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver four proactive intelligence features — session recap (`sb-recap`), action item extraction + tracking (`sb-actions`), stale note nudges, and connection suggestions on capture — all sharing a single daily notification budget. New CLI entry points: `sb-recap`, `sb-actions`. No GUI, no digest (Phase 16), no semantic search (Phase 16).

</domain>

<decisions>
## Implementation Decisions

### Session context detection
- Auto-detect context from current git repo name (`git rev-parse --show-toplevel` + basename)
- Outside a git repo: `sb-recap` requires an explicit name argument (`sb-recap "Alice"`, `sb-recap "Acme project"`)
- Proactive INTL-01 session offer (once-per-day) lives in `~/.claude/CLAUDE.md` — existing file, follows established pattern
- `sb-recap` without args in a non-git dir prints: `"No context detected — try sb-recap <name>"`
- Recap summarizes notes tagged or linked to the detected context name

### Action item extraction
- LLM extraction via existing AI adapter at capture time — handles natural language commitments
- PII note extraction routes through Ollama automatically (existing ModelRouter applies)
- Extract from **all note types** (not just meetings — any note can contain commitments)
- Store in a new `action_items` table in `brain.db`
  - Schema: `id INTEGER PK, note_path TEXT, text TEXT, done BOOL DEFAULT 0, created_at TEXT`
- `sb-actions` default output: all open items, newest first — columns: ID | text | source note | date
- `sb-actions --done <id>` marks an item complete

### Notification budget mechanics
- "Session" = calendar day; budget resets at midnight
- State persisted in `~/.meta/intelligence_state.json` (already decided in roadmap)
- Vault gate: 20 notes minimum before any proactive offer fires (already decided)
- Priority order when multiple features compete for the daily slot: **Recap > connection suggestion > stale nudge**
- Proactive offers only fire from `sb-capture` and `sb-search` — not from maintenance commands (reindex, export, forget, etc.)
- Explicit commands (`sb-recap`, `sb-actions`) always work on-demand — budget only gates **unsolicited** inline offers

### Connection suggestions
- After `sb-capture`: run KNN query against `note_embeddings` for cosine similarity > 0.8
- Show top 3 matching notes as notification lines before prompt returns
- Auto-append `Related: [[note-title]]` to the **new note only** (one-directional; existing notes not modified)
- If embeddings table is empty or missing: silently skip — no error, no hint
- Connection suggestion consumes the daily proactive slot (second priority after recap)

### Stale nudge behavior
- Notes not accessed/updated in 90 days surface as nudges (max 5 per session as per INTL-06)
- Notes with `evergreen: true` frontmatter are exempt
- Stale nudge rechecks at 180 days if not acted on (INTL-08)
- Fires from `sb-search` and `sb-capture` — lowest priority in budget

### Claude's Discretion
- Exact LLM prompt for action item extraction
- `intelligence_state.json` schema (fields, versioning)
- How `sb-recap` generates the summary (prompt structure, note count limit)
- Exact output formatting for `sb-actions` list (spacing, truncation)
- Stale note selection algorithm (oldest first, random sample, or by category)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/capture.py`: Primary integration point for connection suggestions and action item extraction — both fire at end of capture flow
- `engine/search.py`: Integration point for stale nudge check (fires from `sb-search`)
- `engine/db.py:init_schema()`: `action_items` DDL added here; follow `migrate_add_people_column()` pattern for idempotent migration
- `engine/ai.py`: Existing AI adapter — LLM action item extraction prompt goes here
- `engine/embeddings.py`: KNN similarity query for connection suggestions — expose a `find_similar(note_path, threshold, limit)` function
- `engine/router.py`: ModelRouter already handles PII routing — no new bypass needed for action item extraction

### Established Patterns
- Atomic writes: `conn.commit()` after each batch; rollback on error
- `pathlib.Path` throughout — no `os.path`
- `engine/paths.py` for `BRAIN_ROOT`, `DB_PATH` — use these constants
- `~/.meta/` for system metadata files (intelligence_state.json goes here)
- Session state pattern: read JSON → check → write JSON (same as future digest scheduler)

### Integration Points
- `pyproject.toml [project.scripts]`: Add `sb-recap = "engine.intelligence:recap_main"` and `sb-actions = "engine.intelligence:actions_main"`
- `engine/capture.py`: Call `check_connections()` and `extract_action_items()` after successful write+index
- `engine/search.py`: Call `check_stale_nudge()` at end of search if budget available
- `~/.claude/CLAUDE.md`: Add one-line session hook for proactive recap offer

</code_context>

<specifics>
## Specific Ideas

- Budget check pattern: read `intelligence_state.json` → check `last_offer_date` vs today → if same day, skip; if different, fire and update
- `sb-recap` with repo context: search notes where tags or `people`/project fields contain the context name, then summarize via LLM
- Connection backlink format: append `\nRelated: [[{matched_note_stem}]]` to new note body (matches existing backlink convention in codebase)

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-intelligence-layer*
*Context gathered: 2026-03-15*
