# Cybernetic Second Brain

## Vision

A personal AI-augmented knowledge system — local-first, proactively intelligent, brutally secure. The system captures, links, and surfaces information across every domain of work (coding, people management, strategy, clients, personal) without the user having to manually organize it. An AI agent builds it; the user operates it via CLI, Claude Cowork, and eventually a custom GUI.

## Core Value

**Zero-friction capture that surfaces the right context at the right moment.** Information flows in through `/sb-capture`, git hooks, and file drops. The AI asks, connects, and remembers — so the user doesn't have to.

## Owner

Tuomas Leppanen — Operations Manager, Direct Manager, Team Lead, Account Manager, Developer.

---

## Architecture

### Two-Repo Model

| Repo | Contents | Sync |
|------|----------|------|
| `second-brain` (GitHub private) | Engine code, devcontainer, CLI, AI agent logic, schemas | Git |
| Brain content | All notes, files, knowledge — lives in `~/SecondBrain` | Google Drive |

`~/SecondBrain` IS the Google Drive synced folder on the host. The devcontainer bind-mounts it at `/workspace/brain`.

### Storage Layers

| Layer | What | Where |
|-------|------|-------|
| Markdown notes | Source of truth for text content | `~/SecondBrain/` (Drive-synced) |
| Binary files | Presentations, .docx, PDFs | `~/SecondBrain/files/` (Drive-synced) |
| SQLite index | Full-text search, relationships, audit log | Named Docker volume `brain-index-data` (NOT Drive-synced, rebuildable) |
| Secrets | API keys, tokens | `.env.host` (excluded from git AND Drive sync) |

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
  .meta/           # System metadata (schemas, templates) — hidden from Drive UI
```

### AI Interaction Surfaces

- **CLI commands**: `/sb-capture`, `/sb-init`, `/sb-search`, `/sb-link`, `/sb-forget`
- **Claude Code skill**: `second-brain` subagent invokable from any Claude session
- **Git hooks**: Auto-capture on commit (summarize, link to projects/people)
- **File watcher**: Detect new files dropped into `~/SecondBrain`, trigger categorization + AI questioning
- **Proactive prompting**: AI extracts important context through questioning, not passive waiting

### Multi-Model Support

The system routes requests based on content sensitivity:

| Content Type | Routing | Reason |
|-------------|---------|--------|
| Growth discussions, HR notes | Local model (Ollama) or no AI | GDPR — PII must not leave machine |
| General notes, strategy | Claude (cloud) | Full capability |
| Code, technical content | Claude Code | Best for code |

Model used is configurable per content-type in `.meta/config.toml`.

---

## Design Principles

- **KISS**: No unnecessary abstractions. If a shell script does it, don't write Python.
- **DRY**: Schema definitions in one place, referenced everywhere.
- **CODE** (Capture, Organize, Distill, Express): Every note goes through this lifecycle.
- **Atomic**: Each capture operation is a single transaction. Write-then-index; rollback if index fails.
- **Local-first**: The system works without internet. Cloud features (AI, Drive) are enhancements.
- **GDPR-aware**: PII content type-flagged; right to erasure implemented as `sb-forget <person>`; audit trail in SQLite.

---

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Engine language | Python 3.11 | Cross-platform, rich file parsing ecosystem |
| Dev environment | DevContainer (Debian-based) | Consistent across Windows/Mac |
| Note format | Markdown + YAML frontmatter | Human-readable, git-diffable, tool-agnostic |
| Index/search | SQLite (FTS5) | Zero-infrastructure, rebuildable, GDPR-erasable |
| File sync | Google Drive (host-level) | Handles binary files; user already has it |
| Code sync | GitHub private repo | Engine code versioned, brain content excluded |
| AI (primary) | Claude (Anthropic API) | Claude Code + Cowork integration |
| AI (PII/local) | Ollama (TBD) | Local model for sensitive content |
| Secrets | `.env.host` + Docker env injection | Never in git, never in Drive |

---

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Devcontainer setup works on both Windows and Mac
- [ ] Brain folder structure initialized by `/sb-init`
- [ ] `/sb-capture` CLI command captures notes to correct content type
- [ ] AI proactively questions user to extract context (not passive)
- [ ] Git hook triggers AI capture summary on commit
- [ ] File watcher detects new files and triggers categorization
- [ ] Meetings linkable to People entries
- [ ] SQLite index is rebuildable from markdown source (`/sb-reindex`)
- [ ] Secrets stored in `.env.host`, excluded from git and Drive
- [ ] GDPR: PII content routed to local model only
- [ ] GDPR: `sb-forget <person>` deletes all entries + index records for a person
- [ ] GDPR: Audit trail (created/accessed/modified) for all notes
- [ ] Multi-model support configurable per content type
- [ ] Claude Code skill (`second-brain` subagent) works in Claude sessions
- [ ] Fresh install works: clone engine + mount Drive folder + `bootstrap.py`
- [ ] System works offline (Drive sync paused)

### Out of Scope (v1)

- GUI — CLI + Cowork first; GUI is a future milestone
- Calendar sync (Google Calendar / Outlook) — valuable but adds OAuth complexity
- Mobile access — devcontainer is desktop-only
- Team/shared brain — single-user only

---

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Google Drive for brain sync (not git) | Brain contains binary files; git LFS adds friction; Drive is already the user's file sync | Google Drive |
| SQLite in named Docker volume (not Drive) | Drive sync + SQLite = corruption risk; index is rebuildable from markdown | Named volume |
| Separate engine repo from brain content | Brain is personal data; engine is code — different access patterns and risk profiles | Two-repo model |
| GDPR via content-type routing | Marking entire notes as "sensitive" is too coarse; type-level routing is automatic | Per-type model routing |
| `.env.host` for secrets | Docker secrets require Swarm; bind-mounted env file is simpler and auditable | `.env.host` |

---

## Risks & Issues Flagged

### 🔴 Critical

1. **SQLite volume loss on container rebuild**: Named volumes persist between rebuilds but NOT between machines or after `docker volume prune`. `/sb-reindex` must be implemented before any real data is stored.

2. **Windows `${localEnv:HOME}` in devcontainer**: On Windows with Docker Desktop (WSL2), home path expansion behaves differently. Needs explicit testing and possibly a Windows-specific devcontainer override.

3. **`remoteUser` mismatch**: Current `devcontainer.json` uses `root`; gcloud mount targets `/home/vscode/`. Must pick one user and be consistent or you'll get permission errors on gcloud auth.

### 🟡 Important

4. **Drive sync conflicts**: Drive is not atomic. If a note is written while Drive is syncing, conflicts can occur. Notes should use append-only writes where possible; conflict resolution needs documentation.

5. **PII in SQLite index**: Even if markdown PII stays local, the FTS5 index extracts text. The index itself must be treated as PII-containing and never synced.

6. **Binary file indexing complexity**: Parsing `.docx`, `.pptx`, `.pdf` requires `python-docx`, `python-pptx`, `pypdf`. Each has edge cases. Scope this carefully — text extraction only, no deep parsing.

7. **Model routing enforcement**: "Don't send PII to cloud" requires the system to reliably classify content type BEFORE calling an API. If classification itself calls a cloud API, you've already leaked PII. Classification must be local (regex/keyword rules or local model).

### 🟢 Nice to have

8. **No versioning of brain content**: Drive has 30-day version history. For important notes (growth discussions, strategy), consider periodic git snapshots as a separate backup.

9. **Meeting ↔ People link maintenance**: Bidirectional links between `meetings/` and `people/` need to stay consistent. A link checker (`/sb-check-links`) prevents orphans.

---

## Constraints

- No secrets ever in git or Drive sync
- PII (people notes, growth discussions) never sent to cloud AI APIs
- `pathlib.Path` throughout engine — no hardcoded path separators
- `/workspace/brain` is the canonical path inside container regardless of host OS
- Engine code follows KISS/DRY/CODE/Atomic principles
- GDPR: right to erasure, audit trail, no unauthorized data sharing

---

*Last updated: 2026-03-14 after initialization*
