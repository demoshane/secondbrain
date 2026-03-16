# Phase 14: Embedding Infrastructure - Research

**Researched:** 2026-03-15
**Domain:** Local vector embeddings — sentence-transformers, sqlite-vec, Ollama embed
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Stale detection: SHA-256 of note body only (not frontmatter); computed at reindex time; hash diff OR missing row triggers re-embed; write commands do NOT set stale=true directly
- `note_embeddings` schema: single table, columns `note_path TEXT PRIMARY KEY, embedding BLOB, content_hash TEXT, stale BOOL, created_at TEXT, updated_at TEXT`
- GDPR erasure: `sb-forget` deletes embedding row immediately (same transaction as notes delete) — no lazy cleanup
- First-run download: auto-download with visible message `[sb-reindex] Downloading embedding model (~90MB, first-time only)...`; cache in `~/.cache/huggingface/`; no flag/prompt
- Reindex scope: incremental by default (hash-changed or missing only); `--full` flag forces full rebuild; summary-only output: `[sb-reindex] Embedding N new/stale notes...` then `[OK] N embeddings updated, N unchanged`
- Embedding providers: sentence-transformers (primary, `all-MiniLM-L6-v2`) + Ollama fallback (`nomic-embed-text`); provider set in `config.toml` as `embeddings.provider`; no auto-switching; single provider for all notes regardless of sensitivity
- Integration points: `engine/reindex.py` (embed pass after FTS5), `engine/db.py:init_schema()` (DDL), `engine/forget.py` (cascade delete), `pyproject.toml` (new deps)

### Claude's Discretion
- Exact batch size for embedding generation (performance tuning)
- sqlite-vec KNN query API surface (low-level query structure)
- Migration strategy for adding `note_embeddings` table (idempotent ALTER or `CREATE TABLE IF NOT EXISTS`)
- Ollama API call implementation details

### Deferred Ideas (OUT OF SCOPE)
- Per-sensitivity provider routing (PII → Ollama, public → sentence-transformers)
- tqdm progress bar
- Auto-switching to Ollama when available
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EMBED-01 | User can reindex brain with vector embeddings via `sb-reindex` | sentence-transformers encode API, reindex.py integration pattern |
| EMBED-02 | Embeddings are generated locally using `all-MiniLM-L6-v2` — no cloud call | Model runs fully offline after first download; HuggingFace cache at `~/.cache/huggingface/` |
| EMBED-03 | Stale embeddings detected via content-hash and re-embedded on next reindex | SHA-256 of body text; compare stored `content_hash`; mark stale before re-embed |
| EMBED-04 | `sb-forget` cascades to remove embeddings for deleted notes | Add DELETE FROM note_embeddings alongside existing notes/relationships deletes |
</phase_requirements>

---

## Summary

Phase 14 adds local vector embedding generation to the existing `sb-reindex` command and wires GDPR erasure into `sb-forget`. The two core new dependencies are `sentence-transformers` (primary embed provider) and `sqlite-vec` (vector storage + KNN queries). Both are well-established and production-ready.

The architecture is a second pass inside `reindex_brain()`: after the FTS5 upsert walk completes, iterate notes comparing SHA-256 body hashes to the `note_embeddings` table; re-embed only changed or missing notes; store embedding as `float32` BLOB via sqlite-vec serialization. The `note_embeddings` table is a plain table (not a `vec0` virtual table) — embeddings are stored as BLOBs, and a separate `vec0` virtual table is created for KNN queries (Phase 16 consumer). This is the standard sqlite-vec pattern.

The Ollama fallback path uses `ollama.embed(model="nomic-embed-text", input=[...])` returning `response["embeddings"]`. Provider dispatch is config-driven — a thin `embed_texts(texts, config)` function is the natural boundary. The `note_embeddings` table migration is a clean `CREATE TABLE IF NOT EXISTS` (not an ALTER), matching existing `SCHEMA_SQL` style in `engine/db.py`.

**Primary recommendation:** Add `note_embeddings` DDL to `SCHEMA_SQL`, write `engine/embeddings.py` for provider dispatch, call it from `reindex_brain()` after the FTS5 pass, delete from `note_embeddings` in `forget_person()`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sentence-transformers | >=3.0 (v5.3 latest as of 2026-03) | Local text → float[384] vector, `all-MiniLM-L6-v2` | HuggingFace official; all-MiniLM-L6-v2 is the de facto 384-dim local model |
| sqlite-vec | 0.1.6 (stable); 0.1.7a2 (pre-release) | SQLite extension: BLOB storage + vec0 KNN virtual table | Successor to sqlite-vss; pure C, zero deps; ships as Python wheel |
| ollama | >=0.6 (already in pyproject.toml) | Fallback embed via `ollama.embed()` | Already a project dependency; `nomic-embed-text` is the standard local embed model |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hashlib (stdlib) | stdlib | SHA-256 of note body for content hash | Always — no new dependency |
| struct (stdlib) | stdlib | `serialize_float32` for BLOB packing | When not using numpy; `struct.pack("%sf" % len(v), *v)` |
| numpy | transitive via sentence-transformers | Float32 array handling | Use `.astype(np.float32).tobytes()` as serialization path |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sentence-transformers | transformers + AutoModel + mean pooling | More control, more boilerplate; sentence-transformers is the standard wrapper |
| sqlite-vec 0.1.6 (stable) | 0.1.7a2 (pre-release) | Pre-release has pagination features; stick to stable for Phase 14 |
| plain BLOB in `note_embeddings` | vec0 virtual table for storage | vec0 is KNN-optimized but adds complexity; plain BLOB + separate vec0 for search is the recommended two-table pattern |

**Installation:**
```bash
uv add sentence-transformers sqlite-vec
```

---

## Architecture Patterns

### Recommended Project Structure
```
engine/
├── embeddings.py       # NEW: provider dispatch, embed_texts(), load_model()
├── reindex.py          # MODIFIED: calls embed_pass() after FTS5 walk
├── db.py               # MODIFIED: note_embeddings DDL added to SCHEMA_SQL
├── forget.py           # MODIFIED: DELETE FROM note_embeddings cascade
└── config_loader.py    # UNCHANGED: load_config() already reads config.toml
```

### Pattern 1: note_embeddings Table (plain, not vec0)
**What:** A plain table stores the embedding BLOB alongside the content hash and staleness flag. A separate `vec0` virtual table (created at KNN query time in Phase 16) references the rowids.
**When to use:** Phase 14. Separates storage from KNN index; allows incremental update without rebuilding the entire vec0 index.
**DDL to add to SCHEMA_SQL in `engine/db.py`:**
```sql
CREATE TABLE IF NOT EXISTS note_embeddings (
    note_path    TEXT PRIMARY KEY,
    embedding    BLOB,
    content_hash TEXT,
    stale        BOOL NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
```

### Pattern 2: Provider Dispatch (engine/embeddings.py)
**What:** Single `embed_texts(texts: list[str], config: dict) -> list[bytes]` function that routes to sentence-transformers or Ollama based on `config["embeddings"]["provider"]`. Returns serialized float32 BLOBs ready for DB insertion.
**When to use:** Called from `reindex_brain()` once per batch of stale notes.
```python
# Source: HuggingFace sbert.net quickstart + ollama-python GitHub
import struct
from sentence_transformers import SentenceTransformer

_model_cache: SentenceTransformer | None = None

def _get_st_model() -> SentenceTransformer:
    global _model_cache
    if _model_cache is None:
        _model_cache = SentenceTransformer("all-MiniLM-L6-v2")
    return _model_cache

def _serialize(vector) -> bytes:
    """Convert float list or numpy array to sqlite-vec BLOB (float32 little-endian)."""
    import numpy as np
    if hasattr(vector, "astype"):
        return vector.astype(np.float32).tobytes()
    return struct.pack("%sf" % len(vector), *vector)

def embed_texts(texts: list[str], provider: str = "sentence-transformers",
                batch_size: int = 32) -> list[bytes]:
    if provider == "sentence-transformers":
        model = _get_st_model()
        vectors = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
        return [_serialize(v) for v in vectors]
    elif provider == "ollama":
        import ollama
        resp = ollama.embed(model="nomic-embed-text", input=texts)
        return [_serialize(v) for v in resp["embeddings"]]
    else:
        raise ValueError(f"Unknown embedding provider: {provider!r}")
```

### Pattern 3: Incremental Embed Pass in reindex_brain()
**What:** After the FTS5 commit, fetch all note paths + bodies from `notes`, compare SHA-256 body hash to `note_embeddings.content_hash`, collect stale/missing paths, embed in batches, upsert.
**When to use:** Default (incremental). `--full` flag sets `force=True` which skips hash comparison and re-embeds all.
```python
import hashlib, datetime

def embed_pass(conn, provider: str, batch_size: int = 32, force: bool = False) -> dict:
    """Second pass: generate/update embeddings for stale or missing notes."""
    from engine.embeddings import embed_texts

    rows = conn.execute("SELECT path, body FROM notes").fetchall()
    existing = {
        r[0]: r[1]
        for r in conn.execute("SELECT note_path, content_hash FROM note_embeddings").fetchall()
    }
    to_embed = []
    for path, body in rows:
        h = hashlib.sha256(body.encode()).hexdigest()
        if force or existing.get(path) != h:
            to_embed.append((path, body, h))

    if not to_embed:
        return {"updated": 0, "unchanged": len(rows)}

    print(f"[sb-reindex] Embedding {len(to_embed)} new/stale notes...")

    paths, bodies, hashes = zip(*to_embed)
    blobs = embed_texts(list(bodies), provider=provider, batch_size=batch_size)
    now = datetime.datetime.utcnow().isoformat()

    for path, blob, h in zip(paths, blobs, hashes):
        conn.execute(
            """INSERT INTO note_embeddings (note_path, embedding, content_hash, stale, updated_at)
               VALUES (?, ?, ?, 0, ?)
               ON CONFLICT(note_path) DO UPDATE SET
                   embedding=excluded.embedding,
                   content_hash=excluded.content_hash,
                   stale=0,
                   updated_at=excluded.updated_at""",
            (path, blob, h, now),
        )
    conn.commit()
    return {"updated": len(to_embed), "unchanged": len(rows) - len(to_embed)}
```

### Pattern 4: sqlite-vec KNN Query (for Phase 16 reference)
**What:** Load the sqlite-vec extension, create a `vec0` virtual table mirroring `note_embeddings`, run a KNN MATCH query. Phase 14 only needs to store blobs correctly — the vec0 table and queries are Phase 16 work.
**When to use:** Phase 16 semantic search. Document here so embedding storage format is compatible.
```python
# Source: asg017/sqlite-vec GitHub examples/simple-python/demo.py
import sqlite_vec

def get_connection_with_vec() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn

# KNN query (Phase 16):
# conn.execute("""
#     CREATE VIRTUAL TABLE IF NOT EXISTS vec_notes USING vec0(
#         note_path TEXT,
#         embedding float[384]
#     )
# """)
# rows = conn.execute("""
#     SELECT note_path, distance
#     FROM vec_notes
#     WHERE embedding MATCH ?
#     ORDER BY distance
#     LIMIT ?
# """, [query_blob, k]).fetchall()
```

### Anti-Patterns to Avoid
- **Storing embeddings in a vec0 virtual table directly:** vec0 tables do not support incremental upsert in 0.1.6; use a plain table for storage, separate vec0 for search.
- **Hashing the full file (frontmatter + body):** Frontmatter-only edits (tag add, title rename) would trigger false-positive re-embeds. Hash `post.content` only, which is the body string after frontmatter parse.
- **Module-level model load:** Loading `SentenceTransformer(...)` at import time triggers a 90MB download check on every `engine/` import. Use lazy load (`_model_cache` pattern above).
- **Calling `model.encode()` one note at a time:** Batch encoding is 5–20x faster than individual calls due to GPU/CPU batching in sentence-transformers.
- **Forgetting `conn.enable_load_extension(False)` after loading sqlite-vec:** Leaving extensions enabled is a security risk; always re-disable.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Float32 BLOB serialization | Custom packing code | `numpy_array.astype(np.float32).tobytes()` or `struct.pack` | Edge cases around float64 vs float32; numpy is already a transitive dep |
| KNN search | Manual cosine distance loop in Python | sqlite-vec `vec0` + MATCH | Python loop over 10k embeddings is ~50ms; sqlite-vec is SIMD-accelerated C |
| Model download/caching | Custom download logic | HuggingFace default cache (`~/.cache/huggingface/`) | Handles partial downloads, resumption, version pinning automatically |
| Ollama embed HTTP call | `requests.post(...)` | `ollama.embed()` from the `ollama` library (already in deps) | Already a dependency; handles connection errors, response parsing |

**Key insight:** Both the embedding and the vector search are solved problems. The only custom code needed is the hash-comparison loop and DB upsert — everything else delegates to existing libraries.

---

## Common Pitfalls

### Pitfall 1: all-MiniLM-L6-v2 truncates at 256 word pieces
**What goes wrong:** Notes longer than ~200 words are silently truncated; embedding only represents the first 256 tokens.
**Why it happens:** Model max sequence length is 256 word pieces (hard limit in the architecture).
**How to avoid:** For Phase 14 this is acceptable — the model contract is documented. If full-document coverage is needed later, chunk the body before encoding (Phase 16 concern).
**Warning signs:** Similarity scores between long notes are unreliable beyond ~256 tokens.

### Pitfall 2: sqlite-vec extension not loaded for test DB connections
**What goes wrong:** `CREATE VIRTUAL TABLE ... USING vec0(...)` fails in tests with "no such module: vec0".
**Why it happens:** `conn.enable_load_extension(True); sqlite_vec.load(conn)` must be called on every connection that uses vec0. The existing `db_conn` fixture in `conftest.py` does not do this.
**How to avoid:** Phase 14 does NOT use vec0 in `note_embeddings` (plain table). Tests for embedding storage do not need the extension loaded. Only Phase 16 KNN tests need a `vec_conn` fixture.

### Pitfall 3: First-run model download blocks reindex silently
**What goes wrong:** User runs `sb-reindex` and it hangs for 60+ seconds with no output while downloading the 90MB model.
**Why it happens:** `SentenceTransformer("all-MiniLM-L6-v2")` fetches from HuggingFace on first call.
**How to avoid:** Print the download notice BEFORE calling `SentenceTransformer(...)`. Check `sentence_transformers.util.snapshot_download` or `huggingface_hub.try_to_load_from_cache()` to detect cache miss before load — but the simpler approach is to just always print the notice on first `sb-reindex` when no embeddings exist yet.

### Pitfall 4: `note_embeddings.note_path` must match `notes.path` exactly
**What goes wrong:** KNN results can't be joined back to notes if path format differs (trailing slash, relative vs absolute).
**Why it happens:** `notes.path` stores absolute paths (established pattern from SEARCH-01). If embedding pass uses a different path representation, the join fails.
**How to avoid:** Use `str(md_path.resolve())` in the embed pass, same as `reindex_brain()` does for `notes.path`.

### Pitfall 5: Ollama not running causes silent failure or hard crash
**What goes wrong:** `ollama.embed()` raises `httpx.ConnectError` if the Ollama daemon isn't running.
**Why it happens:** The Ollama Python client makes HTTP calls to localhost:11434.
**How to avoid:** Wrap Ollama calls in a try/except; surface a clear error: `[ERROR] Ollama provider selected but Ollama is not running. Start Ollama or set embeddings.provider = "sentence-transformers" in config.toml.`

### Pitfall 6: `stale BOOL` needs explicit `NOT NULL DEFAULT 0`
**What goes wrong:** SQLite's BOOL is really INTEGER; NULLs in `stale` cause incorrect comparisons in `WHERE stale = 1`.
**Why it happens:** Forgetting `NOT NULL DEFAULT 0` allows NULL insertion.
**How to avoid:** DDL enforces `stale BOOL NOT NULL DEFAULT 0`. The upsert always sets `stale=0` on write.

---

## Code Examples

### SHA-256 body hash
```python
# Source: stdlib hashlib — no external dependency
import hashlib
content_hash = hashlib.sha256(post.content.encode()).hexdigest()
```

### Loading sentence-transformers (lazy, module-level cache)
```python
# Source: sbert.net quickstart
from sentence_transformers import SentenceTransformer
_model: SentenceTransformer | None = None

def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model
```

### Batch encode and serialize
```python
# Source: sbert.net + sqlite-vec examples
import numpy as np
vectors = model.encode(texts, batch_size=32, show_progress_bar=False)
# vectors shape: (N, 384), dtype float32
blobs = [v.astype(np.float32).tobytes() for v in vectors]
```

### Ollama embed call
```python
# Source: ollama-python GitHub README
import ollama
response = ollama.embed(model="nomic-embed-text", input=texts)
# response["embeddings"] is list[list[float]]
blobs = [_serialize(v) for v in response["embeddings"]]
```

### Upsert embedding row
```python
# Source: SQLite UPSERT pattern (ON CONFLICT DO UPDATE)
conn.execute("""
    INSERT INTO note_embeddings (note_path, embedding, content_hash, stale, updated_at)
    VALUES (?, ?, ?, 0, ?)
    ON CONFLICT(note_path) DO UPDATE SET
        embedding=excluded.embedding,
        content_hash=excluded.content_hash,
        stale=0,
        updated_at=excluded.updated_at
""", (note_path, blob, content_hash, now))
```

### Cascade delete in forget_person()
```python
# Add alongside existing notes/relationships deletes — same exact_delete_paths list
if exact_delete_paths:
    placeholders = ",".join("?" * len(exact_delete_paths))
    conn.execute(
        f"DELETE FROM note_embeddings WHERE note_path IN ({placeholders})",
        exact_delete_paths,
    )
```

### config.toml provider key
```toml
[embeddings]
provider = "sentence-transformers"  # or "ollama"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| sqlite-vss (Faiss-based) | sqlite-vec (pure C, vec0) | 2023-2024 | No Faiss dependency; ships as Python wheel; simpler install |
| `ollama.embeddings()` (deprecated) | `ollama.embed()` | 2024 (ollama >= 0.4) | New endpoint returns `response["embeddings"]` (list); old endpoint returned `response["embedding"]` (single) |
| sentence-transformers < 3.0 | sentence-transformers >= 3.0 | 2024 | 3.x added ONNX/OpenVINO backends; API is backward compatible |

**Deprecated/outdated:**
- `sqlite-vss`: predecessor to sqlite-vec; requires Faiss; do not use
- `ollama.embeddings()`: deprecated in favor of `ollama.embed()`; project already has `ollama>=0.6` which has the new API

---

## Open Questions

1. **sqlite-vec extension availability in the uv/hatch build environment**
   - What we know: `sqlite-vec` ships as a Python wheel with bundled `.so`; `sqlite_vec.load(conn)` loads it
   - What's unclear: Whether `conn.enable_load_extension(True)` is available in the Python sqlite3 build on the user's macOS (some distros compile it out)
   - Recommendation: Wave 0 test should verify `import sqlite_vec; sqlite_vec.load(conn)` works; if not, document the `--enable-loadable-sqlite-extensions` requirement

2. **`nomic-embed-text` dimension (768 vs 384)**
   - What we know: `all-MiniLM-L6-v2` outputs 384 dimensions; `nomic-embed-text` outputs 768 dimensions
   - What's unclear: If a user switches providers mid-corpus, stored BLOBs are incompatible dimension-wise
   - Recommendation: Store dimension in `note_embeddings` as a comment or enforce same dim in embed pass; `--full` reindex is required when switching providers; document this in user-facing output

3. **Batch size tuning for sentence-transformers on CPU**
   - What we know: Default 32 is safe; larger batches use more RAM but are faster on CPU
   - What's unclear: Optimal value for a Mac with ~8GB RAM and typical brain of 500–2000 notes
   - Recommendation: Default to `batch_size=32`; expose as a config.toml key `embeddings.batch_size` for power users

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 7.0 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/test_embeddings.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EMBED-01 | `reindex_brain()` generates embeddings in `note_embeddings` table | unit | `pytest tests/test_embeddings.py::test_reindex_generates_embeddings -x` | Wave 0 |
| EMBED-01 | `--full` flag re-embeds all notes regardless of hash | unit | `pytest tests/test_embeddings.py::test_reindex_full_flag -x` | Wave 0 |
| EMBED-02 | Embedding is generated without network call (sentence-transformers local) | unit (mock) | `pytest tests/test_embeddings.py::test_embed_no_network_call -x` | Wave 0 |
| EMBED-03 | Unchanged note hash skips re-embedding on second reindex | unit | `pytest tests/test_embeddings.py::test_reindex_incremental_skips_unchanged -x` | Wave 0 |
| EMBED-03 | Edited note (different body hash) is re-embedded on next reindex | unit | `pytest tests/test_embeddings.py::test_reindex_incremental_reembeds_changed -x` | Wave 0 |
| EMBED-04 | `sb-forget` deletes rows from `note_embeddings` for erased person | unit | `pytest tests/test_embeddings.py::test_forget_cascades_to_embeddings -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_embeddings.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_embeddings.py` — covers EMBED-01, EMBED-02, EMBED-03, EMBED-04
- [ ] `conftest.py` update: add `vec_conn` fixture (sqlite-vec loaded) for future Phase 16 tests; not required for Phase 14 plain-table tests
- [ ] Framework install: `uv add sentence-transformers sqlite-vec` — neither is in `pyproject.toml` yet

**Test strategy note:** `sentence_transformers.SentenceTransformer` should be mocked in unit tests to avoid 90MB model download in CI. Use `unittest.mock.patch("engine.embeddings._get_model")` returning a mock whose `.encode()` returns deterministic `np.zeros((N, 384), dtype=np.float32)` arrays.

---

## Sources

### Primary (HIGH confidence)
- [asg017/sqlite-vec GitHub](https://github.com/asg017/sqlite-vec) — vec0 table syntax, KNN MATCH query, Python load pattern
- [sqlite-vec examples/simple-python/demo.py](https://github.com/asg017/sqlite-vec/blob/main/examples/simple-python/demo.py) — concrete Python insert/query code
- [sqlite-vec KNN docs](https://alexgarcia.xyz/sqlite-vec/features/knn.html) — KNN query structure
- [sbert.net quickstart](https://sbert.net/docs/quickstart.html) — SentenceTransformer.encode() API
- [HuggingFace all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) — model specs (384 dim, 256 token limit)
- [ollama-python GitHub](https://github.com/ollama/ollama-python) — `ollama.embed()` API
- `engine/db.py`, `engine/reindex.py`, `engine/forget.py` — existing code patterns (project source)

### Secondary (MEDIUM confidence)
- [sqlite-vec PyPI 0.1.6](https://pypi.org/project/sqlite-vec/) — version confirmed stable
- [sentence-transformers PyPI v5.3](https://pypi.org/project/sentence-transformers/) — latest version confirmed
- [Simon Willison TIL: sqlite-vec](https://til.simonwillison.net/sqlite/sqlite-vec) — practical usage patterns with Python

### Tertiary (LOW confidence)
- WebSearch result for `nomic-embed-text` dimension (768) — not independently verified against official Ollama docs; verify before dimension enforcement

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — sentence-transformers and sqlite-vec are both well-documented, actively maintained, and confirmed current versions
- Architecture: HIGH — patterns derived directly from existing codebase code + official library examples
- Pitfalls: MEDIUM — truncation limit and Ollama dimension mismatch are verified; optimal batch size is LOW (empirical)

**Research date:** 2026-03-15
**Valid until:** 2026-06-15 (90 days — both libraries are stable; sqlite-vec API unlikely to break in patch releases)
