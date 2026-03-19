# Second Brain — Project Orientation

## Mandatory first read

**Before any implementation, debugging, or testing: read `.claude/LEARNINGS.md`.**
It contains rules, deploy pipelines, and known gotchas specific to this project.

**After resolving any issue or bug: update `.claude/LEARNINGS.md`** with the root cause, fix, and rule to prevent recurrence.

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

## v4.0 Milestone (Phases 30–34) — planned

- **Phase 30**: People graph hardening — Unicode entity extraction, people column write-back, `sb_person_context` MCP tool
- **Phase 31**: Smart capture — `sb_capture_smart` (freeform → typed notes), multi-context segmentation, dormant resurfacing
- **Phase 32**: Architecture hardening — relative paths in DB, FK cascade, tags junction table, connection safety
- **Phase 33**: Performance — pagination on all list endpoints, check_connections gate, fast reindex, token budgets
- **Phase 34**: GUI productivity — interactive action items everywhere, Cmd+K palette, entity page create/delete

## Known architectural issues (tracked in Phase 32)

- DB stores **absolute paths** — moving `~/SecondBrain` orphans the entire index (fix: Phase 32-01)
- **No FK cascade** — child tables (`action_items`, `relationships`, `note_embeddings`) have no `ON DELETE CASCADE`; application-level cascade in `forget.py` only (fix: Phase 32-02)
- **Tags stored as JSON TEXT** — tag filter is a full table scan; no indexing (fix: Phase 32-03 adds `note_tags` junction table)
- **Entity extraction misses non-ASCII names** — `[A-Z][a-z]+` regex in `entities.py` skips Finnish/Nordic names (fix: Phase 30-01)

## Usage profile

- Primary interface: **MCP via Claude Desktop and Claude Code** (95% of captures). GUI is management-only.
- People graph is high priority — `sb_person_context` is the key lookup tool once Phase 30 ships.
- `sb_capture_smart` (Phase 31) will replace manual type selection for freeform capture.

## Phase plan format

Plans in `.planning/phases/NN-name/NN-XX-PLAN.md` use XML structure:
`<objective>`, `<context>` (@file refs), `<tasks>` containing `<task type="auto" tdd="true">` blocks
with `<behavior>`, `<action>`, `<verify><automated>cmd</automated></verify>`, `<done>` condition.
After each plan: create `NN-XX-SUMMARY.md` in the same directory.

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

## Devcontainer workflow

Development may happen inside a devcontainer. Detect environment at session start:
- `/workspace` exists + `UV_PROJECT_ENVIRONMENT` set → **devcontainer**
- Otherwise → **host**

**If in devcontainer:**
- Code edits, pytest, git commits — all happen here
- Do NOT start sb-api, sb-watch, or run Playwright GUI tests
- Do NOT run `npm run build` or `uv tool install` — that's the host's job
- When a phase reaches verification/checkpoint: write `VERIFY-HOST.md` in the phase directory
  with all verification steps (UI checks, API endpoints, test commands, expected results)
- Tell the user: "Verification plan written to `.planning/phases/<N>/VERIFY-HOST.md`.
  Run `/sb-verify-phase <N>` on your HOST Claude Code session to execute it."
- `node_modules` is isolated via Docker named volume — container installs don't affect host

**If on host:**
- Full pipeline available: build, install, restart, test, Playwright, browser
- `/sb-verify-phase <N>` runs the complete verification pipeline
- Always `source "$HOME/.nvm/nvm.sh"` before npm commands (nvm not auto-loaded)
- GUI URL: `http://localhost:37491/ui`
