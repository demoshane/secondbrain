# Project Research Summary

**Project:** Second Brain v2.0
**Domain:** Local-first AI-augmented Personal Knowledge Management (CLI + GUI + Intelligence)
**Researched:** 2026-03-15
**Confidence:** MEDIUM-HIGH

## Executive Summary

Second Brain v2.0 extends a fully-shipped v1.5 CLI foundation (capture, search, GDPR, PII routing, launchd daemon, git hooks) with five new capability areas: semantic vector search, a proactive intelligence layer, a cross-platform GUI hub, encryption at rest, and an MCP server for Claude.ai integration. The stack research is unambiguous: all new components slot into the existing Python/SQLite/uv architecture without requiring new infrastructure processes. sqlite-vec runs inside the existing `brain.db`, sentence-transformers embeds locally on CPU, pywebview wraps a Flask server in-process for the GUI, and FastMCP exposes existing CLI commands over stdio. The only genuinely new toolchain is pywebview + Flask for the GUI — the originally-considered Tauri approach was ruled out after confirming PyTauri remains pre-1.0 (v0.8, Feb 2026).

The recommended build order is dependency-driven and matches both ARCHITECTURE.md and PITFALLS.md: encryption foundation first (touches all DB writes), then vector search infrastructure (unblocks intelligence and connections features), then intelligence orchestrators (low cost, high value), then the FastAPI HTTP layer and GUI, and finally the MCP server (independent, can parallelize with GUI). Intelligence features that compose existing components — session recap, stale nudges, action item extraction — deliver the highest value-to-cost ratio and should ship before any GUI or encryption work begins. The differentiating strength of this system is the combination of local-first operation, GDPR-safe PII routing, and proactive IDE integration: no competitor in the PKM space ships all three.

The top risks are: encryption migration corrupting the existing database (mitigated by write-to-new-file, verify integrity, then atomic swap); stale vector embeddings diverging from edited note content (mitigated by content-hash gating written into the schema from day one); and notification fatigue from independent intelligence triggers (mitigated by a single proactive budget per session with persisted cooldown state). One cross-file conflict was resolved during synthesis: FEATURES.md recommended Tauri 2.x for the GUI, but STACK.md and ARCHITECTURE.md both converge on pywebview 5.4 after confirming PyTauri is not production-ready. **The synthesis decision is pywebview.**

---

## Key Findings

### Recommended Stack

The v1.5 stack (Python 3.11+, uv tool install, Typer + Rich CLI, SQLite FTS5, launchd daemon) is locked and extended — not replaced. Eight new packages cover all v2.0 capability areas and add no new infrastructure processes.

**Core technologies — new additions only:**
- `sqlite-vec 0.1.6` — KNN vector search as a SQLite extension inside `brain.db`; replaces deprecated sqlite-vss; SIMD-accelerated; no separate process; pin `<0.2.0` (0.1.7 is pre-release alpha)
- `sentence-transformers 5.3.0` with `all-MiniLM-L6-v2` (~90 MB, 384-dim) — local CPU embeddings; fully offline after first download; the only GDPR-compliant option for PII notes; requires CPU-only torch wheel to avoid 2 GB CUDA download
- `pywebview 5.4` + `flask >=3.0` — cross-platform desktop GUI window wrapping HTML/CSS/JS with in-process Flask backend; no Electron/Chromium; distributes as a standard `uv tool install` entry point (`sb-gui`)
- `sqlcipher3-binary 0.6.2` — transparent AES-256 encryption for `brain.db`; drop-in for stdlib `sqlite3`; binary wheels for macOS arm64/x86_64 and Windows amd64/arm64/win32; released Jan 2026
- `cryptography >=42.0` — Fernet symmetric encryption for individual PII markdown files; AES-128-CBC + HMAC; PyCA library, well-audited
- `keyring 25.7.0` — OS-native credential store for DB passphrase and file encryption key; macOS Keychain / Windows Credential Manager; zero plaintext on disk
- `apscheduler 3.11.2` — in-process background scheduling for weekly digest; **pin `<4.0`** (v4 is a complete API rewrite with different architecture)
- `fastmcp >=3.0` — standalone MCP server library; exposes `sb-*` commands as MCP tools for Claude.ai and Claude Desktop via stdio transport

**Critical encryption scope decision:** `brain.db` is fully encrypted with SQLCipher (all tables: FTS5, embeddings, actions, audit log). Markdown notes with `content_sensitivity: pii` are encrypted with Fernet at the file level. All other Markdown files remain plaintext — Drive sync computes diffs on plaintext; encrypting all notes breaks sync, breaks `sb-check-links`, and breaks git history legibility. This is the correct threat model for a single-user local system backed by Drive's own at-rest encryption.

### Expected Features

**Must have (table stakes for an intelligence-layer PKM):**
- Semantic / vector search — BM25 FTS5 keyword search already ships; users of modern PKM tools now expect "find notes like this"; sqlite-vec + all-MiniLM-L6-v2 handles this fully locally
- Cross-context synthesis ("catch me up on X") — the primary AI value proposition; must respect PII routing (PII notes summarized via Ollama only, never cloud)
- Action item extraction from meeting notes — expected by any tool claiming intelligence on meeting content; post-capture AI pass on `meetings/` type notes
- Claude.ai web integration via MCP — MCP is an industry standard (adopted by OpenAI, Google, Microsoft by mid-2025); Max plan users expect it
- Setup automation (Drive + Ollama in `sb-init`) — `sb-init` must reach a working state without manual steps; silent fallback to a local path is a critical failure mode

**Should have (genuine differentiators):**
- Proactive session recap — no competitor offers ambient context injection into a coding IDE session; HIGH value at LOW cost (CLAUDE.md instruction + one CLI flag)
- Weekly digest (themes + open actions + stale items) — local generation, fully private; cloud tools (Mem, Saner.AI) only offer cloud-processed digests
- Stale note nudges (90-day / 180-day) — local SQLite query; uncommon in PKM space; must respect `evergreen: true` frontmatter flag and batch to 5 per session max
- Connection surfacing at capture time — post-capture KNN similarity query; threshold-gated (cosine similarity > 0.8) to avoid noise
- GUI hub (read-optimized, cross-platform Mac + Windows) — CLI-only limits adoption for daily review workflows; GUI opens files in system default Markdown editor, never embeds an editor
- Encryption at rest — no local-first PKM tool ships encryption by default

**Defer to v3+:**
- Calendar integration for session recap (OAuth complexity; separate integration project)
- Push notifications to macOS notification center (requires signed app bundle; incompatible with `uv tool install` distribution)
- Real-time connection surfacing on every keystroke (noise; surface at capture completion only)
- Auto-push digest to email/Slack (exfiltrates note content; GDPR risk)
- GUI as primary CRUD interface replacing CLI (duplicates engine; kills zero-friction value for developer persona)
- Automatic Drive conflict resolution (auto-merge risks data loss; append-only writes are the correct pattern)

### Architecture Approach

The architecture follows the clean layered model already established in v1.5: engine modules are the single source of truth, imported directly by CLI commands. v2.0 adds two new access surfaces — a thin FastAPI HTTP facade (`engine/api.py`) for the GUI, and a FastMCP stdio server (`engine/mcp_server.py`) for Claude.ai — both calling the same engine functions. A new `engine/intelligence/` sub-package holds thin orchestrators that compose `db.py` + `ai.py` + `embed.py` with no state of their own. `engine/crypto.py` becomes the SQLite connection factory used by `db.py`; all other modules gain encryption transparently without knowing about it.

**Major components:**
1. `engine/embed.py` — sentence-transformers model (loaded once at startup, never per-request); sqlite-vec KNN query; RRF merge with FTS5 BM25 results
2. `engine/crypto.py` — SQLCipher connection factory; Fernet file encrypt/decrypt for PII notes; keyring passphrase retrieval; all DB access goes through this module
3. `engine/intelligence/` — five thin orchestrators: `recap.py`, `digest.py`, `actions.py`, `nudge.py`, `connections.py`; own no state; compose db.py + ai.py + embed.py
4. `engine/api.py` — FastAPI HTTP server on `127.0.0.1:37491`; thin routes only, zero business logic; started as `sb-api` sidecar by GUI process
5. `engine/mcp_server.py` — FastMCP stdio server; wraps engine functions as `@mcp.tool` callables; PII routing inherited from existing ModelRouter
6. `gui/` — pywebview + Flask desktop shell; HTML/CSS/JS frontend; read-optimized; no engine logic imported; all writes go through the API or CLI
7. Extended `brain.db` schema — `note_embeddings` virtual table (sqlite-vec, 384-dim float32), `actions` table with cascade deletes, SQLCipher AES-256 on all tables

**Key patterns to enforce:**
- Engine-as-library: all surfaces (CLI, API, MCP) import engine modules directly; no subprocess calls between engine components
- Thin HTTP facade: `api.py` routes call one engine function and return JSON; zero business logic in the route handler
- Intelligence as orchestrators: `intelligence/*` modules own no state and hold no DB connections; push reusable logic into `db.py` or `ai.py`
- Single proactive budget: one unsolicited message per session, prioritized as: overdue action > session recap > stale nudge > connection / digest; cooldown state persisted in `~/.meta/intelligence_state.json`

### Critical Pitfalls

1. **Encryption migration corrupts existing data (C3)** — Never migrate `brain.db` in-place. Write to `brain.db.enc`, run `PRAGMA integrity_check`, verify round-trip read, then `os.replace()`. The index is rebuildable via `sb-reindex` — treat the Markdown source as the ground truth. Keep `brain.db.plaintext.bak` until verification passes.

2. **Vector embeddings become stale after note edits (C5)** — Store `content_hash` alongside each embedding row. On every index write, compare hashes; mark `stale = true` if different. A background job re-embeds stale entries; `sb-reindex` always re-embeds all. This must be in the schema design, not retrofitted.

3. **Hybrid search produces incoherent results without RRF (C6)** — FTS5 BM25 scores and cosine distances are on incompatible scales. Never add or average them. Use Reciprocal Rank Fusion exclusively: `rrf = 1/(60 + rank_bm25) + 1/(60 + rank_semantic)`. Apply top-K cutoff per retriever before fusion, not after.

4. **MCP server enables prompt injection on destructive tools (C7)** — `sb-forget` and `sb-anonymize` must require two-call confirmation via a short-lived token (60-second TTL, in-memory dict). Split read-only tools from write/destructive tools into separate MCP server configurations. Wrap note content in `sb-read` responses in `<brain_note>` XML tags with a system instruction that content inside is user data, not model instructions.

5. **Notification fatigue from independent intelligence triggers (C8)** — Each intelligence module built in isolation will fire independently, producing noise the user learns to ignore. Define the proactive budget and `intelligence_state.json` cooldown architecture in Phase 2 before any individual module ships a proactive output.

6. **GUI engine tight coupling (C1)** — The GUI cannot import from `engine/` modules directly. `engine/api.py` must be complete and stable before any GUI work begins. This is a hard architectural dependency.

---

## Implications for Roadmap

The dependency graph strictly constrains phase order. Six phases are suggested; the first three can all ship value independently without requiring GUI or MCP work to be complete.

### Phase 1: Encryption + Embedding Infrastructure

**Rationale:** `crypto.py` (SQLCipher connection factory) must exist before any new module writes to `brain.db`. `embed.py` (sentence-transformers + sqlite-vec) must exist before intelligence modules that use similarity queries. Both are self-contained, have no UI dependencies, and can be verified with pure unit tests. Doing encryption last (after intelligence and GUI) would require retrofitting encrypted connections across all new modules — high risk.

**Delivers:** `engine/crypto.py` with SQLCipher connection factory and Fernet PII file encryption; passphrase stored in OS keyring; migration from unencrypted v1.5 `brain.db` (write-to-new, verify, atomic swap, keep `.bak`); `engine/embed.py` with model-load-once pattern; `note_embeddings` virtual table (sqlite-vec, 384-dim, content-hash column); `actions` table schema.

**Features addressed:** Encryption at rest (complete), vector search infrastructure (partial — no CLI exposure yet).

**Pitfalls to prevent:** C3 (migration corruption), C4 (key in plaintext), C5 (stale embedding schema with content-hash column from day one), C6 (RRF merger function written here, before any CLI exposure).

**Research flag:** NEEDS phase research — SQLCipher migration runbook, Argon2id vs PBKDF2 key derivation decision, `sqlcipher_export()` edge cases on populated databases.

---

### Phase 2: Intelligence Layer

**Rationale:** These five orchestrators compose `db.py` + `ai.py` (both existing and stable) + `embed.py` (Phase 1). They deliver the highest value-to-cost ratio in the entire roadmap: session recap is a CLAUDE.md instruction + one CLI flag; stale nudges are a SQLite query; action item extraction is a structured prompt through the existing AI adapter. Build all five `intelligence/` modules and the proactive budget architecture before tackling GUI or MCP — they are the features users will interact with daily.

**Delivers:** `engine/intelligence/` sub-package (recap, digest, actions, nudge, connections); `sb-read --recent` CLI flag; session state file; proactive budget + cooldown architecture in `~/.meta/intelligence_state.json`; action item extraction triggered on meeting note capture; connection surfacing post-capture (threshold-gated); `evergreen: true` frontmatter support; vault-size gate (minimum 20 notes before any proactive output fires).

**Features addressed:** Proactive session recap, action item extraction, stale note nudges, connection surfacing, cross-context synthesis (partial — enhanced by Phase 3 semantic retrieval).

**Pitfalls to prevent:** C8 (notification fatigue — proactive budget and cooldown designed here, before any feature fires), C9 (prompt injection in intelligence prompts — XML-tag isolation applied to every new AI call in this phase).

**Research flag:** Standard patterns for structured prompt extraction and XML-tag isolation (existing v1.5 pattern). Proactive budget design is novel but low-risk.

---

### Phase 3: Semantic Search + Weekly Digest CLI

**Rationale:** With Phase 1 infrastructure complete (`embed.py`, `note_embeddings`, content-hash gating), this phase wires semantic search into the CLI and completes `sb-reindex` with the embedding pass. Weekly digest depends on action items (Phase 2) and stale nudges (Phase 2) being stable — it ships here as the feature that aggregates them. Cross-context synthesis is completed here (Phase 2 built the orchestrator; Phase 3 adds vector-enhanced retrieval).

**Delivers:** `sb-search --semantic` flag; RRF hybrid search in `search.py`; `sb-reindex` with embedding generation pass and content-hash staleness detection; `sb-forget` cascade to `note_embeddings` and `actions` tables; weekly digest with launchd scheduling writing to `.meta/digests/YYYY-WW.md`; `sb-read --digest latest`; cross-context synthesis CLI command.

**Features addressed:** Semantic / vector search (complete), cross-context synthesis (complete), weekly digest (complete), connection surfacing (complete).

**Pitfalls to prevent:** C5 (stale embedding detection verified end-to-end — edit a note, verify `stale=true`, verify background re-embed), C6 (RRF confirmed in code review; no raw score arithmetic anywhere).

**Research flag:** Standard patterns — sqlite-vec and RRF are well-documented by the library author. No phase research needed.

---

### Phase 4: FastAPI HTTP Layer + Setup Automation

**Rationale:** `engine/api.py` must be complete and stable before any GUI work begins (C1 — this is the hard dependency). Setup automation for Drive detection and Ollama auto-install is fully independent of all other phases and slots here for logical grouping. Shipping the API layer first allows GUI development to start against a stable contract without coupling.

**Delivers:** `engine/api.py` (FastAPI on `127.0.0.1:37491`, bound to localhost only) with full route coverage for all engine functions; `sb-api` entry point in `pyproject.toml`; health endpoint for GUI polling; Drive detection with canary verification in `sb-init` (exits code 1 if Drive not found, no silent fallback); Ollama auto-install with health-check and CPU-only performance warning (>30s per embed triggers warning).

**Features addressed:** Setup automation (Drive + Ollama complete), API foundation for GUI.

**Pitfalls to prevent:** C1 (API contract exists and is stable before GUI starts), C10 (Drive canary verification — path existence is not sufficient), C11 (Ollama CPU performance warning).

**Research flag:** Drive path detection has platform-specific variants that change with Drive app versions — a quick verification of current macOS (`~/Library/CloudStorage/GoogleDrive-*/`) and Windows mount paths is warranted at planning time.

---

### Phase 5: GUI Hub

**Rationale:** Depends on `engine/api.py` (Phase 4) being complete. pywebview 5.4 + Flask is the chosen stack (not Tauri — PyTauri is pre-1.0 as of Feb 2026). GUI is strictly read-optimized: no CRUD forms, no embedded editor; opens files in the system default Markdown application. Sidecar lifecycle (spawn, health-check polling, graceful SIGTERM teardown) must be a first-class deliverable in this phase, not an afterthought.

**Delivers:** `gui/` with pywebview + Flask frontend; `sb-gui` entry point; left sidebar (folder tree / note list), center Markdown render (read-only), right panel (backlinks + metadata + related notes); command palette search; PID lockfile at `~/.meta/engine.pid`; stale lock detection on startup; graceful teardown on window close.

**Features addressed:** GUI hub (complete).

**Pitfalls to prevent:** C2 (sidecar orphan process — PID lockfile + explicit teardown on window-destroyed event), C1 (GUI only calls `127.0.0.1:37491`, never imports from `engine/`).

**Research flag:** NEEDS phase research — pywebview two-way JS bridge (`window.pywebview.api`) threading model with Flask, cross-platform rendering differences (WebKit on macOS vs WebView2 on Windows), WebView2 fallback handling for pre-2021 Windows 10 installs.

---

### Phase 6: MCP Server

**Rationale:** Fully independent of the GUI. Depends only on engine modules (Phases 1-3 complete). Can run in parallel with Phase 5 if resources allow. FastMCP with stdio transport is the correct choice: no port binding, no firewall rules, the MCP client spawns the process. Security model (destructive tool confirmation, read/write split) must be specified before any tool registration.

**Delivers:** `engine/mcp_server.py` with FastMCP; `sb-mcp-server` entry point; tools: `sb_search`, `sb_capture`, `sb_read`, `sb_forget`, `sb_recap`, `sb_digest`, `sb_connections`; two-call confirmation gate (token + 60s TTL) for `sb_forget` and `sb_anonymize`; read-only vs read-write server split configuration; `sb-init` auto-writes Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`); PII routing inherited from existing ModelRouter.

**Features addressed:** Claude.ai web integration via MCP (complete).

**Pitfalls to prevent:** C7 (destructive tool confirmation gates, localhost-only binding, XML-tag isolation on `sb_read` responses), C9 (MCP tools call `ai.py` which routes through existing ModelRouter — no new PII bypass).

**Research flag:** Standard patterns — FastMCP documentation covers stdio transport and tool registration. Two-call confirmation token pattern is straightforward (in-memory dict with TTL).

---

### Phase Ordering Rationale

- Encryption first because `crypto.py` is the DB connection factory — retrofitting encrypted connections after intelligence and GUI are built is high-risk and touches every module that writes to `brain.db`.
- Embed infrastructure before intelligence because `connections.py` and the cross-context synthesis retrieval path both call `embed.py`; without it, those features are shells.
- Intelligence before search CLI exposure and weekly digest because action item extraction and stale nudges are prerequisites for the weekly digest (Phase 3), and they are cheap to build against existing infrastructure before any new CLI flags are needed.
- API layer before GUI — hard dependency (C1); no exceptions.
- GUI and MCP are independent of each other and can be parallelized if two engineers are available.
- Setup automation (Drive + Ollama) is fully independent and slots into Phase 4 only for logical grouping; it could move to Phase 1 if early user testing is a higher priority than encryption.

### Research Flags

Phases needing deeper research during planning:
- **Phase 1:** SQLCipher migration runbook — `sqlcipher_export()` semantics, Argon2id vs PBKDF2 key derivation choice, version compatibility between SQLCipher 3 and 4 default KDF parameters
- **Phase 5:** pywebview + Flask integration — two-way JS bridge threading model, WebView2 availability detection on older Windows 10, system default Markdown app open API per platform

Phases with well-documented patterns (research-phase optional):
- **Phase 2:** Intelligence orchestrators — standard prompt engineering + existing `ai.py` abstraction; XML-tag isolation pattern already established in v1.5
- **Phase 3:** sqlite-vec + RRF hybrid search — canonical pattern documented by library author (Alex Garcia at alexgarcia.xyz)
- **Phase 4:** FastAPI thin facade — well-documented; Drive path variants need a quick spot-check only
- **Phase 6:** FastMCP stdio transport — official FastMCP docs cover the complete pattern

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Versions verified on PyPI; alternatives evaluated with specific reasoning; pywebview chosen over Tauri after confirming PyTauri pre-1.0 status Feb 2026; APScheduler `<4.0` pin confirmed |
| Features | HIGH | PKM competitor landscape verified via web research; feature dependency graph is explicit; anti-features well-reasoned against GDPR constraints and developer-persona UX |
| Architecture | MEDIUM-HIGH | Existing v1.5 architecture is known ground (HIGH); pywebview/Flask in-process pattern and FastMCP stdio integration are MEDIUM (community examples exist, shorter production track record) |
| Pitfalls | HIGH | SQLCipher migration, RRF fusion, MCP prompt injection all verified against multiple authoritative sources; Tauri sidecar lifecycle and Ollama edge cases are MEDIUM (community-confirmed) |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **GUI framework conflict resolved:** FEATURES.md recommended Tauri 2.x; STACK.md and ARCHITECTURE.md both converge on pywebview 5.4 after confirming PyTauri is pre-1.0. Synthesis decision: **pywebview**. Revisit Tauri when PyTauri reaches 1.0.
- **Key derivation algorithm:** PITFALLS.md recommends Argon2id (memory-hard, GPU-resistant); STACK.md specifies PBKDF2. Needs a definitive decision in Phase 1 planning. Argon2id is the stronger choice.
- **Embedding model source:** FEATURES.md mentions `nomic-embed-text` via Ollama; STACK.md recommends `all-MiniLM-L6-v2` via sentence-transformers (faster on CPU for sub-100-token notes). Synthesis: sentence-transformers is the primary path (always available, no daemon dependency); Ollama embeddings are the optional GPU-enhanced fallback for users who prefer higher-dimensional models.
- **First-run install time:** `sentence-transformers` pulls in torch CPU wheel (~800 MB total). First `uv tool install` after v2.0 will take 3-5 minutes. Must be documented prominently in setup notes and v2.0 release notes.
- **Vault-size gate threshold:** PITFALLS.md recommends gating proactive intelligence on minimum 20 notes. This constant needs to be defined in Phase 2 before any intelligence module ships.
- **Weekly digest PII routing:** Digest aggregates notes that may include PII content. Must confirm digest generation routes PII note summaries through Ollama and non-PII through Claude — same ModelRouter, but needs an explicit test in Phase 3.

---

## Sources

### Primary (HIGH confidence)
- [sqlite-vec GitHub (asg017/sqlite-vec)](https://github.com/asg017/sqlite-vec) — v0.1.6 stable, KNN API, extension loading
- [alexgarcia.xyz sqlite-vec hybrid search](https://alexgarcia.xyz/blog/2024/sqlite-vec-hybrid-search/index.html) — RRF canonical implementation from library author
- [sqlcipher3-binary PyPI](https://pypi.org/project/sqlcipher3-binary/) — v0.6.2, binary wheels, Jan 2026
- [SQLCipher GitHub](https://github.com/sqlcipher/sqlcipher) — migration path, version compatibility
- [MCP Python SDK GitHub](https://github.com/modelcontextprotocol/python-sdk) — official Anthropic MCP SDK
- [fastmcp PyPI](https://pypi.org/project/fastmcp/) — v3.x standalone package, stdio transport
- [sentence-transformers PyPI](https://pypi.org/project/sentence-transformers/) — v5.3.0, all-MiniLM-L6-v2 specs
- [keyring PyPI](https://pypi.org/project/keyring/) — v25.7.0, platform keychain backends
- [OWASP LLM01:2025 prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — MCP security model rationale
- [Unit42 Palo Alto MCP attack vectors](https://unit42.paloaltonetworks.com/model-context-protocol-attack-vectors/) — indirect prompt injection via MCP tools
- [Tauri v2 architecture docs](https://v2.tauri.app/concept/architecture/) — confirmed Tauri v2.4.x; informed decision to use pywebview instead
- [PyTauri GitHub](https://github.com/pytauri/pytauri) — confirmed pre-1.0 status (v0.8, Feb 2026)
- [MCP Integrations — Anthropic official](https://www.anthropic.com/news/integrations) — claude.ai remote MCP on Max plan confirmed

### Secondary (MEDIUM confidence)
- [pywebview GitHub (r0x0r/pywebview)](https://github.com/r0x0r/pywebview) — v5.4 cross-platform support; Flask in-process pattern
- [APScheduler PyPI](https://pypi.org/project/APScheduler/) — v3.11.2 stable; v4 breaking API rewrite confirmed
- [cryptography PyCA docs](https://cryptography.io/) — Fernet AES-128-CBC + HMAC pattern
- [oneuptime.com SQLCipher post, Feb 2026](https://oneuptime.com/blog/post/2026-02-02-sqlcipher-encryption/view) — SQLCipher migration patterns in Python
- [Electron vs Tauri — DoltHub Blog, Nov 2025](https://www.dolthub.com/blog/2025-11-13-electron-vs-tauri/) — bundle size and RAM comparisons
- [Tauri sidecar docs](https://v2.tauri.app/develop/sidecar/) — orphan process and teardown patterns (informed C2 even though Tauri was not chosen)
- [openreview proactive agent research](https://openreview.net/forum?id=sRIU6k2TcU) — notification fatigue basis (40% success rate on proactive tasks in SOTA systems)
- [Saner.AI second brain UX](https://www.saner.ai/blogs/second-brain) — stale resurfacing and digest UX patterns
- [Obsidian AI second brain guide 2026](https://www.nxcode.io/resources/news/obsidian-ai-second-brain-complete-guide-2026) — competitor feature landscape

### Tertiary (LOW confidence, needs validation at phase planning time)
- pyrage (Python age encryption bindings) — mentioned in ARCHITECTURE.md for optional file encryption; superseded in synthesis by Fernet for PII files; revisit if per-file encryption scope expands
- Ollama CPU inference speed figures — community-reported; measure at Phase 1 with actual hardware before committing to warning thresholds

---
*Research completed: 2026-03-15*
*Ready for roadmap: yes*
