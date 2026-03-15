---
phase: 14-embedding-infrastructure
plan: "03"
subsystem: infra
tags: [embeddings, reindex, sha256, sqlite-vec, ollama]

requires:
  - phase: 14-embedding-infrastructure
    provides: engine/embeddings.py with embed_texts() (plan 14-02)
provides:
  - embed_pass() in engine/reindex.py — SHA-256 hash diff + upsert to note_embeddings
  - reindex_brain() full= flag to force re-embed all notes
  - tests/conftest.py autouse stub for engine.embeddings isolation
affects:
  - 14-04 (forget.py cascade delete — note_embeddings rows now populated by reindex)

tech-stack:
  added: []
  patterns:
    - SHA-256 content hash diffing to skip unchanged notes on reindex
    - sys.modules injection pattern for module-level mocking in tests

key-files:
  created: [tests/conftest.py]
  modified: [engine/reindex.py]

key-decisions:
  - "embed_pass() as separate function inside reindex.py — keeps reindex_brain() readable"
  - "Import engine.embeddings inside embed_pass() not at module top — allows sys.modules mock injection in tests"
  - "conftest.py autouse stub prevents non-embedding tests from accidentally importing fastembed"

patterns-established:
  - "Hash-diff pattern: compute SHA-256, compare to stored content_hash, skip if equal"
  - "Return dict from reindex_brain() includes embed_updated + embed_unchanged for CLI output"

requirements-completed: [EMBED-03]

duration: 20min
completed: 2026-03-15
---

# Plan 14-03: Reindex Embedding Pass Summary

**engine/reindex.py extended with SHA-256 hash-diff embedding second pass; incremental re-embed on change, --full flag forces all; 168 tests GREEN**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-03-15
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- `embed_pass()` added to reindex.py: iterates notes, computes SHA-256 body hash, upserts embedding only when stale or missing
- `reindex_brain()` gains `full=False` parameter — when True, re-embeds all notes regardless of hash
- Returns `embed_updated` and `embed_unchanged` counts for summary output
- `tests/conftest.py` with autouse stub for `engine.embeddings` — isolates non-embedding tests
- All 4 `TestReindexGeneratesEmbeddings` tests GREEN; 168 total passed

## Task Commits

1. **Task 1 (RED):** `46ad400` — RED tests for reindex embedding pass
2. **Task 1 (GREEN):** `58cf6fd` — GREEN implementation

## Files Created/Modified
- `engine/reindex.py` — embed_pass() + full= flag on reindex_brain()
- `tests/conftest.py` — autouse engine.embeddings stub for test isolation

## Decisions Made
- Import `engine.embeddings` lazily inside `embed_pass()` — allows `sys.modules` mock injection in tests without importing at module load
- Separate `embed_pass()` function keeps `reindex_brain()` clean and independently testable

## Deviations from Plan
None.

## Issues Encountered
None.

## Next Phase Readiness
- `note_embeddings` table now populated on every `sb-reindex` run
- 14-04 (forget.py cascade delete) can proceed — rows will exist to delete

---
*Phase: 14-embedding-infrastructure*
*Completed: 2026-03-15*
