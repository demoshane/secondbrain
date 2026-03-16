---
phase: 14-embedding-infrastructure
plan: "01"
subsystem: infra
tags: [sqlite-vec, fastembed, ollama, embeddings, python]

requires: []
provides:
  - sqlite-vec added as project dependency (installs on Intel Mac)
  - Test scaffold for all Phase 14 embedding behaviors in RED state
  - Ollama as default embedding provider (works on Intel Mac without native ML deps)
affects:
  - 14-02 (engine/embeddings.py must implement ollama + fastembed provider dispatch)
  - 14-03 (reindex embedding pass depends on embed_texts)

tech-stack:
  added: [sqlite-vec>=0.1]
  patterns: [ollama-first embedding provider for Intel Mac compatibility]

key-files:
  created: [tests/test_embeddings.py]
  modified: [pyproject.toml, engine/config_loader.py, uv.lock]

key-decisions:
  - "Use Ollama as default embedding provider — fastembed/onnxruntime dropped Intel Mac (x86_64) support; Ollama is already a project dep and works natively"
  - "fastembed NOT added to pyproject.toml — add when on Apple Silicon where onnxruntime arm64 wheels exist"
  - "Python pinned to 3.13 via .python-version — PyTorch has no 3.14 wheels; 3.13 supports onnxruntime if needed on ARM"
  - "embed_texts() tests mock engine.embeddings._get_model to avoid model downloads"

patterns-established:
  - "Provider dispatch pattern: embed_texts(texts, provider=) routes to ollama or fastembed branch"
  - "Lazy model loading: _get_model() called inside embed_texts, not at module import"

requirements-completed: []

duration: 45min
completed: 2026-03-15
---

# Plan 14-01: Embedding Dependencies + Test Scaffold Summary

**sqlite-vec added as project dep; Ollama set as default embedding provider for Intel Mac; RED test scaffold covering DDL, config, and embed_texts dispatch**

## Performance

- **Duration:** ~45 min (including 3 blocked attempts due to platform incompatibility)
- **Completed:** 2026-03-15
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `sqlite-vec>=0.1` added to pyproject.toml and installs cleanly on Intel Mac Python 3.13
- `config_loader.py` default `embeddings.provider` set to `"ollama"` (fully functional on Intel Mac)
- `tests/test_embeddings.py` created: 14 tests covering DDL, config defaults, embed_texts dispatch, serialization, Ollama error handling — all RED (engine/embeddings.py not yet created)

## Task Commits

1. **Task 1: Add embedding dependencies** - `e7b649d` (feat)
2. **Task 2: Test scaffold + config default** - `d4b805a` (test)

## Files Created/Modified
- `tests/test_embeddings.py` - RED test scaffold for all embedding behaviors
- `pyproject.toml` - sqlite-vec added; fastembed omitted (no Intel Mac wheels)
- `engine/config_loader.py` - embeddings.provider defaulted to "ollama"
- `uv.lock` - updated with sqlite-vec resolution

## Decisions Made
- **Ollama over fastembed as default:** `onnxruntime` (required by `fastembed`) dropped Intel Mac x86_64 support entirely. Ollama is already a project dependency and its `embed()` API works on any platform.
- **fastembed deferred to M-chip migration:** Will add `fastembed>=0.4` to pyproject.toml when user switches to Apple Silicon. Can then also update default provider.
- **Python pinned to 3.13:** Project was on 3.14 but PyTorch/onnxruntime have no 3.14 wheels. 3.13 is the correct pin until these libraries catch up.

## Deviations from Plan

### Auto-fixed Issues

**1. [Platform Incompatibility] sentence-transformers → fastembed → ollama provider selection**
- **Found during:** Task 1
- **Issue:** `sentence-transformers` requires PyTorch (no Python 3.14 wheels); `fastembed` requires `onnxruntime` (no Intel Mac x86_64 wheels at any version)
- **Fix:** Use Ollama as default provider; defer fastembed to Apple Silicon migration
- **Files modified:** pyproject.toml, engine/config_loader.py, tests/test_embeddings.py
- **Verification:** `uv sync` succeeds; no native ML library required at install time

---

**Total deviations:** 1 (platform constraint required provider strategy change)
**Impact on plan:** Scope unchanged — test scaffold and dependency declaration complete. Ollama provides equivalent functionality on Intel Mac.

## Issues Encountered
- Three successive attempts blocked by platform incompatibility (Python 3.14 → no torch wheels → no onnxruntime wheels). Resolved by pinning Python 3.13 and switching to Ollama as default provider.

## Next Phase Readiness
- 14-02 can now create `engine/embeddings.py` with provider dispatch supporting both `"ollama"` and `"fastembed"`
- Tests will turn GREEN once `engine/embeddings.py` is implemented
- Ollama must be running with an embedding model (e.g. `nomic-embed-text`) for runtime use

---
*Phase: 14-embedding-infrastructure*
*Completed: 2026-03-15*
