# Second Brain — Project Orientation

## Mandatory first read

**Before any implementation, debugging, or testing: read `.claude/LEARNINGS.md`.**

## Non-negotiable frontend rules — apply to every plan and every task, no exceptions

These are not guidelines. Skipping any of these is not acceptable.

**1. New UI must follow Visily designs.**
Before planning or implementing any new frontend feature, locate and read the relevant
Visily design. Do not invent layouts, components, or visual patterns. If no design exists,
stop and ask before proceeding.

**2. Before touching existing frontend code, fully understand how it works.**
Read the component, trace its data flow, state, API calls, and side effects end to end.
Identify every place the code is used and what depends on it. A change that looks local
often breaks something upstream or downstream. Do not write a single line until you have
this picture.

**3. Understand the business context and user workflow before implementing.**
Know why the change exists, which user problem it solves, how it connects to the rest of
the app, and what the expected user journey looks like. Every change must feel native —
consistent interaction patterns, coherent information hierarchy, no jarring transitions.
If you cannot articulate the "why" and the "big picture", you are not ready to implement.

**When fixing a bug:** before writing any code, identify every place the same bug can appear — other components, pages, or code paths that share the same pattern or call the same function. Fix all of them. Don't patch the one instance you found first and stop.

**After resolving a bug:** only add to LEARNINGS.md if the rule is **universally applicable** to future work in this project AND not already covered by CLAUDE.md. One-time fixes, generic coding mistakes, and already-fixed code patterns belong in git history, not LEARNINGS.md. Keep the file under 80 lines.

**If a UAT step fails and the issue is reproducible in the GUI:** debug it with Playwright tests directly — no permission prompts needed unless the action is destructive. Fix the issue and re-run until the UAT step passes.

**After implementing any fix or feature:** verify it actually works from the user's point of view before declaring done.
- Backend changes: run a focused pytest (`-k filter`) or make a direct API call to confirm the behaviour.
- Frontend changes: use Playwright to exercise the real UI flow — click through the feature, confirm the visible result.
- If `make dev` hasn't been run yet, say so explicitly and list what needs deploying before verification is possible.
- Do not rely on "code looks correct" alone — a fix that works in source but fails at runtime (stale service, missing migration, wrong env) is not done.

## What this is

Personal second brain: capture, search, and surface notes via CLI, desktop GUI, and MCP server.
Core value: zero-friction capture that surfaces the right context at the right moment.

Notes stored as Markdown + YAML frontmatter in `~/SecondBrain` (Google Drive synced).
Engine code lives in this repo (`second-brain`). Brain content lives separately.

## Brain data directory

`~/SecondBrain` — env var `BRAIN_PATH` overrides.

All notes are `.md` files with YAML frontmatter. Subfolders: `coding/`, `people/`, `meetings/`,
`strategy/`, `projects/`, `personal/`, `ideas/`, `files/`, `.meta/`.

SQLite index: `~/SecondBrain/.index/brain.db` (not Drive-synced; rebuildable via `sb-reindex`).

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

SQLite at `~/SecondBrain/.index/brain.db`.

Key tables: `notes`, `notes_fts` (FTS5 virtual), `note_embeddings` (sqlite-vec KNN),
`relationships`, `action_items`, `audit_log`, `attachments`.

Migrations: add-column functions in `engine/db.py`, called from `init_schema()` on startup.

## Test command

```bash
uv run pytest tests/ -q          # full suite (~15s)
uv run pytest tests/test_capture.py -x  # single file, stop on first failure
```

## MCP tools (22 tools as of Phase 30-03)

`sb_capture`, `sb_capture_batch`, `sb_capture_smart`, `sb_capture_link`,
`sb_search`, `sb_read`, `sb_edit`, `sb_recap`, `sb_digest`, `sb_connections`,
`sb_actions`, `sb_actions_done`, `sb_files`, `sb_forget`, `sb_anonymize`,
`sb_tools`, `sb_tag`, `sb_remind`, `sb_link`, `sb_unlink`,
`sb_person_context`, `sb_list_persons`

Configure in Claude Desktop: tool prefix `mcp__second-brain__sb_*`.

### Capture session grouping (Phase 56)

`sb_capture` accepts `session_id` — a UUID grouping captures from the same conversation
thread. Notes sharing a session_id are auto-linked as `co-captured` regardless of time gap.
Without session_id, captures are linked by temporal proximity (15-minute window).

Session IDs are persistent — reuse the same ID when a topic continues in a later conversation,
even days apart. The `capture_session` is stored in the DB and retrievable via
`GET /capture-session/<id>`. `sb_capture_smart` returns a `capture_session` UUID that can
be reused as `session_id` in subsequent `sb_capture` calls.

## Usage profile

- Primary interface: **MCP via Claude Desktop and Claude Code** (95% of captures). GUI is management-only.

## Phase execution strategy

**At the end of every `/gsd:plan-phase` run, always output an execution strategy recommendation before the Next Up block.**

Evaluate by checking `files_modified` overlap across all plans in the phase:

**Use `direct` (single-agent, tell user to instruct Claude directly) when:**
- Any two plans share a file in `files_modified` — parallel agents will conflict
- Tasks are mechanical sweeps or incremental additions to existing functions
- No fresh module creation; all work is inside existing files

**Use `multi-agent` (`/gsd:execute-phase`) when:**
- All plans have zero `files_modified` overlap
- Each plan creates a new independent module or subsystem
- Tasks require deep isolated context (different domains, no shared state)

Output at end of planning:
```
Execution strategy: direct  ← tell Claude to execute, do NOT run /gsd:execute-phase
Reason: Plans 33-01 and 33-04 both modify api.py and mcp_server.py
```
or:
```
Execution strategy: multi-agent  ← safe to run /gsd:execute-phase
Reason: All plans touch independent files, no overlap
```

Tag each plan's frontmatter with `execution_strategy: direct | multi-agent`.

**Why this matters:** Multi-agent burns quota via orchestrator overhead and causes scope leaks when agents share files. Phase 32 example: multi-agent wasted ~500k tokens; single-agent did the same work in 5 minutes.

## Phase plan format

Plans in `.planning/phases/NN-name/NN-XX-PLAN.md` use XML structure:
`<objective>`, `<context>` (@file refs), `<tasks>` containing `<task type="auto" tdd="true">` blocks
with `<behavior>`, `<action>`, `<verify><automated>cmd</automated></verify>`, `<done>` condition.
After each plan: create `NN-XX-SUMMARY.md` in the same directory.

## Build & deploy (host)

Use the Makefile — never do these steps manually:

```bash
make dev      # build frontend + reinstall (--editable --force) + restart launchd services
make restart  # reinstall + restart services only (skip frontend build)
make test     # run full test suite
make e2e      # run all Playwright tests (Python + TypeScript, headless)
```

`make dev` is the single command for all code changes. Always use it instead of
`uv tool install .` (which uses a cached wheel and may not pick up source changes).
Launchd service names: `com.secondbrain.api`, `com.secondbrain.watch`.


## Key gotchas

- **macOS 26 (Darwin 25.x).** `sentence-transformers` cannot install (no torch wheel).
  Embeddings use Ollama (`nomic-embed-text`) — configured in `~/SecondBrain/.meta/config.toml`.
- **Stale launchd services.** `sb-api` and `sb-watch` may run old code after a rebuild.
  Always use `make dev` / `make restart` — never `launchctl` directly.
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
- Code edits, pytest, git commits, Playwright e2e tests — all happen here
- `make e2e` runs both Python and TypeScript Playwright tests (headless, auto-starts Flask)
- `make dev` builds frontend + reinstalls Python package (no launchd restart)
- `node_modules` is isolated via Docker named volume — container installs don't affect host
- **Host-only:** `make restart` (launchd services), testing against real brain data

**If on host:**
- Full pipeline available: build, install, restart, test, Playwright, browser
- `/sb-verify-phase <N>` runs the complete verification pipeline
- Always `source "$HOME/.nvm/nvm.sh"` before npm commands (nvm not auto-loaded)
- GUI URL: `http://localhost:37491/ui`
- To run TS e2e against the running service: `E2E_BASE_URL=http://localhost:37491 npx playwright test`
