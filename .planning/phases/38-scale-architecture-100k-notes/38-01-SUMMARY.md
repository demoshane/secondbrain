---
phase: 38-scale-architecture-100k-notes
plan: "01"
subsystem: ann-index
tags: [hnswlib, vector-search, ann, embeddings, scale]
dependency_graph:
  requires: []
  provides: [engine/ann_index.py]
  affects: [engine/reindex.py]
tech_stack:
  added: [hnswlib>=0.8.0, numpy (transitive)]
  patterns: [module-level singleton cache, try/except graceful fallback, TDD red-green]
key_files:
  created:
    - engine/ann_index.py
    - tests/test_ann_index.py
  modified:
    - pyproject.toml
    - engine/reindex.py
decisions:
  - hnswlib compiled from source using SDKROOT+CXXFLAGS pointing at MacOSX15.4.sdk (macOS 26 / Darwin 25.x build env)
  - DIM=768 matches nomic-embed-text; label_map stores str(rowid)->note_path for JSON serialisation compatibility
  - embed_pass() updates ANN per note (incremental); reindex_brain(force=True) triggers full rebuild
  - load_or_build_index returns None (not raises) when no file and no conn — caller handles fallback
metrics:
  duration_seconds: 601
  completed_date: "2026-03-26"
  tasks_completed: 2
  files_changed: 4
requirements_satisfied: [SCALE-01]
---

# Phase 38 Plan 01: ANN Index Module Summary

**One-liner:** hnswlib ANN index (768-dim cosine, max 200K notes) with incremental update on embed and full rebuild on `--full`, graceful fallback to sqlite-vec when unavailable.

## What Was Built

- `engine/ann_index.py` — ANN index module with five public functions: `rebuild_index()`, `load_or_build_index()`, `add_to_index()`, `knn_query()`, `invalidate_cache()`
- `tests/test_ann_index.py` — 11 tests covering build, query, add, load, and label_map round-trip
- `pyproject.toml` — added `hnswlib>=0.8.0` dependency
- `engine/reindex.py` — wired ANN calls: `embed_pass()` calls `add_to_index()` per note after DB commit; `reindex_brain()` calls `rebuild_index()` when `force=True`

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | c3918d3 | feat(38-01): add ANN index module with hnswlib |
| 2 | 2007c90 | feat(38-01): wire ANN index into reindex pipeline |

## Verification

- `uv run pytest tests/test_ann_index.py -q` — 11 passed
- `uv run pytest tests/test_reindex.py -q` — 11 passed
- `python -c "import hnswlib; ..."` — importable, 768-dim index initialises correctly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] hnswlib build fails on macOS 26 (Darwin 25.x)**

- **Found during:** Task 1 RED phase
- **Issue:** `hnswlib>=0.8.0` failed to compile — `fatal error: 'iostream' file not found`. uv's bundled Python doesn't have the C++ stdlib headers on the default search path.
- **Fix:** Installed with `SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX15.4.sdk CXXFLAGS="-stdlib=libc++ -I<sdk>/usr/include/c++/v1 -isysroot <sdk>"` via `uv add`. The compiled .so then lives in the project venv and works normally.
- **Impact:** Build step requires correct SDK env vars. Documented in decisions. The `make dev` reinstall will need the same flags on this machine.
- **Files modified:** pyproject.toml (dependency recorded), uv.lock (updated by uv add)
- **Commits:** c3918d3

### Out-of-Scope Issues Discovered

- `tests/test_api_tags.py::TestTagSearch::test_filter_returns_matching` was failing before this plan's changes — not caused by this work. Logged to deferred items.

## Known Stubs

None — all functions are fully implemented with real hnswlib calls.

## Self-Check: PASSED

- engine/ann_index.py exists: FOUND
- tests/test_ann_index.py exists: FOUND
- Commit c3918d3 exists: FOUND
- Commit 2007c90 exists: FOUND
