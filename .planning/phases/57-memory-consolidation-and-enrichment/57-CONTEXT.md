# Phase 57: Memory Consolidation & Enrichment

**Gathered:** 2026-04-17
**Status:** Ready for planning (depends on 54; benefits from 50-53)

<domain>
## Phase Boundary

Add a memory consolidation lifecycle to the brain: capture-time similarity awareness,
AI-assisted note enrichment (update-in-place instead of creating duplicates), nightly
consolidation sweep that detects merge/enrich/stale candidates, and user-facing tools
to review and act on consolidation suggestions.

### Problem

Notes accumulate as isolated fragments. When the user captures information about a topic
they've already captured before, the brain creates a second note instead of enriching the
existing one. After 10 captures about "Project X", there are 10 separate notes — search
returns fragments, the graph is scattered, and knowledge doesn't compound.

Phase 54 added synthesis (creating new summary notes alongside originals). This phase
is the complement: **maintaining and evolving the original notes themselves**.

Current gaps:
1. **No enrichment path** — capture always creates; never updates existing notes
2. **Crude merge quality** — `merge_notes()` concatenates bodies with `---` separator.
   Two notes about a meeting become one note with a visible seam, not a coherent document.
3. **Frontmatter lost on merge** — only the kept note's frontmatter survives; the
   discarded note's people, tags, and metadata in YAML frontmatter are lost
4. **Inline backlinks break** — if Note C mentions Note B by path in its body text
   (`[[meetings/standup]]`), merging B into A leaves a dead reference in C
5. **Synthesis source_notes go stale** — synthesis notes reference source paths in
   frontmatter; merged/moved sources break the reference chain
6. **No candidate queueing** — the nightly job detects duplicates and clusters but has
   no staging area for merge/enrich candidates between detection and user action
7. **No stale-note lifecycle** — stale notes are surfaced as nudges but nothing happens;
   no review queue, no archive, no enrichment suggestion

### Scope
- New `enrich_note()` function: AI-assisted content merge (not concatenation)
- Capture-time similarity detection: after writing, check for similar existing notes
- `consolidation_queue` DB table: staging area for merge/enrich/review candidates
- Extend nightly `consolidate_main()`: enrichment sweep + stale review + backlink repair
- Upgrade `merge_notes()`: frontmatter merge + backlink repair + synthesis ref repair
- New MCP tools: `sb_enrich`, `sb_consolidation_review`
- Comprehensive test coverage for all consolidation paths
</domain>

<decisions>
## Implementation Decisions

### AI provider for merge/enrich

**Interactive (MCP tool calls):** Use existing ModelRouter adapter — routes to whatever
is configured (Ollama, Groq, etc.). User is in a conversation; latency acceptable.

**Nightly cron job:** Must use local Ollama only. No API key available in launchd context,
no network dependency for a 03:00 background job. Use the same `_router.get_adapter("public")`
path that Phase 54 synthesis already uses. If Ollama is unavailable, queue candidates
for later review instead of failing.

### enrich_note() function

```python
def enrich_note(existing_path: str, new_content: str, conn, adapter=None) -> dict:
    """Integrate new_content into an existing note using AI-assisted merge.

    Returns: {"path": str, "before_length": int, "after_length": int, "enriched": bool}
    """
```

Behavior:
- Read existing note body and frontmatter
- AI prompt: "Update this note by integrating new information. Preserve all existing
  facts. Add new information naturally. Don't duplicate. Maintain the note's style and
  structure."
- Update note body in place (DB + disk via atomic write)
- Re-generate embedding for the updated note
- Rebuild FTS5 entry
- Write audit log entry (type="enriched", detail=before/after lengths)
- If AI adapter unavailable: fall back to structured append (heading + new content)
  rather than crude `---` concatenation

### Session ID as enrichment handle

Phase 56 introduced `capture_session` (persisted UUID grouping notes from a conversation).
Phase 57 should use this as an enrichment handle: when `sb_enrich` or
`sb_consolidation_review` processes a note, it can find all notes in the same session
and offer to consolidate them into a richer document. This also enables "update existing
context" — pass a session_id to find all prior captures in that thread, then enrich
the most relevant one instead of creating a new note.

### Capture-time similarity detection

**Approach:** Capture-then-suggest (not block-and-ask). Zero-friction capture preserved.

1. `capture_note()` writes the note as usual (unchanged)
2. After write: run `find_similar(new_path, threshold=0.80, limit=3)`
3. If matches found: include in the return dict:
   `{"similar": [{"path": p, "title": t, "similarity": s}]}`
4. The MCP tool (`sb_capture`, `sb_capture_smart`) surfaces this as a hint:
   "Similar note found: {title} ({similarity}%). Use sb_enrich to combine."
5. Latency: ~200ms (one embedding lookup + KNN). Acceptable for MCP flow.
6. No blocking, no automatic merging — user decides.

### consolidation_queue table

```sql
CREATE TABLE IF NOT EXISTS consolidation_queue (
    id INTEGER PRIMARY KEY,
    action TEXT NOT NULL,          -- 'merge', 'enrich', 'review', 'stale'
    source_paths TEXT NOT NULL,    -- JSON array of note paths
    target_path TEXT,              -- suggested merge target (nullable)
    reason TEXT,                   -- human-readable explanation
    similarity REAL,              -- cosine similarity score (nullable)
    detected_at TEXT NOT NULL,    -- ISO 8601 timestamp
    status TEXT DEFAULT 'pending', -- 'pending', 'accepted', 'dismissed'
    resolved_at TEXT              -- when accepted/dismissed
);
```

Dismissed items tracked so nightly job doesn't re-queue them (same pattern as
`dismissed_inbox_items` for duplicates).

### Enhanced nightly consolidation

Extend `consolidate_main()` with three new steps (after existing hygiene + synthesis):

1. **enrichment_sweep()**: Find note pairs with similarity 0.80-0.92 (below duplicate
   threshold of 0.92, above noise). Group by shared person/project/tag. Queue as
   action='enrich' in consolidation_queue. Skip already-dismissed pairs.

2. **stale_review()**: Notes not updated in 90+ days AND access_count < 3 (if Phase 50
   tracking exists, else just age). Queue as action='stale'. These are candidates for
   review — not auto-deletion.

3. **backlink_repair()**: Scan body text for `[[path]]` wiki-link references where the
   target path no longer exists in the notes table. If the target was merged (check audit
   log for type='merged'), find the merge target and update the reference. Otherwise flag
   as broken for review.

All three steps: local Ollama only, graceful degradation if unavailable, idempotent.

### Upgraded merge_notes()

Extend existing `brain_health.py:merge_notes()`:

1. **Frontmatter merge**: Union of people lists, tag lists, and any list-type frontmatter
   fields. For scalar fields (title, type, sensitivity): keep the target note's values.
   For `created_at`: use the earlier date. For `updated_at`: use now.

2. **Body merge quality**: Before concatenation, call `enrich_note()` if AI adapter is
   available. Fall back to current `---` separator approach if AI unavailable.

3. **Backlink repair**: After merge, scan all notes' bodies for `[[discarded_path]]`
   references and replace with `[[kept_path]]`. Do the same for `source_notes` arrays
   in synthesis note frontmatter.

4. **Relationship merge**: Already handled (remapping). No change needed.

### New MCP tools

**`sb_enrich(target_path: str, new_content: str) -> dict`**
Enrich an existing note with new content using AI-assisted merge.
Returns: updated note path, before/after stats, success flag.

**`sb_consolidation_review(action: str = "all", limit: int = 10) -> dict`**
Review pending consolidation candidates.
- Returns: list of queued items with paths, reason, similarity score
- Actions: filter by 'merge', 'enrich', 'stale', or 'all'
- Follow-up: user calls `sb_enrich` or existing `sb_merge` to act, or dismisses

No two-step confirmation needed for `sb_enrich` (non-destructive — it updates, doesn't
delete). The existing `sb_forget` pattern handles destructive ops.

### Testing strategy

Each plan must include:
- Unit tests for the new function with mocked AI adapter
- Integration tests with real DB (test fixtures, in-memory SQLite)
- Edge cases: empty notes, notes with no frontmatter, notes with no embedding,
  broken wiki-links, Ollama unavailable, concurrent merges
- Graph integrity assertions: after every merge/enrich, verify:
  - All relationships point to existing notes
  - No orphaned entries in note_people, note_tags, note_embeddings
  - FTS5 index consistent with notes table
  - No dead wiki-links introduced
- Performance: enrich/merge within perf budget (track via sb-perf framework)

### Where it plugs in

1. `engine/intelligence.py` — `enrich_note()` function
2. `engine/brain_health.py` — upgraded `merge_notes()` with frontmatter + backlink repair
3. `engine/consolidate.py` — enrichment_sweep, stale_review, backlink_repair in nightly job
4. `engine/capture.py` — similarity hint after capture
5. `engine/mcp_server.py` — `sb_enrich`, `sb_consolidation_review` tools
6. `engine/db.py` — consolidation_queue migration
7. `tests/test_consolidation.py` — new test module for full consolidation lifecycle
8. `tests/test_enrich.py` — enrich function unit + integration tests
</decisions>

<canonical_refs>
## Canonical References

### Source files to modify
- `engine/intelligence.py` — add `enrich_note()` function
- `engine/brain_health.py` — upgrade `merge_notes()` (frontmatter, backlinks, synthesis refs)
- `engine/consolidate.py` — add enrichment_sweep, stale_review, backlink_repair to nightly job
- `engine/capture.py` — add similarity hint after capture_note()
- `engine/mcp_server.py` — add `sb_enrich`, `sb_consolidation_review` MCP tools
- `engine/db.py` — add consolidation_queue table migration

### Source files to read
- `engine/consolidate.py` — current `consolidate_main()` + `synthesize_clusters()`
- `engine/brain_health.py` — current `merge_notes()`, `get_duplicate_candidates()`
- `engine/intelligence.py` — `find_similar()`, `cluster_recent_notes()`, `check_stale_nudge()`
- `engine/capture.py` — `capture_note()`, `write_note_atomic()`
- `engine/mcp_server.py` — `sb_capture`, `sb_capture_smart` for response format
- `engine/search.py` — FTS5 rebuild patterns
- `engine/db.py` — migration patterns, `dismissed_inbox_items` table for dismissed-pair pattern

### Dependencies
- Phase 54: consolidation + synthesis layer (must be complete — we extend it)
- Phase 50: access_count for stale detection heuristic (optional — degrade gracefully)
- Phase 51: temporal decay for relevance scoring (optional)
- Phase 52: graph traversal for richer candidate detection (optional)
- Phase 53: proactive surfacing (optional — enrich suggestions could feed into surfacing)
</canonical_refs>

<deferred>
## Deferred Ideas

- Auto-enrich on capture (skip user approval) for very high similarity (>0.95) → risky, defer
- Scheduled CronCreate job for weekly consolidation review notification → future
- GUI consolidation dashboard: visual merge preview, drag-and-drop merge → future
- Cross-note fact extraction: structured knowledge graph from unstructured notes → future
- Confidence scoring: track how many enrichments a note has received → future
- Undo enrichment: snapshot before enrich, allow revert → future (audit log has before state)
</deferred>

---

*Phase: 57-memory-consolidation-and-enrichment*
*Context gathered: 2026-04-17*
