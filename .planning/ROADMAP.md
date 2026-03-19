# Roadmap: Second Brain

## Milestones

- ✅ **v1.5 Second Brain MVP** — Phases 1–13 (shipped 2026-03-15)
- ✅ **v2.0 Intelligence + GUI Hub** — Phases 14–19 (shipped 2026-03-16)
- 🔄 **v3.0 GUI Overhaul & Polish** — Phases 20–29 (in progress)
- 📋 **v4.0 Memory & Reliability** — Phases 30–34 (planned)

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

## v3.0 GUI Overhaul & Polish

- [x] **Phase 20: Frontend Bug Fixes** — Fix scroll, markdown rendering, backlinks, and title sync (pure JS/CSS) (completed 2026-03-16)
- [x] **Phase 21: Live Refresh SSE** — Server-sent events backbone so all writes reflect instantly in the GUI (completed 2026-03-16)
- [x] **Phase 22: Note Deletion + Security Hardening** — Delete from GUI with cascade; path traversal guard on all note endpoints (completed 2026-03-16)
- [x] **Phase 23: Navigation Polish** — Collapsible sidebar sections, tag editing, tag filtering (completed 2026-03-16)
- [x] **Phase 24: Playwright GUI Test Suite** — End-to-end browser tests covering all GUI functionality built in phases 20–23 (completed 2026-03-16)
- [x] **Phase 25: File Capture + Batch Capture** — File upload from GUI; batch capture of unindexed items; watcher dedup guard (completed 2026-03-17)
- [x] **Phase 26: Intelligence Features** — On-demand recap button, brain health dashboard, health score CLI (completed 2026-03-17)
- [x] **Phase 27: Search Quality Tuning** — BM25 column weight tuning, recency boost, AI recap quality improvements (completed 2026-03-17)
- [x] **Phase 27.1: Smart Capture & Proactive Brain** — Entity extraction at capture time, dedup via embedding similarity, multi-capture, CLAUDE.md in repo, MCP tool self-documentation (completed 2026-03-17)
- [x] **Phase 27.2: Action Items Page + Nav Scaffold** — Top tab bar (extensible), dedicated Action Items page, assignee picker with autocomplete, assignee_path on action_items, person note "My Actions" section (completed 2026-03-17)
- [x] **Phase 27.3: UI/UX Overhaul** — Design system (typography, spacing, color tokens), visual consistency across all panels, dark mode polish (completed 2026-03-18)
- [x] **Phase 27.4: People Page** — People directory, per-person view with meetings, action items, and backlinks (completed 2026-03-18)
- [x] **Phase 27.5: Meetings Page** — Chronological meeting log, participants, outcomes, linked action items (completed 2026-03-18)
- [x] **Phase 27.6: Projects Page** — Project status tracking, related notes, open action items per project (completed 2026-03-18)
- [x] **Phase 27.7: Playwright Coverage & Regression Baseline** — Expand Playwright suite to cover all existing features; enforce test isolation; add pre-flight smoke test (completed 2026-03-19)
- [x] **Phase 27.8: Intelligence Page** — Promote recap, brain health, digest from sidebar panel to full dedicated page (completed 2026-03-18)
- [x] **Phase 27.9: Inbox Page** — Review queue: empty notes, unprocessed captures, unassigned action items (completed 2026-03-19)
- [ ] **Phase 27.10: Graph View** — Visual knowledge map, nodes = notes, edges = relationships, zoomable/filterable

### Phase Details

### Phase 20: Frontend Bug Fixes
**Goal**: The GUI viewer is fully usable — note content renders as HTML, scrolls normally, displays correct backlinks, and title changes reflect without restart
**Requirements**: GUIX-02, GUIX-03, GUIX-04, GUIX-05
**Plans:** 3/3 plans complete

Plans:
- [ ] 20-01-PLAN.md — Strip frontmatter in API + save re-index (GUIX-03, GUIX-02)
- [ ] 20-02-PLAN.md — Fix backlinks content query (GUIX-05)
- [ ] 20-03-PLAN.md — CSS scroll fix + human verify (GUIX-04)

**Success criteria**:
1. User can scroll long notes using the mouse wheel in the viewer panel
2. Note content renders as formatted HTML (headings, bold, lists) with no raw markdown or YAML frontmatter visible
3. After editing and saving a note title in the GUI, the sidebar and viewer heading update without a restart
4. Backlinks shown in the viewer panel match the actual relationships stored in the database (no false positives, no missing links)

### Phase 21: Live Refresh SSE
**Goal**: Notes created or edited anywhere (GUI, CLI, file watcher daemon) appear in the sidebar and viewer without restarting the application
**Requirements**: GUIX-01
**Plans:** 6/6 plans complete

Plans:
- [x] 21-01-PLAN.md — Test scaffolds for SSE endpoint + NoteChangeHandler (failing stubs, Wave 1)
- [x] 21-02-PLAN.md — Backend SSE: NoteChangeHandler + /events route + observer wiring (Wave 2)
- [x] 21-03-PLAN.md — Frontend SSE: EventSource, status dot, conflict banner, dirty state (Wave 3)
- [x] 21-04-PLAN.md — Human verify: FAILED — 3 issues found (see 21-04-SUMMARY.md)
- [x] 21-05-PLAN.md — Gap closure: save-suppression (watcher + api), threads=8 in GUI sidecar (Wave 1)
- [x] 21-06-PLAN.md — Gap closure: conflict banner easyMDE guard + human re-verify (Wave 2)

**Gap closure status:**
1. [CRITICAL] Conflict banner — FIXED: easyMDE !== null guard in handleNoteEvent (plan 21-06)
2. [BUG] False deletion on save — FIXED: suppress_next_delete() in watcher + api (plan 21-05)
3. [Minor] Status dot 5s delay — accepted as cosmetic; no code change needed

**Success criteria**:
1. A note created via `sb-capture` appears in the GUI sidebar within 2 seconds without any user action
2. A note edited via CLI appears with updated content in the viewer within 2 seconds
3. The file watcher daemon bridges new file events to the SSE bus via `POST /internal/notify`
4. The GUI reconnects automatically if the SSE connection drops

### Phase 22: Note Deletion + Security Hardening
**Goal**: Users can delete notes from the GUI with full cascade, and all note endpoints are protected against path traversal
**Requirements**: GUIX-06
**Plans:** 4/4 plans complete

Plans:
- [ ] 22-01-PLAN.md — Wave 0: test scaffold (tests/test_delete.py) + engine/delete.py stub
- [ ] 22-02-PLAN.md — Wave 1: implement delete_note() cascade + DELETE route + path traversal guard
- [ ] 22-03-PLAN.md — Wave 2: frontend delete button, confirmation modal, optimistic sidebar removal
- [ ] 22-04-PLAN.md — Wave 3: full suite sign-off + human verify

**Success criteria**:
1. User can delete a note from the GUI using a confirmation dialog; the note disappears from the sidebar immediately
2. Deleting a note removes its FTS5 index entry, backlinks, and embedding row — no orphan DB rows remain
3. Attempting to access a path outside `BRAIN_ROOT` via any notes API returns HTTP 403
4. The `delete_note()` utility is the single shared implementation used by both `forget.py` and the GUI delete endpoint

### Phase 23: Navigation Polish
**Goal**: Users can navigate notes by type/folder, edit tags inline, and filter notes by tag
**Requirements**: GNAV-01, GNAV-02, GNAV-03
**Plans:** 4/4 plans complete

Plans:
- [ ] 23-01-PLAN.md — Test scaffold + backend API extensions (tags save, tag search filter, tags parse)
- [ ] 23-02-PLAN.md — Sidebar hierarchy: folder > type grouping with collapse/expand (localStorage)
- [ ] 23-03-PLAN.md — Tag chips in viewer: display, inline edit, tag filter + banner
- [ ] 23-04-PLAN.md — Full suite sign-off + human verify

**Success criteria**:
1. The sidebar shows notes grouped by type/folder with a collapse/expand toggle per section
2. User can click a tag chip in the viewer and edit it inline; the change saves to both frontmatter and the database without a full reindex
3. User can filter the sidebar or search results to show only notes with a specific tag

### Phase 24: Playwright GUI Test Suite
**Goal**: A pytest-playwright test suite covers all GUI features built in phases 20–23, so regressions are caught automatically on every change
**Requirements**: TEST-01
**Plans:** 4/4 plans complete

Plans:
- [ ] 24-01-PLAN.md — Wave 1: infra — API_BASE fix, pytest-playwright dep, conftest fixtures, xfail stubs
- [ ] 24-02-PLAN.md — Wave 2: markdown rendering, scroll, title sync tests
- [ ] 24-03-PLAN.md — Wave 3: SSE live refresh + delete flow tests
- [ ] 24-04-PLAN.md — Wave 4: tag editing, tag filtering, collapsible sections, path traversal tests

**Success criteria**:
1. `pytest tests/test_gui.py` runs headless against a live Flask dev server with zero manual setup steps
2. Markdown rendering: a note with headings, bold, and lists renders as HTML (no raw `#`, `**`, or `-` visible in the DOM)
3. Scroll: the note viewer panel is scrollable; `scrollTop` changes when scripted (regression for the scroll-lock bug)
4. Title sync: editing and saving a note title updates both the sidebar list item and the viewer heading without a page reload
5. SSE live refresh: capturing a note via API causes a new sidebar entry to appear within 3 seconds without any user action
6. Delete flow: clicking delete shows a confirmation dialog; confirming removes the note from the sidebar; cancelling leaves it
7. Tag editing: clicking a tag chip enables inline edit; typing and pressing Enter saves the new tag to the DOM and API
8. Tag filtering: clicking a tag chip in the viewer filters the sidebar to only show notes with that tag; clearing the filter restores all notes
9. Collapsible sidebar sections: clicking a section header toggles visibility of its note list
10. Path traversal guard: a direct `fetch('/api/notes/../../../etc/passwd')` from the page returns 403 (client-side assertion)

### Phase 25: File Capture + Batch Capture
**Goal**: Users can capture files from the GUI and run a single batch capture of all unindexed items, with no duplicate notes from the watcher race
**Requirements**: GUIF-01, ENGL-01
**Plans:** 4/4 plans complete

Plans:
- [ ] 25-01-PLAN.md — Wave 1: DB migration (attachments table) + test scaffolds
- [ ] 25-02-PLAN.md — Wave 2: backend — engine/attachments.py + API endpoints + watcher dedup guard
- [ ] 25-03-PLAN.md — Wave 3: frontend — upload button, drag-drop, attachment list, batch capture button
- [ ] 25-04-PLAN.md — Wave 4: full suite sign-off + human verify

**Success criteria**:
1. User can select or drag a file in the GUI; the file is saved to `files/` and appears indexed in the sidebar
2. A single "Batch Capture" action captures all unindexed markdown files present in the brain directory
3. Uploading a file via the GUI does not produce a duplicate note when the file watcher also fires on the same path
4. Batch capture returns a structured result showing which items succeeded and which failed with a reason

### Phase 26: Intelligence Features
**Goal**: Users can trigger a weekly recap on demand from the GUI and view a brain health dashboard showing orphans, broken links, duplicates, and a health score
**Requirements**: GUIF-02, ENGL-03, ENGL-04, ENGL-05
**Plans:** 4/4 plans complete

Plans:
- [x] 26-01-PLAN.md — Wave 1: test scaffolds (xfail stubs for all Phase 26 behaviors) (completed 2026-03-17)
- [ ] 26-02-PLAN.md — Wave 2: recap backend — generate_recap_on_demand(), action item dedup, digest column fix, POST /intelligence/recap
- [ ] 26-03-PLAN.md — Wave 2: brain health backend — engine/brain_health.py, GET /brain-health, sb-health --brain
- [ ] 26-04-PLAN.md — Wave 3: frontend — recap button + health panel in GUI + human verify

**Success criteria**:
1. The Intelligence panel has a "Generate Recap" button; clicking it shows a spinner and then displays the generated recap
2. `sb-health --brain` reports a 0-100 brain health score with counts of orphan notes, broken links, and potential duplicates
3. The GUI health panel displays the same score and check results with a clear "no issues found" vs "N issues" distinction
4. AI recap and action extraction produce deduplicated, accurate output (no repeated items across consecutive recaps)

### Phase 27: Search Quality Tuning
**Goal**: Search returns the most relevant notes first, with title matches ranked above body matches and a regression suite confirming no precision regressions; all open TODOs and test coverage gaps resolved
**Requirements**: ENGL-02
**Plans:** 7/7 plans complete

Plans:
- [ ] 27-01-PLAN.md — Wave 0: regression suite scaffolds (10 xfail tests) + sb_edit stub
- [ ] 27-02-PLAN.md — Wave 1: BM25 column weighting (10.0/1.0) + recency multiplier in search.py
- [ ] 27-03-PLAN.md — Wave 1: sb_edit frontmatter fix + sb-recap fallback + capture context heuristics
- [ ] 27-04-PLAN.md — Wave 1: person→note sidebar chips (meta API + app.js)
- [ ] 27-05-PLAN.md — Wave 1: LLM adapter tests + health check tests
- [ ] 27-06-PLAN.md — Wave 1: GitHub Actions CI workflow
- [ ] 27-07-PLAN.md — Wave 2: full suite sign-off + human verify

**Success criteria**:
1. An exact title search returns the matching note as the first result
2. A semantic search for a topic returns contextually relevant notes above unrelated ones
3. A fixed regression suite of at least 5 precision queries and 5 recall queries all pass before any RRF parameter is changed
4. sb_edit preserves YAML frontmatter when editing note body
5. sb-recap returns results when recent notes exist
6. Person chips visible in sidebar for notes with people frontmatter
7. GitHub Actions CI runs pytest on every push to main

### Phase 27.1: Smart Capture & Proactive Brain
**Goal**: Enrich every captured note with extracted entities at write time, deduplicate incoming notes via embedding similarity before saving, support multi-note capture in one call, document the project in CLAUDE.md, and expose MCP tool self-documentation so agents know what tools are available
**Depends on:** Phase 27
**Success criteria**:
1. Capturing a note automatically extracts and stores entities (people, places, topics) in its metadata
2. Capturing a near-duplicate note warns the user and requires confirmation before saving
3. A single MCP call can capture multiple notes atomically
4. A CLAUDE.md exists at the repo root with accurate project context
5. Each MCP tool returns a self-describing schema that agents can query

**Requirements**: 27.1-SC-01, 27.1-SC-02, 27.1-SC-03, 27.1-SC-04, 27.1-SC-05
**Plans:** 5/5 plans complete

Plans:
- [ ] 27.1-01-PLAN.md — Wave 0 test scaffolds (xfail stubs for all 27.1 behaviors)
- [ ] 27.1-02-PLAN.md — Entity extraction: engine/entities.py + DB migration + capture_note() enrichment
- [ ] 27.1-03-PLAN.md — Dedup check: check_capture_dedup() + sb_capture dedup + confirm_token flow
- [ ] 27.1-04-PLAN.md — sb_capture_batch() + sb_tools() MCP tools
- [ ] 27.1-05-PLAN.md — CLAUDE.md at repo root

### Phase 27.2: Action Items Page + Nav Scaffold
**Goal**: Replace the single-panel GUI with a top tab bar and deliver a dedicated Action Items page where users can view, filter, and assign action items to people, with person notes showing their assigned actions
**Depends on:** Phase 27.1
**Success criteria**:
1. A top tab bar is visible in the GUI with at least "Notes" and "Action Items" tabs; clicking switches the main view
2. The Action Items page lists all action items with status, due date, and assignee; supports filtering by status and assignee
3. An action item can be assigned to a person note via an assignee picker with autocomplete
4. Opening a person note shows a "My Actions" section listing all action items where assignee_path matches that note

**Requirements**: GPAG-01, GPAG-02, GPAG-03, GPAG-04
**Plans:** 4/4 plans complete

Plans:
- [x] 27.2-01-PLAN.md — Wave 0: xfail test scaffolds (TestTabBar, filter/assign/my-actions stubs, DB migration stubs)
- [x] 27.2-02-PLAN.md — Wave 1: DB migrations (assignee_path, due_date) + backend API extensions
- [x] 27.2-03-PLAN.md — Wave 2: frontend tab bar, Actions page, assignee picker, My Actions section
- [x] 27.2-04-PLAN.md — Wave 3: full suite sign-off + human verify + bug fixes

### Phase 27.3: React + Shadcn/UI Migration
**Goal**: Migrate the entire GUI frontend from vanilla JS to React + Vite + shadcn/ui + Tailwind CSS, with full feature parity, automatic dark mode via prefers-color-scheme, and React Context for state management
**Depends on:** Phase 27.2
**Success criteria**:
1. Frontend is a Vite-built React app served by Flask — `npm run build` outputs to `engine/gui/static/`
2. All existing features work: sidebar, note viewer, markdown editor, tab bar, actions page, file upload, batch capture, SSE live refresh, intelligence panel
3. shadcn/ui components installed via CLI; Tailwind CSS in use; dark mode auto-detects prefers-color-scheme
4. All existing backend tests pass; no API contract regressions

**Requirements**: UIUX-01, UIUX-02, UIUX-03, UIUX-04
**Plans:** 5/5 plans complete

Plans:
- [ ] 27.3-01-PLAN.md — Vite + React + shadcn/ui scaffold, types, Vitest stubs
- [ ] 27.3-02-PLAN.md — React Contexts (Note, Search, UI, SSE) + hooks
- [ ] 27.3-03-PLAN.md — App shell, Topbar, TabBar, Sidebar
- [ ] 27.3-04-PLAN.md — NoteViewer, NoteEditor, RightPanel, ActionsPage, modals
- [ ] 27.3-05-PLAN.md — Playwright selector update + human verify

### Phase 27.4: People Page

**Goal:** A dedicated People page in the tab bar that shows the people directory, per-person detail view with associated meetings, action items, and backlinks
**Depends on:** Phase 27.3
**Requirements**: 27.4-PP-01, 27.4-PP-02, 27.4-PP-03, 27.4-PP-04
**Plans:** 4/4 plans complete

Plans:
- [ ] 27.4-01-PLAN.md — Wave 0: xfail test scaffolds
- [ ] 27.4-02-PLAN.md — Backend: people API endpoints
- [ ] 27.4-03-PLAN.md — Frontend: People page + person detail view
- [ ] 27.4-04-PLAN.md — Integration, Playwright tests, sign-off

### Phase 27.5: Meetings Page

**Goal:** A dedicated Meetings page in the tab bar showing chronological meeting log with participants, outcomes, and linked action items
**Depends on:** Phase 27.4
**Requirements**: 27.5-MP-01, 27.5-MP-02, 27.5-MP-03, 27.5-MP-04

Plans:
- [ ] 27.5-01-PLAN.md — Backend: meetings API endpoints
- [ ] 27.5-02-PLAN.md — Frontend: Meetings page + meeting detail view
- [ ] 27.5-03-PLAN.md — Integration, Playwright tests, sign-off

### Phase 27.6: Projects Page

**Goal:** A dedicated Projects page in the tab bar that shows all project notes with their status, related notes, and open action items per project
**Depends on:** Phase 27.5
**Requirements**: 27.6-PROJ-01, 27.6-PROJ-02, 27.6-PROJ-03, 27.6-PROJ-04

Plans:
- [ ] 27.6-01-PLAN.md — Backend: projects API endpoints
- [ ] 27.6-02-PLAN.md — Frontend: Projects page + project detail view
- [ ] 27.6-03-PLAN.md — Integration, Playwright tests, sign-off

### Phase 27.7: Playwright Coverage & Regression Baseline

**Goal:** Expand Playwright test coverage to all existing GUI features so regressions are caught automatically before reaching the user. Add pre-flight smoke test, fix test isolation gaps, establish baseline.
**Depends on:** Phase 27.6
**Requirements**: 27.7-QA-01, 27.7-QA-02, 27.7-QA-03, 27.7-QA-04
**Plans:** 4/4 plans complete

Plans:
- [ ] 27.7-01-PLAN.md — Wave 1: conftest gui_brain extension (type='people' + mention seeds) + right panel tests (QA-02)
- [ ] 27.7-02-PLAN.md — Wave 1: pre-flight smoke test — tests/test_preflight.py, all endpoints + /ui (QA-01)
- [ ] 27.7-03-PLAN.md — Wave 1: tab data-correctness tests + orphan spec tests in test_brain_health.py (QA-03, QA-04)
- [ ] 27.7-04-PLAN.md — Wave 2: people/person type isolation regression test + intelligence data assertion + full suite baseline (QA-03, QA-04)

### Phase 27.8: Intelligence Page

**Goal:** Promote recap, brain health, and digest from the sidebar intelligence panel to a full dedicated Intelligence page in the tab bar
**Depends on:** Phase 27.6
**Requirements**: 27.8-INTEL-01, 27.8-INTEL-02, 27.8-INTEL-03, 27.8-INTEL-04

Plans:
- [ ] 27.8-01-PLAN.md — Backend: intelligence page API endpoints
- [ ] 27.8-02-PLAN.md — Frontend: Intelligence page + tab bar wiring
- [ ] 27.8-03-PLAN.md — Integration, Playwright tests, sign-off

### Phase 27.9: Inbox Page

**Goal:** Add a dedicated Inbox tab showing a review queue of empty notes, unprocessed captures, and unassigned action items so the user can triage and act on them without hunting through the note list
**Depends on:** Phase 27.8
**Requirements**: 27.9-INBOX-01, 27.9-INBOX-02, 27.9-INBOX-03, 27.9-INBOX-04

Plans:
- [ ] 27.9-01-PLAN.md — Backend: inbox API endpoint
- [ ] 27.9-02-PLAN.md — Frontend: Inbox page + tab bar wiring
- [ ] 27.9-03-PLAN.md — Integration, Playwright tests, sign-off

### Phase 27.10: Graph View

**Goal:** Render a visual knowledge map where nodes are notes and edges are relationships (backlinks, people mentions, action item links), zoomable and filterable
**Depends on:** Phase 27.9
**Requirements**: 27.10-GRAPH-01, 27.10-GRAPH-02, 27.10-GRAPH-03, 27.10-GRAPH-04

Plans:
- [ ] 27.10-01-PLAN.md — Backend: graph data API endpoint
- [ ] 27.10-02-PLAN.md — Frontend: Graph page + tab bar wiring
- [ ] 27.10-03-PLAN.md — Integration, Playwright tests, sign-off

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
| 20. Frontend Bug Fixes | v3.0 | 3/3 | Complete | 2026-03-16 |
| 21. Live Refresh SSE | v3.0 | Complete    | 2026-03-16 | 2026-03-16 |
| 22. Note Deletion + Security Hardening | 4/4 | Complete    | 2026-03-16 | - |
| 23. Navigation Polish | 4/4 | Complete    | 2026-03-16 | - |
| 24. Playwright GUI Test Suite | 4/4 | Complete    | 2026-03-16 | - |
| 25. File Capture + Batch Capture | 4/4 | Complete   | 2026-03-17 | - |
| 26. Intelligence Features | 4/4 | Complete    | 2026-03-17 | - |
| 27. Search Quality Tuning | 7/7 | Complete    | 2026-03-17 | - |
| 27.1. Smart Capture & Proactive Brain | 5/5 | Complete    | 2026-03-18 | - |
| 27.2. Action Items Page + Nav Scaffold | 4/4 | Complete    | 2026-03-18 | - |
| 27.7. Playwright Coverage & Regression Baseline | 4/4 | Complete    | 2026-03-19 | - |
| 27.8. Intelligence Page | v3.0 | 3/3 | Complete | 2026-03-18 |
| 28. TODO & Gap Resolution | 5/7 | In Progress|  | - |
| 29. Add link capture | v3.0 | 0/0 | Not started | - |
| 30. People Graph Hardening | v4.0 | 0/4 | Not started | - |
| 31. Smart Capture & Multi-Context Intelligence | v4.0 | 0/4 | Not started | - |
| 32. Architecture Hardening | v4.0 | 0/4 | Not started | - |
| 33. Performance & Scale Hardening | v4.0 | 0/3 | Not started | - |
| 34. GUI Management Productivity | v4.0 | 0/4 | Not started | - |

### Phase 28: TODO & Gap Resolution

**Goal:** All open TODOs, known gaps, and deferred issues identified at phase start are resolved before the milestone is closed
**Depends on:** Phase 27
**Plans:** 5/7 plans executed

Plans:
- [ ] 28-01-PLAN.md — Title-only dedup for long captures (fix MCP timeout on large bodies)
- [ ] 28-02-PLAN.md — `sb_capture_smart`: split raw content into typed note suggestions (people, meeting, project) before batch capture
- [ ] 28-03-PLAN.md — `sb_tag`: add/remove tags with existing-tag fuzzy matching; confirm-token gate for new tags
- [ ] 28-04-PLAN.md — `sb_link` / `sb_unlink`: explicit directional relationships between notes (DB-only, no body edit)
- [ ] 28-05-PLAN.md — `sb_remind`: set due date + snooze on action items; overdue surfacing in recap + GUI
- [ ] 28-06-PLAN.md — `sb_person_context`: one-call full context dump (note + meetings + actions + mentions) for a person
- [ ] 28-07-PLAN.md — Fix 9 pre-existing Playwright GUI failures (People/Meetings/Projects pages empty, detail panels, right panel people badge)

### Phase 29: Add link capture

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 28
**Plans:** 0 plans

Plans:

---

## v4.0 Memory & Reliability (Phases 30–33)

### Phase 30: People Graph Hardening

**Goal:** Make the people graph accurate and complete — fix entity extraction for non-ASCII names, consolidate to a single source of truth for who appears in a note, and ship `sb_person_context` as the primary MCP tool for person lookup
**Depends on:** Phase 29
**Milestone:** v4.0
**Requirements**: PEO-01, PEO-02, PEO-03, PEO-04
**Plans:** 0 plans

Requirements detail:
- **PEO-01** — Entity extraction recognises non-ASCII/Finnish names (replace `[A-Z][a-z]+` with Unicode-aware pattern)
- **PEO-02** — Captured note's `people` frontmatter column is populated from entity extraction at write time; body-mention fallback in `note_meta()` removed
- **PEO-03** — `sb_person_context` MCP tool returns in one call: person note body, all meetings they appear in, all action items assigned to or mentioning them, and all notes that mention them by name (chronological)
- **PEO-04** — People page and right panel reflect PEO-01/02 correctly; person type isolation regression tests pass

Plans:
- [ ] 30-01-PLAN.md — Unicode entity extraction + write-back to `people` column at capture (PEO-01, PEO-02)
- [ ] 30-02-PLAN.md — Consolidate `note_meta()`: remove body-mention fallback, single source of truth (PEO-02)
- [ ] 30-03-PLAN.md — `sb_person_context` MCP tool: full person context in one call (PEO-03)
- [ ] 30-04-PLAN.md — Regression tests + Playwright people panel sign-off (PEO-04)

---

### Phase 31: Smart Capture & Multi-Context Intelligence

**Goal:** Capture a raw blob of text in one MCP call and have the brain intelligently split it into multiple typed, linked notes; resurface dormant related knowledge after every capture; deduplicate by auto-linking near-duplicates rather than blocking
**Depends on:** Phase 30
**Milestone:** v4.0
**Requirements**: CAP-01, CAP-02, CAP-03, CAP-04, CAP-05
**Plans:** 0 plans

Requirements detail:
- **CAP-01** — `sb_capture_smart` accepts raw freeform text and returns N typed note suggestions (person / meeting / project / idea / note) with inferred titles, types, and cross-links; user confirms or edits before saving
- **CAP-02** — Multi-context parsing: a single large input (e.g. meeting transcript, conversation dump) is segmented into distinct notes — one meeting note, participant person notes, extracted action items — all linked to each other atomically
- **CAP-03** — `sb_capture_smart` is dedup-aware: before proposing new notes, it checks for near-duplicates and either merges the suggestion into the existing note or proposes a link
- **CAP-04** — After every `sb_capture` or `sb_capture_smart` call, the MCP response includes up to 3 semantically related notes last accessed > 30 days ago ("you wrote something related: …") — dormant knowledge resurfacing
- **CAP-05** — When a near-duplicate is confirmed saved anyway, a `similar` relationship is automatically created between the two notes

Plans:
- [ ] 31-01-PLAN.md — `sb_capture_smart`: AI content parser → typed note suggestion list (CAP-01)
- [ ] 31-02-PLAN.md — Multi-context segmentation: one input → N linked notes atomically (CAP-02, CAP-03)
- [ ] 31-03-PLAN.md — Dormant resurfacing in MCP capture response + auto-link near-duplicates (CAP-04, CAP-05)
- [ ] 31-04-PLAN.md — MCP integration tests + overdue action surfacing in recap + sign-off

---

### Phase 32: Architecture Hardening

**Goal:** Fix the structural issues that will cause data loss or pain as the brain grows — relative path storage, FK cascade, connection leak safety, tags as a proper indexed structure, and action item lifecycle management
**Depends on:** Phase 29
**Milestone:** v4.0
**Requirements**: ARCH-01, ARCH-02, ARCH-03, ARCH-04, ARCH-05, ARCH-06
**Plans:** 0 plans

Requirements detail:
- **ARCH-01** — Notes DB stores paths relative to `BRAIN_ROOT`; absolute path resolution happens at query time; migration script converts existing rows
- **ARCH-02** — SQLite `PRAGMA foreign_keys = ON` enabled on every connection; all child tables (`action_items`, `relationships`, `note_embeddings`, `attachments`, `audit_log`) have `ON DELETE CASCADE` referencing `notes(path)`
- **ARCH-03** — All `get_connection()` / `conn.close()` pairs in `api.py` are wrapped in `try/finally`; `suppress_next_delete` uses a thread-safe `threading.Event` keyed by path
- **ARCH-04** — File upload endpoint enforces 50 MB size cap; `_SlashNormMiddleware` removed (test fixtures fixed to not produce double-slash paths)
- **ARCH-05** — `tags` column replaced by `note_tags(note_path, tag)` junction table; migration converts existing JSON-encoded tags; all tag filter queries use the indexed table
- **ARCH-06** — Completed `action_items` older than 90 days are moved to `action_items_archive` table; `audit_log` has index on `(created_at, note_path)`; `sb-health` reports archive counts

Plans:
- [ ] 32-01-PLAN.md — Relative path migration: DB schema change + migration script + all read/write path resolution (ARCH-01)
- [ ] 32-02-PLAN.md — FK cascade + connection safety + upload cap + thread-safe suppress_next_delete (ARCH-02, ARCH-03, ARCH-04)
- [ ] 32-03-PLAN.md — Tags junction table migration + remove `_SlashNormMiddleware` (ARCH-05)
- [ ] 32-04-PLAN.md — Action item archiving + audit_log index + regression tests + sign-off (ARCH-06)

---

### Phase 33: Performance & Scale Hardening

**Goal:** Ensure the system stays fast and responsive as the brain grows to thousands of notes — paginate all list endpoints, gate expensive O(n) operations, optimise reindex, and cap LLM context for recap/digest
**Depends on:** Phase 32
**Milestone:** v4.0
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04, PERF-05
**Plans:** 0 plans

Requirements detail:
- **PERF-01** — All list endpoints (`/people`, `/meetings`, `/projects`, `/actions`, and MCP equivalents) support `limit`/`offset` pagination; default limit 50; MCP tools expose `page` parameter
- **PERF-02** — `check_connections()` skips KNN pass when brain has < 200 notes (configurable); above threshold uses HNSW approximate search if sqlite-vec supports it, otherwise limits to top-50 candidates
- **PERF-03** — `sb-reindex --fast` rebuilds FTS5 in one `INSERT INTO notes_fts(notes_fts) VALUES ('rebuild')` pass rather than per-row triggers; total reindex time < 5s for 5k notes
- **PERF-04** — `generate_recap_on_demand()` and `generate_digest()` enforce a token budget (default 4000 tokens of note content); oldest/shortest notes truncated first; budget configurable in `~/.config/second-brain/config.toml`
- **PERF-05** — Embedding computation runs in a queue-based background worker (batch every 10s) rather than inline per capture; embedding staleness is visible in `sb-health` output

Plans:
- [ ] 33-01-PLAN.md — Pagination on all list endpoints + MCP page param (PERF-01)
- [ ] 33-02-PLAN.md — `check_connections` gate + fast reindex mode (PERF-02, PERF-03)
- [ ] 33-03-PLAN.md — Recap/digest token budget + batched embedding worker + health visibility (PERF-04, PERF-05)

---

### Phase 34: GUI Management Productivity

**Goal:** Make the management GUI genuinely productive — actions completable everywhere, entity pages self-sufficient with create/delete, a command palette for keyboard-first navigation, and Intelligence page items that are actionable not just informational
**Depends on:** Phase 30 (people graph needed for correct participant links)
**Milestone:** v4.0
**Requirements**: GUI-01, GUI-02, GUI-03, GUI-04, GUI-05, GUI-06
**Plans:** 0 plans

Requirements detail:
- **GUI-01** — Action item checkboxes are interactive in ALL context panels (People detail, Meetings detail, Projects detail); checking one immediately marks it done via `PUT /actions/:id/done`
- **GUI-02** — Actions page shows a clickable source note title per action; clicking opens that note in the Notes tab
- **GUI-03** — Cmd+K command palette: fuzzy search across all notes, people, meetings, projects; keyboard-navigable; opens selected item in its context tab
- **GUI-04** — Each entity page has a context-appropriate create button ("+ Add Person", "+ New Meeting", "+ New Project"); entity pages also expose delete from the detail panel
- **GUI-05** — Meeting detail participants are clickable and navigate to the person's page; Intelligence page orphans, empty notes, and stale nudges are clickable and individually deletable/linkable; last recap timestamp shown + 5 most recent recaps browseable; digest output surfaced in Intelligence page
- **GUI-06** — Tag autocomplete in NoteViewer and NewNoteModal (suggests existing tags); project status field (active/on-hold/complete) settable from Projects detail panel; toast feedback on save, delete, and mark-done; "Open in Notes" button in Inbox preview panel; delete action in Inbox triage

Plans:
- [ ] 34-01-PLAN.md — Interactive action items everywhere + Actions page source note link (GUI-01, GUI-02)
- [ ] 34-02-PLAN.md — Cmd+K command palette (GUI-03)
- [ ] 34-03-PLAN.md — Entity page create/delete + meeting participant links + project status field (GUI-04)
- [ ] 34-04-PLAN.md — Intelligence page actionable items + recap history + digest surface + tag autocomplete + toasts + Inbox polish (GUI-05, GUI-06)
- [ ] TBD (run /gsd:plan-phase 29 to break down)
