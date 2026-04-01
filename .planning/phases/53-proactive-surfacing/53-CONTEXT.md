# Phase 53: Proactive Surfacing

**Gathered:** 2026-04-01
**Status:** Ready for planning (depends on 50, 51; benefits from 52)

<domain>
## Phase Boundary

Make the brain a participant, not a filing cabinet. New MCP tool `sb_surface` takes
conversation context and returns notes the user didn't ask for but should see. Extends
existing dormant resurfacing pattern (capture-time only) to work anytime.

### Problem
All retrieval is user-initiated: explicit search, explicit read, explicit person lookup.
The system never says "hey, this is relevant to what you're discussing." The dormant
resurfacing at capture time (`find_dormant_related()` in intelligence.py) proves the
pattern works — it just only fires on capture, not during conversation.

### Scope
- New MCP tool: `sb_surface(context: str, max_results: int = 5)` — semantic similarity
  against provided context, boosted by access patterns (Phase 50) and decay (Phase 51)
- Enhance existing tools with optional `context_hint` parameter for ambient suggestions
- Use audit_log recent entries to build session context automatically
- Apply graph traversal (Phase 52) to expand surface results beyond direct matches
</domain>

<decisions>
## Implementation Decisions

### Primary tool: sb_surface
```python
sb_surface(context: str, max_results: int = 5, include_graph: bool = True) -> dict
```
- `context`: free-text describing what's being discussed (Claude provides this)
- Runs semantic search against context
- Filters out notes already surfaced in this session (via audit_log)
- Applies Phase 50 access boost + Phase 51 decay scoring
- If `include_graph`: follows 1-hop graph links from top results (Phase 52) to find
  related notes that aren't semantically similar but are associatively connected
- Returns: `{"suggestions": [{"path", "title", "snippet", "relevance_score", "reason"}]}`

### Session dedup via audit log
Query recent `mcp_read` and `mcp_search` audit entries (last 30 min) to avoid
re-surfacing notes the user already saw. This makes surfacing non-repetitive.

### Context-hint on existing tools
Add optional `context_hint: str | None` to `sb_search` and `sb_recap`. When provided,
append a `"proactive_suggestions"` field to the response with 2-3 contextually related
notes that weren't in the primary results.

### Dormant bonus integration
Extend `find_dormant_related()` pattern: notes not updated in 30+ days with 0.5+
similarity get a "dormant" tag in suggestions, signaling "forgotten but relevant."

### When Claude should call sb_surface
Document in tool description: "Call this when starting a new topic, when the user mentions
a person/project, or when you sense the conversation could benefit from historical context."
Claude's judgment drives the trigger — no automatic invocation.
</decisions>

<canonical_refs>
## Canonical References

### Source files to modify
- `engine/mcp_server.py` — add `sb_surface` tool, add `context_hint` to `sb_search`
- `engine/intelligence.py` — extract `find_dormant_related()` into reusable function,
  add `surface_relevant()` function
- `engine/search.py` — add `search_with_boosts()` that applies access + decay scoring

### Source files to read
- `engine/mcp_server.py` — current tool implementations, dormant note pattern in sb_capture
- `engine/intelligence.py:403+` — `find_dormant_related()` implementation
- `engine/search.py` — semantic search, RRF merge
- `engine/db.py` — audit_log table for session dedup

### Dependencies
- Phase 50: access tracking (access_count, last_accessed_at columns)
- Phase 51: decay scoring (_relevance_decay function)
- Phase 52: graph traversal (traverse_graph function) — optional but enriches results
</canonical_refs>

<deferred>
## Deferred Ideas

- Auto-surface on MCP tool calls (middleware that checks context on every call) → future
- Confidence calibration (track if surfaced notes were actually useful) → future
- "Surprise" scoring — prefer notes user wouldn't have found themselves → future
</deferred>

---

*Phase: 53-proactive-surfacing*
*Context gathered: 2026-04-01*
