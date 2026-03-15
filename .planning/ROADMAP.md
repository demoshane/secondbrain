# Roadmap: Cybernetic Second Brain

## Overview

Five phases in strict dependency order: secure the environment before writing any code, prove atomic storage before adding AI, enforce the PII routing guard before any API call leaves the machine, add event-driven automation on top of a tested interactive pipeline, and finally implement GDPR erasure against real accumulated data. Each phase leaves the system in a usable, dogfoodable state.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Secure DevContainer, secrets handling, brain init, and reindex scaffold before any real data is written (completed 2026-03-14)
- [x] **Phase 2: Storage and Index** - Atomic capture pipeline, SQLite FTS5 schema live, plain-text search working without AI (completed 2026-03-14)
- [x] **Phase 3: AI Layer** - PII classifier, ModelRouter, Ollama + Anthropic adapters, proactive questioning, Claude subagent (completed 2026-03-14)
- [ ] **Phase 4: Automation** - File watcher, git hooks, people/meetings/work features, RAG-lite retrieval
- [x] **Phase 5: GDPR and Maintenance** - Full erasure cascade, FTS5 rebuild, access control on PII notes (completed 2026-03-14)
- [ ] **Phase 6: Integration Gap Closure** - Wire update_memory() call, fix watcher PII routing, fix reindex path format mismatch

## Phase Details

### Phase 1: Foundation
**Goal**: The DevContainer is secure, reproducible, and verified on all target platforms — secrets never touch git or Drive, the brain folder structure exists, and `/sb-reindex` can rebuild the index from scratch before a single real note is written
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06, FOUND-07, FOUND-08, FOUND-09, FOUND-10, FOUND-11, FOUND-12
**Success Criteria** (what must be TRUE):
  1. Running `bootstrap.py --dev` in a freshly cloned repo on macOS and Windows each completes without errors and reports all checks green
  2. The pre-commit hook blocks a commit containing a mock API key and passes a commit with no secrets
  3. `.env.host` does not appear in `git status` output and is not present in the Drive-synced folder
  4. `/sb-init` creates all nine brain subdirectories and a populated SQLite schema in the named volume; `/sb-reindex` runs to completion on an empty brain with zero errors
  5. A file written inside the container to `/workspace/brain/` is immediately visible on the host at `~/SecondBrain/` with correct ownership
**Plans**: 10 plans

Plans:
- [ ] 01-00-PLAN.md — Test infrastructure (Wave 0): pyproject.toml, pytest config, 10 stub test files, conftest.py fixtures
- [ ] 01-01-PLAN.md — DevContainer fix: vscode user, brain mount, .env.host injection, .gitignore
- [ ] 01-02-PLAN.md — Pre-commit hook: detect-secrets v1.5.0, .secrets.baseline
- [ ] 01-03-PLAN.md — Engine foundation: engine/paths.py, engine/db.py, engine/init_brain.py (/sb-init)
- [ ] 01-04-PLAN.md — Reindex command: engine/reindex.py (/sb-reindex)
- [ ] 01-05-PLAN.md — Bootstrap validator: scripts/bootstrap.py --dev, static analysis tests (FOUND-12)
- [ ] 01-06-PLAN.md — Manual verification checkpoint: DevContainer on macOS, bind mount ownership, fresh install sequence
- [ ] 01-07-PLAN.md — Gap closure: fix test_blocks_api_key to use detectable secret; add test_anthropic_key_not_detected
- [ ] 01-08-PLAN.md — Gap closure: fix bootstrap.py invocation docs (uv run) and add venv detection guard
- [ ] 01-09-PLAN.md — Gap closure: replace hardcoded Homebrew pre-commit hook with portable .githooks/ wrapper

### Phase 2: Storage and Index
**Goal**: Every capture operation writes an atomic, schema-valid markdown note and indexes it into SQLite FTS5; search returns ranked results; the audit log records every operation — all without requiring an AI API call
**Depends on**: Phase 1
**Requirements**: CAP-01, CAP-02, CAP-03, CAP-07, SEARCH-01, SEARCH-02, GDPR-03, GDPR-05, GDPR-06
**Success Criteria** (what must be TRUE):
  1. `/sb-capture` with valid inputs writes a note whose YAML frontmatter contains all required fields (type, title, date, tags, people, created_at, updated_at, content_sensitivity) and is round-trip parseable
  2. Deliberately killing the process between file write and index write leaves no partial note on disk (rollback is confirmed by checking the file is absent)
  3. `/sb-search "some phrase"` returns the note containing that phrase, ranked by BM25, within two seconds on a 1000-note index
  4. Every capture, read, and update operation produces a row in the SQLite audit log with correct timestamp and operation type
  5. `detect-secrets` scan of the engine codebase reports zero baseline violations; no secret value appears in any log file or error message
**Plans**: 4 plans

Plans:
- [ ] 02-00-PLAN.md — Test scaffold (Wave 0): test_capture.py, test_search.py, test_audit.py stubs + conftest fixtures
- [ ] 02-01-PLAN.md — Capture pipeline: engine/db.py migration, engine/capture.py, engine/templates.py, 6 template files
- [ ] 02-02-PLAN.md — Search engine: engine/search.py, FTS5 BM25, type filter, audit on search
- [ ] 02-03-PLAN.md — CLI wiring: sb-capture + sb-search entry points, remaining test stubs, manual verification checkpoint

### Phase 3: AI Layer
**Goal**: The PII classifier runs locally and enforces routing before any API call is made; notes flagged as PII go only to Ollama; non-PII notes go to Claude; proactive questioning enriches every capture; the Claude Code subagent is installable and usable from any Claude session
**Depends on**: Phase 2
**Requirements**: AI-01, AI-02, AI-03, AI-04, AI-05, AI-06, AI-07, AI-08, AI-09, AI-10, CAP-06
**Success Criteria** (what must be TRUE):
  1. Capturing a note with `content_sensitivity: pii` triggers zero outbound calls to Anthropic (verified via network log or mock); the Ollama adapter receives the request instead
  2. Capturing a note with `content_sensitivity: public` routes to the Anthropic adapter and never touches the Ollama endpoint
  3. Every `/sb-capture` invocation presents 2–3 content-type-aware follow-up questions before writing the note
  4. Changing the model mapping in `.meta/config.toml` takes effect on the next capture with no code change or restart required
  5. The `second-brain` subagent is invokable from a Claude Code session via `/sb-capture` and returns a successful capture confirmation
**Plans**: TBD

### Phase 4: Automation
**Goal**: The system captures context from events (file drops, git commits) without manual intervention; people profiles and meeting backlinks are maintained automatically; work-domain templates are usable; RAG-lite retrieval pre-loads relevant notes into AI context
**Depends on**: Phase 3
**Requirements**: CAP-04, CAP-05, PEOPLE-01, PEOPLE-02, PEOPLE-03, PEOPLE-04, PEOPLE-05, WORK-01, WORK-02, WORK-03, WORK-04, SEARCH-03, SEARCH-04
**Success Criteria** (what must be TRUE):
  1. Dropping a PDF into `~/SecondBrain/files/` triggers a categorization prompt within 10 seconds (with debounce); bulk-dropping 20 files does not produce more than one prompt per 5 seconds
  2. Committing in a project directory fires the git hook; the AI summary is offered and, if accepted, a brain entry is created and linked to the correct project note
  3. Creating a meeting note with two attendees automatically adds a backlink to each person's profile; `/sb-check-links` reports zero orphans in a correctly populated brain
  4. `/sb-search --type people "Alice"` returns Alice's profile plus all meetings and projects that reference her
  5. An AI query response demonstrably includes context pulled from FTS5-retrieved notes (visible in debug output or prompt log)
**Plans**: 12 plans

Plans:
- [ ] 04-00-PLAN.md — Wave 0: test stubs (test_watcher, test_hooks, test_links, test_rag), stub engine modules, pyproject.toml (watchdog dep, sb-watch + sb-check-links entry points)
- [ ] 04-01-PLAN.md — Link engine: engine/links.py (add_backlinks, check_links, main_check_links), wire into capture.py (PEOPLE-03, PEOPLE-04, PEOPLE-05, SEARCH-03)
- [ ] 04-02-PLAN.md — RAG-lite: engine/rag.py (retrieve_context, augment_prompt) (SEARCH-04)
- [ ] 04-03-PLAN.md — Templates + type fixes: projects.md template, idea->ideas subdir fix, projects/personal types, ai.py prompts (PEOPLE-01, PEOPLE-02, WORK-01–04)
- [ ] 04-04-PLAN.md — File watcher daemon: engine/watcher.py (FilesDropHandler, start_watcher, sb-watch main) (CAP-04)
- [ ] 04-05-PLAN.md — Git hook: engine/hooks/post_commit.py, .githooks/post-commit shell wrapper (CAP-05)
- [ ] 04-06-PLAN.md — Manual verification checkpoint: all 5 Phase 4 success criteria
- [ ] 04-07-PLAN.md — Gap closure: person profile auto-creation in links.py (PEOPLE-03, PEOPLE-04, PEOPLE-05, SEARCH-03)
- [ ] 04-08-PLAN.md — Gap closure: templates directory seeding in init_brain.py (PEOPLE-01, PEOPLE-02, WORK-01–04)
- [ ] 04-09-PLAN.md — Gap closure: RAG wiring — conn param + augment_prompt() call in ai.py/capture.py (SEARCH-04)
- [ ] 04-10-PLAN.md — Gap closure: watcher batch fix + post-commit /dev/tty stdin fix (CAP-04, CAP-05)
- [ ] 04-11-PLAN.md — Gap closure: watcher headless on_new_file — replace input() with AI-auto-classify so batch loop is non-blocking (CAP-04)

### Phase 04.1: Native macOS UX: global CLI, launchd watcher autostart, git hook installer (INSERTED)

**Goal:** One-command native macOS setup — `uv tool install --editable` makes all sb-* commands globally accessible; launchd LaunchAgent runs sb-watch at login with crash restart; git hook installer points any project repo at the shared .githooks/ dir
**Requirements**: 4.1-CLI-01, 4.1-CLI-02, 4.1-LAUNCHD-01, 4.1-LAUNCHD-02, 4.1-LAUNCHD-03, 4.1-HOOK-01, 4.1-HOOK-02
**Depends on:** Phase 4
**Status:** Complete (2026-03-14)
**Plans:** 3/3 plans complete

Plans:
- [x] 04.1-00-PLAN.md — Wave 0: test stubs (7 tests in test_install_native.py) + scripts/install_native.py stub
- [x] 04.1-01-PLAN.md — Wave 1: implement all 3 installer functions (global CLI, launchd, git hooks) — all tests GREEN
- [x] 04.1-02-PLAN.md — Wave 2: sb-install entry point in pyproject.toml + manual verification checkpoint

### Phase 5: GDPR and Maintenance
**Goal**: Right to erasure is complete and verifiable — no content fragment for a deleted person survives in markdown, binary attachments, SQLite rows, or FTS5 shadow tables; PII notes require passphrase confirmation before display
**Depends on**: Phase 4
**Requirements**: GDPR-01, GDPR-02, GDPR-04
**Success Criteria** (what must be TRUE):
  1. After `/sb-forget <person>`, that person's markdown file is absent, all meeting notes referencing only them are absent, and `/sb-search <person>` returns zero results including zero FTS5 fragments
  2. `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` is confirmed executed after every `/sb-forget` call (visible in audit log or test assertion)
  3. Attempting to display a note with `content_sensitivity: pii` without the correct passphrase produces an access-denied message and no note content is printed
**Plans**: 4 plans

Plans:
- [ ] 05-00-PLAN.md — Wave 0: test stubs (test_forget.py 6 tests, test_read.py 4 tests), engine/forget.py stub, engine/read.py stub, pyproject.toml entry points (sb-forget, sb-read)
- [ ] 05-01-PLAN.md — Wave 1a: implement engine/forget.py — erasure cascade + FTS5 rebuild (GDPR-01, GDPR-02)
- [ ] 05-02-PLAN.md — Wave 1b: implement engine/read.py — PII passphrase gate (GDPR-04) [parallel with 05-01]
- [ ] 05-03-PLAN.md — Wave 2: manual verification checkpoint — end-to-end sb-forget and sb-read in real DevContainer

### Phase 6: Integration Gap Closure + Claude Interface Wiring
**Goal**: All five integration gaps resolved: `update_memory()` fires after every non-PII capture; watcher classifies per-file before routing; reindex stores absolute paths; all sb-* commands are invocable from Claude Code and Claude Cowork; and Claude proactively offers to capture relevant context it encounters in any session
**Depends on**: Phase 5
**Requirements**: CAP-06, CAP-08, CAP-09, AI-02 (watcher path), SEARCH-01/AI-08 (reindex path)
**Gap Closure**: Closes gaps from v1.0 audit (v1.0-MILESTONE-AUDIT.md)
**Success Criteria** (what must be TRUE):
  1. After `sb-capture`, a Claude memory file is updated (`update_memory()` called for non-PII notes, verified via test)
  2. Dropping a PII-keyword file via watcher routes to OllamaAdapter, not ClaudeAdapter (verified via mock)
  3. After `sb-reindex`, `sb-search <query>` returns notes and RAG reads their content without "[note file not readable]" fallback
  4. All sb-* commands (`sb-capture`, `sb-search`, `sb-forget`, `sb-read`, `sb-check-links`) are invocable from a Claude Code session via the `second-brain` subagent spec; Claude Cowork interface has equivalent access documented
  5. `~/.claude/CLAUDE.md` contains second-brain instructions: when Claude spots capturable content (decisions, people, meetings, project context) it asks the user "Should I add this to your second brain?" before calling `sb-capture`
**Plans**: 4 plans

Plans:
- [ ] 06-00-PLAN.md — Wave 0: test stubs for all 6 new behaviors + fix 3 existing path/closure assertions
- [ ] 06-01-PLAN.md — Wave 1a: reindex absolute path fix (SEARCH-01/AI-08) + watcher per-file PII classification (AI-02)
- [ ] 06-02-PLAN.md — Wave 1b: CAP-06 memory wiring — update_memory() call site in capture.py:main() [parallel with 06-01]
- [ ] 06-03-PLAN.md — Wave 1c: CAP-08 subagent spec expansion + CAP-09 CLAUDE.md proactive capture block [parallel with 06-01, 06-02]

### Phase 7: Fix Path Format Split
**Goal**: All DB rows store absolute paths — RAG and forget work correctly for notes captured since last reindex without requiring `sb-reindex` first
**Depends on**: Phase 6
**Requirements**: SEARCH-01, SEARCH-04, GDPR-01
**Gap Closure**: Closes path format split gap from v1.5 audit

Plans:
- [ ] 07-00-PLAN.md — Wave 0: add/update tests for absolute path storage, RAG path resolution, forget path matching
- [ ] 07-01-PLAN.md — Wave 1: fix engine/capture.py write_note_atomic() → store str(target.resolve()); verify RAG and forget

### Phase 8: Fix update_memory() Routing Bypass
**Goal**: Model routing config (config.toml) applies to memory updates — no dead parameters, no hardcoded adapter
**Depends on**: Phase 7
**Requirements**: AI-05
**Gap Closure**: Closes CAP-06/AI-05 routing bypass gap from v1.5 audit

Plans:
- [ ] 08-00-PLAN.md — Wave 0: add test confirming routing config affects memory update adapter selection
- [ ] 08-01-PLAN.md — Wave 1: wire config_path through get_adapter() in update_memory() or remove dead parameter

### Phase 9: Nyquist Sign-off
**Goal**: All 9 phases reach `nyquist_compliant: true` — VALIDATION.md sign-off checklist completed and verified for every phase
**Depends on**: Phase 8
**Requirements**: (tech debt — no new requirements)
**Tech Debt**: Closes Nyquist compliance gap from v1.5 audit

Plans:
- [ ] 09-00-PLAN.md — Run /gsd:validate-phase for all 9 phases; update each VALIDATION.md to nyquist_compliant: true

### Phase 10: Quick Code Fixes
**Goal**: Stale docstring in engine/ai.py removed; forget.py uses .resolve() for consistent path handling
**Depends on**: Phase 8
**Requirements**: (tech debt — no new requirements)
**Tech Debt**: Closes stale docstring and forget.py latent path risk from v1.5 audit

Plans:
- [ ] 10-00-PLAN.md — Fix engine/ai.py:126 docstring; add .resolve() to brain_root in forget.py forget_person()

### Phase 11: GDPR Scope Expansion
**Goal**: Implement the three GDPR capabilities that v1.5 scoped narrower than standard: sb-export CLI (data portability), runtime anonymize() function, and first-run consent prompt
**Depends on**: Phase 10
**Requirements**: GDPR-02, GDPR-03, GDPR-06
**Tech Debt**: Closes GDPR definition ambiguity from v1.5 audit
**Plans**: 4 plans

Plans:
- [ ] 11-00-PLAN.md — Wave 0 (Wave 1): test stubs (15 total: test_export.py 4, test_anonymize.py 6, test_consent.py 5) + engine/export.py stub + engine/anonymize.py stub + init_brain.py consent functions stub + pyproject.toml sb-export entry point
- [ ] 11-01-PLAN.md — Wave 1a: implement engine/export.py — export_brain() JSON export + sb-export CLI (GDPR-02 expanded)
- [ ] 11-02-PLAN.md — Wave 1b: implement engine/anonymize.py — anonymize_note() token scrubbing + atomic write + FTS5 update via trigger (GDPR-03 expanded) [parallel with 11-01]
- [ ] 11-03-PLAN.md — Wave 1c: implement prompt_consent() in engine/init_brain.py + wire into main() + human checkpoint (GDPR-06 expanded) [parallel with 11-01, 11-02]

### Phase 12: Micro-Code Fixes
**Goal**: All five v1.5 audit gaps closed — `sb-anonymize` and `sb-update-memory` are registered CLI entry points; `sb-export` initialises the DB schema before querying; `sb-reindex` stores absolute paths and preserves the `people` column
**Depends on**: Phase 11
**Requirements**: GDPR-03, GDPR-01, GDPR-05, CAP-02, AI-06
**Gap Closure**: Closes 5 requirement gaps and 4 integration gaps from v1.5 audit; restores Flow 2 (GDPR forget) and Flow 5 (sb-export)
**Success Criteria** (what must be TRUE):
  1. `sb-anonymize --help` runs without error (entry point registered)
  2. `sb-update-memory --help` runs without error (entry point registered)
  3. `sb-export` on a fresh install completes without OperationalError
  4. After `sb-reindex` then `sb-forget <person>`, DELETE matches > 0 rows (resolved path match)
  5. After `sb-reindex`, notes retain their original `people` field values

Plans:
- [ ] 12-00-PLAN.md — Wave 0: regression tests for all 5 fixes (pyproject entries, export init_schema, reindex resolve, reindex people column)
- [ ] 12-01-PLAN.md — Wave 1a: pyproject.toml — add `sb-anonymize` and `sb-update-memory` entry points (GDPR-03, AI-06)
- [ ] 12-02-PLAN.md — Wave 1b: engine/export.py — call `init_schema(conn)` after `get_connection()` (GDPR-05) [parallel with 12-01]
- [ ] 12-03-PLAN.md — Wave 1c: engine/reindex.py — `str(md_path)` → `str(md_path.resolve())`; add `people` to INSERT/DO UPDATE (GDPR-01, CAP-02) [parallel with 12-01, 12-02]
- [ ] 12-04-PLAN.md — Wave 2: manual verification checkpoint — run all 5 success criteria end-to-end

### Phase 13: Nyquist Completion
**Goal**: Phase 10 and Phase 11 reach `nyquist_compliant: true` — VALIDATION.md created for Phase 10, updated to true for Phase 11
**Depends on**: Phase 12
**Requirements**: (tech debt — no new requirements)
**Tech Debt**: Closes Nyquist compliance gap from v1.5 audit (Phase 10 missing VALIDATION.md; Phase 11 draft/false)

Plans:
- [ ] 13-00-PLAN.md — Write Phase 10 VALIDATION.md (nyquist_compliant: true); update Phase 11 VALIDATION.md to nyquist_compliant: true
- [ ] 13-01-PLAN.md — Verify all phases 1–13 are nyquist_compliant: true; run /gsd:audit-milestone to confirm clean pass

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 10/10 | Complete   | 2026-03-14 |
| 2. Storage and Index | 4/4 | Complete   | 2026-03-14 |
| 3. AI Layer | 6/6 | Complete   | 2026-03-14 |
| 4. Automation | 9/12 | In Progress|  |
| 4.1. Native macOS UX | 3/3 | Complete    | 2026-03-14 |
| 5. GDPR and Maintenance | 4/4 | Complete   | 2026-03-14 |
| 6. Integration Gap Closure | 2/4 | In Progress|  |
| 7. Fix Path Format Split | 0/2 | Pending |  |
| 8. Fix update_memory() Routing Bypass | 0/2 | Pending |  |
| 9. Nyquist Sign-off | 1/1 | Complete   | 2026-03-15 |
| 10. Quick Code Fixes | 1/1 | Complete    | 2026-03-15 |
| 11. GDPR Scope Expansion | 4/4 | Complete    | 2026-03-15 |
| 12. Micro-Code Fixes | 5/5 | Complete    | 2026-03-15 |
| 13. Nyquist Completion | 1/2 | In Progress|  |
