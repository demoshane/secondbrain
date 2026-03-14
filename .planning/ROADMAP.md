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
- [ ] **Phase 3: AI Layer** - PII classifier, ModelRouter, Ollama + Anthropic adapters, proactive questioning, Claude subagent
- [ ] **Phase 4: Automation** - File watcher, git hooks, people/meetings/work features, RAG-lite retrieval
- [ ] **Phase 5: GDPR and Maintenance** - Full erasure cascade, FTS5 rebuild, access control on PII notes

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
**Plans**: TBD

### Phase 5: GDPR and Maintenance
**Goal**: Right to erasure is complete and verifiable — no content fragment for a deleted person survives in markdown, binary attachments, SQLite rows, or FTS5 shadow tables; PII notes require passphrase confirmation before display
**Depends on**: Phase 4
**Requirements**: GDPR-01, GDPR-02, GDPR-04
**Success Criteria** (what must be TRUE):
  1. After `/sb-forget <person>`, that person's markdown file is absent, all meeting notes referencing only them are absent, and `/sb-search <person>` returns zero results including zero FTS5 fragments
  2. `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` is confirmed executed after every `/sb-forget` call (visible in audit log or test assertion)
  3. Attempting to display a note with `content_sensitivity: pii` without the correct passphrase produces an access-denied message and no note content is printed
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 10/10 | Complete   | 2026-03-14 |
| 2. Storage and Index | 4/4 | Complete   | 2026-03-14 |
| 3. AI Layer | 5/6 | In Progress|  |
| 4. Automation | 0/TBD | Not started | - |
| 5. GDPR and Maintenance | 0/TBD | Not started | - |
