# Phase 52: Associative Graph Traversal

**Gathered:** 2026-04-01
**Status:** Ready for planning (independent of 50-51)

<domain>
## Phase Boundary

Enable multi-hop relationship traversal so the system can follow associative chains:
"Alice → ProjectX → Bob" to answer "how is Alice connected to Bob?" Today all relationship
queries are single-hop only.

### Problem
The `relationships` table stores directed edges (wiki-link, backlink, connection, similar,
co-captured) but queries never follow chains. `sb_person_context` aggregates via junction
tables, not the graph. Can't answer transitive questions like "who worked with Alice on
something related to ProjectY?" — the data exists but the query path doesn't.

### Scope
- Add graph traversal function using recursive CTEs (2-3 hop max)
- Add `strength` column to relationships for weighted traversal
- New MCP tool: `sb_traverse` — given a starting note, return connected notes up to N hops
- Enhance `sb_person_context` to include 2nd-degree connections
- Add index on relationships table for traversal performance
</domain>

<decisions>
## Implementation Decisions

### Recursive CTE approach
SQLite supports recursive CTEs natively. Max depth capped at 3 hops to prevent runaway
queries. Activation score decays by depth: `1.0 / (2 ^ depth)`.

### Relationship strength
Add `strength REAL DEFAULT 1.0` to relationships. Initial population:
- wiki-link: 1.0 (explicit intent)
- backlink: 0.8 (reverse of explicit)
- connection: 0.9 (user-confirmed)
- similar: cosine_similarity value (0.7-1.0 range)
- co-captured: 0.5 (weak association)

### Traversal types
Two query modes:
1. **Explore**: follow all relationship types, return full subgraph up to N hops
2. **Path**: find shortest path between two specific notes (BFS via CTE)

### New MCP tool shape
```python
sb_traverse(start_path: str, max_depth: int = 2, rel_types: list[str] | None = None) -> dict
# Returns: {"nodes": [...], "edges": [...], "paths": [...]}
```

### Performance
Add composite index: `CREATE INDEX idx_rel_source_type ON relationships(source_path, rel_type)`.
With typical brain size (<5000 notes), 3-hop CTE completes in <50ms.
</decisions>

<canonical_refs>
## Canonical References

### Source files to modify
- `engine/db.py` — add `strength` column, add index, migration
- `engine/links.py` — add `traverse_graph()` and `find_path()` functions
- `engine/mcp_server.py` — add `sb_traverse` tool
- `engine/mcp_server.py` — enhance `sb_person_context` with 2nd-degree connections

### Source files to read
- `engine/db.py:66-72` — relationships table schema
- `engine/links.py` — current link operations, `add_note_connection()`, `extract_wiki_links()`
- `engine/mcp_server.py` — `sb_person_context()` implementation
- `engine/intelligence.py` — `check_connections()` for similarity-based auto-linking
</canonical_refs>

<deferred>
## Deferred Ideas

- Graph visualization in GUI (force-directed layout) → future
- Community detection (clusters of densely connected notes) → future
- Relationship type inference from note content → future
- Strengthen relationships on co-access (read A then B in same session) → Phase 50+ integration
</deferred>

---

*Phase: 52-associative-graph-traversal*
*Context gathered: 2026-04-01*
