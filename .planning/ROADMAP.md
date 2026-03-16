# Roadmap: Second Brain

## Milestones

- ✅ **v1.5 Second Brain MVP** — Phases 1–13 (shipped 2026-03-15)
- ✅ **v2.0 Intelligence + GUI Hub** — Phases 14–19 (shipped 2026-03-16)
- 🔄 **v3.0 GUI Overhaul & Polish** — Phases 20–26 (in progress)

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
- [ ] **Phase 22: Note Deletion + Security Hardening** — Delete from GUI with cascade; path traversal guard on all note endpoints
- [ ] **Phase 23: Navigation Polish** — Collapsible sidebar sections, tag editing, tag filtering
- [ ] **Phase 24: File Capture + Batch Capture** — File upload from GUI; batch capture of unindexed items; watcher dedup guard
- [ ] **Phase 25: Intelligence Features** — On-demand recap button, brain health dashboard, health score CLI
- [ ] **Phase 26: Search Quality Tuning** — BM25 column weight tuning, recency boost, AI recap quality improvements

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
**Plans:** 1/4 plans executed

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
**Success criteria**:
1. The sidebar shows notes grouped by type/folder with a collapse/expand toggle per section
2. User can click a tag chip in the viewer and edit it inline; the change saves to both frontmatter and the database without a full reindex
3. User can filter the sidebar or search results to show only notes with a specific tag

### Phase 24: File Capture + Batch Capture
**Goal**: Users can capture files from the GUI and run a single batch capture of all unindexed items, with no duplicate notes from the watcher race
**Requirements**: GUIF-01, ENGL-01
**Success criteria**:
1. User can select or drag a file in the GUI; the file is saved to `files/` and appears indexed in the sidebar
2. A single "Batch Capture" action captures all unindexed markdown files present in the brain directory
3. Uploading a file via the GUI does not produce a duplicate note when the file watcher also fires on the same path
4. Batch capture returns a structured result showing which items succeeded and which failed with a reason

### Phase 25: Intelligence Features
**Goal**: Users can trigger a weekly recap on demand from the GUI and view a brain health dashboard showing orphans, broken links, duplicates, and a health score
**Requirements**: GUIF-02, ENGL-03, ENGL-04, ENGL-05
**Success criteria**:
1. The Intelligence panel has a "Generate Recap" button; clicking it shows a spinner and then displays the generated recap
2. `sb-health` CLI command reports a 0-100 brain health score with counts of orphan notes, broken links, and potential duplicates
3. The GUI health panel displays the same score and check results with a clear "no issues found" vs "N issues" distinction
4. AI recap and action extraction produce deduplicated, accurate output (no repeated items across consecutive recaps)

### Phase 26: Search Quality Tuning
**Goal**: Search returns the most relevant notes first, with title matches ranked above body matches and a regression suite confirming no precision regressions
**Requirements**: ENGL-02
**Success criteria**:
1. An exact title search returns the matching note as the first result
2. A semantic search for a topic returns contextually relevant notes above unrelated ones
3. A fixed regression suite of at least 5 precision queries and 5 recall queries all pass before any RRF parameter is changed

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
| 22. Note Deletion + Security Hardening | 1/4 | In Progress|  | - |
| 23. Navigation Polish | v3.0 | 0/? | Not started | - |
| 24. File Capture + Batch Capture | v3.0 | 0/? | Not started | - |
| 25. Intelligence Features | v3.0 | 0/? | Not started | - |
| 26. Search Quality Tuning | v3.0 | 0/? | Not started | - |
