# Requirements — Cybernetic Second Brain

## v1 Requirements

### Foundation (FOUND)

- [ ] **FOUND-01**: DevContainer runs correctly on macOS with correct `remoteUser: vscode`, gcloud bind-mount, and `.env.host` injection
- [ ] **FOUND-02**: DevContainer runs correctly on Windows (Docker Desktop + WSL2) with correct `${localEnv:HOME}` path expansion
- [ ] **FOUND-03**: `/sb-init` creates full brain folder structure (`coding/`, `people/`, `meetings/`, `strategy/`, `projects/`, `personal/`, `ideas/`, `files/`, `.meta/`)
- [ ] **FOUND-04**: `/sb-init` initializes SQLite schema (notes table, FTS5 index, audit log, relationships table) in named Docker volume `brain-index-data`
- [ ] **FOUND-05**: `/sb-init` validates Google Drive mount is active and writable before completing
- [ ] **FOUND-06**: `/sb-init` generates `.vscode/settings.json` hiding binary files from VS Code explorer
- [ ] **FOUND-07**: `/sb-reindex` rebuilds SQLite index fully from markdown source files (used after volume loss or fresh install)
- [ ] **FOUND-08**: Pre-commit git hook scans staged files for secrets (API keys, tokens, passwords) and blocks commit if found
- [ ] **FOUND-09**: `.env.host` is excluded from git tracking AND from Google Drive sync (`.gdriveignore` or equivalent)
- [ ] **FOUND-10**: `bootstrap.py --dev` validates environment: Drive mount, `.env.host` present, SQLite volume exists, Python deps installed
- [ ] **FOUND-11**: Fresh install procedure works: clone engine repo → mount Drive folder → run `bootstrap.py` → `/sb-init` → fully operational
- [ ] **FOUND-12**: `pathlib.Path` used throughout engine — no hardcoded path separators; `/workspace/brain` is canonical container path

### Capture & Notes (CAP)

- [ ] **CAP-01**: `/sb-capture` CLI prompts for content type, title, body, and optional tags; writes atomic markdown note with YAML frontmatter
- [ ] **CAP-02**: YAML frontmatter includes: `type`, `title`, `date`, `tags`, `people` (refs), `created_at`, `updated_at`, `content_sensitivity` (public/private/pii)
- [ ] **CAP-03**: Capture operation is atomic: write file then index; if indexing fails, file write is rolled back
- [ ] **CAP-04**: File watcher detects new files dropped into `files/` (presentations, .docx, .pdf) and triggers AI categorization prompt
- [ ] **CAP-05**: Git commit hook fires when user commits in any project directory; AI summarizes the commit and offers to link it to a brain entry
- [ ] **CAP-06**: AI automatically updates Claude memory (CLAUDE.md or memory files) when relevant project/people context is captured
- [ ] **CAP-07**: Notes use consistent Markdown templates per content type (defined in `.meta/templates/`)

### People & Meetings (PEOPLE)

- [ ] **PEOPLE-01**: `brain/people/<name>.md` profile created via `/sb-capture --type people`; includes role, notes, growth discussion history section
- [ ] **PEOPLE-02**: Meeting notes captured to `brain/meetings/` with attendees list that references `people/` entries by filename
- [ ] **PEOPLE-03**: When a meeting note is created with attendees, each referenced person's profile is auto-updated with a backlink to the meeting
- [ ] **PEOPLE-04**: `/sb-check-links` validates all people↔meetings↔projects bidirectional links and reports orphans
- [ ] **PEOPLE-05**: `/sb-search --type people <name>` returns all notes, meetings, and projects referencing that person

### Strategy & Work (WORK)

- [ ] **WORK-01**: `brain/strategy/` supports OKR notes with structured template (objective, key results, status, linked initiatives)
- [ ] **WORK-02**: `brain/projects/` supports client/account notes with client name, key contacts (linked to `people/`), status, meeting history
- [ ] **WORK-03**: `brain/coding/` supports architecture decision records (ADR) and project notes with links to GitHub repos
- [ ] **WORK-04**: `brain/ideas/` captures ideas; on capture AI asks 2-3 elaboration questions to develop the idea further

### AI Behavior (AI)

- [ ] **AI-01**: On every `/sb-capture` invocation, AI asks 2-3 proactive questions to extract context the user didn't write (questions are content-type-aware)
- [ ] **AI-02**: PII classifier runs locally (keyword rules + `content_sensitivity` frontmatter field) BEFORE any AI API call is made
- [ ] **AI-03**: Notes with `content_sensitivity: pii` are routed to Ollama (local model) only — never sent to cloud APIs
- [ ] **AI-04**: Notes with `content_sensitivity: private` or `public` are routed to Claude (Anthropic API)
- [ ] **AI-05**: Per-content-type model routing is configurable in `.meta/config.toml` without code changes
- [ ] **AI-06**: Other AI models (OpenAI, Gemini) can be added via adapter pattern in `engine/adapters/` without changing core logic
- [ ] **AI-07**: `second-brain` Claude Code subagent is installable and invokable from any Claude session
- [ ] **AI-08**: `/sb-capture` is available as a Claude Code skill (`/sb-capture`)
- [ ] **AI-09**: File watcher includes debounce (min 5s) and rate limiting to prevent runaway API calls on bulk file operations
- [ ] **AI-10**: Prompt injection protection: captured note content is never interpolated directly into system prompts; always passed as quoted user content

### Search & Retrieval (SEARCH)

- [ ] **SEARCH-01**: `/sb-search <query>` performs FTS5 full-text search across all notes with BM25 ranking
- [ ] **SEARCH-02**: `/sb-search --type <type> <query>` scopes search to a single content type folder
- [ ] **SEARCH-03**: `/sb-check-links` reports all orphaned bidirectional links across people/meetings/projects
- [ ] **SEARCH-04**: AI queries automatically retrieve relevant notes via FTS5 as context before generating responses (RAG-lite)

### GDPR & Security (GDPR)

- [ ] **GDPR-01**: `/sb-forget <person>` deletes: person's markdown file, all meeting notes that reference only that person, FTS5 shadow table entries (explicit purge), audit log entries, backlinks in other notes
- [ ] **GDPR-02**: After `/sb-forget`, FTS5 index is rebuilt (`INSERT INTO notes_fts(notes_fts) VALUES('rebuild')`) to ensure no content fragments remain
- [ ] **GDPR-03**: Every note creation, access, and modification is recorded in SQLite audit log with timestamp and operation type
- [ ] **GDPR-04**: Access control: notes with `content_sensitivity: pii` require passphrase confirmation before displaying content in CLI
- [ ] **GDPR-05**: `.env.host` secrets are never logged, never included in error messages, never written to any file except `.env.host` itself
- [ ] **GDPR-06**: Engine code passes `detect-secrets` scan (zero baseline violations) — enforced in CI

---

## v2 Requirements (Deferred)

- GUI (web or Electron) — CLI + Cowork first
- Calendar sync (Google Calendar / Outlook) — adds OAuth complexity
- Pre-meeting brief generator — needs accumulated people data to be useful
- Mobile access — devcontainer is desktop-only
- Team / shared brain — single-user only in v1
- Periodic git snapshots of brain content — Drive history is sufficient for v1
- Conflict resolution UI for Drive sync conflicts — manual resolution acceptable for v1

---

## Out of Scope

- **Cloud-hosted brain** — local-first is a hard constraint; no SaaS deployment
- **Real-time collaboration** — single-user system
- **Public sharing** — brain content is private by design
- **Automatic PII detection via NLP** — rule-based + frontmatter classification is sufficient and safer (NLP would require sending content to a model to classify it)

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| FOUND-01 – FOUND-12 | Phase 1 | Pending |
| CAP-01 – CAP-07 | Phase 2 | Pending |
| PEOPLE-01 – PEOPLE-05 | Phase 3 | Pending |
| WORK-01 – WORK-04 | Phase 3 | Pending |
| AI-01 – AI-10 | Phase 3–4 | Pending |
| SEARCH-01 – SEARCH-04 | Phase 2–4 | Pending |
| GDPR-01 – GDPR-06 | Phase 5 | Pending |

*Traceability will be updated by roadmapper agent.*
