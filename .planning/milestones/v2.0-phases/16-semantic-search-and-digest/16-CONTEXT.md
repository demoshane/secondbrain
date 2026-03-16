# Phase 16: Semantic Search and Digest - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade `sb-search` with vector/hybrid search, add `sb-recap <name>` for cross-context synthesis across all notes about a person or topic, and auto-generate weekly digests to `.meta/digests/`. Creating/modifying notes, GUI, and MCP are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Hybrid search output
- Default `sb-search` (no flags) = hybrid BM25 + vector via RRF; output looks identical to today (ranked list, no source indicator or score shown)
- `--keyword` flag added for pure BM25 bypass (exact/literal match use case)
- `--semantic` flag retained for pure vector-only queries
- Default result limit: 20 (no change from current FTS5 default)
- Three modes: `sb-search` (hybrid), `sb-search --semantic` (pure vector), `sb-search --keyword` (pure BM25)

### sb-recap <name> scope
- Works for both people AND projects/topics (unified command, any entity name)
- Source notes: full-brain search — all notes mentioning the name via FTS + semantic match
- Context window: top 20 most semantically relevant notes
- Output structure: narrative summary + open action items (prose + bullet actions)
- PII routing: Ollama for PII, Claude for non-PII (per SRCH-04)

### Digest content and format
- **Trigger**: both automatic (launchd weekly) AND on-demand (`sb-digest` command)
- **Sections**: Key Themes, Open Actions, Stale Notes, Captures This Week
- **Format**: Structured Markdown with YAML frontmatter (`title`, `date`, `type: digest`)
- **File naming**: `YYYY-WNN.md` (e.g. `2026-W11.md`) in `.meta/digests/`
- **Readable via**: `sb-read --digest latest`
- PII summaries via Ollama, non-PII via Claude

### Semantic fallback
- **Missing embeddings at query time**: generate on the fly (up to 50 notes); if >50 unembed, warn and suggest `sb-reindex`
- **No embeddings in DB at all**: hybrid silently falls back to pure FTS5 + shows notification: "Semantic unavailable. Run sb-reindex to enable."
- **`sb-recap <name>` entity not found**: graceful empty state — "No notes found about 'alice'. Capture a meeting or note to build context."

### Claude's Discretion
- RRF fusion weights (BM25 vs vector score balance)
- launchd schedule day/time for weekly digest (e.g. Monday 08:00)
- Exact wording of Key Themes synthesis prompt
- `sb-digest` CLI verb and flag design

</decisions>

<specifics>
## Specific Ideas

- Digest format approved by user: frontmatter + `## Key Themes`, `## Open Actions`, `## Stale Notes`, `## Captures This Week` — exactly as shown in the preview mockup
- `sb-recap` should work for "onboarding" (topic) just as well as "alice" (person)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/search.py`: `search_notes(conn, query, note_type, limit)` — FTS5 BM25; extend to accept `mode` param or call alongside vector path
- `engine/embeddings.py`: `embed_texts(texts, provider)` — already handles lazy-load and provider routing; use for on-the-fly embedding at query time
- `engine/reindex.py`: `embed_pass(conn, provider, batch_size, force)` — reuse for the on-the-fly batch (≤50)
- `engine/intelligence.py`: `recap_main()` — session recap exists; add `recap_entity(name)` alongside it

### Established Patterns
- PII routing: `engine/router.py` / `engine/ai.py` — use same pattern for digest and recap synthesis
- Audit log: `search_notes` already inserts audit rows; continue for semantic queries
- Frontmatter + Markdown: standard note format applies to digest files; use `engine/templates.py` if templates exist

### Integration Points
- `sb-search` CLI entry point — add `--semantic` (already planned?) and `--keyword` flags, change default to call hybrid
- `sb-recap` — currently no-args session recap in `intelligence.py`; add name argument branch
- `sb-reindex` launchd plist — add second weekly plist for digest generation (or add `--digest` flag to existing job)
- `.meta/digests/` — new directory, create on first run

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-semantic-search-and-digest*
*Context gathered: 2026-03-15*
