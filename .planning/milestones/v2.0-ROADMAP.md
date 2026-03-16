# Roadmap: Second Brain

## Milestones

- ✅ **v1.5 Second Brain MVP** — Phases 1–13 (shipped 2026-03-15)
- 🚧 **v2.0 Intelligence + GUI Hub** — Phases 14–19 (in progress)

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

### 🚧 v2.0 Intelligence + GUI Hub (In Progress)

**Milestone Goal:** Elevate the brain from a capture/search tool to an active knowledge partner with proactive intelligence and a cross-platform desktop GUI.

- [x] **Phase 14: Embedding Infrastructure** — sqlite-vec KNN table, sentence-transformers local embeddings, content-hash staleness detection (completed 2026-03-15)
- [x] **Phase 15: Intelligence Layer** — Session recap, action item extraction, stale nudges, connection surfacing, proactive budget (completed 2026-03-15)
- [x] **Phase 16: Semantic Search and Digest** — `sb-search --semantic`, RRF hybrid search, weekly digest via launchd, cross-context synthesis CLI (completed 2026-03-15)
- [x] **Phase 17: API Layer and Setup Automation** — Flask HTTP sidecar (`engine/api.py`), Drive auto-detection, Ollama auto-install (completed 2026-03-15)
- [x] **Phase 18: GUI Hub** — pywebview + Flask desktop app (`sb-gui`), sidebar/viewer/panel layout, action items and intelligence panels (completed 2026-03-15)
- [x] **Phase 19: MCP Server** — FastMCP stdio server (`sb-mcp-server`), full tool parity, two-step destructive confirmation, Claude Desktop config (completed 2026-03-15)

## Phase Details

### Phase 14: Embedding Infrastructure
**Goal**: Local vector embeddings exist for all notes, enabling similarity-based features in subsequent phases
**Depends on**: Phase 13 (v1.5 complete)
**Requirements**: EMBED-01, EMBED-02, EMBED-03, EMBED-04
**Success Criteria** (what must be TRUE):
  1. Running `sb-reindex` generates vector embeddings for every note using `all-MiniLM-L6-v2` without any network call
  2. The `note_embeddings` table in `brain.db` contains a `content_hash` column and marks rows `stale=true` when a note is edited before the next reindex
  3. Running `sb-forget <person>` removes that person's embedding rows from `note_embeddings` along with all other note data
  4. `sb-reindex` completes without error and embeddings are queryable via sqlite-vec KNN
**Plans**: 4 plans

Plans:
- [ ] 14-01-PLAN.md — Add sentence-transformers + sqlite-vec deps; write failing test scaffold (Wave 0)
- [ ] 14-02-PLAN.md — note_embeddings DDL in db.py; engine/embeddings.py provider dispatch (Wave 1)
- [ ] 14-03-PLAN.md — embed_pass() + incremental reindex + --full flag in reindex.py (Wave 2)
- [ ] 14-04-PLAN.md — GDPR cascade delete from note_embeddings in forget.py (Wave 2)

### Phase 15: Intelligence Layer
**Goal**: The brain proactively surfaces the right context at the right moment — session recap, action items, stale notes, and connection suggestions — with a single notification budget so it never becomes noise
**Depends on**: Phase 14
**Requirements**: INTL-01, INTL-02, INTL-03, INTL-04, INTL-05, INTL-06, INTL-07, INTL-08, INTL-09, INTL-10
**Success Criteria** (what must be TRUE):
  1. When working in a known context, Claude Code offers a session recap at most once per session; running `sb-recap` returns a summary of recent activity in that context
  2. After capturing a meeting note, action items are automatically extracted and stored; user can list open items via `sb-actions` and mark them done via `sb-actions --done <id>`
  3. Running any `sb-*` command surfaces at most one unsolicited notification per session (stale nudge, connection suggestion, or recap offer — never more than one combined)
  4. Notes last accessed more than 90 days ago appear in stale nudges (max 5 per session); notes with `evergreen: true` frontmatter never appear
  5. After a new capture, if a closely matching existing note is found (cosine similarity > 0.8), the user sees one connection suggestion before the prompt returns
**Plans**: 3 plans

Plans:
- [ ] 15-01-PLAN.md — Wave 0 RED scaffold: test stubs (INTL-01–10), intelligence.py stubs, action_items DDL in db.py
- [ ] 15-02-PLAN.md — Implement budget gate, action item extraction + CLI, stale nudge (INTL-03/04/05/06/07/08/10)
- [ ] 15-03-PLAN.md — Implement recap + connection suggestions; wire capture.py/search.py hooks + entry points (INTL-01/02/09)

### Phase 16: Semantic Search and Digest
**Goal**: Users can find notes by meaning (not just keywords) and receive a weekly digest of brain activity, themes, and open actions
**Depends on**: Phase 15
**Requirements**: SRCH-01, SRCH-02, SRCH-03, SRCH-04, DIAG-01, DIAG-02, DIAG-03, DIAG-04
**Success Criteria** (what must be TRUE):
  1. Running `sb-search --semantic <query>` returns semantically relevant notes even when the query shares no keywords with the note content
  2. Hybrid search results combine BM25 keyword ranking and vector similarity via Reciprocal Rank Fusion — running `sb-search` (no flag) uses the merged ranking
  3. Running `sb-recap <name>` returns a cross-context synthesis of all notes about a person or project; PII notes are summarized via Ollama, non-PII via Claude
  4. A weekly digest file is written automatically to `.meta/digests/` each week and is readable via `sb-read --digest latest`; the digest includes captured notes, key themes, open actions, and stale items; PII note summaries in the digest route through Ollama
**Plans**: 4 plans

Plans:
- [ ] 16-01-PLAN.md — Wave 0 RED scaffold: test stubs for all 14 behaviors; engine/digest.py stub; sb-digest entry point
- [ ] 16-02-PLAN.md — search_semantic(), _rrf_merge(), search_hybrid(); --semantic/--keyword flags in search.py (SRCH-01/02)
- [ ] 16-03-PLAN.md — recap_entity() + extend recap_main() for entity names; PII routing (SRCH-03/04)
- [ ] 16-04-PLAN.md — engine/digest.py full impl; sb-read --digest flag; launchd digest plist (DIAG-01/02/03/04)

### Phase 17: API Layer and Setup Automation
**Goal**: A stable local HTTP API exists for the GUI to call, and `sb-init` completes a working setup without any manual Drive or Ollama configuration steps
**Depends on**: Phase 16
**Requirements**: SETUP-01, SETUP-02, SETUP-03, SETUP-04
**Success Criteria** (what must be TRUE):
  1. Running `sb-init` on a fresh macOS or Windows machine auto-detects the Google Drive path and exits with a clear error (non-zero exit code, readable message) if Drive is not found — no silent fallback to a wrong path
  2. Running `sb-init` on a machine without Ollama auto-installs it; if the embedding model download will take significant time (~800 MB), the user sees a warning before it begins
  3. `engine/api.py` is running on `127.0.0.1:37491` and all engine functions are callable via HTTP — the GUI can retrieve a note list, search, read a note, and get action items without importing any `engine/` module
  4. The API health endpoint responds to `GET /health` so the GUI can detect when the sidecar is ready
**Plans**: 3 plans

Plans:
- [ ] 17-00-PLAN.md — Wave 0 RED scaffold: tests/test_api.py + extend tests/test_init_brain.py; add Flask/Waitress/flask-cors deps
- [ ] 17-01-PLAN.md — Implement engine/api.py: /health, /notes, /search, /notes/<path>, /actions; sb-api entry point (Wave 2)
- [ ] 17-02-PLAN.md — Extend engine/init_brain.py: Drive detection, Ollama auto-install, model size warning (Wave 2)

### Phase 18: GUI Hub
**Goal**: Users can browse, read, and create notes through a cross-platform desktop app that complements — but does not replace — the CLI
**Depends on**: Phase 17
**Requirements**: GUI-01, GUI-02, GUI-03, GUI-04, GUI-05, GUI-06, GUI-07, GUI-08, GUI-09, GUI-10, GUI-11
**Success Criteria** (what must be TRUE):
  1. Running `sb-gui` opens a desktop window on macOS and Windows showing a sidebar of notes organized by folder and type; user can click any note to read it
  2. User can search notes from the GUI using keyword or semantic search and see results update in the center panel
  3. User can create a new note of any type (meeting, project, person, idea, etc.) from the GUI and the note is saved atomically to disk and indexed
  4. The right panel shows backlinks, related notes, and metadata for the currently open note; user can view the action items panel and mark items done; intelligence panel shows recent recap and stale nudges
  5. User can browse and move binary files between subfolders in the GUI; user can open any note in the system default editor as an alternative to the GUI viewer
**Plans**: 4 plans

Plans:
- [ ] 18-00-PLAN.md — Wave 0 RED scaffold: pywebview dep, engine/gui.py stub, tests/test_api_extensions.py stubs (GUI-01)
- [ ] 18-01-PLAN.md — API extensions: PUT /notes, POST /notes, GET /notes/meta, GET /files, POST /files/move, POST /actions/done, GET /intelligence (GUI-04–10)
- [ ] 18-02-PLAN.md — engine/gui.py implementation + full HTML/JS three-panel frontend + EasyMDE vendored (GUI-01–03, GUI-11)
- [ ] 18-03-PLAN.md — Human verification checkpoint: all 11 GUI requirements confirmed in live window (GUI-01–11)

### Phase 19: MCP Server
**Goal**: Users can use brain commands from Claude Desktop and Claude.ai via MCP tools with the same capabilities as the CLI
**Depends on**: Phase 14, Phase 15, Phase 16 (Phase 17 and 18 not required — MCP calls engine directly)
**Requirements**: MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, MCP-06, MCP-07, MCP-08, MCP-09, MCP-10
**Success Criteria** (what must be TRUE):
  1. After running `sb-init`, Claude Desktop is automatically configured with the MCP server; user can invoke `sb_search`, `sb_capture`, `sb_read`, `sb_recap`, `sb_digest`, `sb_forget`, `sb_connections`, and action item tools from a Claude.ai session
  2. Calling `sb_forget` or `sb_anonymize` via MCP requires a two-step confirmation: first call returns a token, second call within 60 seconds with the token executes the action — a single call does nothing destructive
  3. PII notes returned by `sb_read` are routed through Ollama; MCP tools never bypass the existing ModelRouter
  4. All MCP tool inputs are validated before execution (type, path, size limits); transient failures retry with exponential backoff; every tool call is recorded in the audit log; write tools are idempotent (duplicate `sb_capture` with identical content creates no duplicate note)
**Plans**: 4 plans

Plans:
- [ ] 19-01-PLAN.md — Wave 0: install fastmcp+tenacity, engine/mcp_server.py stubs, tests/test_mcp.py RED scaffold (all requirements)
- [ ] 19-02-PLAN.md — Wave 1: implement 10 non-destructive tools — search, capture, read, edit, recap, digest, connections, actions, files (MCP-01/03/05–10)
- [ ] 19-03-PLAN.md — Wave 1: two-step confirmation for sb_forget + sb_anonymize; sb-init writes Claude Desktop config (MCP-02/04)
- [ ] 19-04-PLAN.md — Wave 2: human verification — Claude Desktop discovers server and sb_search runs live (MCP-01/02)

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
| 19. MCP Server | 4/4 | Complete    | 2026-03-15 | - |
