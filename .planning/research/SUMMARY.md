# Project Research Summary

**Project:** Cybernetic Second Brain
**Domain:** AI-augmented Personal Knowledge Management (local-first)
**Researched:** 2026-03-14
**Confidence:** MEDIUM (training data only; web search unavailable during research)

## Executive Summary

The Cybernetic Second Brain is a local-first, CLI-driven PKM engine built inside a DevContainer. The architecture is fundamentally differentiated from off-the-shelf tools (Obsidian, Notion) by two design decisions: (1) proactive AI questioning at capture time instead of passive storage, and (2) a hard local-only routing rule for PII content that guarantees GDPR compliance by construction. Research across all four domains converges on a clear implementation path: Python 3.11 + Typer CLI + SQLite FTS5 for the core, with a thin dual-adapter AI layer (Anthropic API for non-PII, Ollama for PII). There are no exotic choices — every technology selected is the obvious best-fit tool with strong ecosystem support.

The recommended approach is to build in strict dependency order: DevContainer foundation first, then storage and index, then AI enrichment, then automation (file watcher, git hooks), then GDPR tooling. The single biggest risk is skipping this order — the AI capture surface is the exciting part, but it depends on correct atomic writes and a solid SQLite schema. Building the AI layer before storage is proven is the failure mode that causes rewrites. The second biggest risk is GDPR: PII routing logic must be baked in at the architecture level (Phase 0), not added later.

Critical success factors: `sb-reindex` must exist before any real data is stored; PII classification must be local-only with no fallback to cloud APIs; SQLite must live in a named Docker volume (never Drive-synced); and the capture flow must stay at one command with no blocking prompts. Dogfood the system in real work from Phase 1 forward — PKM systems die from friction, not from technical failures.

## Key Findings

### Recommended Stack

The stack is intentionally minimal. Python 3.11 stdlib provides the core (pathlib, tomllib, sqlite3). Typer + Rich handle the CLI surface with zero boilerplate. sqlite-utils wraps SQLite FTS5 in a way that handles the 90% case while staying out of the way for raw FTS5 queries. The AI layer is two direct SDK calls (anthropic, ollama) plus a 50-line router — no LangChain, no LlamaIndex.

**Core technologies:**
- Python 3.11 + stdlib (pathlib, tomllib, sqlite3): runtime — LTS-stable, DevContainer-ready, zero extra dependencies for core concerns
- Typer + Rich: CLI framework — type-annotated functions become commands; auto-generates `--help`; Rich handles result display
- sqlite-utils + FTS5: search index — purpose-built for SQLite power features; `db.enable_fts()` in one call; handles FTS5 schema, population, and rebuild
- python-frontmatter + mistune v3: markdown layer — round-trip safe frontmatter read/write; mistune v3 AST for wikilink extraction and heading indexing
- anthropic SDK + ollama Python client: AI adapters — direct SDK calls via a thin ModelRouter; avoids LangChain version churn
- watchdog (PollingObserver): file watching — use PollingObserver explicitly inside Docker; inotify does not reliably propagate from host bind-mounts
- pydantic v2: note schema validation — validate YAML frontmatter on ingest; Rust core is fast; catches bad data at the boundary
- pytest + freezegun: testing — freezegun is required for audit trail timestamp assertions

**Version notes:** Verify anthropic SDK version at install time (frequent releases). Confirm package name is `pypdf` not `PyPDF2` on PyPI.

### Expected Features

The persona (Operations Manager + Team Lead + Developer) shifts feature priorities significantly from a generic PKM user. People notes are critical infrastructure. CLI-first is non-negotiable. Meeting prep is the killer use case once enough history accumulates.

**Must have (table stakes):**
- `sb-init` — bootstraps folder structure and note templates
- `sb-capture` with AI proactive questioning — the core differentiator; must work in <3 seconds
- `sb-search` via SQLite FTS5 — full-text search with date range and tag filters
- `sb-reindex` — full rebuild from source; must exist before real data is stored
- `sb-forget <person>` — GDPR erasure (non-negotiable given PII in people notes)
- People profile template + 1:1 note template — manager persona value from day 1
- Git hook auto-capture — coding-to-knowledge loop; zero friction
- Backlinks and bidirectional links — Obsidian-normalized; users expect this
- Audit trail (created/accessed/modified events in SQLite) — GDPR requirement

**Should have (differentiators):**
- "What do I know about X?" AI synthesis query — pre-meeting brief use case
- AI-inferred backlink suggestions at capture time
- File-drop categorization via file watcher
- `sb-check-links` — find broken/orphaned links
- Claude Code subagent interface — highest leverage for developer-manager persona

**Defer (v2+):**
- Pre-meeting brief — needs accumulated history to be valuable; little value on day 1
- Action item extraction from meeting notes — complex AI pass; validate capture quality first
- GUI / web interface — explicit future milestone; no value until CLI is solid
- Calendar sync, mobile access, plugin system — out of scope per PROJECT.md

### Architecture Approach

The system has five clean layers: Capture (CLI + file watcher + git hooks), AI (router + local/cloud adapters), Storage (atomic markdown writer + binary parsers), Index (SQLite FTS5 + relationship graph + audit log), and Sync (host-level Google Drive — the container never touches this). Component boundaries are strict: CLI never touches SQLite directly; AI Router classifies before any API call; Markdown writer uses atomic temp-file-then-rename; FTS5 deletes require explicit shadow table cleanup before the parent row is deleted.

**Major components:**
1. Capture layer (CLI + watcher + git hooks) — all entry points into the capture pipeline
2. AI Router + adapters — local-first classification, hard PII guard, routes to Ollama or Anthropic
3. Markdown writer — atomic writes (temp file + `os.rename()`); rolls back on index failure
4. SQLite index — FTS5 full-text search, relationship graph (bidirectional links), audit log, people registry
5. DevContainer runtime — Python 3.11 in `mcr.microsoft.com/devcontainers/python:1-3.11-bullseye`; SQLite in named volume `brain-index-data`; brain content bind-mounted from host

### Critical Pitfalls

1. **SQLite on Drive-synced volume** — WAL files sync out of order, producing immediate corruption. Prevention: named Docker volume only; implement `/sb-reindex` before any capture command.
2. **PII sent to cloud before local classification** — the input to classification IS the sensitive data. Prevention: deterministic local rules (path-based + keyword regex) first; Ollama fallback if ambiguous; cloud API call only after PII=False confirmed.
3. **Non-atomic note writes** — crash between file write and index write leaves partial state. Prevention: write to `.tmp`, index, then `os.rename()` to final path. Roll back `.tmp` on any failure.
4. **FTS5 shadow table drift after `sb-forget`** — row DELETE does not purge FTS5 internal B-tree structures. Prevention: `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` after every erasure; add integration test asserting zero FTS5 results post-erasure.
5. **DevContainer `remoteUser` mismatch** — mixing `root` and `vscode` user creates Drive sync failures. Prevention: set `remoteUser: vscode` consistently; test full write-from-container-readable-on-host cycle in Phase 0.

## Implications for Roadmap

Research strongly supports a 5-phase structure that mirrors the architectural dependency graph. Do not collapse phases; each must be solid before the next.

### Phase 0: Secure Foundation
**Rationale:** Security and permission issues discovered late cause rewrites. API key exposure, remoteUser conflicts, and Windows path failures are all Phase 0 problems that cannot be fixed retroactively.
**Delivers:** Working DevContainer with correct user permissions; `.env.host` pattern established; pre-commit key scanner installed; `~/SecondBrain` bind-mount verified on all target platforms.
**Addresses:** `sb-init` (folder structure bootstrap)
**Avoids:** Pitfalls C3 (API keys in Drive), C4 (remoteUser mismatch), C5 (Windows path expansion failure)

### Phase 1: Storage and Index
**Rationale:** Every subsequent feature writes to or reads from storage. The AI layer, file watcher, and GDPR tooling all depend on correct, tested storage. Build and dogfood the non-AI capture path first.
**Delivers:** Atomic markdown write, SQLite schema (notes + FTS5 + relationships + audit_log), `sb-reindex`, basic `sb-search` (no AI), `sb-capture` writing plain notes.
**Uses:** sqlite-utils, python-frontmatter, pydantic v2, pathlib
**Avoids:** Pitfalls C1 (SQLite on Drive), M1 (Drive sync conflicts), M2 (index drift), Mi1 (over-engineering capture before storage works), Mi4 (friction)
**Research flag:** Standard patterns — well-documented SQLite FTS5 and Python atomic write patterns. No additional research needed.

### Phase 2: AI Layer
**Rationale:** AI enrichment sits on top of proven storage. Classification logic must be built before either AI adapter, because the classifier is the GDPR guard. Build classifier → router → Ollama adapter → Anthropic adapter in that order.
**Delivers:** Local PII classifier (rule-based + Ollama fallback), ModelRouter, Ollama adapter, Anthropic adapter, `sb-capture` with AI proactive questioning and backlink suggestions.
**Uses:** anthropic SDK, ollama Python client, Ollama on host at `host.docker.internal:11434`
**Implements:** AI layer (classifier + router + adapters)
**Avoids:** Pitfalls C2 (PII to cloud before routing), M3 (prompt injection), M4 (runaway AI costs), M5 (context window exhaustion)
**Research flag:** Needs research on Anthropic rate limits and current SDK version at phase planning time; Ollama model availability and sizes should be verified.

### Phase 3: Automation
**Rationale:** File watcher and git hooks depend on the full capture pipeline being tested interactively first. Adding event-driven triggers to an untested pipeline amplifies bugs.
**Delivers:** watchdog file watcher (PollingObserver fallback), git post-commit hook, binary file parsing (docx/pptx/pdf — text extraction only), Claude Code subagent interface.
**Uses:** watchdog (PollingObserver), python-docx, python-pptx, pypdf
**Avoids:** Pitfall M4 (runaway AI costs from watcher — debounce + rate limit), Mi2 (binary file scope creep)
**Research flag:** Standard patterns for watchdog and git hooks. Binary file parsing edge cases may need spot-checking against pypdf current docs.

### Phase 4: GDPR and Maintenance
**Rationale:** GDPR tooling requires real data to test against; erasure logic depends on the full relationship graph being populated. This is also when link management tooling becomes worth building (enough data exists to have broken links).
**Delivers:** `sb-forget` with full cascade (markdown + binary attachments + SQLite rows + FTS5 rebuild + backlink patching), `sb-audit` log viewer, `sb-check-links`, schema migration system.
**Avoids:** Pitfalls C6 (FTS5 shadow table drift), M6 (incomplete erasure cascade), Mi3 (link rot on rename), Mi5 (audit log as PII surface)
**Research flag:** Verify current EU GDPR Art. 17 guidance for automated personal data systems at planning time. FTS5 shadow table deletion semantics should be verified against sqlite.org/fts5.html.

### Phase 5: Advanced Features
**Rationale:** High-value AI features ("What do I know about X?", pre-meeting brief, action item extraction) depend on accumulated history. They have no value on day 1; build them once the vault is populated.
**Delivers:** AI synthesis queries, pre-meeting brief, action item extraction from meeting notes, person profile enrichment from meeting history.
**Avoids:** M5 (context window exhaustion — retrieval design must limit notes passed to AI)
**Research flag:** Needs research on retrieval patterns (FTS5 + embedding hybrid) for context window management; current Claude context window sizes and pricing at planning time.

### Phase Ordering Rationale

- Storage before AI: the AI layer writes to storage; writing to broken storage creates corrupt state that is hard to diagnose and hard to recover from.
- Classifier before API adapters: this is the GDPR guard; the order is not optional.
- Watcher after interactive capture: event-driven triggers amplify bugs in the underlying pipeline.
- GDPR tooling after real data: erasure logic needs a populated database to test against; testing erasure on empty tables is not meaningful.
- Advanced AI features last: they require accumulated vault history to produce value; building them early is premature.

### Research Flags

Phases needing deeper research during planning:
- **Phase 2 (AI Layer):** Anthropic SDK current version and rate limits; Ollama model availability and sizes (3-7GB estimates need verification); prompt injection mitigation patterns for note content.
- **Phase 4 (GDPR):** Current EU guidance on Art. 17 erasure for automated personal data systems; FTS5 shadow table deletion semantics.
- **Phase 5 (Advanced AI):** Retrieval patterns for context window management; current Claude context window sizes; potential embedding library if hybrid search needed.

Phases with standard patterns (skip research-phase):
- **Phase 0:** DevContainer setup, .gitignore, pre-commit hooks — well-documented.
- **Phase 1:** SQLite FTS5 schema, atomic Python file writes, watchdog PollingObserver — established patterns.
- **Phase 3:** git post-commit hooks, text-extraction-only binary parsing — standard.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Python 3.11 stdlib and core libraries (Typer, sqlite-utils, pytest) are HIGH. Anthropic SDK version and Ollama client API are MEDIUM — verify at install time. |
| Features | MEDIUM | PKM feature landscape is stable; persona-specific priorities sourced from PROJECT.md (HIGH). Live competitor feature verification was not performed. |
| Architecture | HIGH | Architecture decisions sourced from PROJECT.md (owner decisions) + well-established patterns (SQLite FTS5, POSIX atomic rename, Docker volume patterns). |
| Pitfalls | MEDIUM | Project-specific risk register items (PROJECT.md) are HIGH. SQLite WAL behavior, GDPR Art. 17 edge cases sourced from training data (MEDIUM). |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Anthropic SDK version ceiling:** SDK releases frequently; 0.28 is the floor but verify latest stable before pinning in requirements.txt.
- **Windows `${localEnv:HOME}` behavior:** Flagged in PROJECT.md as untested; must be explicitly tested in Phase 0 before any other work proceeds on Windows.
- **Ollama on host vs sidecar:** Model storage size estimates (3-7GB) are based on mid-2025 training data; verify current model sizes before committing to host-only Ollama architecture.
- **watchdog PollingObserver in Docker:** Community-confirmed issue; no single authoritative doc. Test explicitly in Phase 0 as part of DevContainer validation.
- **FTS5 shadow table deletion:** Verify against current sqlite.org/fts5.html documentation before implementing `sb-forget` erasure logic.
- **GDPR Art. 17 audit log scope:** Whether audit log records are themselves subject to erasure requires current EU guidance verification.
- **mistune vs markdown-it-py:** Both are valid; final choice is subjective. Either can be substituted without architectural impact.

## Sources

### Primary (HIGH confidence)
- `/Users/tuomasleppanen/second-brain/.planning/PROJECT.md` — owner decisions on architecture, GDPR requirements, risk register
- Python 3.11 release timeline + stdlib documentation — tomllib, pathlib, sqlite3 facts
- SQLite FTS5 documentation: https://www.sqlite.org/fts5.html
- POSIX `rename(2)` atomicity: POSIX standard

### Secondary (MEDIUM confidence)
- Training knowledge of sqlite-utils (Simon Willison), Typer, watchdog, anthropic Python SDK, ollama Python client — stable libraries, verify version pinning
- Training knowledge of Obsidian, Notion AI, Mem.ai, Roam Research, Logseq feature landscape — PKM feature comparison
- PKM adoption research (PARA/CODE methodology, Obsidian community patterns)
- Docker DevContainer bind-mount inotify behavior — widely reported community issue

### Tertiary (LOW confidence)
- mistune v3 vs markdown-it-py preference — subjective API comparison, either is acceptable
- Ollama model sizes (3-7GB) — based on mid-2025 known model sizes; verify current sizes
- GDPR Art. 17 audit log scope — inferred from regulation text; verify with current EU guidance

---
*Research completed: 2026-03-14*
*Ready for roadmap: yes*
