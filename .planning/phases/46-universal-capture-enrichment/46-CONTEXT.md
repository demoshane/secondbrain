# Phase 46: Universal Capture Enrichment — Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire person stub creation (Pass 5 from the Phase 43 decomposer) into `capture_note()` so every capture path — `sb_capture`, `sb_capture_batch`, `sb_capture_link` — builds person stubs consistently with `sb_capture_smart`.

**In scope:**
- Extend `_run_intelligence_hooks` background thread in `capture_note()` to call Pass 5 stub creation
- Two-layer gate before stub creation: skip if `note_type in {coding, link, files}` OR if `entities["people"]` is empty
- No response surface changes — stub creation is transparent to callers

**Out of scope:**
- Context detection audit (`extract_entities()` interface, source_type signal enrichment) — deferred; no concrete failure case to anchor it
- Any changes to Pass 1–4 behaviour
- Any changes to `sb_capture_smart` — already works correctly

</domain>

<decisions>
## Implementation Decisions

### Stub Creation Scope — D-01
- **D-01:** Two-layer gate in `capture_note()` before calling Pass 5:
  1. Skip if `note_type in {"coding", "link", "files"}` — these types rarely contain meaningful person mentions
  2. Skip if `entities["people"]` is empty after entity extraction (which already runs synchronously)
  Both conditions checked before entering the background thread stub logic. Zero overhead when neither condition passes.

### Threading Model — D-02
- **D-02:** Person stub creation runs **async** in the existing `_run_intelligence_hooks` background daemon thread in `capture_note()`. The thread already handles `check_connections` and `extract_action_items`. Stub creation is a third task added to that same thread. Capture returns immediately — no latency impact.

### Response Surface — D-03
- **D-03:** No changes to `sb_capture` or `sb_capture_batch` response shapes. Stub creation is transparent to callers — stubs appear in the brain asynchronously. No `person_stubs_created` field or `"person_extraction": "queued"` hint added.

### Context Detection — D-04
- **D-04:** Context detection audit descoped. No changes to `extract_entities()`, `_PERSON_CONTEXT_SIGNALS`, or extraction thresholds. Deferred to a future phase if a concrete failure case surfaces.

### Claude's Discretion
- Whether stub creation in the background thread reuses `p5_assemble` module directly or calls `capture_note()` recursively for each stub (existing `sb_capture_smart` pattern)
- Error handling within the thread — stub creation failures must not surface or crash the thread (same silent-catch pattern as existing hooks)
- Whether `_run_intelligence_hooks` is refactored into named sub-functions or kept as a single closure

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core write path
- `engine/capture.py` — `capture_note()` function (~line 485); `_run_intelligence_hooks` closure inside it; entity extraction call at ~line 547
- `engine/passes/__init__.py` — `DecomposedResult`, `decompose()` entry point; Pass 5 integration pattern
- `engine/passes/p5_assemble.py` — person stub assembly logic; what it needs (conn, brain_root, entities)

### Smart capture reference (existing stub creation pattern)
- `engine/mcp_server.py` — `sb_capture_smart` (~line 830); Pass 5 / person stub creation loop (~line 929); this is the pattern to replicate in `capture_note()`

### Entity extraction (already runs in capture_note)
- `engine/entities.py` — `extract_entities(title, body)`; `_PERSON_CONTEXT_SIGNALS` gate logic

### Test patterns
- `tests/conftest.py` — `stub_engine_embeddings` skip list; `BRAIN_ROOT` patching pattern
- `tests/test_capture.py` — existing capture tests to extend with stub assertions

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_run_intelligence_hooks` closure in `capture_note()` — extend this; don't create a new thread
- `p5_assemble.py` — already handles stub creation; needs `conn`, `brain_root`, `entities` dict
- Entity extraction result (`entities` dict) is already computed synchronously before the thread starts — pass it into the closure via closure variable

### Established Patterns
- Background thread pattern: `threading.Thread(target=_run_intelligence_hooks, daemon=True).start()` — reuse exactly
- Silent-catch pattern in the thread: `try: ... except Exception: pass` — all three tasks (connections, action items, stubs) follow this
- Stub creation in `sb_capture_smart`: iterates `results.person_stubs`, calls `capture_note()` for each stub with `note_type='people'` — replicate this logic

### Integration Points
- `capture_note()` → extend `_run_intelligence_hooks` closure to include stub creation as a third task
- Gate check before thread: `if note_type not in {"coding", "link", "files"} and entities.get("people"):`
- Pass `entities` and `merged_people` into the closure so the thread has what Pass 5 needs

</code_context>

<specifics>
## Specific Ideas

- The existing thread already has a `_target_str`, `_body`, `_sensitivity`, `_brain_root` pattern for passing closure vars — extend with `_entities` and `_note_type`
- Stub creation should check if a person profile already exists before creating (same dedup as `sb_capture_smart` — `capture_note` with `note_type='people'` already handles slug collision)

</specifics>

<deferred>
## Deferred Ideas

- **Context detection audit** — using `source_type`/`note_type` as signals to `extract_entities()` to improve extraction accuracy. No concrete failure case to target. Revisit if a specific misfiring scenario surfaces.
- **Response surface enrichment** — returning `person_stubs_created` in `sb_capture` responses. Not needed until a caller has a use case for it.

</deferred>

---

*Phase: 46-universal-capture-enrichment*
*Context gathered: 2026-03-30*
