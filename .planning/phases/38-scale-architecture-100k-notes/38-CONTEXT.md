# Phase 38: Scale Architecture (100K Notes) — Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the brain functional and fast at 100K+ atomic notes. Delivers: ANN vector index (hnswlib),
filesystem sharding, audit log rotation, tiered storage, chunked embeddings with excerpt-aware
search, summarization layer, encrypted backup to Drive, and memory consolidation engine (backend
only — UI layer deferred to a follow-on phase).

Drive setup and health check are a prerequisite delivered in Phase 37 (Housekeeping).

**Not in this phase:** merge/update UI in Chrome extension, GUI capture modal merge prompts, CLI
merge flags. Those are the UI surface of consolidation and ship after the backend is proven.

</domain>

<decisions>
## Implementation Decisions

### A. Scope
- Full 8-workstream scope — brain is pre-production but expected to grow; build ahead of scale curve
- Filesystem sharding and tiered storage are included (future-proofing, not current pain)
- Memory consolidation engine ships in this phase (backend + background job only)
- Consolidation UI (Chrome extension prompt, GUI modal, CLI flag) is deferred to a follow-on phase

### Memory Consolidation Strategy
- **Capture default: always create new** — no interruption to capture flow, no silent merges
- **Background consolidation pass**: periodic job clusters related notes by topic/entity/similarity,
  surfaces merge candidates in health dashboard (same pattern as Phase 35 duplicate detection,
  but entity-aware and smarter than raw similarity score)
- **User action**: reviews candidates, approves merges explicitly — full control, no auto-merge
- Consolidation engine requires ANN index (hnswlib) to find similar notes efficiently — ships together

### B. Backup
- **Target**: `~/SecondBrain/.backup/` — Drive-synced once Drive is configured (Phase 37 prerequisite)
- **Coverage**: markdown files + SQLite DB + embeddings index — full restore, not just markdown
- **Encryption**: encrypted at rest (Fernet, consistent with PLAT-01 requirement)
- **Interface**: single command (`sb-backup`) + single command restore (`sb-restore`)
- **Health check**: `sb-health` reports last backup timestamp and warns if > N days stale
- No new cloud infrastructure needed — Drive is the transport once Phase 37 sets it up
- **Phase 37 dependency**: `setup.sh` must guide Drive setup + `sb-health` must verify Drive active
  before Phase 38 backup is meaningful. Add Drive setup + health check to Phase 37 scope.

### C. ANN Vector Index
- **Library**: hnswlib (`pip install hnswlib`) — zero-infra, no compilation, HNSW graph
- sqlite-vec retained for storage and non-vector queries; hnswlib handles vector search only
- Index stored as a file alongside the DB (e.g. `~/SecondBrain/.meta/brain.hnsw`)
- Rebuild from DB on `sb-reindex --full`; incremental updates on capture
- Fallback: if hnswlib index missing/corrupt, fall back to sqlite-vec KNN with a warning

### D. Chunked Embeddings
- **D1 — Threshold**: Claude's discretion (agent decides optimal chunk size and length threshold)
- **D2 — Search result**: backend returns parent note path + matched chunk excerpt text
  - Chunk text stored in a `note_chunks` table alongside chunk embeddings
  - Search response shape: `{ path, title, score, excerpt }` — excerpt is the matching chunk text
  - UI layer (future phase) can render excerpt as a highlighted snippet
- Overlap strategy: Claude's discretion (typical: 200 tokens / 50-token overlap)

### Claude's Discretion
- Exact chunk size and overlap (tokens/chars)
- Note length threshold for chunking (if not chunking all notes)
- hnswlib HNSW parameters (M, ef_construction)
- Filesystem sharding strategy (by type prefix, by date, by hash)
- Tiered storage criteria (age threshold, access frequency)
- Audit log rotation threshold and archive format
- Summarization trigger (length threshold, note types eligible)
- Backup encryption key storage location and rotation policy

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/embeddings.py`: `embed_texts()` with batch_size param — wrap for chunked embedding
- `engine/reindex.py`: `embed_pass()` + incremental reindex (mtime-based, Phase 33) — extend for chunks
- `engine/brain_health.py`: health reporting pattern — add backup staleness check + consolidation candidates
- `engine/intelligence.py`: `check_connections()` cooldown pattern — reuse for consolidation job gating
- `engine/db.py`: `init_schema()` migration pattern — add `note_chunks` table migration here
- Phase 35: near-duplicate cluster detection — consolidation engine extends this with entity awareness

### Established Patterns
- `sb-health` report for surfacing maintenance items (orphans, duplicates, broken links) — add consolidation candidates + backup status here
- `config.toml` via `engine/paths.py CONFIG_PATH` — tunable thresholds (backup interval, chunk size)
- Two-step token confirmation for destructive ops — apply to bulk merge operations
- `~/SecondBrain/.meta/` for system metadata — home for `.hnsw` index file and `.backup/` symlink

### Integration Points
- `engine/embeddings.py`: add `embed_chunks()` that splits text and returns `[(chunk_text, embedding)]`
- `engine/reindex.py`: extend `embed_pass()` to write chunks to `note_chunks` table
- `engine/search.py`: `search_hybrid()` queries `note_chunks` via hnswlib, returns `{path, excerpt}`
- `engine/brain_health.py`: add consolidation candidate surfacing + backup health check
- New: `engine/backup.py` — `sb-backup` and `sb-restore` entry points
- New: `engine/consolidate.py` — background consolidation pass, merge candidate logic

</code_context>

<specifics>
## Specific Decisions

- Drive setup + `sb-health` Drive check must land in Phase 37 before Phase 38 backup is meaningful
- Memory merge UI (Chrome extension, GUI modal, CLI `--update` flag) is explicitly deferred — do not implement in Phase 38
- Backup covers full brain state: markdown + DB + hnswlib index file. "Rebuild from reindex" is not acceptable as the only recovery path for a production brain
- Consolidation candidates surface in the same health dashboard as duplicates (Phase 35 pattern) — not a new UI surface

</specifics>

<deferred>
## Deferred to Follow-on Phase

- **Memory merge UI**: Chrome extension "Similar note found — update instead?" prompt
- **GUI capture modal**: merge suggestion inline
- **CLI**: `--update <path>` flag to route capture to existing note
- **MCP**: `sb_capture_smart` routing to update vs create based on consolidation signal
- These all depend on the consolidation engine from Phase 38 being proven reliable first

</deferred>

---

*Phase: 38-scale-architecture-100k-notes*
*Context gathered: 2026-03-25*
