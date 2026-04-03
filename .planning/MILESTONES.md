# Milestones

## v4.0 Memory & Reliability (Shipped: 2026-04-03)

**Phases completed:** 22 phases (32–49), 100 plans
**Commits:** 314
**Timeline:** 11 days (2026-03-21 → 2026-04-01)
**Codebase:** 35,189 LOC Python + 9,996 LOC TypeScript

**Key accomplishments:**
1. Architecture hardening — relative path storage, FK cascades, junction tables with SQLite triggers (Phase 32, 48.1)
2. Scale to 100K notes — ANN vector index, encrypted backup/restore, chunked embeddings, tiered storage (Phase 38)
3. Complete visual redesign — React + Tailwind frontend matching Visily mockups across all 8 pages (Phases 41–41.3)
4. Chrome extension — full capture (articles, selections, Gmail, URLs) + page summarisation (Phases 36, 41.3)
5. Smart capture decomposer — 5-pass pipeline: entity extraction → URL splitting → classification → action items → assembly (Phase 43)
6. AI provider flexibility — Groq API via Keychain, all-local Ollama toggle, auto-routing, Settings UI (Phase 44)
7. Full codebase audit — 31 findings across security/architecture/performance/testing, all remediated (Phase 39 + 40–48.1)
8. Data integrity hardening — SQLite triggers for junction table consistency, backend cleanup, Blueprint partitioning (Phases 48, 48.1)

### Known Gaps

Process debt accepted (no functional gaps):
- Nyquist validation incomplete for 17/22 phases (paperwork, not code)
- No VERIFICATION.md files created during v4.0 (verification via UAT and test suites)
- REQUIREMENTS.md was v3.0 vintage; v4.0 used per-phase requirements in ROADMAP.md

---

## v3.0 GUI Overhaul & Polish (Shipped: 2026-03-21)

**Phases completed:** 20 phases (20–31), 88 plans

**Key accomplishments:**
1. React + shadcn/UI frontend rewrite with 8 pages (Notes, Actions, People, Meetings, Projects, Intelligence, Inbox, Links)
2. Live refresh via SSE, note deletion with cascade, collapsible sidebar
3. Smart capture with entity extraction, deduplication, and multi-capture
4. People graph hardening, link capture, MCP server expansion to 22 tools
5. Playwright end-to-end test suite

---

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

