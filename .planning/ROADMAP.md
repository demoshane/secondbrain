# Roadmap: Second Brain

## Milestones

- ✅ **v1.5 Second Brain MVP** — Phases 1–13 (shipped 2026-03-15)
- ✅ **v2.0 Intelligence + GUI Hub** — Phases 14–19 (shipped 2026-03-16)

## Phases

<details>
<summary>✅ v1.5 Second Brain MVP (Phases 1–13) — SHIPPED 2026-03-15</summary>

- [x] **Phase 1: Foundation** — DevContainer, secrets handling, brain init, reindex scaffold (completed 2026-03-14)
- [x] **Phase 2: Storage and Index** — Atomic capture pipeline, SQLite FTS5 schema, plain-text search (completed 2026-03-14)
- [x] **Phase 3: AI Layer** — PII classifier, ModelRouter, Ollama + Claude adapters, proactive questioning, subagent (completed 2026-03-14)
- [x] **Phase 4: Automation** — File watcher, git hooks, people/meetings/work templates, RAG-lite retrieval (completed 2026-03-14)
- [x] **Phase 4.1: Native macOS UX** — Global CLI via `uv tool`, launchd watcher daemon, git hook installer (completed 2026-03-14)
- [x] **Phase 5: GDPR and Maintenance** — Full erasure cascade, FTS5 rebuild, PII passphrase gate (completed 2026-03-14)
- [x] **Phase 6: Integration Gap Closure** — `update_memory()` wiring, watcher PII routing, reindex path fix, subagent spec, CLAUDE.md proactive capture (completed 2026-03-14)
- [x] **Phase 7: Fix Path Format Split** — All DB rows store absolute paths; RAG and forget work without pre-reindex (completed 2026-03-15)
- [x] **Phase 8: Fix update_memory() Routing Bypass** — Model routing config applies to memory updates (completed 2026-03-15)
- [x] **Phase 9: Nyquist Sign-off** — All phases reach `nyquist_compliant: true` (completed 2026-03-15)
- [x] **Phase 10: Quick Code Fixes** — Stale docstring removed; forget.py uses `.resolve()` consistently (completed 2026-03-15)
- [x] **Phase 11: GDPR Scope Expansion** — `sb-export` (Article 20), runtime `anonymize()`, first-run consent prompt (completed 2026-03-15)
- [x] **Phase 12: Micro-Code Fixes** — `sb-anonymize` + `sb-update-memory` entry points; export init_schema; reindex absolute paths + people column (completed 2026-03-15)
- [x] **Phase 13: Nyquist Completion** — Phase 10 + 11 VALIDATION.md sign-off; full compliance pass (completed 2026-03-15)

</details>

<details>
<summary>✅ v2.0 Intelligence + GUI Hub (Phases 14–19) — SHIPPED 2026-03-16</summary>

- [x] **Phase 14: Embedding Infrastructure** — sqlite-vec KNN table, sentence-transformers local embeddings, content-hash staleness detection (completed 2026-03-15)
- [x] **Phase 15: Intelligence Layer** — Session recap, action item extraction, stale nudges, connection surfacing, proactive budget (completed 2026-03-15)
- [x] **Phase 16: Semantic Search and Digest** — `sb-search --semantic`, RRF hybrid search, weekly digest via launchd, cross-context synthesis CLI (completed 2026-03-15)
- [x] **Phase 17: API Layer and Setup Automation** — Flask HTTP sidecar (`engine/api.py`), Drive auto-detection, Ollama auto-install (completed 2026-03-15)
- [x] **Phase 18: GUI Hub** — pywebview + Flask desktop app (`sb-gui`), sidebar/viewer/panel layout, action items and intelligence panels (completed 2026-03-15)
- [x] **Phase 19: MCP Server** — FastMCP stdio server (`sb-mcp-server`), full tool parity, two-step destructive confirmation, Claude Desktop config (completed 2026-03-15)

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.5 | 10/10 | Complete | 2026-03-14 |
| 2. Storage and Index | v1.5 | 4/4 | Complete | 2026-03-14 |
| 3. AI Layer | v1.5 | 6/6 | Complete | 2026-03-14 |
| 4. Automation | v1.5 | 12/12 | Complete | 2026-03-14 |
| 4.1. Native macOS UX | v1.5 | 3/3 | Complete | 2026-03-14 |
| 5. GDPR and Maintenance | v1.5 | 4/4 | Complete | 2026-03-14 |
| 6. Integration Gap Closure | v1.5 | 4/4 | Complete | 2026-03-14 |
| 7. Fix Path Format Split | v1.5 | 2/2 | Complete | 2026-03-15 |
| 8. Fix update_memory() Routing Bypass | v1.5 | 2/2 | Complete | 2026-03-15 |
| 9. Nyquist Sign-off | v1.5 | 1/1 | Complete | 2026-03-15 |
| 10. Quick Code Fixes | v1.5 | 1/1 | Complete | 2026-03-15 |
| 11. GDPR Scope Expansion | v1.5 | 4/4 | Complete | 2026-03-15 |
| 12. Micro-Code Fixes | v1.5 | 5/5 | Complete | 2026-03-15 |
| 13. Nyquist Completion | v1.5 | 2/2 | Complete | 2026-03-15 |
| 14. Embedding Infrastructure | v2.0 | 4/4 | Complete | 2026-03-15 |
| 15. Intelligence Layer | v2.0 | 4/4 | Complete | 2026-03-15 |
| 16. Semantic Search and Digest | v2.0 | 4/4 | Complete | 2026-03-15 |
| 17. API Layer and Setup Automation | v2.0 | 3/3 | Complete | 2026-03-15 |
| 18. GUI Hub | v2.0 | 4/4 | Complete | 2026-03-15 |
| 19. MCP Server | v2.0 | 4/4 | Complete | 2026-03-15 |
