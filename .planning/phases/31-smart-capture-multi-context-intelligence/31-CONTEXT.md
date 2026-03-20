# Phase 31: Smart Capture & Multi-Context Intelligence - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Accept raw freeform text (meeting notes, conversation dumps, mixed content) via `sb_capture_smart` and intelligently segment it into multiple typed, linked notes. Resolve existing entities instead of duplicating. Create stubs for new entities. Resurface dormant related knowledge after capture. Improve dedup handling. Add sensitivity auto-classification. Run intelligence hooks asynchronously post-capture.

</domain>

<decisions>
## Implementation Decisions

### Segmentation strategy
- Two-pass heuristic: structural markers first (headings, `---`, date/time stamps, `RE:`, `Subject:` patterns, bullet list starts), then name-cluster detection for unstructured prose
- Short segments (<50 chars or <2 lines) merge into previous segment
- Maximum 20 notes per single `sb_capture_smart` call; if more, merge smallest segments until under limit
- URLs detected in blob become `type='link'` notes via existing `link_capture.py`; code blocks and tables stay inline in parent segment

### Entity resolution
- Link to existing notes, don't create duplicates. FTS5 + fuzzy match against existing person/project notes
- Auto-create minimal stub notes (title + type + empty body) for genuinely new entities not found in brain
- All segments from one input share a `capture_session: <uuid>` frontmatter field + `co-captured` relationships between them

### Save policy
- Auto-save via MCP: no confirm token round-trip. Segments + stubs + links saved atomically. Response returns what was created.
- Action items found in segments: keep inline in note body AND extract to `action_items` table (double-visibility)

### Dedup & near-duplicate policy
- Three-path heuristic when near-duplicate found (>threshold similarity):
  1. **Superset**: new content is longer and contains existing key phrases → update existing note, append changelog section
  2. **Complementary**: different angle on same topic → save as new note + create `similar` relationship
  3. **Ambiguous**: return both options in response for caller to decide
- Changelog format appended to updated notes: `## Changelog` section with date, action, previous content hash
- `sb_capture_batch` dedup checks each note against brain AND against earlier notes in same batch (intra-batch dedup)
- Similarity threshold configurable in `.meta/config.toml` (default 0.92)

### Dormant resurfacing
- MCP response only (sb_capture + sb_capture_smart). Not in GUI inbox or recap.
- Dormant = `updated_at` older than 30 days
- Ranked by semantic similarity (embedding cosine) to just-captured content
- Up to 3 dormant notes returned per capture call

### Sensitivity auto-classify
- Three tiers: `public` / `private` / `pii`
- Entity-based PII detection only: phone numbers, email addresses, national ID patterns (Finnish hetu, SSN), credit card numbers. No keyword scanning.
- Classify per-segment individually (not blob-level)
- Never-downgrade rule: if classifier says `pii` and user says `public`, `pii` wins
- Silent upgrade + note in response: `'Sensitivity upgraded to pii (detected: phone number)'`

### Async intelligence hooks (CAP-06)
- Background daemon thread spawned after capture returns
- Runs action item extraction + connection detection on just-saved notes
- Error isolation: catch all exceptions, log to `audit_log` with `type='intelligence_error'`. Never surface to user.

### Configuration
- Segmentation config stored in `.meta/config.toml` with sensible defaults
- Dedup similarity threshold in same config file
- GUI settings page to expose these is a future phase (deferred)

### Performance
- Target: <5 seconds total for sb_capture_smart (segmentation + entity resolution + dedup + dormant search + save)
- Performance regression test with synthetic brain (~500 notes + embeddings), assert <5s

### Testing
- Synthetic test fixtures for unit tests (each heuristic path in isolation)
- Golden path end-to-end test with flexible assertions (ranges: 3-5 notes, at least 1 relationship, at least 2 action items)
- Performance regression test as described above

### Claude's Discretion
- Exact heuristic weights for topic-shift detection
- Fuzzy match threshold for entity resolution
- Internal data structures for segment processing
- Background thread implementation details

</decisions>

<specifics>
## Specific Ideas

- "Brain should be able to process/combine memories to stay coherent" — captured as Phase 35 (Brain Consolidation)
- Segmentation should handle real-world messiness: pasted emails, chat logs, mixed-format meeting notes
- Config in `.meta/config.toml` is the backend foundation for a future GUI settings page

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/mcp_server.py:sb_capture_smart()` — existing basic classifier (double-newline split, regex-based type detection). Needs major upgrade but structure is there.
- `engine/mcp_server.py:sb_capture_batch()` — per-note try/except isolation pattern. Reuse for atomic multi-note save.
- `engine/embeddings.py:embed_texts()` — embedding dispatch for dormant similarity search
- `engine/link_capture.py:fetch_link_metadata()` — URL-to-link-note pipeline for detected URLs
- `engine/entities.py:extract_entities()` — entity extraction (people, orgs, topics) for entity resolution
- `engine/intelligence.py:extract_action_items()` — action item extraction for async hooks
- `engine/search.py:find_similar()` — cosine similarity search for dedup and dormant resurfacing

### Established Patterns
- Two-step confirm token pattern (existing but being removed for smart capture — auto-save instead)
- `capture_note()` is the single write path — all segments must flow through it
- `write_note_atomic()` with `url=` keyword-only param pattern
- `get_connection(db_path)` for test isolation
- xfail(strict=False) for stub tests that auto-promote

### Integration Points
- `.meta/config.toml` — already exists for brain config; add segmentation + dedup sections
- `audit_log` table — intelligence error logging
- `relationships` table — co-captured, similar relationship types
- `action_items` table — extracted action items from segments
- People column (JSON) — entity resolution source of truth (Phase 30)

</code_context>

<deferred>
## Deferred Ideas

- **GUI settings page**: expose `.meta/config.toml` settings (segmentation, dedup threshold) in a GUI settings tab. First settings UI for the app.
- **Brain consolidation / "brain sleep"** (Phase 35): periodic scanning to merge near-duplicates, enrich stubs, clean orphan relationships, track health trends over time. Prevents knowledge fragmentation as brain grows.
- **Performance optimization of existing tools**: broader speed-up effort beyond Phase 31's smart capture path. Covered by Phase 33.

</deferred>

---

*Phase: 31-smart-capture-multi-context-intelligence*
*Context gathered: 2026-03-20*
