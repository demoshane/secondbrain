# Roadmap: Second Brain

## Milestones

- ✅ **v1.5 Second Brain MVP** — Phases 1–13 (shipped 2026-03-15)
- ✅ **v2.0 Intelligence + GUI Hub** — Phases 14–19 (shipped 2026-03-16)
- ✅ **v3.0 GUI Overhaul & Polish** — Phases 20–31 (shipped 2026-03-21)
- 📋 **v4.0 Memory & Reliability** — Phases 32–41 (planned)

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
#### Phase 27.10: Graph View
Visual knowledge map, nodes = notes, edges = relationships, zoomable/filterable (not started)

</details>

## v4.0 Memory & Reliability (Phases 32–36)

### Phase 32: Architecture Hardening

**Goal:** Fix structural issues that will cause data loss or pain as the brain grows — relative path storage, FK cascade, connection leak safety, tags as indexed structure, action item lifecycle, security/consistency fixes
**Depends on:** Phase 29
**Milestone:** v4.0
**Requirements**: ARCH-01 through ARCH-16
**Plans:** 6/6 plans complete

Plans:
- [x] 32-01-PLAN.md — Relative path migration (ARCH-01)
- [x] 32-02-PLAN.md — FK cascade + connection safety + upload cap (ARCH-02, ARCH-03, ARCH-04)
- [x] 32-03-PLAN.md — Tags + note_people junction tables (ARCH-05, ARCH-15)
- [x] 32-04-PLAN.md — Action item archiving + audit_log index (ARCH-06)
- [x] 32-05-PLAN.md — Security + consistency fixes (ARCH-07, ARCH-08, ARCH-09, ARCH-14, ARCH-16)
- [x] 32-06-PLAN.md — People graph correctness + shared service + parity tests (ARCH-10–ARCH-13)

---

### Phase 33: Performance & Scale Hardening

**Goal:** Keep system fast at thousands of notes — paginate all list endpoints, gate expensive O(n) operations, optimise reindex, cap LLM context
**Depends on:** Phase 32
**Milestone:** v4.0
**Requirements**: PERF-01 through PERF-07

Plans:
- [x] 33-01-PLAN.md — Pagination on all list endpoints + MCP page param (PERF-01)
- [x] 33-02-PLAN.md — check_connections gate + fast reindex (PERF-02, PERF-03)
- [x] 33-03-PLAN.md — Recap/digest token budget + batched embedding worker (PERF-04, PERF-05)
- [x] 33-04-PLAN.md — Entity-based filtering API + MCP (PERF-06)
- [x] 33-05-PLAN.md — sb_person_context query consolidation (PERF-07)

---

### Phase 34: GUI Management Productivity

**Goal:** Make GUI genuinely productive — interactive action items everywhere, Cmd+K palette, entity page create/delete, sb_create_person MCP tool
**Depends on:** Phase 30
**Milestone:** v4.0
**Requirements**: GUI-01 through GUI-07

Plans:
- [x] 34-01-PLAN.md — Interactive action items + Actions page source note link (GUI-01, GUI-02)
- [x] 34-02-PLAN.md — Cmd+K command palette (GUI-03)
- [x] 34-03-PLAN.md — Entity page create/delete + sb_create_person MCP (GUI-04, GUI-07)
- [x] 34-04-PLAN.md — Intelligence actionable items + tag autocomplete + toasts + Inbox polish (GUI-05, GUI-06)

---

### Phase 35: Brain Consolidation & Knowledge Hygiene

**Goal:** Keep brain coherent as it grows — near-duplicate merging, stub enrichment, connection cleanup, health trends, scheduled consolidation
**Depends on:** Phase 31, Phase 32
**Milestone:** v4.0
**Requirements**: CONS-01 through CONS-05

Plans:
- [x] 35-01-PLAN.md — Near-duplicate cluster detection + merge workflow (CONS-01)
- [x] 35-02-PLAN.md — Stub enrichment + connection graph cleanup (CONS-02, CONS-03)
- [x] 35-03-PLAN.md — Health trend tracking + scheduled consolidation (CONS-04, CONS-05)

---

### Phase 36: Chrome Extension Capture

**Goal:** Capture web content directly from Chrome into the second brain via a browser extension — full article extraction, text selection, Gmail threads, URL bookmarks, with edit-before-save popup and connection status awareness
**Depends on:** Phase 31
**Milestone:** v4.0
**Requirements**: D-01 through D-17
**Plans:** 4/4 plans complete

Plans:
- [x] 36-01-PLAN.md — Backend API: /ping, CORS, source_url/source_type (D-13, D-14, D-15)
- [x] 36-02-PLAN.md — Extension scaffold + core capture: manifest, popup, context menus, article/selection/link capture (D-01, D-02, D-04, D-05, D-06, D-12)
- [x] 36-03-PLAN.md — Gmail integration: injected button, thread extraction, Gmail context menu (D-07, D-08)
- [x] 36-04-PLAN.md — Rich UX + install: badge polling, capture history, setup.sh, Intelligence page button (D-09, D-10, D-11, D-16, D-17)

---

### Phase 37: Housekeeping

**Goal:** Close known UX gaps and test coverage holes surfaced during v4.0 development: fix broken sb-recap weekly view, add action item creation from person note view, people chips in NoteViewer, cascade delete completeness, cover install_subagent.py in tests, fix failing Playwright and embedding tests, and establish Drive sync setup + health check (prerequisite for Phase 38 backup).
**Depends on:** Phase 34
**Milestone:** v4.0
**Status:** ✅ Complete (UAT passed 2026-03-26)
**Plans:** 11/11 plans complete

Plans:
- [x] 37-01-PLAN.md — Fix sb-recap weekly view (MCP `sb_recap` -> `generate_recap_on_demand`)
- [x] 37-02-PLAN.md — Action item creation from person note view
- [x] 37-03-PLAN.md — People chips in NoteViewer (add/remove person links on notes)
- [x] 37-04-PLAN.md — Cascade delete completeness: impact preview + orphan cleanup
- [x] 37-05-PLAN.md — Tests for install_subagent.py
- [x] 37-06-PLAN.md — Fix 3 failing Playwright tests (title sync, delete flow, people badge)
- [x] 37-07-PLAN.md — Fix 4 failing embedding reindex tests (synchronous mode)
- [x] 37-08-PLAN.md — Drive sync setup guidance + sb-health Drive check
- [x] 37-09-PLAN.md — [GAP] Fix action item disappearing after assigning person
- [x] 37-10-PLAN.md — [GAP] Wire check_drive_sync into sb-health CLI
- [x] 37-11-PLAN.md — [GAP] Fix sb_recap MCP timeout (raw mode for MCP path; content cap; adapter timeout 30s)

---

### Phase 38: Scale Architecture (100K Notes)

**Goal:** Make the brain functional and fast at 100K+ atomic notes — ANN vector index, incremental reindex, filesystem sharding, audit rotation, tiered storage, chunked embeddings, summarization layer, memory consolidation engine. Encrypted backup to secure off-machine storage with single-command restore (DB + embeddings + relationships — not just markdown files)
**Depends on:** Phase 32, Phase 33
**Milestone:** v4.0
**Requirements**: SCALE-01 through SCALE-08
**Status:** ✅ Complete (UAT skipped — infrastructure-only phase, 2026-03-27)
**Plans:** 7/7 plans complete

Plans:
- [x] 38-01-PLAN.md — hnswlib ANN index module + reindex integration (SCALE-01)
- [x] 38-02-PLAN.md — Audit log rotation + filesystem sharding helpers (SCALE-04, SCALE-03)
- [x] 38-03-PLAN.md — Encrypted backup + restore + health check (SCALE-08)
- [x] 38-04-PLAN.md — Chunked embeddings: note_chunks table + embed_chunks + reindex (SCALE-06, SCALE-02)
- [x] 38-05-PLAN.md — Search excerpt via hnswlib ANN + API/MCP passthrough (SCALE-06, SCALE-02)
- [x] 38-06-PLAN.md — Tiered storage (archived flag) + summarization layer (SCALE-05, SCALE-07)
- [x] 38-07-PLAN.md — Memory consolidation engine: candidates via ANN + health reporting (SCALE-01, SCALE-06)

---

### Phase 39: Full Codebase Review

**Goal:** Cross-cutting security, architecture, performance, and test-coverage audit of the entire codebase. Produce prioritised findings and actionable fix plans.
**Depends on:** Phase 34
**Milestone:** v4.0
**Requirements**: N/A (quality gate)
**Plans:** 7/7 plans complete

Plans:
- [x] 39-01-PLAN.md — Security audit: API surfaces, MCP tools, Chrome extension
- [x] 39-02-PLAN.md — Architecture audit: module coupling, dead code, dual-write consistency
- [x] 39-03-PLAN.md — Performance audit: queries, loops, indexes, scale bottlenecks
- [x] 39-04-PLAN.md — Test coverage audit: module mapping, MCP tools, thin tests
- [x] 39-05-PLAN.md — Dead code + optimisation audit: stale paths, duplication, cleanup
- [x] 39-06-PLAN.md — Triage: consolidate findings into 39-FINDINGS.md
- [ ] 39-07-PLAN.md — User review + remediation scope approval

---

### Phase 40: UI Feature Completeness

**Goal:** Add the backend API capabilities required by the new Visily designs that don't exist yet — per-person Brain Insight, weekly synthesis endpoint, project status field + stats, linked meetings on projects, meetings participants as linkable objects, action items grouped-by-source endpoint, markdown body rendering for links.
**Depends on:** Phase 37
**Milestone:** v4.0

Plans:
- [ ] 40-01-PLAN.md — Per-person AI Brain Insight endpoint (`GET /people/:path/insight`)
- [ ] 40-02-PLAN.md — Weekly Synthesis endpoint (`GET /intelligence/synthesis`)
- [ ] 40-03-PLAN.md — Project status field + stats API (status, related_notes_count, linked_meetings_count)
- [ ] 40-04-PLAN.md — Linked meetings on projects + participant objects on meetings
- [ ] 40-05-PLAN.md — Action items grouped-by-source endpoint + Links markdown rendering fix

---

### Phase 41: Visual Redesign

**Goal:** Implement the complete Visily UI redesign across the entire frontend — new design system tokens, component library overhaul, app shell, command palette, and all 8 page redesigns (Notes, Actions, People, Meetings, Projects, Intelligence, Inbox, Links) to match the approved mockups in `ui-design-files/`.
**Depends on:** Phase 40
**Milestone:** v4.0

Plans:
- [ ] 41-01-PLAN.md — Design system tokens + base component overhaul (colors, typography, buttons, badges, inputs, overlays, skeletons)
- [ ] 41-02-PLAN.md — App shell redesign: topbar, tabbar with icons, command palette
- [ ] 41-03-PLAN.md — Notes view redesign: sidebar, NoteViewer, NoteEditor, Right Panel
- [ ] 41-04-PLAN.md — People + Meetings + Projects page redesigns
- [ ] 41-05-PLAN.md — Actions + Inbox + Intelligence + Links page redesigns

### Phase 42: Add importance field to notes

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 41
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 42 to break down)

---

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1–13 | v1.5 | 60/60 | Complete | 2026-03-15 |
| 14–19 | v2.0 | 23/23 | Complete | 2026-03-16 |
| 20–31 | v3.0 | 88/88 | Complete | 2026-03-21 |
| 32 | v4.0 | 6/6 | Complete | 2026-03-22 |
| 33 | v4.0 | 5/5 | Complete | 2026-03-22 |
| 34 | v4.0 | 4/4 | Complete | 2026-03-22 |
| 35 | v4.0 | 3/3 | Complete | 2026-03-23 |
| 36 | v4.0 | 4/4 | Complete | 2026-03-25 |
| 37 | v4.0 | 11/11 | Complete | 2026-03-26 |
| 38 | v4.0 | 7/7 | Complete | 2026-03-27 |
| 39 | v4.0 | 6/7 | Complete    | 2026-03-27 |
| 40 | v4.0 | 0/5 | Not started | - |
| 41 | v4.0 | 0/5 | Not started | - |
