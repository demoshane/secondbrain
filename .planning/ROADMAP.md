# Roadmap: Second Brain

## Milestones

- ✅ **v1.5 Second Brain MVP** — Phases 1–13 (shipped 2026-03-15)
- ✅ **v2.0 Intelligence + GUI Hub** — Phases 14–19 (shipped 2026-03-16)
- ✅ **v3.0 GUI Overhaul & Polish** — Phases 20–31 (shipped 2026-03-21)
- ✅ **v4.0 Memory & Reliability** — Phases 32–49 (shipped 2026-04-03)
- 📋 **v5.0 Cognitive Intelligence** — Phases 50–54 (planned)

## Phases

<details>
<summary>✅ v1.5 Second Brain MVP (Phases 01–13) — SHIPPED 2026-03-15</summary>

#### Phase 01: Foundation
DevContainer, secrets handling, brain init, reindex scaffold (completed 2026-03-14)
#### Phase 02: Storage and Index
Atomic capture pipeline, SQLite FTS5 schema, plain-text search (completed 2026-03-14)
#### Phase 03: AI Layer
PII classifier, ModelRouter, Ollama + Claude adapters, proactive questioning, subagent (completed 2026-03-14)
#### Phase 04: Automation
File watcher, git hooks, people/meetings/work templates, RAG-lite retrieval (completed 2026-03-14)
#### Phase 04.1: Native macOS UX
Global CLI via `uv tool`, launchd watcher daemon, git hook installer (completed 2026-03-14)
#### Phase 05: GDPR and Maintenance
Full erasure cascade, FTS5 rebuild, PII passphrase gate (completed 2026-03-14)
#### Phase 06: Integration Gap Closure
`update_memory()` wiring, watcher PII routing, reindex path fix, subagent spec, CLAUDE.md proactive capture (completed 2026-03-14)
#### Phase 07: Fix Path Format Split
All DB rows store absolute paths; RAG and forget work without pre-reindex (completed 2026-03-15)
#### Phase 08: Fix update_memory() Routing Bypass
Model routing config applies to memory updates (completed 2026-03-15)
#### Phase 09: Nyquist Sign-off
All phases reach `nyquist_compliant: true` (completed 2026-03-15)
#### Phase 10: Quick Code Fixes
Stale docstring removed; forget.py uses `.resolve()` consistently (completed 2026-03-15)
#### Phase 11: GDPR Scope Expansion
`sb-export` (Article 20), runtime `anonymize()`, first-run consent prompt (completed 2026-03-15)
#### Phase 12: Micro-Code Fixes
`sb-anonymize` + `sb-update-memory` entry points; export init_schema; reindex absolute paths + people column (completed 2026-03-15)
#### Phase 13: Nyquist Completion
Phase 10 + 11 VALIDATION.md sign-off; full compliance pass (completed 2026-03-15)

</details>

<details>
<summary>✅ v2.0 Intelligence + GUI Hub (Phases 14–19) — SHIPPED 2026-03-16</summary>

#### Phase 14: Embedding Infrastructure
sqlite-vec KNN table, sentence-transformers local embeddings, content-hash staleness detection (completed 2026-03-15)
#### Phase 15: Intelligence Layer
Session recap, action item extraction, stale nudges, connection surfacing, proactive budget (completed 2026-03-15)
#### Phase 16: Semantic Search and Digest
`sb-search --semantic`, RRF hybrid search, weekly digest via launchd, cross-context synthesis CLI (completed 2026-03-15)
#### Phase 17: API Layer and Setup Automation
Flask HTTP sidecar (`engine/api.py`), Drive auto-detection, Ollama auto-install (completed 2026-03-15)
#### Phase 18: GUI Hub
pywebview + Flask desktop app (`sb-gui`), sidebar/viewer/panel layout, action items and intelligence panels (completed 2026-03-15)
#### Phase 19: MCP Server
FastMCP stdio server (`sb-mcp-server`), full tool parity, two-step destructive confirmation, Claude Desktop config (completed 2026-03-15)

</details>

<details>
<summary>✅ v3.0 GUI Overhaul & Polish (Phases 20–31) — SHIPPED 2026-03-21</summary>

#### Phase 20: Frontend Bug Fixes
Fix scroll, markdown rendering, backlinks, and title sync (3 plans, completed 2026-03-16)
#### Phase 21: Live Refresh SSE
Server-sent events backbone for instant write reflection (6 plans, completed 2026-03-16)
#### Phase 22: Note Deletion + Security Hardening
Delete from GUI with cascade; path traversal guard (4 plans, completed 2026-03-16)
#### Phase 23: Navigation Polish
Collapsible sidebar sections, tag editing, tag filtering (4 plans, completed 2026-03-16)
#### Phase 24: Playwright GUI Test Suite
End-to-end browser tests covering phases 20–23 (4 plans, completed 2026-03-16)
#### Phase 25: File Capture + Batch Capture
File upload from GUI; batch capture; watcher dedup guard (4 plans, completed 2026-03-17)
#### Phase 26: Intelligence Features
On-demand recap, brain health dashboard, health score CLI (4 plans, completed 2026-03-17)
#### Phase 27: Search Quality Tuning
BM25 column weights, recency boost, AI recap quality (7 plans, completed 2026-03-17)
#### Phase 27.1: Smart Capture & Proactive Brain
Entity extraction, dedup, multi-capture, CLAUDE.md, MCP self-doc (5 plans, completed 2026-03-17)
#### Phase 27.2: Action Items Page + Nav Scaffold
Top tab bar, Actions page, assignee picker (4 plans, completed 2026-03-17)
#### Phase 27.3: React + Shadcn/UI Migration
Full frontend rewrite: React + Vite + shadcn/ui + Tailwind (5 plans, completed 2026-03-18)
#### Phase 27.4: People Page
People directory, per-person detail view (4 plans, completed 2026-03-18)
#### Phase 27.5: Meetings Page
Chronological meeting log with participants and outcomes (3 plans, completed 2026-03-18)
#### Phase 27.6: Projects Page
Project status tracking, related notes, open action items (3 plans, completed 2026-03-18)
#### Phase 27.7: Playwright Coverage & Regression Baseline
Expanded Playwright suite, test isolation, pre-flight smoke (4 plans, completed 2026-03-19)
#### Phase 27.8: Intelligence Page
Full Intelligence page: recap, brain health, stale notes (3 plans, completed 2026-03-18)
#### Phase 27.9: Inbox Page
Review queue: empty notes, unprocessed captures, unassigned actions (4 plans, completed 2026-03-19)
#### Phase 28: TODO & Gap Resolution
Dedup fix, sb_capture_smart, sb_tag, sb_link/unlink, sb_remind, sb_person_context, Playwright fixes (8 plans, completed 2026-03-19)
#### Phase 29: Add Link Capture
URL capture with metadata fetch, MCP tool, Flask API, LinksPage (4 plans, completed 2026-03-19)
#### Phase 30: People Graph Hardening
Unicode entity extraction, people column consolidation, sb_person_context (4 plans, completed 2026-03-20)
#### Phase 31: Smart Capture & Multi-Context Intelligence
Freeform → typed notes, segmentation, dormant resurfacing, bidirectional links, GUI modal (6 plans, completed 2026-03-21)
</details>

<details>
<summary>v4.0 Memory & Reliability (Phases 32–49) — SHIPPED 2026-04-03</summary>

#### Phase 32: Architecture Hardening
Relative path storage, FK cascades, junction tables, connection safety (6 plans, completed 2026-03-22)

#### Phase 33: Performance & Scale Hardening
Pagination, O(n) gates, reindex optimization, LLM context caps (5 plans, completed 2026-03-22)
#### Phase 34: GUI Management Productivity
Interactive action items, Cmd+K palette, entity CRUD, sb_create_person MCP (4 plans, completed 2026-03-22)
#### Phase 35: Brain Consolidation
Near-duplicate merging, stub enrichment, connection cleanup, health trends (3 plans, completed 2026-03-23)
#### Phase 36: Chrome Extension Capture
Full article/selection/Gmail/URL capture with edit-before-save popup (4 plans, completed 2026-03-25)
#### Phase 37: Housekeeping
UX gaps, test coverage holes, Drive sync, 3 gap closures (11 plans, completed 2026-03-26)
#### Phase 38: Scale Architecture (100K Notes)
ANN vector index, encrypted backup, chunked embeddings, tiered storage, consolidation engine (7 plans, completed 2026-03-27)
#### Phase 39: Full Codebase Review
Security/architecture/performance/test audit, 31 findings, 6 remediation groups (13 plans, completed 2026-04-01)
#### Phase 40: UI Feature Completeness
Backend APIs for Visily designs: Brain Insight, weekly synthesis, project stats (5 plans, completed 2026-03-28)
#### Phase 41: Visual Redesign
Complete React + Tailwind redesign matching Visily mockups, all 8 pages (5 plans, completed 2026-03-28)
#### Phase 41.1–41.3: Visual Fidelity + Interactive Gaps + UI Polish
Gap closure, bug fixes, sidebar/extension retheme, wiki-links (18 plans, completed 2026-03-28)
#### Phase 42: Importance Field
Low/medium/high importance across DB, capture, MCP, API, frontend (3 plans, completed 2026-03-29)
#### Phase 43: Smart Capture Decomposer
Multi-pass pipeline: entities → URLs → classification → actions → assembly (4 plans, completed 2026-03-30)
#### Phase 44: AI Provider Settings
Groq via Keychain, Ollama toggle, auto-routing, Settings UI (3 plans, completed 2026-03-30)
#### Phase 45: Performance Testing Framework
sb-perf benchmarks, soft limits, delta reporting, GUI Performance page (2 plans, completed 2026-03-30)
#### Phase 46: Universal Capture Enrichment
Person stub creation in all capture paths (1 plan, completed 2026-03-30)
#### Phase 47: Fix Pre-existing Test Failures
4 long-standing test failures resolved (1 plan, completed 2026-03-30)
#### Phase 48: Backend Code Cleanup
Phase 39 audit remediation: dead routes, helpers, Blueprint partitioning (3 plans, completed 2026-03-31)
#### Phase 48.1: Data Integrity Hardening
SQLite triggers for junction tables, batch-capture fix (2 plans, completed 2026-03-31)
#### Phase 49: Chrome Extension Page Summarisation
Delivered in Phase 41.3 (0 plans needed)

</details>

---

## v5.0 Cognitive Intelligence (Phases 50–54)

### Phase 50: Retrieval Reinforcement (Learning from Use)

**Goal:** Add access tracking (`last_accessed_at`, `access_count`) so frequently-used notes rank higher in search. Access boost up to 15%, capped at 20 accesses, 60-day half-life. Tracking wired into `sb_read`, `sb_search`, `sb_person_context`, and API.
**Depends on:** None (foundation phase)
**Plans:** 3 plans (not started)

Plans:
- [ ] 50-01-PLAN.md — DB migration (access tracking columns) + helper functions + tests
- [ ] 50-02-PLAN.md — Wire access tracking into read/search/API surfaces
- [ ] 50-03-PLAN.md — Post-RRF access boost multiplier in search ranking

### Phase 51: Temporal Decay (Forgetting Curve)

**Goal:** Replace flat creation-time recency boost with dual-axis decay: age + last-access. Per-type half-lives (meeting=30d, note=60d, project=120d, decision=180d, person=never). Graduated stale detection bands replace binary 90-day threshold.
**Depends on:** Phase 50
**Plans:** 2 plans (not started)

Plans:
- [ ] 51-01-PLAN.md — `_relevance_decay()` replacing `_recency_multiplier()` in search.py
- [ ] 51-02-PLAN.md — Graduated stale detection in intelligence.py

### Phase 52: Associative Graph Traversal + Graph View

**Goal:** Multi-hop relationship traversal (2–3 hops) via recursive CTEs. New `sb_traverse` MCP tool. Add `strength` column to relationships. Enhance `sb_person_context` with 2nd-degree connections. Visual graph view page in GUI (D3 force-directed layout, zoom/filter/click-to-navigate). Subsumes former Phase 27.10.
**Depends on:** None
**Plans:** 3 plans (not started)

Plans:
- [ ] 52-01-PLAN.md — Graph traversal functions + weighted edges + composite index
- [ ] 52-02-PLAN.md — `sb_traverse` MCP tool + `sb_person_context` 2nd-degree expansion
- [ ] 52-03-PLAN.md — Graph View page: D3 force-directed layout, node/edge rendering, zoom/filter/navigate (ex-27.10)

### Phase 53: Proactive Surfacing

**Goal:** New `sb_surface` MCP tool that returns notes the user didn't ask for but should see, based on conversation context. Session dedup via audit log. Optional `context_hint` param on `sb_search`/`sb_recap`.
**Depends on:** Phase 50, Phase 51; benefits from Phase 52 (optional)
**Plans:** 2 plans (not started)

Plans:
- [ ] 53-01-PLAN.md — Surfacing engine: semantic context match + access/decay scoring
- [ ] 53-02-PLAN.md — `sb_surface` MCP tool + context_hint integration

### Phase 54: Consolidation & Synthesis Layer

**Goal:** Periodic "sleep" process that clusters recent notes by person/project/topic and generates synthesis notes. Contradiction detection. New `sb_insights` MCP tool. Runs as extension of nightly consolidation job.
**Depends on:** Phase 50, Phase 52; benefits from Phase 53
**Plans:** 3 plans (not started)

Plans:
- [ ] 54-01-PLAN.md — Cluster detection (3+ notes sharing person/tag in 7-day window)
- [ ] 54-02-PLAN.md — AI synthesis generation + `synthesis` note type
- [ ] 54-03-PLAN.md — `sb_insights` MCP tool + dedup protection

### Phase 56: Intelligence GUI — Synthesis, Suggestions & Contradictions

**Goal:** Surface Phases 53–54 backend features in the GUI. Add "Syntheses" and "Contradictions" sections to the Intelligence page. Add "Suggested for You" section to the Inbox page showing proactive surfacing results. Synthesis notes filterable/readable like any other note type.
**Depends on:** Phase 53, Phase 54
**Plans:** 3 plans (not started)

Plans:
- [ ] 56-01-PLAN.md — Flask API endpoints for syntheses list, contradictions, and proactive suggestions
- [ ] 56-02-PLAN.md — Intelligence page: Syntheses section + Contradictions alerts
- [ ] 56-03-PLAN.md — Inbox page: "Suggested for You" section with proactive surfacing

---

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1-13 | v1.5 | 60/60 | Complete | 2026-03-15 |
| 14-19 | v2.0 | 23/23 | Complete | 2026-03-16 |
| 20-31 | v3.0 | 88/88 | Complete | 2026-03-21 |
| 32-49 | v4.0 | 100/100 | Complete | 2026-04-03 |
| 50 | v5.0 | 0/3 | Not started | - |
| 51 | v5.0 | 0/2 | Not started | - |
| 52 | v5.0 | 0/3 | Not started | - |
| 53 | v5.0 | 0/2 | Not started | - |
| 54 | v5.0 | 0/3 | Not started | - |
