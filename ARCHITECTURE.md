# Architecture — Second Brain

Last updated: 2026-03-20

## Overview

Personal second brain: capture, search, and surface notes via CLI, MCP server, desktop GUI, and Flask API.
Python 3.13 backend + React 19 frontend. SQLite for storage. Local-first, no cloud dependencies except Google Drive sync for note files.

```
┌─────────────────────────────────────────────────────────┐
│                    User Interfaces                       │
│  Claude Code/Desktop (MCP)  │  Browser (GUI)  │  CLI    │
└────────┬───────────────────────────┬──────────────┬─────┘
         │ stdio                     │ HTTP :37491  │ direct
    ┌────▼────┐               ┌──────▼──────┐  ┌───▼───┐
    │ FastMCP │               │  Flask API  │  │ CLI   │
    │ server  │               │  (waitress) │  │ cmds  │
    └────┬────┘               └──────┬──────┘  └───┬───┘
         │                           │             │
    ┌────▼───────────────────────────▼─────────────▼────┐
    │                   Engine Layer                      │
    │  capture │ search │ intelligence │ forget │ links  │
    └────┬──────────┬──────────┬──────────┬─────────────┘
         │          │          │          │
    ┌────▼────┐ ┌───▼───┐ ┌───▼───┐ ┌───▼──────┐
    │ SQLite  │ │ FTS5  │ │sqlite │ │ Markdown │
    │  notes  │ │ index │ │ -vec  │ │  files   │
    └─────────┘ └───────┘ └───────┘ └──────────┘
```

## Repository Layout

```
second-brain/
  engine/               Python backend — all business logic
  engine/adapters/      AI adapter implementations (Ollama, Claude)
  engine/hooks/         Git hook helpers (post-commit)
  engine/gui/           pywebview desktop GUI + static/ (compiled React)
  frontend/             React 19 + TypeScript + Vite 8 SPA source
  scripts/              Native macOS install tooling (launchd, CLI)
  tests/                pytest suite (~50 files)
  .devcontainer/        Docker devcontainer config
  .githooks/            Git hooks (post-commit, post-merge, pre-commit)
  .planning/            GSD phase planning documents
  .claude/              Project-level Claude config, learnings, security
```

Brain data: `~/SecondBrain/` (Google Drive synced). Separate from this repo.

## Engine Modules

| Module | Purpose | Key functions |
|--------|---------|---------------|
| `paths.py` | Environment detection, canonical paths | `_detect_roots()` → BRAIN_ROOT, DB_PATH |
| `db.py` | SQLite schema, migrations, connections | `init_schema()`, `get_connection()` |
| `capture.py` | Single write path for all notes | `capture_note()`, `write_note_atomic()` |
| `search.py` | FTS5 + semantic + hybrid search | `search_hybrid()`, `_rrf_merge()` |
| `embeddings.py` | Vector embeddings dispatch | `embed_texts()` — sentence-transformers or Ollama |
| `intelligence.py` | Recap, actions, connections, nudges | `generate_recap_on_demand()`, `extract_action_items()` |
| `api.py` | Flask HTTP API (40+ endpoints) | GUI sidecar on port 37491 |
| `mcp_server.py` | FastMCP stdio server (21 tools) | `sb_capture`, `sb_search`, `sb_read`, etc. |
| `router.py` | AI adapter dispatch by sensitivity | `get_adapter(sensitivity, config_path)` |
| `classifier.py` | Local PII detection (regex, no AI) | `classify()` → pii/private/public |
| `entities.py` | Regex entity extraction | People, topics, places |
| `links.py` | Backlinks, wiki-links, relationships | `add_backlinks()`, `update_wiki_link_relationships()` |
| `link_capture.py` | SSRF-safe URL metadata fetch | `fetch_link_metadata()` with IP blocklist |
| `forget.py` | GDPR erasure cascade | `forget_person()` — 10-step cascade |
| `delete.py` | Note deletion cascade | `delete_note()` — disk + 6 DB tables |
| `anonymize.py` | PII token redaction | `anonymize_note()` — atomic write |
| `reindex.py` | Full index rebuild from disk | `reindex_brain()` — walk + upsert + purge |
| `watcher.py` | FSEvents file watcher | `FilesDropHandler`, `NoteChangeHandler` |
| `brain_health.py` | Content quality checks | Orphans, duplicates, broken links, score |
| `health.py` | System component health | CLI, launchd, Ollama, MCP, git hooks |
| `digest.py` | Weekly digest generation | Idempotent, launchd-triggered |
| `rag.py` | RAG-lite context retrieval | `retrieve_context()`, `augment_prompt()` |
| `ai.py` | CLI capture AI enrichment | `ask_followup_questions()`, `update_memory()` |
| `config_loader.py` | TOML config with defaults | `load_config()` from `~/SecondBrain/.meta/config.toml` |
| `export.py` | GDPR data portability | JSON export of all notes |
| `templates.py` | Per-type note body templates | Loaded from `.meta/templates/` |
| `ratelimit.py` | Sliding window rate limiter | Used by file watcher |
| `attachments.py` | File attachment CRUD | `save_attachment()`, `list_attachments()` |

## Database Schema

SQLite at `~/SecondBrain/.index/brain.db` (host) or `/workspace/brain-index/brain.db` (container).

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `notes` | Core note store | path (UNIQUE), type, title, body, tags (JSON), sensitivity, url, people, entities |
| `notes_fts` | FTS5 virtual table | title, body — auto-synced via triggers |
| `note_embeddings` | Vector store | note_path (PK), embedding (BLOB float32), content_hash, stale |
| `relationships` | Note links | source_path, target_path, rel_type — PK is triple |
| `action_items` | Extracted actions | note_path, text, done, assignee_path, due_date |
| `attachments` | File uploads | note_path, file_path, filename, size |
| `audit_log` | GDPR accountability | event_type, note_path, detail, created_at |
| `dismissed_inbox_items` | UI state | path, item_type |

Indexes: `idx_notes_type`, `idx_notes_url`. FTS5 triggers: `notes_ai`, `notes_ad`, `notes_au`.

No FK cascade — child-table cleanup is application-level in `forget.py` and `delete.py`.

## API Endpoints (Flask, port 37491)

### Core CRUD
- `GET /notes` — list all notes
- `POST /notes` — create note
- `GET /notes/<path>` — read note (title, body, type, tags)
- `PUT /notes/<path>` — update (title, body, tags, or full)
- `DELETE /notes/<path>` — delete with cascade
- `GET /notes/<path>/meta` — backlinks, related, people

### Search & Intelligence
- `POST /search` — FTS5/semantic/hybrid search
- `GET /intelligence` — stale note nudges
- `POST /intelligence/recap` — on-demand recap generation
- `GET /brain-health` — health score, orphans, broken links, duplicates

### Domain Pages
- `GET /people`, `GET /meetings`, `GET /meetings/<path>`, `GET /projects`, `GET /projects/<path>`
- `GET /links`, `GET /links/<path>` — link notes with pagination
- `GET /actions`, `POST /actions/<id>/done`, `PUT /actions/<id>`
- `GET /inbox`, `POST /inbox/dismiss`

### Files & Attachments
- `GET /files`, `DELETE /files`, `POST /files/move`, `POST /files/upload`
- `GET /notes/attachments?path=`
- `POST /batch-capture` — index untracked .md files

### Infrastructure
- `GET /health` — liveness check
- `GET /events` — SSE stream (15s heartbeat)
- `POST /notes/refresh` — force SSE broadcast
- `POST /relationships` — create note link
- `GET /ui/prefs`, `PUT /ui/prefs` — GUI preferences
- `GET /ui`, `GET /ui/<file>` — serve React SPA

## MCP Tools (FastMCP, stdio)

21 tools exposed to Claude Desktop / Claude Code:

| Tool | Purpose |
|------|---------|
| `sb_search` | Hybrid/semantic/keyword search |
| `sb_capture` | Create note with dedup check |
| `sb_capture_batch` | Batch capture multiple notes |
| `sb_capture_link` | URL capture with og: metadata fetch |
| `sb_capture_smart` | Classify freeform text into typed suggestions |
| `sb_read` | Read note (PII → Ollama summarization) |
| `sb_edit` | Atomic body edit |
| `sb_recap` | Entity or session recap |
| `sb_digest` | Weekly digest |
| `sb_connections` | Find similar notes via embeddings |
| `sb_actions` / `sb_actions_done` | List / complete action items |
| `sb_remind` | Set due date on action |
| `sb_files` | List brain files |
| `sb_forget` | GDPR person erasure (two-step token) |
| `sb_anonymize` | PII token scrubbing (two-step token) |
| `sb_tag` | Add/remove tags with fuzzy matching |
| `sb_link` / `sb_unlink` | Create/remove note relationships |
| `sb_person_context` | Full person context dump |
| `sb_tools` | Self-introspection |

Two-step token pattern: destructive ops (`sb_forget`, `sb_anonymize`) require first call → `confirm_token` (60s expiry) → second call with token to execute.

## Frontend (React 19 + Vite 8)

Built to `engine/gui/static/`. Served by Flask at `/ui`.

### Context Providers
```
ThemeProvider → NoteProvider → SearchProvider → UIProvider → SSEProvider → App
```

### State Management
Four React contexts, no external library:
- **NoteContext**: notes list, current note, dirty state
- **SearchContext**: query, mode, results, tag filter
- **UIContext**: current view tab (notes/actions/people/meetings/projects/intelligence/inbox/links)
- **SSEContext**: EventSource connection to `/events`, triggers `loadNotes()` on changes

### Key Components
TabBar (8 views) → Sidebar (note list + search) → NoteViewer (markdown + CodeMirror editor) → RightPanel (backlinks, related, people). Domain pages: ActionsPage, PeoplePage, MeetingsPage, ProjectsPage, IntelligencePage, InboxPage, LinksPage.

### API Base Detection
Flask injects `window.API_BASE` into `index.html` at serve time. `getAPI()` in `lib/utils.ts` reads it, falls back to `http://127.0.0.1:37491`.

## Runtime Environments

### Host (macOS)

| Component | Location | Lifecycle |
|-----------|----------|-----------|
| Brain data | `~/SecondBrain/` | Google Drive synced |
| SQLite DB | `~/SecondBrain/.index/brain.db` | Rebuilt via `sb-reindex` |
| CLI commands | `~/.local/bin/sb-*` | `uv tool install --editable .` |
| sb-api | port 37491 | launchd KeepAlive (`com.secondbrain.api`) |
| sb-watch | file watcher daemon | launchd KeepAlive (`com.secondbrain.watch`) |
| sb-digest | weekly digest | launchd Monday 08:00 (`com.secondbrain.digest`) |
| Git hooks | `.githooks/` | `git config core.hooksPath .githooks` |
| Python | 3.13 (Intel Mac, nvm Node 22) | `.python-version` pinned |

Path detection: `paths._detect_roots()` → `/workspace` not found → `~/SecondBrain`.

### Devcontainer (Docker/OrbStack)

| Component | Location | Notes |
|-----------|----------|-------|
| Repo | `/workspace` (bind mount) | Shared with host — edits visible on both sides |
| Brain data | `/workspace/brain` (bind mount from `~/SecondBrain`) | Shared with host |
| SQLite DB | `/workspace/brain-index` (named volume) | Separate from host DB |
| Python venv | `/home/vscode/.venv/second-brain` | `UV_PROJECT_ENVIRONMENT` — host `.venv` untouched |
| node_modules | `/workspace/frontend/node_modules` (named volume) | Linux binaries, host macOS binaries untouched |
| Claude auth | `~/.claude/.credentials.json` | Extracted from macOS Keychain at container start |
| Claude config | `/home/vscode/.claude` (bind mount from `~/.claude`) | Settings, plugins, GSD shared with host |

Path detection: `paths._detect_roots()` → `/workspace` exists → `(/workspace/brain, /workspace/brain-index)`.

**Purpose**: code editing + pytest + git. GUI testing runs on host via `/sb-verify-phase`.

**Guardrails**: `claude-dev.sh` wrapper adds `--dangerously-skip-permissions` with system prompt safety rules. `guardrail-hook.sh` blocks brain bulk deletion and credential file reads.

### MCP Server (Claude Desktop / Claude Code)

Registered in `~/Library/Application Support/Claude/claude_desktop_config.json`. Transport: stdio. `sb-mcp-server` → `mcp.run(transport="stdio")`. All tools call `_ensure_ready()` (5s timeout) before executing.

## Data Flows

### Capture (MCP → disk + DB)
```
sb_capture() → check_capture_dedup() → capture_note()
  → build_post() → extract_entities() → write_note_atomic()
  → add_backlinks() → update_wiki_link_relationships()
  → daemon thread: check_connections() + extract_action_items()
```

### Search (query → ranked results)
```
search_hybrid() → FTS5 BM25 (2x limit) + sqlite-vec KNN (2x limit)
  → _rrf_merge(k=60) → recency boost → return top N
```

### Live Refresh (file change → browser update)
```
File write → NoteChangeHandler → _broadcast(event) → subscriber queues
  → EventSource in SSEContext.tsx → loadNotes() + openNote()
```

### PII Routing (read path)
```
sb_read(path) → check sensitivity field
  → if "pii": OllamaAdapter.summarize() (local, never sent to Anthropic)
  → if "public"/"private": return raw content to caller
```

## External Integrations

| System | Usage | Network |
|--------|-------|---------|
| **Ollama** | PII text generation (llama3.2), embeddings (nomic-embed-text) | Local: `host.docker.internal:11434` |
| **sentence-transformers** | Embeddings (all-MiniLM-L6-v2, 384d) | Local only, no network |
| **sqlite-vec** | KNN vector search | SQLite extension, local |
| **Google Drive** | Passive sync of `~/SecondBrain/` | macOS client, no API calls |
| **Claude** (subprocess) | AI adapter for public/private text | `claude -p` via Anthropic Max plan |
| **pywebview** | Desktop GUI (WKWebView on macOS) | Local only |

## Security

- **Path traversal**: `_resolve_note_path()` (api.py), `_safe_path()` (mcp_server.py)
- **SSRF**: `link_capture.py` — private IP blocklist + redirect re-validation
- **PII routing**: classifier → router → local Ollama (PII never sent to Anthropic)
- **GDPR**: forget (erasure), anonymize (redaction), export (portability), audit_log
- **Two-step tokens**: destructive MCP ops require confirm_token (60s, cryptographic)
- **Input limits**: query 500 chars, title 200, body 50K, URL 2048
- **File uploads**: MIME allowlist, `secure_filename()`, collision handling
- **Atomic writes**: tempfile + `os.replace()` everywhere
- **Error messages**: `type(e).__name__` only — no content in error strings (GDPR-05)

See `.claude/SECURITY.md` for project-specific security docs and `~/.claude/SECURITY.md` for global guardrails.

## Known Architectural Issues

1. **Absolute paths in DB** — moving `~/SecondBrain` orphans the entire index (Phase 32)
2. **No FK cascade** — child-table cleanup is application-level only (Phase 32)
3. **Tags as JSON TEXT** — no indexing, full table scan for tag filters (Phase 32)
4. **Entity extraction ASCII-only** — `[A-Z][a-z]+` misses Finnish/Nordic names (Phase 30)
5. **intelligence_state.json outside brain root** — not synced, can be lost

## Configuration

Single file: `~/SecondBrain/.meta/config.toml`. Read fresh on every `get_adapter()` call (no restart needed).

Default routing: PII → `ollama/llama3.2`, private/public → `claude`. Embeddings: `sentence-transformers` provider, batch size 32.
