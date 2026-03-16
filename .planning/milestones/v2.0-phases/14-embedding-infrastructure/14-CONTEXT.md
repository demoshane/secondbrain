# Phase 14: Embedding Infrastructure - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Add local vector embedding support to the brain: create `note_embeddings` table in `brain.db`, generate `all-MiniLM-L6-v2` embeddings during `sb-reindex`, detect staleness via content hash, cascade erasure in `sb-forget`, and expose KNN queries via sqlite-vec. Semantic search consumption is Phase 16 — this phase is infrastructure only.

</domain>

<decisions>
## Implementation Decisions

### Stale detection mechanism
- `sb-reindex` computes SHA-256 of each note's body content during the walk and compares to the stored `content_hash` in `note_embeddings`
- If hash differs (or embedding is missing), the row is marked `stale=true` before embedding
- This approach catches edits from ALL sources: CLI commands, direct file edits, and Drive-synced changes
- Write commands (`sb-capture`, `sb-update-memory`) do NOT set `stale=true` directly — the hash comparison in reindex is authoritative

### note_embeddings table schema
- Single table — no separate blobs table
- Columns: `note_path TEXT, embedding BLOB, content_hash TEXT, stale BOOL, created_at TEXT, updated_at TEXT`
- `note_path` is the primary key (unique, matches `notes.path`)

### GDPR erasure (sb-forget cascade)
- `sb-forget` deletes the embedding row immediately — no lazy cleanup on next reindex
- No residual vector data after erasure (PII compliance)

### First-run model download
- Auto-download silently with a visible progress bar on first `sb-reindex`
- Print before download: `[sb-reindex] Downloading embedding model (~90MB, first-time only)...`
- Cache in HuggingFace default cache (`~/.cache/huggingface/`) — not inside brain folder (avoids Drive sync of model files)
- No explicit flag or prompt required

### Reindex scope behavior
- Incremental by default: only re-embeds notes where `content_hash` changed or embedding is missing
- `sb-reindex --full` flag forces full rebuild of all embeddings
- Output: summary only at end — `[sb-reindex] Embedding N new/stale notes...` then `[OK] N embeddings updated, N unchanged`
- No per-note output, no tqdm progress bar

### Embedding provider architecture
- Phase 14 ships BOTH sentence-transformers and Ollama fallback
- Primary: `sentence-transformers` with `all-MiniLM-L6-v2` (no cloud call)
- Fallback: Ollama with `nomic-embed-text` model
- Provider selected via `config.toml`: `embeddings.provider = "sentence-transformers" | "ollama"` — no auto-switching
- Single provider for all notes regardless of `content_sensitivity` (both are local; no PII risk)
- `all-MiniLM-L6-v2` is used for ALL notes including PII-flagged ones — model runs fully locally

### Claude's Discretion
- Exact batch size for embedding generation (performance tuning)
- sqlite-vec KNN query API surface (low-level query structure)
- Migration strategy for adding `note_embeddings` table to existing `brain.db` (idempotent ALTER or new CREATE IF NOT EXISTS)
- Ollama API call implementation details

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/reindex.py:reindex_brain()`: Current FTS5 reindex — embedding logic should be added here or called from here after the FTS5 walk
- `engine/db.py:init_schema()`: Schema init + migration pattern — `note_embeddings` table creation goes here; use `migrate_add_people_column()` as the pattern for idempotent migrations
- `engine/db.py:get_connection()`: WAL mode connection — use as-is for embedding writes
- `engine/forget.py`: Erasure logic — add `note_embeddings` DELETE alongside existing `notes` DELETE

### Established Patterns
- Idempotent schema: `CREATE TABLE IF NOT EXISTS` + separate `migrate_*` functions for additive changes
- Atomic writes: `conn.commit()` after each batch; rollback on error
- `pathlib.Path` throughout — no `os.path`
- `engine/paths.py` for `BRAIN_ROOT`, `DB_PATH` — use these constants, don't hardcode

### Integration Points
- `engine/reindex.py`: Embedding generation runs after FTS5 rebuild in `reindex_brain()` or as a second pass
- `engine/db.py:init_schema()`: `note_embeddings` DDL added here
- `engine/forget.py`: Cascade delete added alongside existing erasure
- `pyproject.toml`: `sentence-transformers` and `sqlite-vec` added as dependencies

</code_context>

<specifics>
## Specific Ideas

- No specific UX references — standard CLI output patterns are fine
- The `content_hash` should be SHA-256 of the note body (not frontmatter) to avoid false-positives on metadata-only updates
- `sqlite-vec` KNN query API needed for Phase 16 semantic search — expose as a queryable function in `engine/db.py` or `engine/search.py`

</specifics>

<deferred>
## Deferred Ideas

- Per-sensitivity provider routing (PII → Ollama, public → sentence-transformers) — explicitly rejected for Phase 14; revisit if needed in Phase 16
- tqdm progress bar — deferred; summary output is sufficient
- Auto-switching to Ollama when available — explicitly rejected; config-only provider selection

</deferred>

---

*Phase: 14-embedding-infrastructure*
*Context gathered: 2026-03-15*
