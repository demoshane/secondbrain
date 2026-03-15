# Roadmap: Second Brain

## Milestones

- ✅ **v1.5 Second Brain MVP** — Phases 1–13 (shipped 2026-03-15)
- 📋 **v2.0** — Phases TBD (planned)

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

### 📋 v2.0 (Planned)

*Phases TBD — run `/gsd:new-milestone` to define.*

Known gaps to address:
- Claude.ai web integration (MCP tools)
- Google Drive setup automated in `sb-init`
- Ollama auto-installed during `sb-init`
- Semantic / vector search (beyond BM25)
- Encryption at rest

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 10/10 | Complete | 2026-03-14 |
| 2. Storage and Index | 4/4 | Complete | 2026-03-14 |
| 3. AI Layer | 6/6 | Complete | 2026-03-14 |
| 4. Automation | 12/12 | Complete | 2026-03-14 |
| 4.1. Native macOS UX | 3/3 | Complete | 2026-03-14 |
| 5. GDPR and Maintenance | 4/4 | Complete | 2026-03-14 |
| 6. Integration Gap Closure | 4/4 | Complete | 2026-03-14 |
| 7. Fix Path Format Split | 2/2 | Complete | 2026-03-15 |
| 8. Fix update_memory() Routing Bypass | 2/2 | Complete | 2026-03-15 |
| 9. Nyquist Sign-off | 1/1 | Complete | 2026-03-15 |
| 10. Quick Code Fixes | 1/1 | Complete | 2026-03-15 |
| 11. GDPR Scope Expansion | 4/4 | Complete | 2026-03-15 |
| 12. Micro-Code Fixes | 5/5 | Complete | 2026-03-15 |
| 13. Nyquist Completion | 2/2 | Complete | 2026-03-15 |
