---
phase: 38-scale-architecture-100k-notes
plan: "04"
subsystem: embeddings
tags: [chunking, embeddings, reindex, sqlite, scale]
one_liner: "Chunked embeddings infrastructure: note_chunks table, overlapping text splitter, embed_chunks(), and reindex pipeline integration"

dependency_graph:
  requires:
    - "38-01"  # ANN index (embed_pass uses add_to_index)
  provides:
    - note_chunks table with chunk text + embedding BLOBs
    - split_text_into_chunks() function
    - embed_chunks() function
  affects:
    - engine/embeddings.py
    - engine/db.py
    - engine/reindex.py

tech_stack:
  added: []
  patterns:
    - "Overlapping character-window chunking (chunk_size=1200, overlap=200)"
    - "CHUNK_THRESHOLD=600: short notes get single-chunk, long notes get multi-chunk"
    - "embed_pass chunk pass wrapped in try/except for graceful degradation"
    - "note_chunks DELETE+INSERT on force rebuild; UPSERT for incremental updates"

key_files:
  created:
    - tests/test_chunks.py
  modified:
    - engine/embeddings.py
    - engine/db.py
    - engine/reindex.py
    - tests/conftest.py

decisions:
  - "CHUNK_THRESHOLD < CHUNK_SIZE: short notes (< 600 chars) reuse note-level blob as single chunk rather than re-embedding"
  - "Chunk pass imports from sys.modules['engine.embeddings'] — honours test stubs consistent with embed_pass pattern"
  - "conftest.py stub_engine_embeddings skip list extended with TestSplitTextIntoChunks, TestEmbedChunks, TestNoteChunksSchema"

metrics:
  duration_seconds: 459
  completed_date: "2026-03-26"
  tasks_completed: 2
  files_modified: 4
---

# Phase 38 Plan 04: Chunked Embeddings Infrastructure Summary

Chunked embeddings infrastructure: note_chunks table, overlapping text splitter, embed_chunks(), and reindex pipeline integration.

## What Was Built

**engine/embeddings.py** — Added three new exports:
- `CHUNK_SIZE = 1200`, `CHUNK_OVERLAP = 200`, `CHUNK_THRESHOLD = 600` — tunable constants
- `split_text_into_chunks(text, chunk_size, overlap)` — overlapping char-window chunking; texts <= chunk_size return `[text]` as-is
- `embed_chunks(text, provider, batch_size)` — splits + embeds, returns `[(chunk_text, blob), ...]`

**engine/db.py** — Added `migrate_create_note_chunks()`:
- Creates `note_chunks(id, note_path, chunk_index, chunk_text, embedding, created_at)`
- `UNIQUE(note_path, chunk_index)` constraint enables safe upsert pattern
- `idx_note_chunks_path` index for path-based lookups
- Called from `init_schema()` after other migrations

**engine/reindex.py** — Extended `embed_pass()` with a chunk pass after note-level embedding:
- Short notes (`len(body) < CHUNK_THRESHOLD`): one chunk = full body, reuse note-level blob
- Long notes: `split_text_into_chunks()` + `embed_texts()` per chunk; DELETE + INSERT for idempotency
- `reindex_brain(full=True)` deletes all `note_chunks` rows before embed_pass

**tests/test_chunks.py** — 19 tests covering:
- `split_text_into_chunks`: threshold, boundary, overlap, coverage, custom params, empty text, chunk count
- `embed_chunks`: return types, blob size consistency, chunk text matches split, empty text
- `note_chunks` schema: table creation, columns, UNIQUE constraint, upsert, index, idempotency

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing config] conftest stub_engine_embeddings masked new functions**
- **Found during:** Task 1 GREEN phase
- **Issue:** The autouse `stub_engine_embeddings` fixture in conftest.py injected a minimal fake module for all test classes except a hardcoded set. Our new `TestSplitTextIntoChunks`, `TestEmbedChunks`, and `TestNoteChunksSchema` classes weren't in the skip set, so they got the stub without the new functions.
- **Fix:** Added all three class names to `skip_classes` in `stub_engine_embeddings` fixture
- **Files modified:** `tests/conftest.py`
- **Commit:** 0523118

## Known Stubs

None — all functionality is wired and tested.

## Self-Check: PASSED

- FOUND: tests/test_chunks.py
- FOUND: engine/embeddings.py (with split_text_into_chunks, embed_chunks, CHUNK_SIZE)
- FOUND: engine/db.py (with migrate_create_note_chunks, note_chunks in init_schema)
- FOUND: engine/reindex.py (chunk pass in embed_pass, DELETE on full rebuild)
- FOUND: commit feb9d4b (test RED)
- FOUND: commit 0523118 (feat GREEN — schema + splitting)
- FOUND: commit 5308eb1 (feat — reindex pipeline)
