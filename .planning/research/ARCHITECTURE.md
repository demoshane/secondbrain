# Architecture Research

**Domain:** Local-first AI personal knowledge management — v2.0 Intelligence + GUI Hub
**Researched:** 2026-03-15
**Confidence:** HIGH (existing system from PROJECT.md), MEDIUM (new integration patterns)

---

## System Overview

### Current v1.5 Architecture (baseline)

```
┌──────────────────────────────────────────────────────────────────┐
│                  CLI Entry Points (uv tool install)               │
│  sb-capture  sb-search  sb-read  sb-forget  sb-export  sb-watch   │
│  sb-anonymize  sb-reindex  sb-check-links  sb-update-memory       │
├──────────────────────────────────────────────────────────────────┤
│                       engine/ package                             │
│  capture · search · read · forget · export · anonymize            │
│  reindex · links · watcher · rag · router · classifier            │
│  ai · templates · db · config_loader · paths · ratelimit          │
│  ┌─────────────────────┐   ┌─────────────────────────────────┐   │
│  │  adapters/           │   │  hooks/                         │   │
│  │  claude_adapter.py   │   │  git commit hook installer      │   │
│  │  ollama_adapter.py   │   └─────────────────────────────────┘   │
│  │  base.py             │                                         │
│  └─────────────────────┘                                         │
├──────────────────────────────────────────────────────────────────┤
│                        Storage Layer                              │
│  ┌──────────────────────┐   ┌─────────────────────────────────┐  │
│  │  ~/SecondBrain/       │   │  ~/SecondBrain/.meta/brain.db   │  │
│  │  Markdown + YAML      │   │  SQLite FTS5 + audit_log        │  │
│  │  Google Drive synced  │   │  NOT Drive-synced, rebuildable  │  │
│  └──────────────────────┘   └─────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                     System Integration                            │
│  ┌───────────────────┐   ┌────────────────────────────────────┐  │
│  │  launchd daemon   │   │  .claude/commands/ (10 slash cmds) │  │
│  │  sb-watch         │   │  Claude Code MCP subagent          │  │
│  └───────────────────┘   └────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Target v2.0 Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                  Access Layer  (v2.0 adds GUI + MCP server)           │
│                                                                       │
│  ┌─────────────────┐  ┌──────────────────────┐  ┌─────────────────┐  │
│  │  CLI (existing) │  │  GUI Hub (new)        │  │  MCP Server     │  │
│  │  sb-* commands  │  │  Tauri + React        │  │  (new)          │  │
│  │  direct imports │  │  HTTP → localhost API │  │  FastMCP stdio  │  │
│  └────────┬────────┘  └──────────┬───────────┘  └────────┬────────┘  │
│           │                      │                        │           │
├───────────┴──────────────────────┴────────────────────────┴───────────┤
│               engine/ package  (existing + new modules)               │
│                                                                       │
│  Existing (unchanged):          New (v2.0):                           │
│  capture  search  read          api.py  (FastAPI HTTP server)         │
│  forget   export  rag           mcp_server.py  (FastMCP)              │
│  anonymize  reindex  links      embed.py  (sentence-transformers)     │
│  router   classifier  ai        crypto.py  (SQLCipher + pyrage)       │
│  adapters/  hooks/              intelligence/  (recap · digest ·      │
│                                   actions · nudge · connections)      │
├──────────────────────────────────────────────────────────────────────┤
│                         Storage Layer                                 │
│                                                                       │
│  ┌─────────────────────────┐  ┌──────────────────────────────────┐   │
│  │  ~/SecondBrain/          │  │  ~/SecondBrain/.meta/brain.db    │   │
│  │  Markdown + YAML         │  │  SQLite FTS5  (existing)         │   │
│  │  Drive-synced            │  │  + sqlite-vec embeddings  (new)  │   │
│  │  + pyrage encryption     │  │  + actions table  (new)          │   │
│  │    (optional, new)       │  │  + SQLCipher AES-256  (new)      │   │
│  └─────────────────────────┘  └──────────────────────────────────┘   │
│  ┌─────────────────────────┐                                          │
│  │  ~/.cache/sb-embed/      │                                          │
│  │  sentence-transformer    │                                          │
│  │  model (~90MB, new)      │                                          │
│  └─────────────────────────┘                                          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## New vs Existing Components

| Component | Status | Location | Connects To |
|-----------|--------|----------|-------------|
| CLI entry points (sb-*) | Existing — no change | pyproject.toml scripts | engine/* direct import |
| SQLite FTS5 + audit_log | Existing — extend schema | engine/db.py | brain.db |
| AI adapters (Claude, Ollama) | Existing — no change | engine/adapters/ | subprocess / HTTP |
| ModelRouter + PII classifier | Existing — no change | engine/router.py, classifier.py | adapters/ |
| watcher.py (launchd daemon) | Modified — session hook | engine/watcher.py | db.py, intelligence/recap.py |
| capture.py | Modified — connection hook | engine/capture.py | embed.py, intelligence/connections.py |
| search.py | Modified — --semantic flag | engine/search.py | embed.py (RRF merge) |
| forget.py | Modified — clean new tables | engine/forget.py | note_embeddings, actions tables |
| reindex.py | Modified — embedding pass | engine/reindex.py | embed.py |
| init_brain.py | Modified — Drive + Ollama automation | engine/init_brain.py | OS subprocess |
| db.py | Modified — connection factory | engine/db.py | crypto.py, new DDL |
| **api.py** | New | engine/api.py | All engine modules |
| **mcp_server.py** | New | engine/mcp_server.py | FastMCP, engine modules |
| **embed.py** | New | engine/embed.py | sentence-transformers, db.py |
| **crypto.py** | New | engine/crypto.py | sqlcipher3, pyrage, keyring |
| **intelligence/recap.py** | New | engine/intelligence/ | db.py, ai.py |
| **intelligence/digest.py** | New | engine/intelligence/ | db.py, ai.py, actions.py |
| **intelligence/actions.py** | New | engine/intelligence/ | ai.py, db.py |
| **intelligence/nudge.py** | New | engine/intelligence/ | db.py |
| **intelligence/connections.py** | New | engine/intelligence/ | embed.py, rag.py |
| **gui/** | New — Tauri + React | gui/ (repo root) | localhost:37491 HTTP |

---

## Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| engine/api.py | FastAPI HTTP facade — thin routes, no business logic, calls engine functions |
| engine/mcp_server.py | FastMCP stdio server — exposes brain commands as MCP tools |
| engine/embed.py | Embedding generation (sentence-transformers) + sqlite-vec query + RRF merge |
| engine/crypto.py | SQLCipher connection factory; pyrage file encrypt/decrypt; keyring passphrase access |
| engine/intelligence/ | Orchestrators composing db.py + ai.py + embed.py into proactive features |
| gui/ | Tauri desktop shell + React webview — UI only, no engine logic |

---

## GUI Hub: Integration Pattern

### Decision: Tauri + React + FastAPI sidecar

The GUI talks to the Python engine via a local HTTP REST API (FastAPI on `127.0.0.1:37491`). Tauri wraps the webview and manages the Python sidecar process lifecycle.

**Why Tauri over alternatives:**
- PyQt/PySide: Qt ships a heavy runtime; no web UI ecosystem; non-native look on Windows
- Electron: 150–200MB bundle; ships Chromium; memory-heavy
- Tauri: uses OS native WebView (WebKit on macOS, WebView2 on Windows); 3–10MB overhead; cross-platform; active 2026 maintenance (v2.4.x)

**Why FastAPI sidecar over direct Tauri–Python bindings (PyTauri):**
- PyTauri is a new project (Oct 2025); production readiness unclear (LOW confidence)
- FastAPI sidecar is a proven pattern with documented production examples as of Feb 2026
- FastAPI gives a clean REST API that CLI tools can also call — one surface for GUI and future integrations

**Communication path:**
```
GUI (Tauri webview React)
    └─ fetch("http://127.0.0.1:37491/search?q=...")  ← HTTP/JSON
    └─ fetch("http://127.0.0.1:37491/capture", POST)
    └─ fetch("http://127.0.0.1:37491/intelligence/recap")

engine/api.py (FastAPI on 127.0.0.1:37491)
    └─ import engine.search, capture, intelligence.*
    └─ calls engine functions in-process (no subprocess)
    └─ returns JSON responses
```

**Sidecar startup sequence:**
1. Tauri launches `sb-api` (Python/FastAPI) as a sidecar process at GUI startup
2. React polls `GET /health` until ready (5-second timeout with exponential backoff)
3. GUI renders after health check passes
4. On GUI close: Tauri sends SIGTERM; FastAPI handles graceful shutdown

**Security constraints:**
- API bound to `127.0.0.1` only — never `0.0.0.0`
- Tauri CSP policy restricts webview to only connect to localhost
- No authentication token needed (single-user, local-only)

**New pyproject.toml entry point needed:** `sb-api` — starts FastAPI on `127.0.0.1:37491`.

---

## MCP Server: Integration Pattern

### Decision: FastMCP with stdio transport

The brain is exposed to Claude.ai web and Claude Code as a local MCP server. The client spawns the process over stdio — no TCP port, no configuration beyond a one-time JSON entry.

```
Claude.ai / Claude Code
    └─ stdio ──► python -m engine.mcp_server  (spawned by MCP client)
                    └─ FastMCP @mcp.tool decorators
                    │     sb_search(query, type)
                    │     sb_capture(type, title, body)
                    │     sb_read(path)
                    │     sb_forget(person)
                    │     sb_recap(days)
                    │     sb_digest()
                    │     sb_connections(note_id)
                    └─ direct import engine.search, capture, ...
                         └─ PII routing via existing ModelRouter
```

FastMCP wraps existing engine functions as `@mcp.tool` callables. Each tool call passes through the existing PII classifier and ModelRouter — no new security logic needed.

**Configuration (one-time):** Add entry to `~/.claude/settings.json` (Claude Code) or `~/Library/Application Support/Claude/claude_desktop_config.json` (Claude Desktop). `sb-init` can write this automatically.

**Transport:** stdio (default for FastMCP, correct for local servers). No port binding, no firewall rules, no process management beyond what the MCP client handles.

---

## Vector Search: Integration Pattern

### Decision: sqlite-vec inside existing brain.db

sqlite-vec extends the existing SQLite database with a virtual table for KNN vector search. No new process, no new file — same brain.db, same connection, same GDPR erasure guarantees.

**New schema additions:**

```sql
-- Vector embeddings (sqlite-vec virtual table)
CREATE VIRTUAL TABLE note_embeddings USING vec0(
    note_id TEXT PRIMARY KEY,
    embedding FLOAT[384]     -- all-MiniLM-L6-v2 output dimensions
);

-- Action items extracted from notes
CREATE TABLE actions (
    id           TEXT PRIMARY KEY,
    source_note_id TEXT NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    action_text  TEXT NOT NULL,
    due_date     TEXT,
    status       TEXT NOT NULL DEFAULT 'open',  -- open | done | stale
    extracted_at TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
CREATE INDEX idx_actions_source ON actions(source_note_id);
CREATE INDEX idx_actions_status ON actions(status);
```

**Embedding model:** `sentence-transformers/all-MiniLM-L6-v2` — 384 dimensions, ~90MB, CPU-capable, runs fully offline. Model cached in `~/.cache/sb-embed/` (not in brain folder, not Drive-synced). First run downloads once; subsequent runs load from cache.

**PII routing:** The embedding model runs on-device for all notes including PII content. No vectors are sent to cloud APIs. sqlite-vec lives inside brain.db — `sb-forget` deletes from `note_embeddings` alongside all other note data.

**Hybrid search (RRF merge):**
```
sb-search --semantic "query"
    └─ BM25 results from FTS5  (existing)
    └─ encode query → cosine KNN from note_embeddings  (new)
    └─ Reciprocal Rank Fusion: score = Σ 1/(k + rank_i), k=60
    └─ return merged, deduplicated, re-ranked results
```
BM25 remains the default for plain `sb-search`. Semantic mode is opt-in via `--semantic` flag.

---

## Encryption at Rest: Integration Pattern

### Decision: SQLCipher (index) + pyrage (files, opt-in)

**SQLite encryption (strongly recommended):**

SQLCipher (`sqlcipher3` Python package) replaces the stdlib `sqlite3` connection. Provides transparent AES-256 encryption for brain.db. `crypto.py` becomes the connection factory that `db.py` uses — no other module changes.

Passphrase stored in system keychain (`keyring` package — uses macOS Keychain, Windows Credential Manager). Never stored in `.env`, config files, or git.

```
Any sb-* command starts
    └─ crypto.get_connection(brain_db_path)
        └─ keyring.get_password("second-brain", getpass.getuser())
        └─ conn = sqlcipher3.connect(path)
        └─ conn.execute("PRAGMA key = ?", (passphrase,))
        └─ returns encrypted connection (transparent to all callers)
```

First-run: `sb-init` generates a random 32-byte passphrase, stores it in keychain, creates encrypted brain.db.

**File encryption (opt-in, high-threat model):**

`pyrage` (Python bindings for age encryption, uploaded Jun 2025, supports CPython 3.9+ macOS + Windows) for encrypting note `.md` files. Identity key stored at `~/.config/second-brain/identity.age` (not in brain folder).

This is gated behind a config flag: `[encryption] encrypt_files = false` in `.meta/config.toml`. Default off — Drive access control is sufficient for most users. File encryption adds friction (files become binary blobs to editors and Drive search).

**Key insight:** Drive sync still works with encrypted files. Drive treats `.age` files as binary blobs and syncs them normally. The encryption/decryption is done locally by `sb-read` / `sb-capture`.

---

## Intelligence Modules: Architecture

### engine/intelligence/ — thin orchestrators only

These modules do not implement AI logic. They compose `db.py` (data retrieval), `ai.py` (model calls), and `embed.py` (similarity) into higher-level operations. Each module is a single function or a small class — no state, no DB connections of their own.

| Module | Core Function | Key Dependencies |
|--------|---------------|-----------------|
| recap.py | Summarize notes created in last N days for session-start | db.py (recent notes), ai.py (Claude/Ollama summary) |
| digest.py | Weekly summary: themes, open actions, stale items | db.py, ai.py, actions.py |
| actions.py | Extract commitments from meeting/project notes; write to actions table | ai.py (Claude extraction prompt), db.py |
| nudge.py | Find notes with no access/update in 90+ days | db.py (last_accessed query), no AI needed |
| connections.py | For a new note, find top-N related notes by embedding similarity | embed.py (cosine KNN), rag.py |

**Proactive recap trigger in watcher.py:**

`sb-watch` (launchd daemon) already runs at login. It gains a session-start detection: on first activation after system idle > 8 hours, run `recap.py`. Output via `osascript` macOS notification or printed to any open terminal. Once-per-session flag stored in `~/SecondBrain/.meta/session.json` (reset on new day).

**PII routing is inherited:** All intelligence modules call `ai.py`, which calls the existing ModelRouter. Recap of PII notes routes to Ollama. No new routing logic needed.

---

## Setup Automation: Changes to init_brain.py

Two additions to `sb-init`, both gated by user consent prompts:

**Google Drive validation (modify existing):** Currently checks if brain directory is mounted. Extend to guide setup if not found. macOS: check `~/Library/CloudStorage/GoogleDrive-*/` pattern. If not found: print Drive install URL and wait for user confirmation before proceeding. Do not auto-install Drive (requires browser OAuth, outside subprocess scope).

**Ollama auto-install (new):** Check `which ollama`. If missing:
- macOS with Homebrew: `brew install ollama`
- macOS without Homebrew: download from `https://ollama.ai/download/mac`
- Windows: download installer via PowerShell `Invoke-WebRequest`

After install: pull default model (`ollama pull llama3.2:3b` — 2GB, reasonable default). Entire flow gated by explicit user `y/n` prompt.

---

## Data Flow Changes

### Capture Flow (v2.0 additions shown)

```
sb-capture (CLI) or GUI capture form
    │
    ▼
engine/capture.py
    ├── Write markdown note (atomic, unchanged)
    ├── Index in FTS5 (unchanged)
    ├── PII routing + AI proactive prompt (unchanged)
    ├── [NEW] embed.py: generate embedding → INSERT note_embeddings
    └── [NEW] intelligence/connections.py: KNN → surface related notes to user
```

### Search Flow (v2.0 additions shown)

```
sb-search "query" [--semantic]
    │
    ▼
engine/search.py
    ├── FTS5 BM25 results (existing path, always runs)
    └── [--semantic only]
        ├── embed.py: encode query string
        ├── sqlite-vec KNN on note_embeddings
        └── RRF merge of BM25 + cosine results → return re-ranked list
```

### Session Recap Flow (new)

```
sb-watch (launchd daemon, running at login)
    └── On activation after idle > 8h AND date changed since last recap
        └── intelligence/recap.py
            ├── db.py: SELECT notes WHERE created_at > (now - 7d)
            ├── ai.py: summarize via Claude (non-PII) or Ollama (PII)
            └── output recap → macOS notification + stdout
```

### GUI ↔ Engine Flow (new)

```
Tauri webview (React)
    └── fetch("http://127.0.0.1:37491/search?q=foo")
    └── fetch("http://127.0.0.1:37491/capture", {method: POST, body: ...})
    └── fetch("http://127.0.0.1:37491/intelligence/recap")

engine/api.py (FastAPI, 127.0.0.1:37491)
    └── route handler calls engine.search.search() directly (in-process)
    └── returns JSON — same data as CLI stdout, structured
```

### MCP Tool Flow (new)

```
Claude.ai or Claude Code
    └── MCP tool call: sb_search(query="Alice workload")
        └── stdio → engine/mcp_server.py (FastMCP, spawned process)
            └── @mcp.tool function → engine.search.search("Alice workload")
            └── returns ToolResult with structured note list
```

---

## Recommended Project Structure (v2.0)

```
second-brain/
├── engine/
│   ├── __init__.py
│   ├── adapters/
│   │   ├── base.py
│   │   ├── claude_adapter.py
│   │   └── ollama_adapter.py
│   ├── hooks/
│   ├── intelligence/               # NEW sub-package
│   │   ├── __init__.py
│   │   ├── recap.py
│   │   ├── digest.py
│   │   ├── actions.py
│   │   ├── nudge.py
│   │   └── connections.py
│   ├── ai.py
│   ├── anonymize.py
│   ├── api.py                      # NEW — FastAPI HTTP server
│   ├── capture.py                  # MODIFIED — embed + connections hook
│   ├── classifier.py
│   ├── config_loader.py
│   ├── crypto.py                   # NEW — SQLCipher + pyrage + keyring
│   ├── db.py                       # MODIFIED — uses crypto.py, new tables
│   ├── embed.py                    # NEW — sentence-transformers + sqlite-vec
│   ├── export.py
│   ├── forget.py                   # MODIFIED — cleans note_embeddings + actions
│   ├── init_brain.py               # MODIFIED — Drive guidance + Ollama install
│   ├── links.py
│   ├── mcp_server.py               # NEW — FastMCP server
│   ├── paths.py
│   ├── rag.py
│   ├── ratelimit.py
│   ├── read.py
│   ├── reindex.py                  # MODIFIED — embedding generation pass
│   ├── router.py
│   ├── search.py                   # MODIFIED — --semantic + RRF merge
│   ├── templates.py
│   └── watcher.py                  # MODIFIED — session-start recap trigger
├── gui/                            # NEW — Tauri + React desktop app
│   ├── src-tauri/
│   │   ├── src/                    # Rust Tauri shell (minimal — just sidecar mgmt)
│   │   └── tauri.conf.json
│   ├── src/                        # React + TypeScript
│   │   ├── components/
│   │   ├── pages/
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── tests/
├── scripts/
├── pyproject.toml                  # MODIFIED — new deps + sb-api entry point
└── uv.lock
```

---

## Architectural Patterns

### Pattern 1: Engine-as-Library (existing, extended)

**What:** All CLI commands, the API server, and the MCP server import engine modules directly. No subprocess calls between engine components.
**When to use:** Always for intra-engine communication.
**Trade-offs:** Single process per entry point; no module isolation. Acceptable for a single-user tool.

### Pattern 2: Thin HTTP Facade (new for GUI)

**What:** `engine/api.py` is a thin FastAPI wrapper — each route calls one engine function and returns its result as JSON. Zero business logic in the API layer.
**When to use:** GUI integration only. CLI commands remain direct imports.
**Trade-offs:** GUI requires the API server process to be running. Mitigated by Tauri sidecar auto-launch.

```python
# Pattern: route calls function, returns JSON — nothing else
@app.get("/search")
async def search(q: str, type: str = None, semantic: bool = False):
    return engine.search.search(q, content_type=type, semantic=semantic)
```

### Pattern 3: Intelligence as Orchestrators (new)

**What:** `intelligence/*` modules compose `db.py` + `ai.py` + `embed.py` — they own no state and hold no DB connections.
**When to use:** All intelligence features. Keeps logic testable and swappable.
**Trade-offs:** Multiple dependencies per module. Keep them thin — push reusable logic into db.py or ai.py, not into intelligence modules.

---

## Anti-Patterns

### Anti-Pattern 1: GUI Shelling Out to CLI Commands

**What people do:** GUI shell-execs `sb-search`, `sb-capture` etc. as subprocesses and parses stdout.
**Why it's wrong:** ~300ms process spawn latency per call; output format coupling; brittle error handling.
**Do this instead:** GUI calls `GET /search`, `POST /capture` on the local FastAPI server. Engine runs in-process.

### Anti-Pattern 2: Separate Vector Database Process

**What people do:** Run ChromaDB or Qdrant as a separate server for vector search.
**Why it's wrong:** Extra infrastructure for a single-user tool. sqlite-vec runs inside existing brain.db — no separate process, no ops overhead, same GDPR erasure path.
**Do this instead:** sqlite-vec virtual table inside brain.db, loaded as a SQLite extension.

### Anti-Pattern 3: MCP Server on a TCP Port

**What people do:** Bind the MCP server to a localhost TCP port.
**Why it's wrong:** Port management, potential conflicts, more firewall surface. Stdio is the correct transport for local MCP servers spawned by a client.
**Do this instead:** FastMCP with stdio transport. Client spawns the process; no port needed.

### Anti-Pattern 4: Passphrase in .env

**What people do:** Put the SQLCipher passphrase in `.env` alongside API keys.
**Why it's wrong:** `.env` is a plaintext file. Storing the encryption key next to the ciphertext negates the encryption.
**Do this instead:** `keyring.get_password()` at connection time. Passphrase lives in OS keychain only.

### Anti-Pattern 5: Loading Embedding Model Per-Request

**What people do:** Instantiate `SentenceTransformer(...)` inside the search function, so it loads on every call.
**Why it's wrong:** Model load is ~1–2 seconds cold start. Ruins interactive search latency.
**Do this instead:** Load model once at `embed.py` module level (or in `api.py` startup) and reuse across calls.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Claude (AI) | subprocess `claude -p` via claude_adapter.py | Existing, no change |
| Ollama | HTTP GET/POST localhost:11434 | Existing, no change |
| Google Drive | Filesystem — files appear at mount path | No API, no change |
| Claude.ai / Claude Code (MCP) | FastMCP stdio — spawned by MCP client | New — one-time config in Claude settings |
| sentence-transformers | Python import, model downloaded once to ~/.cache/sb-embed/ | New — first run ~90MB download |
| sqlite-vec | SQLite extension loaded via `conn.load_extension()` | New — installed as Python package |
| SQLCipher | Replaces sqlite3 connection in crypto.py factory | New — sqlcipher3 package |
| keyring | OS keychain access via Python keyring package | New — no config, uses OS credential store |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CLI ↔ engine | Direct Python import | No change |
| GUI ↔ engine | HTTP REST via localhost FastAPI | New — webview cannot import Python |
| Claude.ai ↔ engine | MCP stdio via FastMCP | New — spawned by MCP client |
| intelligence/* ↔ db.py | Direct import | intelligence modules own no state |
| intelligence/* ↔ ai.py | Direct import | PII routing still applies inside ai.py |
| embed.py ↔ db.py | Direct import — embed uses crypto.get_connection() | embed owns no connection |
| crypto.py ↔ db.py | crypto.py IS the connection factory — db.py calls it | All DB access goes through crypto.py |

---

## Suggested Build Order

Dependencies drive this order strictly. Encryption touches everything that writes to db — it must come first.

```
Step 1: crypto.py + db.py migration
    Rationale: SQLCipher connection factory; every other module
    depends on db.py. Migrate before adding new data writers.
    Risk: highest data integrity risk — do first with backup/restore test.

Step 2: embed.py + sqlite-vec schema (note_embeddings table)
    Rationale: search.py --semantic and intelligence/connections.py
    both depend on this. Needed before any intelligence module.

Step 3: intelligence/ modules
    Rationale: all use db.py (now encrypted) + ai.py.
    connections.py also needs embed.py (step 2 complete).
    Can be built incrementally — each module is independent.

Step 4: engine/api.py (FastAPI)
    Rationale: GUI depends on this being complete and stable.
    Build and verify all endpoints before starting GUI work.

Step 5: GUI hub (Tauri + React)
    Rationale: depends on api.py (step 4). Longest build — frontend
    toolchain (Node, Rust) separate from Python engine.

Step 6: engine/mcp_server.py (FastMCP)
    Rationale: independent of GUI. Can run in parallel with step 5.
    Depends only on engine modules (steps 1–3 complete).

Step 7: init_brain.py automation (Drive + Ollama)
    Rationale: fully independent. No other feature depends on it.
    Can slot anywhere after step 1. Lowest risk, lowest coupling.
```

---

## Scaling Considerations

Single-user local system. Scale concerns are note volume and feature latency, not concurrency.

| Scale | Concern | Approach |
|-------|---------|----------|
| < 10k notes | All features fast | Default behavior |
| 10k–50k notes | Reindex embedding pass takes minutes | Background threading in reindex.py; progress output |
| 50k+ notes | sqlite-vec KNN scan may slow (full table scan) | Add sqlite-vec IVF/HNSW index — available in extension |
| Large binary files | PDF/docx extraction in reindex | Already handled; no change needed |

The embedding model cold-start (~1–2s) is the main latency concern for interactive use. Mitigated by keeping the model loaded in the FastAPI server process (loaded once at startup, reused for all requests). CLI tools load it on first invocation in a session — acceptable for batch reindex, slightly noticeable for single-note capture.

---

## Sources

- [FastMCP documentation — stdio transport](https://gofastmcp.com/deployment/running-server) — MEDIUM confidence (official project site)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — HIGH confidence (official Anthropic repo)
- [sqlite-vec GitHub — asg017/sqlite-vec](https://github.com/asg017/sqlite-vec) — HIGH confidence (official repo, active development)
- [sentence-transformers documentation](https://www.sbert.net/) — HIGH confidence (official docs)
- [Tauri v2 architecture docs](https://v2.tauri.app/concept/architecture/) — HIGH confidence (official docs, v2.4.x current as of 2026)
- [tauri-fastapi production template](https://github.com/fudanglp/tauri-fastapi-full-stack-template) — MEDIUM confidence (community reference, Feb 2026)
- [Tauri v2 Python sidecar example](https://github.com/dieharders/example-tauri-v2-python-server-sidecar) — MEDIUM confidence (community)
- [SQLCipher Python implementation — Feb 2026](https://oneuptime.com/blog/post/2026-02-02-sqlcipher-encryption/view) — MEDIUM confidence
- [pyrage on PyPI](https://pypi.org/project/pyrage/) — MEDIUM confidence (Python age bindings, Jun 2025, macOS + Windows support confirmed)
- [PyTauri GitHub](https://github.com/pytauri/pytauri) — LOW confidence for direct use (Oct 2025, new project; FastAPI sidecar preferred)

---

*Architecture research for: Second Brain v2.0 — Intelligence + GUI Hub*
*Researched: 2026-03-15*
