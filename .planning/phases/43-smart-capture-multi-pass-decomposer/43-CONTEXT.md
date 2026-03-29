# Phase 43: Smart Capture Multi-Pass Decomposer — Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Refactor `engine/segmenter.py` + `engine/typeclassifier.py` into a modular 5-pass decomposer under `engine/passes/`. Fix URL hard-override bug in typeclassifier. Add conversation-format meeting signal (`Name [HH:MM]` pattern). Align GUI `/smart-capture` path with MCP `sb_capture_smart` for person stub creation.

**In scope:**
- New `engine/passes/` directory with per-pass modules
- `decompose(content) -> result` replaces `segment_blob()` in all callers
- `segment_blob()` deleted; `api.py` and `mcp_server.py` updated to call `decompose()` directly
- Pass 1: entity extraction (people, links, dates) unconditionally
- Pass 2: URL extraction → separate link note(s), always (even if URL is primary content)
- Pass 3: classify URL-stripped content (meeting, note, coding, etc.)
- Pass 4: action item extraction with configurable markers + intelligence.py for intent-based items; writes to `action_items` DB table at capture time
- Pass 5: assemble primary note + link notes + person stubs + action items
- GUI settings panel for configurable action-item markers (e.g. "AP", "TODO")
- GUI `/smart-capture` creates person stubs (full parity with MCP)

**Out of scope:**
- Extraction enrichment for regular `sb_capture` / `sb_capture_batch` / `sb_capture_link` calls — those still call `capture_note()` directly without decomposer passes. Deferred to a future phase.

</domain>

<decisions>
## Implementation Decisions

### Pass Architecture
- **D-01:** Single `decompose(content: str) -> DecomposedResult` function in `engine/passes/__init__.py` as the public entry point. Each pass is a separate module (`engine/passes/p1_entities.py`, `p2_urls.py`, `p3_classify.py`, `p4_actions.py`, `p5_assemble.py`) — independently importable and testable.
- **D-02:** `segment_blob()` in `segmenter.py` is **deleted** (not wrapped). All callers (`api.py`, `mcp_server.py`) updated to call `decompose()` directly. `segmenter.py` retains only `resolve_entities()` and `dedup_segment()` (still used independently).
- **D-03:** Principle: full modularity — every extractable thing (URL, entity, action item, conversation turn) lives in its own pass module.

### URL Extraction — Pass 2
- **D-04:** ANY URL in the blob is always extracted into a separate link note. No threshold. No URL-into-frontmatter fallback.
- **D-05:** If the URL is the primary content (blob = URL + short description), Pass 2 still produces a link note — same code path, no special case.
- **D-06:** After URL extraction, the URL-stripped content goes to Pass 3 for type classification. A meeting note with a Zoom link → 2 notes: one meeting + one link.

### Action Item Extraction — Pass 4
- **D-07:** Two-layer extraction: (a) configurable keyword markers checked first (default: `TODO`, `AP`, `action:`, `@owner`, `Action Point`), (b) intelligence layer (`intelligence.py` `extract_action_items()`) runs on the saved note body for intent-based extraction (e.g. "tuomas would call the fastly").
- **D-08:** Action items extracted by Pass 4 are **written to `action_items` DB table at capture time** by the caller (Pass 5 includes them in the assembly output; api.py/mcp_server.py persist them). User sees action items in Actions page immediately after smart capture.
- **D-09:** Configurable action-item markers stored in `config.toml` under `[action_items] custom_markers = ["AP", ...]`. User can add custom markers.
- **D-10:** A new **GUI settings panel** for action-item markers — view/add/remove custom markers. Location: Settings page or Intelligence page settings section (Claude's discretion on exact placement).

### Conversation-Format Detection — Pass 3
- **D-11:** `Name [HH:MM]` pattern (e.g., `Alice [14:32]`) is a strong meeting-type signal. Pass 3 adds this to the classifier as a high-confidence meeting indicator (≥ 0.85 confidence when ≥ 2 turns detected).

### GUI/MCP Parity — Pass 5
- **D-12:** `POST /smart-capture` (GUI path) now calls `decompose()` and Pass 5 creates person stubs — **full behavioral parity with MCP**. Stubs created silently. Created stubs appear in the capture response for display in the GUI.
- **D-13:** Both `sb_capture_smart` and `POST /smart-capture` call the same `decompose()` function. Code-level parity enforced.

### Claude's Discretion
- Exact file naming within `engine/passes/` (e.g., `p1_entities.py` vs `entities.py`)
- `DecomposedResult` type shape (dataclass vs TypedDict vs plain dict)
- Whether `segmenter.py` is deleted entirely or kept with only `resolve_entities()` and `dedup_segment()`
- GUI settings panel exact location (Settings page vs Intelligence page section)
- Conversation-format split behaviour: whether `Name [HH:MM]` lines also trigger segment splits or only add a meeting signal to the classifier

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Current segmenter (being replaced)
- `engine/segmenter.py` — current `segment_blob()` implementation and `resolve_entities()` / `dedup_segment()` helpers that stay
- `engine/typeclassifier.py` — URL hard-override to fix; `classify_note_type()` to extend with conversation-format signal; `CONFIDENCE_THRESHOLD` constant used by callers

### Callers being updated
- `engine/api.py` — `POST /smart-capture` and `POST /smart-capture/confirm` routes
- `engine/mcp_server.py` — `sb_capture_smart` tool; person stub creation pattern

### Action item DB pattern
- `engine/intelligence.py` — existing `extract_action_items()` function: reuse in Pass 4 layer (b)
- `engine/db.py` — `action_items` table schema; `init_schema()` migration pattern

### Config pattern
- `engine/config_loader.py` — how to read config.toml settings

### Test patterns
- `tests/test_segmenter.py` (if exists) — existing tests to migrate/replace for new `decompose()` function
- `tests/conftest.py` — `stub_engine_embeddings` skip list; `BRAIN_ROOT` patching pattern

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `resolve_entities()` in `segmenter.py`: stays, called from Pass 5 (entity→stub resolution)
- `dedup_segment()` in `segmenter.py`: stays, called per-segment during assembly
- `_classify_segment()` / `_derive_title()` in `segmenter.py`: move logic into Pass 3 module
- `extract_action_items()` in `intelligence.py`: reused in Pass 4 layer (b) for intent-based extraction

### Established Patterns
- URL detection: `_URL_PAT = re.compile(r'https?://\S+')` — already in both `segmenter.py` and `typeclassifier.py`; consolidate into Pass 1 or Pass 2 module
- Person stub creation: already in `sb_capture_smart` around line 882 of `mcp_server.py` — move into Pass 5
- `CONFIDENCE_THRESHOLD = 0.75` imported by callers — keep and re-export from `engine/passes/`
- Config reading: `config_loader.py` used elsewhere — follow same pattern for `[action_items]` section

### Integration Points
- `engine/api.py` → replace `from engine.segmenter import segment_blob` with `from engine.passes import decompose`
- `engine/mcp_server.py` → same import replacement; person stub loop moves into Pass 5
- `engine/typeclassifier.py` → remove URL hard-override (line ~80-81); add conversation-format signal
- `frontend/src/` → new settings panel component for action-item markers
- `engine/api.py` → new endpoint for reading/writing custom action-item markers (for settings panel)

</code_context>

<specifics>
## Specific Ideas

- User example: "tuomas would call the fastly" — must be caught as an action item via intelligence layer, not just keyword matching
- "AP" as custom action-item marker — example of domain-specific abbreviation users need to configure
- GUI dropdown: "full modularity for everything that is intended to be captured" — architecture principle driving pass isolation

</specifics>

<deferred>
## Deferred Ideas

- **Extraction enrichment on all capture paths** — running entity/action item/person stub extraction for regular `sb_capture`, `sb_capture_batch`, `sb_capture_link` calls via `capture_note()`. Deferred to a future phase (Phase 43.1 or 46). Explicit user request, not scope creep — just separated for scope discipline.

</deferred>

---

*Phase: 43-smart-capture-multi-pass-decomposer*
*Context gathered: 2026-03-29*
