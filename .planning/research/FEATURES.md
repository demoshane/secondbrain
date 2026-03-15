# Feature Research

**Domain:** AI-augmented Personal Knowledge Management — v2.0 Intelligence + GUI
**Researched:** 2026-03-15
**Confidence:** HIGH for PKM UX patterns (web-verified), MEDIUM for implementation specifics

---

## Scope Note

v1.5 shipped the full capture/search/GDPR foundation. This file covers only the **11 v2.0 features**. v1.5 features (sb-capture, sb-search, sb-read, sb-forget, sb-export, sb-anonymize, sb-reindex, sb-check-links, sb-watch, PII routing, git hooks, backlinks, GDPR) are treated as existing dependencies — not re-researched.

---

## Feature Landscape

### Table Stakes (Users Expect These)

For a tool positioning itself as an "active knowledge partner with proactive intelligence," these behaviors are expected baselines. Missing them makes the intelligence layer feel incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Cross-context synthesis ("catch me up on X") | Any AI-augmented PKM (Mem, Notion AI, Saner.AI) offers person/project summarization; it's the primary AI value prop | HIGH | Aggregates all notes for a person/project; must respect PII routing — synthesis of PII notes must stay local via Ollama |
| Action item extraction from meeting notes | Every serious meeting note tool (Fellow, Notion, Obsidian AI) extracts tasks post-capture; managers expect it | HIGH | Post-capture AI pass on `meetings/` type notes; produces structured task list with owner + due date; depends on capture already working |
| Semantic / vector search | BM25 FTS5 is table stakes for keyword search; users now expect "find notes like this" — Obsidian, Notion, Logseq all added it | HIGH | `sqlite-vec` (successor to sqlite-vss, pure C, no deps) is the right choice for this stack; co-exists with FTS5 in same SQLite DB |
| Claude.ai web integration via MCP | MCP became an industry standard by mid-2025 (adopted by OpenAI, Google, Microsoft); exposing brain tools as MCP server is now a standard pattern | MEDIUM | Implement as MCP server exposing sb-search, sb-capture, sb-read tools; claude.ai Integrations feature (Beta on Max plan) supports remote MCP — HIGH fit for this user |
| Setup automation (Drive + Ollama in sb-init) | Users expect `sb-init` to reach a working state without manual steps; anything requiring separate installs feels broken | MEDIUM | Ollama: detect via `which ollama`, install via Homebrew on macOS / winget on Windows if absent; Drive: detect mount point, document if absent (Drive install requires GUI consent — can't fully automate) |

### Differentiators (Competitive Advantage)

Features that elevate this system above passive note tools and generic PKM apps. These match the owner's specific persona (Operations Manager, Team Lead, Developer).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Proactive session recap (once-per-session) | No PKM tool does ambient context injection into a coding IDE session; this is unique to Claude Code integration | MEDIUM | Implement as CLAUDE.md instruction + `/sb-read` of recent notes on session start; "once-per-session" enforced via session-scoped state file in `.meta/`; offer text: "3 things happened since your last session — recap?" |
| Weekly digest (themes + open actions + stale items) | Saner.AI and Mem offer daily/weekly digests; differentiator here is digest is generated locally from own notes (not cloud-processed), and surfaces stale items | HIGH | Scheduled via launchd on macOS (existing infrastructure); generates Markdown digest note in `.meta/digests/`; open actions require action item extraction to be working first |
| Stale note nudges (3mo / 6mo) | Logseq and Roam have no staleness detection; Mem's "resurface" is cloud-only; local staleness nudge is uncommon | MEDIUM | Track `last_accessed_at` in SQLite (already has audit log); query notes with no access in >90 days; surface via session recap or launchd-triggered CLI notification |
| Connection surfacing (proactive "this relates to X") | Obsidian has backlink graphs but no proactive notification; Mem.ai does this but cloud-only | HIGH | Triggered at capture time: after writing note, run similarity query against vector index, surface top 3 related notes; threshold-gated to avoid noise |
| GUI hub (cross-platform Mac + Windows) | CLI-only limits adoption and review workflows; a read-optimized GUI makes the brain accessible for browsing and daily review without terminal | HIGH | See GUI section below for full analysis |
| Encryption at rest | No PKM tool in the local-first space ships encryption by default; Notesnook is the only encrypted notes app but it's cloud-sync | HIGH | See Encryption section below for analysis |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time connection surfacing (on every keystroke) | "Instant" feels more powerful | Generates noise, interrupts writing flow, kills performance | Surface connections only at capture completion — once, not continuously |
| Auto-push digest to email / Slack | "Deliver to me" feels convenient | Exfiltrates note content to third-party services; GDPR risk; Drive sync already covers delivery | Write digest as a Markdown note in brain; read it in morning via sb-read |
| GUI as primary interface (replace CLI) | Prettier UX | CLI is what makes this zero-friction for the developer persona; building a full CRUD GUI duplicates the engine | GUI is read-optimized and review-focused; all writes go through CLI commands |
| Calendar integration for session recap | "Know what meetings I have" | OAuth complexity, token refresh, API rate limits — a separate integration project; already listed as out-of-scope | Manual capture of upcoming meetings; pre-meeting brief on demand |
| Full encryption with passphrase-on-every-read | Security feels maximized | Kills the zero-friction value proposition; passphrase fatigue means users disable it | Encrypt the SQLite index + `.meta/` only; plain Markdown files rely on Drive's access controls; passphrase gate already exists for PII display |
| Automatic Drive conflict resolution | "Just handle it" | Drive sync is not atomic; auto-resolution risks data loss | Append-only note writes (already the pattern); document conflict indicators; never auto-merge |
| Weekly digest sent as push notification (macOS notification center) | Feels native | macOS notification entitlements require signed app bundle; complex for a `uv tool` install | launchd-triggered CLI print + write to brain as Markdown note |
| Semantic search replacing BM25 entirely | "AI search is better" | Vector search has low precision for exact terms, names, dates; BM25 excels at these | Hybrid search: BM25 + vector re-ranking; keep FTS5 as primary, vector as re-ranker |

---

## Feature Deep Dives

### GUI Hub

**Expected UX pattern (from Obsidian, Capacities, Craft):**
- Left sidebar: folder tree / note list
- Center: rendered Markdown view (read-only or light edit)
- Right panel: backlinks, related notes, metadata
- Command palette for search
- No heavy CRUD forms — those belong in CLI

**Framework recommendation: Tauri 2.x**

Tauri 2.0 released late 2024; adoption up 35% year-over-year. Key facts for this project:
- Ships <10MB bundle vs Electron's 100MB+
- Uses system WebView (WebKit on macOS, WebView2 on Windows) — no bundled Chromium
- Backend is Rust; Python sidecar support is on the roadmap but not production-ready
- Pattern for Python backends: spawn Python CLI commands via Tauri's `Command` API (shell sidecar), communicate over stdout/JSON
- Security: strict permission system, reduces attack surface vs Electron

**Alternative considered: Electron**
- Larger bundles, higher RAM (~100MB idle vs ~30-40MB for Tauri)
- Better Python integration via child_process
- Rejected: bloat contradicts local-first / lightweight philosophy

**Complexity: HIGH** — new language (Rust for sidecar bridge), new build toolchain, frontend framework choice (React/Svelte), packaging for both platforms.

**Constraint: GUI is read-optimized.** All writes go through existing CLI. GUI calls `sb-search`, `sb-read`, `sb-capture` as subprocess commands. This keeps the engine as single source of truth and avoids duplicating business logic.

### Semantic / Vector Search

**Recommended library: `sqlite-vec`**

`sqlite-vec` is the maintained successor to `sqlite-vss`. Key properties:
- Pure C, no dependencies — runs anywhere SQLite runs
- K-Nearest Neighbor (KNN) search with SIMD acceleration
- Ships as a Python-loadable SQLite extension
- Stores float32 or int8 quantized vectors directly in SQLite tables

**Embedding model for local-first:** `nomic-embed-text` via Ollama (already a dependency). Produces 768-dim embeddings, runs entirely locally, no cloud call.

**Hybrid search pattern (correct approach):**
1. BM25 FTS5 search (existing) returns top-N candidates
2. Vector re-ranking re-orders by semantic similarity
3. Final result merges both scores (RRF — Reciprocal Rank Fusion)

This gives precision (BM25 handles exact names/dates) + recall (vector handles concept similarity). Do NOT replace FTS5 with vector-only.

**Complexity: HIGH** — embedding pipeline at capture time (index all notes on first `sb-reindex`), incremental embedding on new notes, storage growth (~3KB per note for 768-dim float32 vectors).

### Encryption at Rest

**Scope decision (opinionated):**
Encrypting raw Markdown files creates a severe UX problem: Drive sync sees encrypted blobs, no diff-ability, no human-readable recovery. The correct scope is:

1. **Encrypt SQLite index** (`brain.db`) — contains FTS5 index, audit log, embeddings. Use SQLCipher (SQLite encryption extension) or encrypt the file at rest with Fernet (Python cryptography library) and decrypt to a temp file on open.
2. **Encrypt `.meta/` directory** — config, schemas, secrets.
3. **Leave Markdown files unencrypted** — they rely on Google Drive's access controls + OS-level full-disk encryption (FileVault on macOS). This is the correct threat model for a single-user local system.

**Recommended library:** Python `cryptography` (Fernet, AES-256-GCM) for file-level encryption of the SQLite DB file. Key derived from passphrase via PBKDF2. Key stored in macOS Keychain via `keyring` library.

**Anti-pattern to avoid:** Per-note encryption. Kills FTS5, kills backlinks, kills all indexing. Wrong granularity.

**Complexity: HIGH** — key management, keychain integration, migration path for existing unencrypted DBs, GDPR interaction (encrypted DB still needs `sb-forget` to work).

### Claude.ai Web Integration (MCP)

**Current state (verified March 2026):**
- MCP became industry standard by mid-2025; Linux Foundation donated
- claude.ai Integrations (Beta) supports remote MCP servers on Max, Team, Enterprise plans
- This user is on Max plan — direct fit
- MCP spec (Nov 2025 update) added OAuth 2.1, stateless Streamable HTTP transport

**Implementation pattern:**
- Build a local MCP server exposing: `sb_search`, `sb_capture`, `sb_read`, `sb_cross_context_synthesis`
- Transport: stdio (for Claude Code, already done conceptually) + HTTP (for claude.ai web)
- PII routing must still apply — MCP tools must run the same classifier before routing to Claude vs Ollama
- Local server runs on localhost; claude.ai web integration requires the server to be reachable (use ngrok or Cloudflare Tunnel for remote access, or accept Claude Code-only for local use)

**Complexity: MEDIUM** — MCP Python SDK available; main complexity is HTTP transport + auth for remote access.

### Proactive Session Recap

**PKM tools that do this:** None at the CLI/IDE level. This is a genuine differentiator.

**Expected behavior (from CLAUDE.md instruction pattern):**
1. Claude Code session starts
2. CLAUDE.md instruction triggers `sb-read --recent` on first tool use
3. Brain returns: "Last session: [date]. Since then: 3 notes captured (2 meetings, 1 strategy). 2 open action items. 1 stale nudge."
4. Offer: "Recap? [y/n]"
5. Session-scoped deduplication: offer made once, state stored in `.meta/session_state.json` keyed by session start timestamp

**Complexity: MEDIUM** — mostly a CLAUDE.md + `sb-read --recent` CLI flag + session state file. No new infrastructure. High leverage, low cost.

### Action Item Extraction

**Expected behavior (from Fellow, Notion AI, Obsidian AI):**
- Triggered automatically on capture of a `meeting` type note
- AI reads note body, extracts: task description, owner (person name), due date or urgency
- Writes extracted items to a structured section in the note (`## Action Items`)
- Optionally creates a separate `actions/` note or appends to a running action log
- Does NOT create external task manager integrations (no Jira, no Todoist — out of scope)

**Edge cases:**
- Implicit commitments ("I'll look into that") vs explicit tasks ("Action: Alice to send report by Friday") — AI must handle both
- PII notes: extraction must run via Ollama if note is PII-typed
- Duplicate detection: same action captured in two meeting notes

**Complexity: HIGH** — prompt engineering for reliable extraction, structured output parsing, PII-safe routing, deduplication logic.

### Weekly Digest

**Expected behavior (from Saner.AI, Mem weekly review):**
- Runs every Monday morning via launchd
- Aggregates: notes captured in last 7 days, open action items, stale notes (>90 days), recurring themes (from tags + content)
- Writes to `.meta/digests/YYYY-WW.md`
- User reads it via `sb-read --digest latest` or GUI

**Differentiator vs cloud tools:** fully local generation, no note content sent to cloud for digest (use Ollama for summarization, Claude only for non-PII theme extraction).

**Complexity: HIGH** — requires action item extraction to be working (for "open actions" section), stale detection query, theme extraction AI pass, scheduling via launchd.

**Dependency chain:** launchd (existing) → action item extraction → stale note tracking → digest writer.

### Stale Note Nudges

**Expected behavior:**
- 90-day nudge: "You haven't reviewed `people/alice.md` in 3 months. Still relevant?"
- 180-day nudge: "This note may be outdated. Archive, update, or forget?"
- Nudge delivery: via session recap (not push notification — avoids macOS entitlement complexity)
- Tracking: `last_accessed_at` already in SQLite audit log

**Edge cases:**
- Notes that are intentionally static (e.g., reference docs) — need a frontmatter flag `evergreen: true` to suppress nudges
- Bulk nudges: if 40 notes go stale at once (e.g., after a vacation), don't flood the user — batch to "5 oldest stale notes" per session

**Complexity: MEDIUM** — SQLite query is trivial; the UX (batching, evergreen flag, nudge delivery via session recap) is the design work.

---

## Feature Dependencies

```
[Existing: sb-capture, sb-search, SQLite FTS5, PII routing, Ollama, launchd]
    └── all v2.0 features depend on v1.5 foundation

Semantic / Vector Search
    └── requires: sqlite-vec extension installed
    └── requires: embedding model (nomic-embed-text via Ollama)
    └── requires: sb-reindex updated to generate embeddings
    └── enhances: Cross-context synthesis (better retrieval)
    └── enhances: Connection surfacing (similarity threshold query)

Action Item Extraction
    └── requires: sb-capture (meeting notes exist)
    └── requires: PII routing (meeting notes may be PII)
    └── enhances: Weekly digest (open actions section)
    └── enhances: Cross-context synthesis (surfaces commitments)

Cross-context synthesis ("catch me up on X")
    └── requires: sb-search (base retrieval)
    └── enhanced by: Semantic search (better recall)
    └── enhanced by: Action item extraction (richer context)
    └── requires: PII routing (synthesis of PII notes stays local)

Stale Note Nudges
    └── requires: SQLite audit log with last_accessed_at (v1.5)
    └── enhances: Weekly digest (stale items section)
    └── enhances: Session recap (surfaces nudges inline)

Proactive Session Recap
    └── requires: sb-read --recent (new CLI flag)
    └── enhanced by: Stale note nudges (includes nudges in recap)
    └── enhanced by: Action item extraction (surfaces open actions)
    └── requires: session state file in .meta/ (new, trivial)

Weekly Digest
    └── requires: Action item extraction (open actions section)
    └── requires: Stale note nudges (stale items section)
    └── requires: launchd (existing scheduler)
    └── requires: Ollama (local summarization for PII content)

Connection Surfacing
    └── requires: Semantic search / sqlite-vec (similarity query)
    └── triggered by: sb-capture (post-write hook)
    └── threshold-gated (suppress if similarity < 0.75)

GUI Hub
    └── requires: sb-search, sb-read, sb-capture as stable CLI (v1.5)
    └── enhanced by: Semantic search (GUI search experience)
    └── enhanced by: Cross-context synthesis (GUI "catch me up" view)
    └── requires: Tauri 2.x + frontend framework (new stack)

Encryption at Rest
    └── requires: Key management (macOS Keychain via keyring)
    └── conflicts with: plain-text Drive diff (Markdown stays unencrypted)
    └── requires: migration path for existing unencrypted brain.db
    └── must preserve: sb-forget erasure through encrypted DB

Claude.ai Web Integration (MCP)
    └── requires: MCP server wrapping existing sb-* CLI tools
    └── requires: same PII routing as CLI (classifier runs inside MCP tool)
    └── enhanced by: Cross-context synthesis (expose as MCP tool)
    └── optional: HTTP transport for claude.ai remote access

Setup Automation (Drive + Ollama)
    └── modifies: sb-init
    └── requires: Ollama detection + Homebrew/winget install path
    └── Drive: detect mount only; cannot automate Drive app install
    └── enhances: Semantic search (ensures Ollama available)
```

---

## MVP Definition for v2.0

### Phase 1 — Intelligence Core (Build First)

These features have the highest leverage and lowest new-infrastructure cost. They run on existing CLI + SQLite.

- [ ] Proactive session recap — CLAUDE.md instruction + `sb-read --recent` flag; unlocks daily value immediately
- [ ] Action item extraction — triggered on meeting capture; highest manager persona value
- [ ] Stale note nudges — SQLite query + session recap integration; low complexity, high utility
- [ ] Setup automation (Ollama in sb-init) — unblocks semantic search and local AI features

### Phase 2 — Search + Synthesis

Requires new infrastructure (sqlite-vec, embedding pipeline) but unlocks multiple downstream features.

- [ ] Semantic / vector search — sqlite-vec + nomic-embed-text; enables connection surfacing
- [ ] Cross-context synthesis — aggregation + AI summarization; uses improved retrieval
- [ ] Connection surfacing — post-capture similarity query; depends on vector search

### Phase 3 — Digest + Automation

Depends on Phase 1 outputs (action items, stale nudges) being stable.

- [ ] Weekly digest — aggregates action items + stale notes + themes; launchd scheduler

### Phase 4 — GUI + Encryption + Integration

Highest complexity, new toolchains, least dependent on other phases.

- [ ] GUI hub (Tauri) — read-optimized; calls existing CLI as subprocess
- [ ] Encryption at rest — SQLite DB + .meta/ only; Markdown stays plain
- [ ] Claude.ai web integration (MCP) — MCP server wrapping sb-* tools

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Proactive session recap | HIGH | LOW | P1 |
| Action item extraction | HIGH | HIGH | P1 |
| Setup automation | HIGH | MEDIUM | P1 |
| Stale note nudges | MEDIUM | MEDIUM | P1 |
| Cross-context synthesis | HIGH | HIGH | P2 |
| Semantic / vector search | HIGH | HIGH | P2 |
| Connection surfacing | MEDIUM | HIGH | P2 |
| Weekly digest | MEDIUM | HIGH | P2 |
| Claude.ai MCP integration | MEDIUM | MEDIUM | P2 |
| GUI hub | MEDIUM | HIGH | P3 |
| Encryption at rest | LOW | HIGH | P3 |

**Priority key:** P1 = Phase 1 MVP, P2 = Phase 2 after search infra, P3 = Phase 3 new toolchain

---

## Competitor Feature Analysis

| Feature | Obsidian AI | Mem.ai | Saner.AI | This System |
|---------|-------------|--------|----------|-------------|
| Proactive session recap | No | No | No | CLAUDE.md injection — unique to IDE workflow |
| Action item extraction | Plugin-based | Yes (cloud) | Yes (cloud) | Local, PII-safe, meeting-triggered |
| Weekly digest | No | Yes (cloud) | Yes (cloud) | Local generation, fully private |
| Stale nudges | No | Resurface (cloud) | Partial | Local SQLite query, evergreen flag |
| Cross-context synthesis | Q&A plugin | Yes (cloud) | Yes (cloud) | Local for PII, Claude for non-PII |
| Vector search | Plugin (cloud embed) | Yes (cloud) | Yes (cloud) | sqlite-vec + Ollama embeddings, fully local |
| Connection surfacing | Backlink graph (manual) | Yes (cloud) | No | Post-capture similarity, threshold-gated |
| GUI | Yes | Web-only | Web-only | Tauri, read-optimized, offline |
| Encryption | No | Cloud-managed | No | SQLite + .meta/ only, keys in Keychain |
| MCP / API | Community plugin | No | No | First-class MCP server |
| Local-first / offline | Yes | No | No | Yes — core constraint |
| GDPR / PII routing | No | No | No | Per-type routing, sb-forget, audit log |

**Differentiation verdict:** No competitor combines local-first + GDPR-safe PII routing + proactive IDE integration + offline vector search. The combination is the moat, not any single feature.

---

## Sources

- [Best PKM Apps 2026 — ToolFinder](https://toolfinder.com/best/pkm-apps) — MEDIUM confidence
- [Obsidian AI Second Brain Guide 2026 — NxCode](https://www.nxcode.io/resources/news/obsidian-ai-second-brain-complete-guide-2026) — MEDIUM confidence
- [Saner.AI Second Brain — stale resurfacing UX](https://www.saner.ai/blogs/second-brain) — MEDIUM confidence
- [sqlite-vec GitHub — asg017/sqlite-vec](https://github.com/asg017/sqlite-vec) — HIGH confidence (official repo)
- [The State of Vector Search in SQLite — Marco Bambini](https://marcobambini.substack.com/p/the-state-of-vector-search-in-sqlite) — MEDIUM confidence
- [Electron vs Tauri — DoltHub Blog, Nov 2025](https://www.dolthub.com/blog/2025-11-13-electron-vs-tauri/) — HIGH confidence (dated Nov 2025)
- [Tauri vs Electron — gethopp.app](https://www.gethopp.app/blog/tauri-vs-electron) — MEDIUM confidence
- [MCP Integrations — Anthropic official](https://www.anthropic.com/news/integrations) — HIGH confidence (official source)
- [Connect to local MCP servers — modelcontextprotocol.io](https://modelcontextprotocol.io/docs/develop/connect-local-servers) — HIGH confidence (official spec)
- [Claude Code Session Memory — claudefa.st](https://claudefa.st/blog/guide/mechanics/session-memory) — MEDIUM confidence
- [Ollama Setup Guide 2026 — SitePoint](https://www.sitepoint.com/ollama-setup-guide-2026/) — MEDIUM confidence
- [Python cryptography library — PyPI](https://pypi.org/project/cryptography/) — HIGH confidence

---
*Feature research for: Second Brain v2.0 Intelligence + GUI*
*Researched: 2026-03-15*
