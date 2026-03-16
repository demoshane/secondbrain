# Milestones

## v2.0 Intelligence + GUI Hub (Shipped: 2026-03-16)

**Phases completed:** 6 phases (14–19), 23 plans
**Git range:** b574997 → 880b2d5
**Files changed:** 81 files, +12,732 / -145 lines
**Timeline:** 2026-03-15

**Key accomplishments:**
1. Local vector embeddings: sqlite-vec KNN table + sentence-transformers (`all-MiniLM-L6-v2`), no cloud (Phase 14)
2. Intelligence layer: session recap, action item extraction, stale nudges, connection surfacing with proactive budget gate (Phase 15)
3. Semantic search with RRF hybrid ranking + weekly digest auto-written via launchd (Phase 16)
4. Flask API sidecar on `127.0.0.1:37491` with Drive/Ollama auto-detection and install (Phase 17)
5. `sb-gui` desktop app via pywebview — three-panel sidebar/viewer/intelligence layout, EasyMDE editor (Phase 18)
6. `sb-mcp-server` FastMCP stdio server with 10 tools, two-step destructive confirmation, Claude Desktop config auto-write (Phase 19)

### Known Gaps

User chose to proceed with 4 EMBED requirements showing "Pending" in traceability table (Phase 14 phase is marked complete with all 4 SUMMARY files present — table was not updated):

- `EMBED-01`: `sb-reindex` generates vector embeddings (Phase 14)
- `EMBED-02`: Local `all-MiniLM-L6-v2`, no cloud (Phase 14)
- `EMBED-03`: Stale embedding detection via content-hash (Phase 14)
- `EMBED-04`: `sb-forget` cascades to remove embeddings (Phase 14)

---

## v1.5 Second Brain MVP (Shipped: 2026-03-15)

**Phases completed:** 14 phases, 60 plans, 4 tasks

**Key accomplishments:**
- (none recorded)

---

