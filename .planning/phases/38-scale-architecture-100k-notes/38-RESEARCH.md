# Phase 38: Scale Architecture (100K Notes) - Research

**Researched:** 2026-03-26
**Domain:** Vector ANN indexing, SQLite scaling, encrypted backup, filesystem sharding, text chunking, memory consolidation
**Confidence:** HIGH (library decisions are locked; patterns verified against existing codebase)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**A. Scope**
- Full 8-workstream scope — brain is pre-production but expected to grow; build ahead of scale curve
- Filesystem sharding and tiered storage are included (future-proofing, not current pain)
- Memory consolidation engine ships in this phase (backend + background job only)
- Consolidation UI (Chrome extension prompt, GUI modal, CLI flag) is deferred to a follow-on phase

**Memory Consolidation Strategy**
- Capture default: always create new — no interruption to capture flow, no silent merges
- Background consolidation pass: periodic job clusters related notes by topic/entity/similarity, surfaces merge candidates in health dashboard
- User action: reviews candidates, approves merges explicitly — full control, no auto-merge
- Consolidation engine requires ANN index (hnswlib) to find similar notes efficiently — ships together

**B. Backup**
- Target: `~/SecondBrain/.backup/` — Drive-synced once Drive is configured (Phase 37 prerequisite)
- Coverage: markdown files + SQLite DB + embeddings index — full restore, not just markdown
- Encryption: encrypted at rest (Fernet, consistent with PLAT-01 requirement)
- Interface: single command (`sb-backup`) + single command restore (`sb-restore`)
- Health check: `sb-health` reports last backup timestamp and warns if > N days stale
- No new cloud infrastructure needed — Drive is the transport once Phase 37 sets it up

**C. ANN Vector Index**
- Library: hnswlib (`pip install hnswlib`) — zero-infra, no compilation, HNSW graph
- sqlite-vec retained for storage and non-vector queries; hnswlib handles vector search only
- Index stored as a file alongside the DB (e.g. `~/SecondBrain/.meta/brain.hnsw`)
- Rebuild from DB on `sb-reindex --full`; incremental updates on capture
- Fallback: if hnswlib index missing/corrupt, fall back to sqlite-vec KNN with a warning

**D. Chunked Embeddings**
- D1 — Threshold: Claude's discretion (agent decides optimal chunk size and length threshold)
- D2 — Search result: backend returns parent note path + matched chunk excerpt text
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

### Deferred Ideas (OUT OF SCOPE)
- Memory merge UI: Chrome extension "Similar note found — update instead?" prompt
- GUI capture modal: merge suggestion inline
- CLI: `--update <path>` flag to route capture to existing note
- MCP: `sb_capture_smart` routing to update vs create based on consolidation signal
- These all depend on the consolidation engine from Phase 38 being proven reliable first
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCALE-01 | ANN vector index (hnswlib) for fast similarity search at 100K+ notes | hnswlib 0.8.0 available via uv; HNSW cosine space; 768-dim (nomic-embed-text); incremental add_items; fallback to sqlite-vec |
| SCALE-02 | Incremental reindex — only re-embed changed notes, chunk new/changed notes | Existing `embed_pass()` hash-based staleness detection; extend to also write chunks on change |
| SCALE-03 | Filesystem sharding — split notes across subdirectories to avoid filesystem limits | New `engine/sharding.py`; move-on-write strategy with DB path update; by-type prefix is safest |
| SCALE-04 | Audit log rotation — archive old audit entries, cap table size | Existing `archive_old_action_items` pattern in `brain_health.py`; add `archive_old_audit_entries()` |
| SCALE-05 | Tiered storage — move cold notes to an archive tier, keep hot notes active | Age-threshold strategy; add `archived` flag to notes; API filters archived notes by default |
| SCALE-06 | Chunked embeddings with excerpt-aware search — long notes split into chunks, search returns matching excerpt | `note_chunks` table; `embed_chunks()` in `engine/embeddings.py`; extend `search_hybrid()` response shape |
| SCALE-07 | Summarization layer — auto-generate summary for long notes; store as frontmatter | Length threshold trigger; LLM summarize call via existing router; write to `summary` frontmatter field |
| SCALE-08 | Encrypted backup + restore — full brain backup (MD + DB + hnswlib index) with Fernet encryption, single-command restore | `engine/backup.py`; `sb-backup` / `sb-restore` entry points; key stored in `~/.config/second-brain/backup.key` |
</phase_requirements>

---

## Summary

Phase 38 builds the infrastructure layer that keeps the brain functional and fast at 100K+ notes. The core dependency is **hnswlib 0.8.0**, which provides HNSW approximate nearest-neighbour search without requiring a vector database server. All vector queries currently handled by sqlite-vec will migrate to hnswlib for ANN at scale, with sqlite-vec retained for storage and exact queries.

The phase has 8 workstreams that fall into two dependency tiers. Tier 1 (independent): ANN index, audit rotation, filesystem sharding, tiered storage. Tier 2 (depends on ANN): chunked embeddings (uses hnswlib for chunk vectors), memory consolidation (uses hnswlib to find merge candidates), summarization (independent but pairs well with chunking). Encrypted backup is independent of all others and can be built in parallel.

The critical integration path is: `hnswlib index built` → `note_chunks table added` → `embed_chunks() added to embeddings.py` → `reindex extended` → `search_hybrid() returns excerpts` → `consolidation engine can query hnswlib`. Every other workstream is additive and does not block this path.

**Primary recommendation:** Build hnswlib index first (SCALE-01), then chunked embeddings (SCALE-06), then consolidation engine (which reuses both). Ship backup (SCALE-08) and audit rotation (SCALE-04) as early independent plans. Sharding and tiered storage can be Wave 2 since they are future-proofing, not current pain.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hnswlib | 0.8.0 | HNSW approximate nearest-neighbour index | Locked decision; zero-infra; pure Python wheel; no server needed |
| cryptography | already in env | Fernet symmetric encryption for backup | Already used (PLAT-01); stable; key rotation built-in |
| sqlite-vec | already in env | Embedding BLOB storage; exact KNN fallback | Already deployed; retained alongside hnswlib |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | 2.4.3 (pulled by hnswlib) | Float32 array preparation for hnswlib | Required for `add_items()` / `knn_query()` |
| tomllib (stdlib) | stdlib 3.11+ | Config reads | Already used via `config_loader.py` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hnswlib | usearch | usearch is faster but requires compilation; hnswlib is pure wheel on macOS |
| hnswlib | faiss | faiss is GPU-optional, heavier install, more complex API |
| Fernet backup | age/GPG | age is excellent but adds a new dep; Fernet is already available |

**Installation (add to pyproject.toml dependencies):**
```bash
# Add to [project] dependencies in pyproject.toml:
"hnswlib>=0.8.0"
# numpy will be pulled in as hnswlib dependency — no explicit pin needed

# Then reinstall:
make dev
```

**Version verification:** hnswlib 0.8.0 confirmed via `uv pip install hnswlib --dry-run` (2026-03-26). Embedding dimension in production brain DB is **768** (nomic-embed-text). hnswlib index must be initialised with `dim=768`.

---

## Architecture Patterns

### Recommended Module Structure
```
engine/
├── embeddings.py        # ADD: embed_chunks(), split_text_into_chunks()
├── reindex.py           # EXTEND: embed_pass() writes to note_chunks
├── search.py            # EXTEND: search_hybrid() returns excerpt field
├── brain_health.py      # EXTEND: audit rotation, consolidation candidates
├── backup.py            # NEW: sb-backup, sb-restore
├── consolidate.py       # EXTEND: add consolidation_candidates() pass
├── sharding.py          # NEW: filesystem sharding helpers
└── db.py                # EXTEND: note_chunks migration, note_summaries column

scripts/
└── pyproject.toml       # ADD: sb-backup, sb-restore entry points
```

### Pattern 1: hnswlib Index Lifecycle
**What:** HNSW index is a file on disk (`~/SecondBrain/.meta/brain.hnsw`). Loaded into RAM on first query, kept in a module-level singleton. Saved to disk after each `add_items()` call.
**When to use:** All ANN vector queries at search time and consolidation candidate surfacing.

```python
# Source: hnswlib docs + dry-run verified API
import hnswlib
import numpy as np

DIM = 768  # nomic-embed-text / matches existing note_embeddings BLOBs

def _load_or_create_index(index_path: str, max_elements: int = 200_000) -> hnswlib.Index:
    p = hnswlib.Index(space='cosine', dim=DIM)
    if Path(index_path).exists():
        p.load_index(index_path, max_elements=max_elements)
    else:
        p.init_index(max_elements=max_elements, ef_construction=200, M=16)
    p.set_ef(50)  # ef at query time — higher = more accurate, slower
    return p

def add_to_index(p: hnswlib.Index, note_path: str, embedding_blob: bytes, index_path: str):
    """Add single note embedding. Note: label must be integer. Use note DB rowid."""
    vec = np.frombuffer(embedding_blob, dtype=np.float32).reshape(1, DIM)
    # label = integer rowid from note_embeddings table
    p.add_items(vec, np.array([label]))
    p.save_index(index_path)

def knn_query(p: hnswlib.Index, query_blob: bytes, k: int = 20) -> list[tuple[int, float]]:
    """Returns [(label, distance), ...] ordered by ascending distance."""
    vec = np.frombuffer(query_blob, dtype=np.float32).reshape(1, DIM)
    labels, distances = p.knn_query(vec, k=k)
    return list(zip(labels[0].tolist(), distances[0].tolist()))
```

**Critical note:** hnswlib labels must be non-negative integers. Use the `note_embeddings.rowid` (or a sequential label → path mapping stored alongside the index). A `label_to_path` dict serialised as JSON next to the `.hnsw` file is the standard pattern.

### Pattern 2: note_chunks Table + embed_chunks()
**What:** Long notes are split into overlapping character-window chunks. Each chunk gets an embedding. `note_chunks` stores chunk text + embedding blob. Search queries hnswlib for chunk embeddings, then returns the matching chunk text as `excerpt`.

```python
# Chunking function (discretion: 1200-char chunks, 200-char overlap, threshold 600 chars)
def split_text_into_chunks(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    """Character-window chunking. Returns list of chunk strings."""
    if len(text) <= chunk_size:
        return [text]  # short notes: single chunk = full body
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += chunk_size - overlap
    return chunks

# note_chunks schema migration (add to db.py init_schema):
# CREATE TABLE IF NOT EXISTS note_chunks (
#     id          INTEGER PRIMARY KEY,
#     note_path   TEXT NOT NULL,
#     chunk_index INTEGER NOT NULL,
#     chunk_text  TEXT NOT NULL,
#     embedding   BLOB,
#     created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
#     UNIQUE(note_path, chunk_index)
# )
```

### Pattern 3: Fernet Backup Encryption
**What:** Full brain backup tarball, encrypted with Fernet before writing to `~/SecondBrain/.backup/`. Key stored at `~/.config/second-brain/backup.key`, generated on first run.

```python
from cryptography.fernet import Fernet
import tarfile, io, os
from pathlib import Path

KEY_PATH = Path.home() / ".config" / "second-brain" / "backup.key"

def _get_or_create_key() -> bytes:
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        return KEY_PATH.read_bytes()
    key = Fernet.generate_key()
    KEY_PATH.write_bytes(key)
    KEY_PATH.chmod(0o600)
    return key

def backup_brain(brain_root: Path, db_path: Path, hnsw_path: Path, backup_dir: Path) -> Path:
    fernet = Fernet(_get_or_create_key())
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        tar.add(brain_root, arcname='notes')
        tar.add(db_path, arcname='brain.db')
        if hnsw_path.exists():
            tar.add(hnsw_path, arcname='brain.hnsw')
    encrypted = fernet.encrypt(buf.getvalue())
    ts = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    out_path = backup_dir / f"brain-{ts}.enc"
    out_path.write_bytes(encrypted)
    return out_path
```

### Pattern 4: Audit Log Rotation
**What:** Mirror of `archive_old_action_items()` in `brain_health.py`. Archive rows older than N days to `audit_log_archive`, delete from `audit_log`. Current `audit_log` has 2002 rows already.

```python
# Reuse exact pattern from brain_health.archive_old_action_items()
def archive_old_audit_entries(conn, days: int = 90) -> int:
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT id, event_type, note_path, detail, created_at FROM audit_log WHERE created_at < ?",
        (cutoff,)
    ).fetchall()
    # INSERT into audit_log_archive, DELETE from audit_log per-row
    # (semgrep-safe executemany+DELETE pattern from Phase 32)
```

### Pattern 5: Memory Consolidation Candidates
**What:** Background pass that queries hnswlib for similar notes (above a configurable similarity threshold), groups by shared entity (people/tags), and writes candidates to a new `consolidation_candidates` table. `sb-health` surfaces candidates like duplicates. No auto-merge.

```python
# Extend consolidate.py — add consolidation_candidates() function
# Use hnswlib knn_query per note, filter by similarity > 0.80 (discretion)
# AND shared entity dimension (same person in `people` column or same tag)
# Write to consolidation_candidates table, deduplicate pairs
# sb-health reports count of open candidates
```

### Anti-Patterns to Avoid
- **Storing hnswlib labels as note paths:** Labels must be integers. Use `rowid` from `note_embeddings`. Keep a `label_map.json` alongside the `.hnsw` file for path resolution.
- **Rebuilding hnswlib index on every startup:** Load from file at first query. Only rebuild on `sb-reindex --full` or index corruption.
- **Chunking all notes unconditionally:** Notes shorter than chunk_size should produce a single chunk = full body. This keeps short notes searchable without inflating the chunk table.
- **Blocking capture on backup:** `sb-backup` is a standalone command, not hooked into capture path.
- **Writing backup key to git-tracked files:** Key must live at `~/.config/second-brain/backup.key` (chmod 600), never in `~/SecondBrain/` or the repo.
- **Encrypting the key with Fernet:** The Fernet key IS the secret. Protect the file, don't recurse.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Approximate nearest-neighbour search | sqlite-vec exact KNN loop | hnswlib | sqlite-vec KNN is O(n) full scan at 100K; hnswlib is O(log n) |
| Encryption key generation + secret handling | Custom AES + key encoding | `Fernet.generate_key()` + file | Fernet handles key format, base64, HMAC auth; custom crypto has subtle bugs |
| Archive tarball | Manual file copy loop | `tarfile` stdlib | Handles symlinks, permissions, streaming; handles cross-platform paths |
| Text chunking overlap | Custom tokeniser | Character-window with overlap | Token counting via tiktoken adds overhead; char window is fast and predictable |
| Integer label mapping for hnswlib | Separate DB table | JSON file `label_map.json` alongside `.hnsw` | Same lifecycle as the index; atomic save; no DB round-trip at query time |

**Key insight:** hnswlib is specifically designed for the "persist to disk, load into RAM, query fast" use case — it handles serialisation, space metrics, and ef tuning. Do not wrap sqlite-vec with a custom index layer.

---

## Runtime State Inventory

> Not a rename/refactor phase. However, the hnswlib index is new runtime state.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `note_embeddings` table — 58 rows, 768-dim BLOBs | Wave 0: read all BLOBs, populate hnswlib index file |
| Live service config | `sb-api` launchd service — runs in background | Must be restarted after `make dev` when search.py changes |
| OS-registered state | No hnswlib index file exists yet | Wave 0 plan must create `brain.hnsw` + `label_map.json` on first `sb-reindex` |
| Secrets/env vars | Backup key does not exist yet — generated on first `sb-backup` | `~/.config/second-brain/backup.key` — outside repo, chmod 600 |
| Build artifacts | `sb-backup` / `sb-restore` entry points not in pyproject.toml yet | Add to `[project.scripts]` + `make dev` to register |

---

## Common Pitfalls

### Pitfall 1: hnswlib label type mismatch
**What goes wrong:** `add_items()` crashes with "wrong label type" if labels are Python strings or floats.
**Why it happens:** hnswlib labels must be `uint64` integers. Note paths are strings.
**How to avoid:** Use `note_embeddings.rowid` as label. Maintain a `{rowid: note_path}` dict serialised to `label_map.json` alongside the `.hnsw` file. Load both together.
**Warning signs:** `TypeError` or `ValueError` at `add_items()` call.

### Pitfall 2: hnswlib index capacity exhausted
**What goes wrong:** `add_items()` raises `RuntimeError: The number of elements exceeds the specified limit`.
**Why it happens:** `max_elements` is fixed at `init_index()` time. If brain grows past initial cap, add fails silently or errors.
**How to avoid:** Initialise with `max_elements=200_000` (well above 100K note target). On `sb-reindex --full`, compare current note count to index capacity and resize if needed via `resize_index()`.
**Warning signs:** RuntimeError on capture after brain grows large.

### Pitfall 3: hnswlib index / label_map desync
**What goes wrong:** Note deleted from DB but label remains in hnswlib index. KNN results return dead paths.
**Why it happens:** hnswlib does not support true deletion in cosine space (mark_deleted() works but not reversible in all modes). label_map.json points to deleted note.
**How to avoid:** On `sb-reindex` or on `sb-forget`, rebuild the index (or use `mark_deleted()` if HNSW mode supports it). On KNN query, filter results by checking path existence in DB before returning.
**Warning signs:** Search results returning paths that no longer exist in `notes` table.

### Pitfall 4: Backup key loss = data unrecoverable
**What goes wrong:** Fernet-encrypted `.enc` files cannot be decrypted without the original key.
**Why it happens:** Key stored only at `~/.config/second-brain/backup.key` — not in backup itself.
**How to avoid:** `sb-health` must warn if backup key file is missing. Document that the key must be backed up separately (e.g., added to macOS Keychain or personal password manager). Consider including a key verification step in `sb-restore` that checks key before writing any files.
**Warning signs:** `sb-health` key check fails; `sb-restore` raises `InvalidToken`.

### Pitfall 5: Chunked embeddings inflating hnswlib index size
**What goes wrong:** A 100K-note brain with 5 chunks/note = 500K vectors in hnswlib. Index RAM exceeds available memory.
**Why it happens:** Chunked embeddings are stored in `note_chunks`, but if hnswlib is used for chunk-level ANN, index size scales with chunks not notes.
**How to avoid:** Keep two separate hnswlib indices: `brain.hnsw` for note-level (used for consolidation/dedup), `brain-chunks.hnsw` for chunk-level (used for search excerpts). Or: use sqlite-vec for chunk KNN (smaller scale than note-level) and hnswlib only for note-level.
**Warning signs:** High RAM usage on search; hnswlib OOM on large brains.

### Pitfall 6: Tiered storage path updates breaking existing DB rows
**What goes wrong:** Moving a note file to an archive directory changes its absolute path. All `note_path` foreign keys across 6+ tables become stale.
**Why it happens:** Phase 32 kept absolute paths in DB. Moving the file without updating all FK columns causes broken lookups everywhere.
**How to avoid:** Tiered storage move must be a DB transaction: update `notes.path`, then cascade to `note_embeddings`, `note_chunks`, `note_tags`, `note_people`, `action_items`, `relationships`, `audit_log`. Test with `brain_health.get_missing_file_notes()` after any move.
**Warning signs:** `get_missing_file_notes()` returns moved notes; search returns broken results.

---

## Code Examples

### hnswlib index build from existing note_embeddings

```python
# Source: hnswlib 0.8.0 API + production brain has 768-dim embeddings (verified 2026-03-26)
import hnswlib
import numpy as np
import json
from pathlib import Path

DIM = 768  # nomic-embed-text output dimension (verified from brain.db)

def build_hnsw_index(conn, index_path: Path, label_map_path: Path):
    rows = conn.execute(
        "SELECT rowid, note_path, embedding FROM note_embeddings WHERE embedding IS NOT NULL"
    ).fetchall()
    if not rows:
        return

    p = hnswlib.Index(space='cosine', dim=DIM)
    p.init_index(max_elements=max(len(rows) * 2, 200_000), ef_construction=200, M=16)

    labels = np.array([r[0] for r in rows], dtype=np.uint64)
    vecs = np.array([
        np.frombuffer(r[2], dtype=np.float32) for r in rows
    ])
    p.add_items(vecs, labels)
    p.save_index(str(index_path))

    label_map = {str(r[0]): r[1] for r in rows}  # rowid -> note_path
    label_map_path.write_text(json.dumps(label_map))
```

### search_hybrid() returning excerpt

```python
# Extend existing search_hybrid() in engine/search.py
# After getting RRF-merged results, enrich each result with excerpt from note_chunks

def _get_excerpt(conn, note_path: str, query_blob: bytes) -> str | None:
    """Return the chunk text most similar to query, or None if no chunks."""
    rows = conn.execute(
        "SELECT chunk_text, embedding FROM note_chunks WHERE note_path=?",
        (note_path,)
    ).fetchall()
    if not rows:
        return None
    # pick chunk with minimum cosine distance to query embedding
    query_vec = np.frombuffer(query_blob, dtype=np.float32)
    best_chunk = min(rows, key=lambda r: np.dot(
        query_vec,
        np.frombuffer(r[1], dtype=np.float32)
    ) / (np.linalg.norm(query_vec) * np.linalg.norm(np.frombuffer(r[1], dtype=np.float32)) + 1e-9) * -1
    )
    return best_chunk[0][:300]  # trim to 300 chars for API response
```

### Audit log rotation (mirrors brain_health.archive_old_action_items pattern)

```python
# Add to engine/brain_health.py — same semgrep-safe pattern as archive_old_action_items
def archive_old_audit_entries(conn: sqlite3.Connection, days: int = 90) -> int:
    """Move audit_log rows older than `days` to audit_log_archive. Returns count archived."""
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT id, event_type, note_path, detail, created_at FROM audit_log WHERE created_at < ?",
        (cutoff,)
    ).fetchall()
    if not rows:
        return 0
    conn.executemany(
        "INSERT OR IGNORE INTO audit_log_archive "
        "(id, event_type, note_path, detail, created_at) VALUES (?, ?, ?, ?, ?)",
        rows
    )
    for (row_id, *_) in rows:
        conn.execute("DELETE FROM audit_log WHERE id=?", (row_id,))
    conn.commit()
    return len(rows)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| sqlite-vec exact KNN for all semantic search | hnswlib HNSW for ANN at scale, sqlite-vec for storage | Phase 38 | search_semantic() becomes O(log n) instead of O(n) |
| No chunking — note body embedded as one unit | Chunked embeddings with excerpt return | Phase 38 | Long notes now searchable at paragraph level |
| No backup — "rebuild from reindex" is DR plan | Encrypted tar backup with single-command restore | Phase 38 | Production-grade DR; markdown + DB + embeddings covered |
| audit_log grows unbounded | audit_log_archive rotation at 90 days | Phase 38 | Keeps hot table small; audit history preserved |

---

## Open Questions

1. **nomic-embed-text vs all-MiniLM-L6-v2 dimension mismatch**
   - What we know: Brain DB has 768-dim embeddings (nomic-embed-text). all-MiniLM-L6-v2 produces 384-dim. Config shows provider is "ollama" (nomic-embed-text).
   - What's unclear: If someone switches provider to sentence-transformers, existing 768-dim embeddings in DB won't match new 384-dim index.
   - Recommendation: Encode DIM in the label_map.json or index metadata. On index load, assert DIM matches current provider's output size. If mismatch, require `sb-reindex --full`.

2. **hnswlib mark_deleted() for tiered storage**
   - What we know: hnswlib supports `mark_deleted(label)` but behaviour in cosine space varies between versions.
   - What's unclear: Whether mark_deleted is sufficient for archived notes, or full index rebuild is needed.
   - Recommendation: Use DB-side filter (check note exists in active notes table) as primary guard. Mark_deleted as optional optimisation. Document rebuild as the clean path.

3. **Filesystem sharding — when to shard**
   - What we know: Current brain has 66 notes; sharding is future-proofing.
   - What's unclear: macOS HFS+/APFS directory performance degradation threshold (typically ~100K files/dir).
   - Recommendation: Implement sharding as an opt-in migration triggered by `sb-shard` command (or auto-triggered by `sb-reindex` when note count > 10K). Default strategy: by-type-prefix (`notes/`, `people/`, `meetings/`, etc.) which is already partly implemented by the existing folder structure.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| hnswlib | SCALE-01, SCALE-06 | Not yet installed | 0.8.0 (dry-run verified) | sqlite-vec KNN (already in use, O(n)) |
| cryptography | SCALE-08 | Installed | confirmed | none — required |
| numpy | hnswlib | Not yet installed | 2.4.3 (pulled by hnswlib) | none — required with hnswlib |
| sqlite-vec | fallback + storage | Installed | confirmed | — |
| Ollama + nomic-embed-text | chunked embeddings | Running (brain has 58 embeddings) | confirmed | sentence-transformers (384-dim, requires reindex) |

**Missing dependencies with no fallback:**
- hnswlib: must be added to pyproject.toml before any SCALE-01 work. Install: `uv add hnswlib` or add `"hnswlib>=0.8.0"` to pyproject.toml dependencies.

**Missing dependencies with fallback:**
- None — all others already installed.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/ -q -x` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCALE-01 | hnswlib index builds from existing embeddings; knn_query returns correct note paths | unit | `uv run pytest tests/test_hnsw.py -x` | Wave 0 |
| SCALE-02 | Incremental reindex writes chunks for changed notes only | unit | `uv run pytest tests/test_reindex.py -x` | Exists |
| SCALE-03 | Shard move updates all DB foreign key paths; missing_file_notes returns empty after shard | unit | `uv run pytest tests/test_sharding.py -x` | Wave 0 |
| SCALE-04 | Audit entries older than threshold are archived; audit_log count decreases | unit | `uv run pytest tests/test_brain_health.py -x` | Exists |
| SCALE-05 | Note flagged archived is excluded from default search; sb-health reports archived count | unit | `uv run pytest tests/test_tiered.py -x` | Wave 0 |
| SCALE-06 | Long note produces multiple chunks; search returns excerpt field | unit | `uv run pytest tests/test_search.py -x` | Exists |
| SCALE-07 | Note above length threshold gets summary written to frontmatter | unit | `uv run pytest tests/test_summarize.py -x` | Wave 0 |
| SCALE-08 | sb-backup creates encrypted file; sb-restore reconstructs DB + notes + hnsw index | unit + smoke | `uv run pytest tests/test_backup.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -q -x`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_hnsw.py` — covers SCALE-01: index build, knn_query, label_map round-trip, fallback to sqlite-vec
- [ ] `tests/test_sharding.py` — covers SCALE-03: move note, verify all FK paths updated, verify health check clean
- [ ] `tests/test_tiered.py` — covers SCALE-05: archive flag, search exclusion, health report
- [ ] `tests/test_summarize.py` — covers SCALE-07: length threshold, summary written to frontmatter
- [ ] `tests/test_backup.py` — covers SCALE-08: encrypt/decrypt round-trip, restore recreates all artefacts

---

## Project Constraints (from CLAUDE.md)

| Directive | Implication for Phase 38 |
|-----------|--------------------------|
| `make dev` is the single deploy command | All new entry points (`sb-backup`, `sb-restore`) must be added to `[project.scripts]` in pyproject.toml and registered via `make dev` |
| macOS 26 (Darwin 25.x) — no sentence-transformers torch wheel | Embeddings via Ollama (nomic-embed-text, 768-dim). hnswlib dim must be 768. No sentence-transformers dependency. |
| No direct Anthropic API key — Max plan, MCP adapter | Summarization (SCALE-07) uses existing router/adapter pattern, not direct SDK |
| Two-step token pattern for destructive ops | `sb-restore` overwrites live DB + files — must use confirm_token pattern |
| BRAIN_PATH env var used by tests — monkeypatch both `engine.db.DB_PATH` and `engine.paths.DB_PATH` | All new tests (backup, sharding, hnsw) must follow this pattern |
| After frontend changes: build → reinstall uv tool → restart sb-api | Phase 38 has no frontend changes, but any API response shape change (excerpt field) requires frontend awareness. No frontend work this phase per CONTEXT.md. |
| Never use WebFetch — use `mcp__plugin_context-mode_context-mode__fetch_and_index` | N/A for implementation, relevant if agent needs to fetch docs |

---

## Sources

### Primary (HIGH confidence)
- Direct inspection of `engine/embeddings.py`, `engine/reindex.py`, `engine/search.py`, `engine/brain_health.py`, `engine/db.py`, `engine/consolidate.py`, `engine/config_loader.py` — actual codebase patterns
- `uv pip install hnswlib --dry-run` — version 0.8.0 confirmed installable 2026-03-26
- Production brain.db introspection — 768-dim embeddings, 2002 audit_log rows, 66 notes, 58 embeddings
- `pyproject.toml` — current dependency inventory
- `.planning/phases/38-scale-architecture-100k-notes/38-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- hnswlib GitHub README (0.8.0) — API: `init_index`, `add_items`, `knn_query`, `save_index`, `load_index`, `resize_index`, `mark_deleted`, label type requirements
- cryptography.fernet docs — `Fernet.generate_key()`, `encrypt()`, `decrypt()`, `InvalidToken` exception

### Tertiary (LOW confidence)
- macOS APFS directory performance at 100K+ files — community reports suggest degradation above 100K items/directory; APFS handles better than HFS+ but sharding is still prudent

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — hnswlib installability dry-run confirmed; cryptography already in env; embedding dim verified from live DB
- Architecture: HIGH — all patterns are extensions of existing verified codebase patterns
- Pitfalls: HIGH — hnswlib label type, capacity, and desync pitfalls are documented in hnswlib issue tracker and README; tiered storage FK cascade pitfall derived directly from Phase 32 lessons
- Chunking: MEDIUM — chunk size (1200 chars / 200 overlap) is Claude's discretion; no domain-specific tuning done

**Research date:** 2026-03-26
**Valid until:** 2026-05-01 (hnswlib is stable; cryptography is stable; architecture is based on locked decisions)
