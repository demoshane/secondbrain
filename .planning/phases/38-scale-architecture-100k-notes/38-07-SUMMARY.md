---
phase: 38-scale-architecture-100k-notes
plan: 07
status: complete
completed_at: "2026-03-27"
files_modified:
  - engine/db.py
  - engine/consolidate.py
  - engine/brain_health.py
  - engine/health.py
  - tests/test_consolidation.py
---

# 38-07 Summary — Memory Consolidation Engine

## What was built

ANN-driven background consolidation pass that surfaces merge-worthy note clusters without auto-merging.

### DB schema (`engine/db.py`)
- Added `migrate_create_consolidation_candidates()` — creates `consolidation_candidates` table with `note_a`, `note_b`, `similarity`, `shared_entities`, `status` (default `'open'`), `UNIQUE(note_a, note_b)`
- Called from `init_schema()` as last migration before indexes

### Consolidation engine (`engine/consolidate.py`)
- Added `SIMILARITY_THRESHOLD = 0.80`
- Added `find_consolidation_candidates(conn, limit=50)`:
  - Calls `load_or_build_index` + `knn_query` from `engine.ann_index`
  - Falls back gracefully if hnswlib unavailable (`return 0`)
  - Iterates non-archived notes with embeddings, queries ANN for 10 nearest neighbours
  - Filters: similarity ≥ 0.80, shared person or tag, not self, not already in table (any status)
  - Writes canonical sorted pair (note_a ≤ note_b alphabetically) to avoid duplicate rows
  - Limit check in both outer and inner loop to respect `limit` precisely
  - Returns count of new candidates inserted
- Wired into `consolidate_main()` — `results["consolidation_candidates"] = find_consolidation_candidates(conn)`

### Health reporting (`engine/brain_health.py`)
- Added `get_consolidation_candidate_count(conn)` — counts `status='open'` rows, returns 0 on missing table

### `sb-health --brain` output (`engine/health.py`)
- Imports `get_consolidation_candidate_count`
- Prints `"Consolidation: N merge candidates pending review"` or `"No merge candidates"`

### Tests (`tests/test_consolidation.py`)
- 16 tests across 4 classes: `TestConsolidationCandidatesTable`, `TestFindConsolidationCandidates`, `TestGetConsolidationCandidateCount`, `TestConsolidateMainWiring`
- Mocks `engine.ann_index.load_or_build_index` and `engine.ann_index.knn_query` via `patch.object` (imports are inside function body, so source module must be patched)
- Covers: table creation, field defaults, shared person, shared tag, no shared entity, self-skip, below-threshold skip, pair deduplication, correct candidate fields, dismissed-not-resurfaced, limit respected, health count, missing-table safety, consolidate_main output key

## Key decisions
- Limit check added to inner neighbour loop (not just outer note loop) — prevents overshooting limit within a single note's neighbour batch
- `pair = tuple(sorted([path, neighbor_path]))` ensures canonical ordering, preventing (A,B) and (B,A) as distinct rows
- `existing` set tracks both orderings for O(1) skip check
- `load_or_build_index` / `knn_query` imported locally inside function — consistent with Phase 38 patterns; tests patch `engine.ann_index` attributes directly

## Verification
```
uv run pytest tests/test_consolidation.py -q  → 16 passed
uv run pytest tests/test_consolidation.py tests/test_db.py tests/test_health.py -v → 54 passed, 2 xpassed
```
