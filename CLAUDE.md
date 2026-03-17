# Second Brain — Project Orientation

## What this is

Personal second brain: capture, search, and surface notes via CLI, desktop GUI, and MCP server.
Core value: zero-friction capture that surfaces the right context at the right moment.

Notes stored as Markdown + YAML frontmatter in `~/SecondBrain` (Google Drive synced).
Engine code lives in this repo (`second-brain`). Brain content lives separately.

## Brain data directory

`~/SecondBrain` — env var `BRAIN_PATH` overrides.

All notes are `.md` files with YAML frontmatter. Subfolders: `coding/`, `people/`, `meetings/`,
`strategy/`, `projects/`, `personal/`, `ideas/`, `files/`, `.meta/`.

SQLite index: `~/SecondBrain/.meta/brain.db` (not Drive-synced; rebuildable via `sb-reindex`).

## Key entry points

All commands installed via `uv tool install .` (see `pyproject.toml [project.scripts]`).

| Command | Purpose |
|---------|---------|
| `sb-capture` | Capture a note (interactive CLI) |
| `sb-search` | Search notes (FTS5 + semantic hybrid) |
| `sb-gui` | Launch the desktop GUI (pywebview + Flask, port 5001) |
| `sb-api` | Start Flask HTTP sidecar only (port 5001) |
| `sb-mcp-server` | Start FastMCP stdio server for Claude Desktop / Claude.ai |
| `sb-health` | Brain health check: orphans, broken links, duplicates |
| `sb-reindex` | Rebuild SQLite index from disk |
| `sb-recap` | Session recap (recent notes + action items) |
| `sb-actions` | List pending action items |
| `sb-forget` | GDPR erasure — delete note + cascade (DB, embeddings, audit log) |
| `sb-export` | GDPR data portability — export all notes as JSON |
| `sb-anonymize` | Scrub PII tokens with atomic write |
| `sb-watch` | File watcher daemon (normally run via launchd, not manually) |

## Engine layout (`engine/`)

| Module | Purpose |
|--------|---------|
| `capture.py` | Single write path for all captures; `capture_note()` is the entry point |
| `db.py` | SQLite schema, migrations, `get_connection()` |
| `api.py` | Flask HTTP API (GUI sidecar; all GUI-facing routes) |
| `mcp_server.py` | FastMCP MCP server; all `sb_*` MCP tools |
| `intelligence.py` | Recap, action items, connections, stale nudges, digest |
| `embeddings.py` | Sentence-transformers embedding dispatch (`embed_texts()`) |
| `search.py` | FTS5 + semantic search, RRF hybrid ranking |
| `entities.py` | Regex entity extraction (people, places, topics) |
| `brain_health.py` | Orphan, duplicate, broken-link health checks |
| `paths.py` | Canonical paths: `BRAIN_ROOT`, `DB_PATH`, `CONFIG_PATH` |
| `watcher.py` | FSEvents file watcher; debounce + suppress logic |

## Database

SQLite at `~/SecondBrain/.meta/brain.db`.

Key tables: `notes`, `notes_fts` (FTS5 virtual), `note_embeddings` (sqlite-vec KNN),
`relationships`, `action_items`, `audit_log`, `attachments`.

Migrations: add-column functions in `engine/db.py`, called from `init_schema()` on startup.

## Test command

```bash
uv run pytest tests/ -q          # full suite (~15s)
uv run pytest tests/test_capture.py -x  # single file, stop on first failure
```

## MCP tools (13 tools as of Phase 27.1)

`sb_capture`, `sb_capture_batch`, `sb_search`, `sb_read`, `sb_edit`, `sb_recap`,
`sb_digest`, `sb_connections`, `sb_actions`, `sb_actions_done`, `sb_files`,
`sb_forget`, `sb_anonymize`, `sb_tools`

Configure in Claude Desktop: tool prefix `mcp__second-brain__sb_*`.

## Key gotchas

- **Intel Mac, Python 3.13 pinned.** When moving to M-chip: re-run embedding setup
  (lazy-import workaround for sentence-transformers is in place).
- **Stale launchd services.** `sb-api` and `sb-watch` may run old code after a rebuild.
  Check: `launchctl list | grep second-brain` — restart if needed.
- **No direct Anthropic API key.** User is on Anthropic Max plan. AI features use
  Claude Code/MCP adapter pattern, not direct SDK calls.
- **Two-step token pattern** for destructive MCP ops (`sb_forget`, `sb_anonymize`):
  first call returns `confirm_token`; second call with token executes. Token expires in 60s.
- **BRAIN_PATH env var** used by tests for isolation — always monkeypatch both
  `engine.db.DB_PATH` and `engine.paths.DB_PATH` in fixtures.
