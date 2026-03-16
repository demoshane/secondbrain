---
phase: 14-embedding-infrastructure
plan: "02"
subsystem: infra
tags: [embeddings, ollama, fastembed, sqlite-vec, sqlite]

requires:
  - phase: 14-embedding-infrastructure
    provides: note_embeddings DDL and test scaffold (plan 14-01)
provides:
  - engine/embeddings.py with full provider dispatch (ollama + fastembed)
  - _serialize() for float32 BLOB encoding
  - note_embeddings DDL in engine/db.py
  - embeddings config defaults in engine/config_loader.py
affects:
  - 14-03 (reindex.py embed pass imports embed_texts from engine.embeddings)
  - 14-04 (forget.py cascade delete touches note_embeddings)

tech-stack:
  added: []
  patterns:
    - lazy-import pattern for fastembed (_get_model loads on first call)
    - provider dispatch via string key in embed_texts()
    - module-level _model_cache for fastembed model reuse

key-files:
  created: [engine/embeddings.py]
  modified: [engine/db.py, engine/config_loader.py]

key-decisions:
  - "Ollama provider uses ollama.embed(model, input=texts) — synchronous, no model download"
  - "fastembed provider uses lazy import inside _get_model() to avoid ImportError on Intel Mac"
  - "Connection failure to Ollama raises RuntimeError with [ERROR] prefix for user-friendly CLI output"
  - "_model_cache at module level avoids re-initializing fastembed TextEmbedding on every call"

patterns-established:
  - "Lazy ML import pattern: heavy imports inside function, not at module top level"
  - "Provider dispatch: embed_texts(texts, provider=None) — None loads from config"

requirements-completed: [EMBED-01, EMBED-02]

duration: 25min
completed: 2026-03-15
---

# Plan 14-02: Embeddings Engine Summary

**engine/embeddings.py with ollama + fastembed provider dispatch, note_embeddings DDL, and config defaults — 17/21 embedding tests GREEN**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-03-15
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `engine/embeddings.py`: full provider dispatch — ollama (default, Intel Mac) and fastembed (lazy, ARM/Linux)
- `_serialize(vector)` → little-endian float32 BLOB via struct.pack
- `note_embeddings` DDL in engine/db.py (note_path PK, embedding BLOB, content_hash, stale flag)
- `embeddings` defaults in config_loader.py (provider: "ollama", batch_size: 32)
- 17 of 21 embedding tests GREEN; 4 reindex tests RED (expected — plan 14-03)

## Task Commits

1. **Task 1: DDL + config defaults** - `b574997` (feat)
2. **Task 2: engine/embeddings.py** - `b1bd08f` (feat)

## Files Created/Modified
- `engine/embeddings.py` — embed_texts dispatch, _serialize, _get_model, _model_cache
- `engine/db.py` — note_embeddings table DDL
- `engine/config_loader.py` — embeddings section defaults

## Decisions Made
- Ollama as primary provider: `ollama.embed(model="nomic-embed-text", input=texts)` — fully synchronous, no native deps
- fastembed via lazy import so Intel Mac can import the module without triggering onnxruntime install error
- RuntimeError on Ollama connection failure with `[ERROR]` prefix to match CLI output conventions

## Deviations from Plan
None — implemented exactly as architected, with provider names adjusted from original plan (ollama default vs fastembed default).

## Issues Encountered
None at implementation level. Platform blockers were resolved in plan 14-01.

## Next Phase Readiness
- `embed_texts()` callable from reindex.py and any other engine module
- 4 reindex RED tests waiting for plan 14-03 implementation
- Ollama must be running with `nomic-embed-text` model for runtime embedding calls

---
*Phase: 14-embedding-infrastructure*
*Completed: 2026-03-15*
