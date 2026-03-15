# Second Brain

## What This Is

A local-first, AI-augmented personal knowledge CLI system. Markdown notes stored in `~/SecondBrain` (Google Drive synced), indexed by SQLite FTS5, enriched by multi-model AI (Claude for public/private content, Ollama for PII). Operated entirely via CLI commands (`sb-capture`, `sb-search`, `sb-read`, `sb-forget`, `sb-export`, `sb-anonymize`, `sb-update-memory`, `sb-reindex`, `sb-check-links`, `sb-watch`). Native macOS integration via `uv tool` global install, launchd watcher daemon, and git hook installer. GDPR-compliant with right to erasure, data export, anonymization, passphrase PII gate, and full audit log.

## Core Value

**Zero-friction capture that surfaces the right context at the right moment.** Information flows in through `sb-capture`, git hooks, and file drops. The AI asks, connects, and remembers — so the user doesn't have to.

## Owner

Tuomas Leppanen — Operations Manager, Direct Manager, Team Lead, Account Manager, Developer.

---

## Architecture

### Two-Repo Model

| Repo | Contents | Sync |
|------|----------|------|
| `second-brain` (GitHub private) | Engine code, CLI, AI agent logic, schemas | Git |
| Brain content | All notes, files, knowledge — lives in `~/SecondBrain` | Google Drive |

`~/SecondBrain` IS the Google Drive synced folder on the host.

### Storage Layers

| Layer | What | Where |
|-------|------|-------|
| Markdown notes | Source of truth for text content | `~/SecondBrain/` (Drive-synced) |
| Binary files | Presentations, .docx, PDFs | `~/SecondBrain/files/` (Drive-synced) |
| SQLite index | Full-text search, relationships, audit log | `~/SecondBrain/.meta/brain.db` (NOT Drive-synced, rebuildable) |
| Secrets | API keys, tokens | `.env` (excluded from git) |

### Brain Folder Structure

```
~/SecondBrain/
  coding/          # Projects, snippets, architecture decisions
  people/          # Per-person notes, growth discussions, 1:1s
  meetings/        # Meeting notes linked to people + projects
  strategy/        # OKRs, initiatives, roadmaps
  projects/        # Client work, account management
  personal/        # Personal notes, journal
  ideas/           # Innovation, experiments
  files/           # Binary attachments (docx, pptx, pdf)
  .meta/           # System metadata (schemas, templates, DB) — hidden
```

### AI Interaction Surfaces

- **CLI commands**: `sb-capture`, `sb-search`, `sb-read`, `sb-forget`, `sb-export`, `sb-anonymize`, `sb-update-memory`, `sb-reindex`, `sb-check-links`, `sb-watch`
- **Claude Code skills**: 10 slash commands in `.claude/commands/`
- **Git hooks**: Auto-capture on commit (summarize, link to projects/people)
- **File watcher**: `sb-watch` via launchd — detects new files dropped into `~/SecondBrain`, triggers AI categorization
- **Proactive prompting**: AI extracts context through follow-up questions on every capture

### Multi-Model Routing

| Content Type | Routing | Reason |
|-------------|---------|--------|
| PII (people notes, HR) | Local model (Ollama) | GDPR — PII must not leave machine |
| Private / general notes | Claude (via Claude Code/MCP) | Full capability |
| Code, technical content | Claude | Best for code |

Model routing configurable per content-type in `.meta/config.toml`.

---

## Design Principles

- **KISS**: No unnecessary abstractions.
- **DRY**: Schema definitions in one place, referenced everywhere.
- **CODE** (Capture, Organize, Distill, Express): Every note goes through this lifecycle.
- **Atomic**: Each capture is a single transaction. Write-then-index; rollback if index fails.
- **Local-first**: Works without internet. Cloud AI is an enhancement.
- **GDPR-aware**: PII content type-flagged; right to erasure (`sb-forget`); right to portability (`sb-export`); anonymization (`sb-anonymize`); audit trail in SQLite.

---

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Engine language | Python 3.11+ | Cross-platform, rich ecosystem |
| Install method | `uv tool install` (global) | Native macOS — no venv activation |
| Note format | Markdown + YAML frontmatter | Human-readable, git-diffable, tool-agnostic |
| Index/search | SQLite (FTS5) | Zero-infrastructure, rebuildable, GDPR-erasable |
| File sync | Google Drive (host-level) | Handles binary files; user already has it |
| Code sync | GitHub private repo | Engine code versioned, brain content excluded |
| AI (primary) | Claude (via Claude Code/MCP) | No direct API key — uses Anthropic Max plan |
| AI (PII/local) | Ollama | Local model for sensitive content |
| Daemon | launchd LaunchAgent | Native macOS autostart |
| Secrets | `.env` file | Never in git |

---

## Requirements

### Validated

- ✓ DevContainer runs correctly on macOS — v1.5
- ✓ `sb-init` creates full brain folder structure — v1.5
- ✓ `sb-init` initializes SQLite schema — v1.5
- ✓ `sb-init` validates Google Drive mount — v1.5
- ✓ `sb-reindex` rebuilds SQLite index from markdown source — v1.5
- ✓ Pre-commit hook blocks commits with secrets — v1.5
- ✓ `.env` excluded from git and Drive sync — v1.5
- ✓ `pathlib.Path` used throughout engine — v1.5
- ✓ `sb-capture` writes atomic markdown note with YAML frontmatter — v1.5
- ✓ YAML frontmatter includes all required fields (type, title, date, tags, people, created_at, updated_at, content_sensitivity) — v1.5
- ✓ Capture is atomic: rollback on index failure — v1.5
- ✓ File watcher detects new files and triggers AI categorization — v1.5
- ✓ Git commit hook fires and offers to link commit to brain entry — v1.5
- ✓ AI updates Claude memory on non-PII capture — v1.5
- ✓ Notes use per-type Markdown templates from `.meta/templates/` — v1.5
- ✓ All sb-* commands invokable from Claude Code via subagent spec — v1.5
- ✓ `~/.claude/CLAUDE.md` contains proactive capture instructions — v1.5
- ✓ People profiles auto-created and backlinked on meeting capture — v1.5
- ✓ `sb-check-links` validates bidirectional links, reports orphans — v1.5
- ✓ `sb-search --type people <name>` returns all referencing notes — v1.5
- ✓ Strategy, projects, coding, ideas content types with templates — v1.5
- ✓ PII classifier runs locally before any API call — v1.5
- ✓ PII notes routed to Ollama only — v1.5
- ✓ Non-PII notes routed to Claude — v1.5
- ✓ Per-content-type model routing configurable in config.toml — v1.5
- ✓ Adapter pattern for additional AI models — v1.5
- ✓ `second-brain` Claude Code subagent installable and invokable — v1.5
- ✓ File watcher debounce and rate limiting — v1.5
- ✓ Prompt injection protection (note content never interpolated into system prompts) — v1.5
- ✓ `sb-search` FTS5 BM25 ranked full-text search — v1.5
- ✓ `sb-search --type <type>` scopes to content type — v1.5
- ✓ RAG-lite: AI queries retrieve relevant notes as context — v1.5
- ✓ `sb-forget <person>` deletes markdown, meetings, FTS5 entries, audit log, backlinks — v1.5
- ✓ FTS5 rebuilt after `sb-forget` — v1.5
- ✓ Audit log records every note creation, access, modification — v1.5
- ✓ PII notes require passphrase before display — v1.5
- ✓ Secrets never in logs or error messages — v1.5
- ✓ Engine passes detect-secrets scan — v1.5
- ✓ Global CLI via `uv tool install` — v1.5
- ✓ launchd LaunchAgent runs `sb-watch` at login with crash restart — v1.5
- ✓ Git hook installer points any project repo at shared `.githooks/` — v1.5
- ✓ `sb-export` produces GDPR data portability JSON — v1.5
- ✓ `sb-anonymize` scrubs PII tokens with atomic write — v1.5
- ✓ First-run consent prompt in `sb-init` — v1.5
- ✓ `sb-anonymize` and `sb-update-memory` registered as CLI entry points — v1.5
- ✓ `sb-reindex` stores absolute paths and preserves `people` column — v1.5
- ✓ All 13 phases reach `nyquist_compliant: true` — v1.5

### Active (v2.0)

- [ ] Claude.ai web integration — MCP tools to expose brain commands to claude.ai sessions
- [ ] Google Drive setup automated in `sb-init` — currently requires manual configuration
- [ ] Ollama auto-installed during `sb-init` — currently requires manual setup
- [ ] Semantic / vector search — BM25-only; add embedding-based retrieval
- [ ] Encryption at rest — brain content and SQLite index unencrypted on disk

### Out of Scope

- GUI — CLI first; GUI is a future milestone beyond v2.0
- Calendar sync (Google Calendar / Outlook) — adds OAuth complexity
- Mobile access — desktop-only
- Team / shared brain — single-user only
- Cloud-hosted brain — local-first is a hard constraint
- Real-time collaboration — single-user system
- Public sharing — brain content is private by design
- Automatic PII detection via NLP — rule-based + frontmatter is sufficient and safer

---

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Google Drive for brain sync (not git) | Brain contains binary files; git LFS adds friction; Drive is already the user's file sync | Google Drive |
| SQLite in brain folder (not Docker volume) | Volume approach abandoned — native macOS install has no container; index lives in `~/SecondBrain/.meta/brain.db` | `~/SecondBrain/.meta/brain.db` |
| Separate engine repo from brain content | Brain is personal data; engine is code — different access patterns and risk profiles | Two-repo model |
| GDPR via content-type routing | Marking entire notes as "sensitive" is too coarse; type-level routing is automatic | Per-type model routing |
| No direct Anthropic API key | User has Max plan; engine uses Claude Code/MCP — no key management needed | MCP adapter pattern |
| `uv tool install` for global CLI | Native macOS — no venv activation; commands available system-wide | `uv tool` |
| launchd for watcher daemon | Native macOS — no Docker required; crash restart built in | launchd LaunchAgent |
| Stub-first TDD (Wave 0 → Wave 1) | Write all test stubs before implementation; prevents scope creep and ensures coverage | Wave-based execution |
| Sensitivity tier architecture (public / private / pii) | Three-tier model gives clear routing rules without NLP classification | Frontmatter `content_sensitivity` field |
| GDPR scope: export + anonymize + consent | v1.5 added Article 20 (export), runtime anonymize, and first-run consent — not just erasure | Full GDPR trio in v1.5 |

---

## Context

- **Codebase**: 5,348 Python LOC, 58 files
- **Development**: 186 commits, 14 phases, 60 plans, ~15 sessions, 2 days
- **Shipped**: 2026-03-15
- **Milestone**: v1.5 Second Brain MVP

---

## Risks & Issues

### Resolved in v1.5

- SQLite volume loss on container rebuild — resolved: no container; DB in brain folder, rebuildable with `sb-reindex`
- Windows `${localEnv:HOME}` devcontainer path issues — resolved: dropped DevContainer; native macOS install
- PII in SQLite index must not be synced — resolved: `.meta/brain.db` excluded from Drive sync

### Open

- **Drive sync conflicts**: Drive is not atomic. Notes should use append-only writes; conflict resolution undocumented.
- **Binary file indexing**: `.docx`/`.pptx`/`.pdf` text extraction uses python-docx/python-pptx/pypdf — each has edge cases.
- **No encryption at rest**: Brain content and index unencrypted. Covered by v2.0 active requirement.

---

## Constraints

- No secrets ever in git or Drive sync
- PII (people notes, growth discussions) never sent to cloud AI APIs
- `pathlib.Path` throughout engine — no hardcoded path separators
- Engine follows KISS/DRY/CODE/Atomic principles
- GDPR: right to erasure, right to portability, anonymization, audit trail, no unauthorized data sharing

---

*Last updated: 2026-03-15 after v1.5 milestone*
