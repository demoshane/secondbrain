# Phase 54: Consolidation & Synthesis Layer

**Gathered:** 2026-04-01
**Status:** Ready for planning (depends on 50-52; benefits from 53)

<domain>
## Phase Boundary

Add a periodic "sleep" process that synthesizes recent notes into higher-order knowledge:
clusters meeting notes into project trajectories, detects contradictions, compresses detail
while preserving insight. Runs as extension of existing nightly consolidation job.

### Problem
Notes accumulate forever but are never distilled. After 4 meetings about ProjectX, you
have 4 separate meeting notes — but no synthesis of "where is ProjectX headed?" The
existing `consolidate_main()` handles hygiene only (archiving old items, cleaning dangling
relationships). `generate_weekly_synthesis()` exists in intelligence.py but is never
called automatically.

### Scope
- Extend `consolidate_main()` with synthesis phase (runs after hygiene, ~03:30 UTC)
- Cluster recent notes by person/project/topic using junction tables + embeddings
- Generate synthesis notes (new note type) for clusters with 3+ notes in 7-day window
- Detect contradictions between notes (e.g., conflicting deadlines)
- Store synthesis notes in `syntheses/` subfolder as first-class notes
- New MCP tool: `sb_insights` — surface recent synthesis and contradictions
</domain>

<decisions>
## Implementation Decisions

### Synthesis trigger
Cluster criteria: 3+ notes sharing a person OR tag within a 7-day window.
Use `note_people` and `note_tags` junction tables for grouping.
Semantic similarity (0.6+ threshold) as secondary signal for notes without shared metadata.

### Synthesis note format
```yaml
---
type: synthesis
title: "ProjectX — Week of 2026-03-31"
tags: [projectx, auto-synthesized]
people: [person/alice.md, person/bob.md]
source_notes: [meetings/m1.md, meetings/m2.md, notes/n3.md]
created_at: 2026-04-01T03:30:00Z
---
## Summary
[AI-generated synthesis of the cluster]

## Key Decisions
[Extracted from source notes]

## Open Questions
[Contradictions or unresolved items]

## Action Items
[Aggregated from source notes]
```

### AI provider
Use existing Ollama adapter (same as entity extraction, person insights).
Model: whatever is configured in config.toml. Falls back gracefully if Ollama unavailable.

### Contradiction detection
Compare extracted facts (deadlines, decisions, status) across cluster notes.
Simple heuristic: if two notes in a cluster mention different dates for the same entity,
flag as contradiction. AI-assisted for nuanced conflicts.

### Dedup protection
Before generating synthesis, check if a synthesis note already exists for this cluster
(same source_notes set within 7 days). Skip if found. Tag with `auto-synthesized` for
easy filtering.

### New MCP tool
```python
sb_insights(days: int = 7) -> dict
# Returns recent synthesis notes + any detected contradictions
```

### Where it plugs in
1. `consolidate_main()` calls new `synthesize_clusters()` after existing hygiene steps
2. `synthesize_clusters()` lives in `engine/consolidate.py` (extends existing module)
3. Uses `write_note_atomic()` from capture pipeline for safe note creation
4. Synthesis notes indexed like any other note — searchable, linkable, show in GUI
</decisions>

<canonical_refs>
## Canonical References

### Source files to modify
- `engine/consolidate.py` — add `synthesize_clusters()` to consolidation pipeline
- `engine/intelligence.py` — add cluster detection, contradiction checking
- `engine/mcp_server.py` — add `sb_insights` tool
- `engine/capture.py` — ensure `write_note_atomic()` handles type="synthesis"

### Source files to read
- `engine/consolidate.py` — current `consolidate_main()` structure
- `engine/intelligence.py` — `generate_weekly_synthesis()`, `generate_person_insight()`
- `engine/capture.py` — `write_note_atomic()`, `build_post()` for note creation
- `engine/db.py` — `note_people`, `note_tags` junction tables for clustering

### Dependencies
- Phase 50: access_count informs which notes are "load-bearing" in a cluster
- Phase 52: graph traversal enriches cluster discovery beyond junction tables
</canonical_refs>

<deferred>
## Deferred Ideas

- Weekly email/notification digest of synthesis notes → future
- User review workflow: "approve/edit/discard" synthesis before it becomes permanent → future
- Cross-week trend detection (compare this week's synthesis to last week's) → future
- Auto-archive source notes after synthesis is approved → future
</deferred>

---

*Phase: 54-consolidation-synthesis-layer*
*Context gathered: 2026-04-01*
