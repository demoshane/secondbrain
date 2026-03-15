# Stack Research

**Domain:** v2.0 additions — Python CLI second brain app (GUI hub, vector search, encryption at rest, intelligence layer, MCP server)
**Researched:** 2026-03-15
**Confidence:** MEDIUM-HIGH (versions verified via PyPI/official sources; GUI tradeoffs noted honestly)

---

## Context: v1.5 Stack Is Locked — Do Not Re-Research

The following are already validated and shipped. This document covers ONLY new additions for v2.0.

| Component | Choice | Status |
|-----------|--------|--------|
| Language | Python 3.11+ | Locked |
| Install | `uv tool install` (global) | Locked |
| CLI | Typer + Rich | Locked |
| Full-text search | SQLite FTS5 BM25 | Locked — extended in v2.0 |
| AI adapters | Claude (MCP/subprocess) + Ollama | Locked |
| Daemon | launchd LaunchAgent (macOS) | Locked |
| Note format | Markdown + YAML frontmatter | Locked |
| DB | `brain.db` SQLite (sqlite-utils) | Extended in v2.0 (encryption) |

---

## Recommended Stack — New Additions for v2.0

### 1. GUI Hub

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pywebview | 5.4 | Cross-platform desktop window wrapping HTML/CSS/JS | Pure Python; installable via `uv tool install` with no extra toolchain; uses native WebView2 on Windows (pre-installed on Win10/11 since 2021) and WebKit on macOS; Flask backend runs in-process; no Electron/Chromium bundle; binary wheel available |
| Flask | >=3.0 | In-process HTTP server behind pywebview window | Already a common transitive dep; zero-config single-file server; pywebview's two-way JS bridge (`window.pywebview.api`) calls Python methods directly without REST overhead |

**Why not Electron:** Bundles Chromium (~300 MB); requires Node.js toolchain alongside Python; cross-language IPC adds complexity; binary distribution requires separate packaging pipeline.

**Why not Tauri + PyTauri:** PyTauri is pre-1.0 (v0.8, last commit Feb 2026); requires Rust toolchain to build; not suitable for production. Revisit when PyTauri reaches 1.0.

**Why not PyQt6 / PySide6:** Widget-based layout system requires learning Qt internals; HTML/CSS frontend reuses web skills and shares with any future web UI; PyQt6 is GPL (forces open-source or paid commercial license); PySide6 (LGPL) is acceptable but heavier install than pywebview.

**Why not Textual:** TUI (terminal UI), not a desktop GUI — does not satisfy "cross-platform desktop GUI hub" requirement; cannot render rich note previews or graph-style visualizations.

**Distribution:** pywebview apps are distributable as `uv tool install` just like current CLI. No PyInstaller needed. Users run `sb-gui` entry point.

---

### 2. Vector / Semantic Search

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| sqlite-vec | 0.1.6 (stable) | KNN vector search as SQLite extension inside `brain.db` | Runs inside the existing `brain.db`; no new infrastructure process; replaces deprecated `sqlite-vss` (same author); SIMD-accelerated C extension; Python wheel on PyPI; local-first; supports cosine and L2 distance |
| sentence-transformers | 5.3.0 | Generate local embeddings on CPU without any API | Pure Python; `all-MiniLM-L6-v2` model (~22 MB, 384-dim vectors) runs at 5–14k sentences/sec on CPU; no internet required after first model download; fully GDPR-safe for PII notes |

**Embedding model:** Use `all-MiniLM-L6-v2` — best speed/quality tradeoff for CPU-only inference at this note volume. First run downloads ~90 MB from HuggingFace and caches to `~/.cache/huggingface/`. For notes already flagged `content_sensitivity: pii`, this is the only compliant option (no cloud API).

**Search architecture:** Hybrid BM25 + KNN. FTS5 BM25 (existing) runs in parallel with sqlite-vec KNN cosine search. Results merged with Reciprocal Rank Fusion (RRF) — a pure Python function of ~10 lines, no new library. Hybrid consistently outperforms either alone.

**sqlite-vec note:** Version 0.1.7 is in pre-release (alpha as of Jan 2025). Pin to 0.1.6 stable; upgrade once 0.1.7 reaches stable.

**Why not ChromaDB:** Separate server process; ~500 MB dependency tree; violates local-first constraint; overkill for single-user note volume.

**Why not Weaviate / Pinecone:** Cloud-oriented; local-first is a hard constraint.

**Why not sqlite-vss:** Deprecated by the same author (Alex Garcia) in favor of sqlite-vec. Do not use.

**Why not Ollama embeddings as primary:** Ollama `/api/embeddings` is usable as fallback for GPU users, but requires the Ollama daemon running; adds startup latency; sentence-transformers is faster on CPU for sub-100-token notes.

---

### 3. Encryption at Rest

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| sqlcipher3-binary | 0.6.2 | Transparent AES-256 encryption of entire `brain.db` | Drop-in replacement for stdlib `sqlite3`; encrypts FTS5 tables, vector tables, audit log — everything; `-binary` variant ships pre-compiled SQLCipher (no external `libsqlcipher` needed); binary wheels available for macOS arm64/x86_64 and Windows amd64/arm64/win32; released Jan 7 2026 |
| cryptography | >=42.0 | Fernet symmetric encryption for individual PII markdown files | AES-128-CBC + HMAC integrity check; handles IV, padding, authentication automatically; PyCA library — well-audited; already a transitive dep of many security packages; binary wheels on all platforms |
| keyring | 25.7.0 | OS-native secure storage for DB passphrase and file encryption key | Uses macOS Keychain on Mac, Windows Credential Manager on Windows; zero user friction after first unlock; keys never stored in `.env` or config files; no extra deps on Mac/Windows |

**Encryption scope decision (critical):**

- `brain.db` — fully encrypted with SQLCipher. One passphrase stored in OS keyring. All tables (FTS5, notes index, vector store, audit log) are transparently encrypted at the file level.
- Markdown notes with `content_sensitivity: pii` — encrypted at rest with Fernet (file-level). `cryptography` library handles this.
- Markdown notes with `content_sensitivity: private` or `public` — NOT encrypted. Rationale: Drive sync computes diffs on plaintext; encrypting all notes breaks Google Drive sync, breaks `sb-check-links`, and breaks git history legibility. Drive's own at-rest encryption covers non-PII content.

**Key hierarchy:** One SQLCipher DB passphrase + one Fernet file key, both stored in OS keyring. Derived from a single user passphrase via PBKDF2 on first `sb-init --encrypt`.

**Migration:** Existing unencrypted `brain.db` requires a one-time migration in `sb-init --encrypt`: read plaintext → write encrypted copy → verify round-trip → swap files. Phase must include explicit rollback path (keep `brain.db.plaintext.bak` until verification passes).

**Why not pysqlcipher3:** Abandoned since 2020; no binary wheels for Windows; requires manual SQLCipher install.

**Why not column-level encryption (SQLAlchemy pattern):** Does not encrypt FTS5 or vector tables; defeats the purpose; breaks full-text search.

---

### 4. Intelligence Layer (Proactive Features)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| APScheduler | 3.11.2 | Background scheduling for weekly digest and stale nudge triggers | In-process scheduler; no separate cron daemon; cron trigger supports `day_of_week`/time expressions; integrates with existing launchd `sb-watch` daemon; **pin `<4.0`** — v4 is a breaking API rewrite with different architecture |

**Intelligence features require no new AI libraries.** All proactive features (session recap, action item extraction, weekly digest, stale nudges, connection surfacing, cross-context synthesis) are implemented as a new `engine/intelligence.py` module that:

1. Queries SQLite for relevant notes/metadata
2. Builds a structured context window
3. Dispatches to the existing Claude MCP adapter

The intelligence layer is pure Python + existing dependencies.

**Session detection:** No new library. Compare last `sb-capture` timestamp in audit log against current time. Gap > 4 hours = new session. One SQLite query.

**Stale note detection:** Pure SQLite — `SELECT path FROM notes WHERE last_accessed < date('now', '-90 days')`. No library needed.

**Action item extraction:** Structured prompt to Claude adapter with meeting note content. Response parsed with stdlib `re` or `json`. No new library.

**Connection surfacing:** Run on each new capture — query sqlite-vec for KNN neighbors of the new note's embedding with cosine similarity > 0.8. Already covered by vector search infrastructure.

---

### 5. Claude.ai Web Integration (MCP Server)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| fastmcp | >=3.0 | Python MCP server exposing `sb-*` commands to claude.ai and Claude Desktop | Standalone actively-maintained package (not the 1.0 bundled in `mcp` SDK); `uv add fastmcp` installs cleanly; decorator-based tool registration maps naturally to existing CLI commands; asyncio-native; 97M+ monthly SDK downloads across MCP ecosystem |

**Integration pattern:** New `sb-mcp-server` CLI entry point (registered in `pyproject.toml`) starts a FastMCP server. Claude Desktop and claude.ai connect via `stdio` transport (local). Exposes tools mirroring existing CLI: `capture`, `search`, `read`, `forget`, `export`, `anonymize`, `reindex`.

**Why fastmcp over `mcp` SDK directly:** The `mcp` SDK 1.x bundles `FastMCP` 1.0 but standalone `fastmcp` 3.x has richer tool/resource/prompt abstractions and more active development. Wire protocol is identical — migration is trivial if needed.

---

### 6. Setup Automation (sb-init Extensions)

No new libraries. Both Drive and Ollama automation use stdlib `subprocess` and `pathlib`:

- **Ollama detection:** `subprocess.run(['which', 'ollama'])` on macOS/Linux, `shutil.which('ollama')` cross-platform. If absent, print install URL and instructions; do not silently install.
- **Google Drive detection:** Check for `~/Library/CloudStorage/GoogleDrive-*/` (macOS) or `~/Google Drive/` (Windows). If absent, open download URL via `webbrowser.open()` (stdlib). Full Drive automation via OAuth is out of scope — detect and guide, do not silently install.

---

## Full Dependency Delta for `pyproject.toml`

These are the ONLY new additions to the existing v1.5 dependencies:

```toml
[project.dependencies]
# --- v2.0 additions ---

# Vector search
sqlite-vec = ">=0.1.6,<0.2.0"
sentence-transformers = ">=5.3.0"

# GUI
pywebview = ">=5.4,<6.0"
flask = ">=3.0"

# Encryption
sqlcipher3-binary = ">=0.6.2"
cryptography = ">=42.0"
keyring = ">=25.0"

# Scheduling (intelligence layer)
apscheduler = ">=3.11,<4.0"

# MCP server
fastmcp = ">=3.0"
```

**Large install warning:** `sentence-transformers` pulls in `torch`. Specify CPU-only wheel to avoid downloading GPU CUDA binaries (~2 GB). Add to `pyproject.toml`:

```toml
[tool.uv]
extra-index-url = ["https://download.pytorch.org/whl/cpu"]

[project.dependencies]
torch = ">=2.0"  # resolves to CPU-only from pytorch.org/whl/cpu
```

First `uv tool install` after v2.0 will take 3–5 minutes on first run. Document this in setup notes.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| pywebview 5.4 | Electron | Requires Node.js + Chromium ~300 MB; cross-language IPC |
| pywebview 5.4 | Tauri + PyTauri | Pre-1.0 (v0.8 Feb 2026); Rust toolchain required; not production-ready |
| pywebview 5.4 | PyQt6 | GPL license (closed source = paid); widget layout steeper than HTML/CSS |
| pywebview 5.4 | PySide6 (LGPL) | Viable license, but heavier install; widget system vs HTML/CSS frontend |
| pywebview 5.4 | Textual | TUI not GUI; no rich visual rendering |
| sqlite-vec | ChromaDB | Separate process; 500 MB deps; overkill for single-user |
| sqlite-vec | Weaviate | Cloud-oriented; violates local-first |
| sqlite-vec | sqlite-vss | Deprecated by same author; use sqlite-vec |
| all-MiniLM-L6-v2 | OpenAI embeddings | Requires API key + internet; PII notes cannot leave machine |
| all-MiniLM-L6-v2 | Ollama embeddings | Requires daemon running; adds latency; sentence-transformers faster on CPU for small batches |
| sqlcipher3-binary | pysqlcipher3 | Abandoned 2020; no binary wheels for Windows |
| sqlcipher3-binary | SQLAlchemy column encryption | Does not cover FTS5 or vector tables; partial protection |
| fastmcp >=3.0 | `mcp` SDK `FastMCP` 1.0 | Less active; fastmcp 3.x standalone has more features |
| APScheduler 3.x | APScheduler 4.x | 4.x is a complete API rewrite; ecosystem not yet caught up; pin `<4.0` |
| keyring | `.env` for key storage | `.env` is plaintext on disk; keyring uses OS-protected credential store |
| keyring | Hardcoded passphrase in config | Never. Keys must be in OS keyring. |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| LangChain | 500+ MB dep tree; version churn notorious; overkill for 2 AI backends | Direct adapter pattern (existing) |
| LlamaIndex | Same as LangChain — abstraction over retrieval we own | sqlite-vec + RRF in pure Python |
| ChromaDB | Separate process; large install; no advantage over sqlite-vec at this scale | sqlite-vec |
| pgvector / PostgreSQL | Server dependency; violates local-first constraint | sqlite-vec |
| Celery + Redis | Distributed task queue; overkill for single-user in-process scheduling | APScheduler in-process |
| PyInstaller | macOS notarization complexity; `uv tool install` is already the distribution method | `uv tool install` from PyPI |
| Tauri + PyTauri | Pre-1.0, Rust toolchain required | pywebview (revisit Tauri at 1.0) |
| Docker | Dropped in v1.5 for good reason — native macOS install is the pattern | `uv tool` + launchd |
| APScheduler 4.x | Breaking API rewrite; ecosystem not caught up | APScheduler 3.11.x pinned `<4.0` |
| pysqlcipher3 | Abandoned; Windows install is manual; no wheels | sqlcipher3-binary |

---

## Version Compatibility

| Package | Python | Notes |
|---------|--------|-------|
| sqlcipher3-binary 0.6.2 | >=3.9 | Binary wheels: macOS arm64, macOS x86_64, Windows amd64/arm64/win32 |
| sqlite-vec 0.1.6 | >=3.8 | SQLite >=3.41 recommended; macOS ships 3.43+ by default |
| sentence-transformers 5.3.0 | >=3.9 | Requires torch >=2.0; use CPU-only wheel (see pytorch.org/whl/cpu) |
| pywebview 5.4 | >=3.9 | Windows requires WebView2 runtime (default since Win10/11 2021 update) |
| APScheduler 3.11.2 | >=3.8 | **Pin `<4.0`** — v4 is a full API rewrite |
| fastmcp >=3.0 | >=3.10 | asyncio required |
| keyring 25.7.0 | >=3.9 | No extra deps on macOS/Windows; Linux requires `secretstorage` |
| cryptography >=42.0 | >=3.9 | Binary wheels on all platforms; no system OpenSSL needed |

---

## Stack Patterns by Phase

**If building vector search before GUI (recommended order):**
- sqlite-vec + sentence-transformers shipped first
- Hybrid search working in CLI before any GUI work starts
- GUI phases can expose semantic search immediately on their first release

**If user has no internet at first install after v2.0:**
- sentence-transformers model download will fail silently; implement `--offline` flag in `sb-reindex` that falls back to BM25-only and warns user
- All other packages are pre-downloaded into uv cache at install time

**If encryption migration fails midway:**
- Keep `brain.db.plaintext.bak` until encrypted DB passes a read-back test
- Only delete backup after passphrase round-trip verified successful
- Phase implementation MUST include explicit rollback path

**If Windows target has no WebView2 (very old Windows 10):**
- pywebview falls back gracefully with an error
- `sb-gui` should detect and print download URL for WebView2 runtime bootstrapper
- This is an edge case — WebView2 ships with Windows 11 and all Win10 updates since 2021

---

## Sources

- [sqlite-vec GitHub (asg017/sqlite-vec)](https://github.com/asg017/sqlite-vec) — MEDIUM confidence; PyPI version verified
- [sqlite-vec PyPI](https://pypi.org/project/sqlite-vec/) — v0.1.6 stable confirmed
- [sentence-transformers PyPI](https://pypi.org/project/sentence-transformers/) — v5.3.0 current
- [all-MiniLM-L6-v2 HuggingFace](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) — benchmark specs confirmed
- [pywebview 5.0 release post](https://pywebview.flowrl.com/blog/pywebview5.html) — v5.4 latest stable confirmed
- [pywebview GitHub (r0x0r/pywebview)](https://github.com/r0x0r/pywebview) — cross-platform support confirmed
- [sqlcipher3-binary PyPI](https://pypi.org/project/sqlcipher3-binary/) — v0.6.2, Jan 7 2026, binary wheel platforms confirmed
- [sqlcipher3 GitHub (coleifer/sqlcipher3)](https://github.com/coleifer/sqlcipher3) — Python 3 bindings confirmed
- [keyring PyPI](https://pypi.org/project/keyring/) — v25.7.0 current; platform backends confirmed
- [cryptography PyCA docs](https://cryptography.io/) — Fernet + AES pattern confirmed
- [APScheduler PyPI](https://pypi.org/project/APScheduler/) — v3.11.2 current stable
- [fastmcp PyPI](https://pypi.org/project/fastmcp/) — v3.x standalone package confirmed
- [PyTauri GitHub (pytauri/pytauri)](https://github.com/pytauri/pytauri) — v0.8 pre-1.0 status confirmed, Feb 2026
- [MCP Python SDK GitHub](https://github.com/modelcontextprotocol/python-sdk) — official SDK confirmed

---

*Stack research for: second-brain v2.0 (GUI hub + vector search + encryption at rest + intelligence layer + MCP server)*
*Researched: 2026-03-15*
