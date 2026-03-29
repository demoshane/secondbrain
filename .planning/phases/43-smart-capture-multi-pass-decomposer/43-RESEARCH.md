# Phase 43: Smart Capture Multi-Pass Decomposer — Research

**Researched:** 2026-03-29
**Domain:** Python module refactor — segmentation pipeline, type classification, action item extraction, GUI settings panel
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Single `decompose(content: str) -> DecomposedResult` public entry point in `engine/passes/__init__.py`. Each pass is a separate module (`p1_entities.py`, `p2_urls.py`, `p3_classify.py`, `p4_actions.py`, `p5_assemble.py`).
- **D-02:** `segment_blob()` is deleted (not wrapped). All callers updated to call `decompose()`. `segmenter.py` retains `resolve_entities()` and `dedup_segment()` only.
- **D-03:** Full modularity principle — every extractable thing lives in its own pass module.
- **D-04:** ANY URL in blob always extracted into a separate link note. No threshold. No URL-into-frontmatter fallback.
- **D-05:** If URL is the primary content (blob = URL + short description), Pass 2 still produces a link note — same code path, no special case.
- **D-06:** After URL extraction, URL-stripped content goes to Pass 3 for type classification. Meeting note with Zoom link → 2 notes: meeting + link.
- **D-07:** Two-layer action item extraction: (a) configurable keyword markers (default: `TODO`, `AP`, `action:`, `@owner`, `Action Point`), (b) `extract_action_items()` in `intelligence.py` for intent-based.
- **D-08:** Action items written to `action_items` DB table at capture time. Pass 5 includes them in assembly output; api.py/mcp_server.py persist them.
- **D-09:** Configurable markers stored in `config.toml` under `[action_items] custom_markers = [...]`.
- **D-10:** New GUI settings panel for action-item markers (view/add/remove). Location: Claude's discretion.
- **D-11:** `Name [HH:MM]` pattern is a strong meeting-type signal (>= 2 turns → 0.85 confidence).
- **D-12:** `POST /smart-capture` creates person stubs — full behavioral parity with MCP.
- **D-13:** Both `sb_capture_smart` and `POST /smart-capture` call the same `decompose()` function. Code-level parity enforced.

### Claude's Discretion

- Exact file naming within `engine/passes/` (e.g., `p1_entities.py` vs `entities.py`)
- `DecomposedResult` type shape (dataclass vs TypedDict vs plain dict)
- Whether `segmenter.py` is deleted entirely or kept with only `resolve_entities()` and `dedup_segment()`
- GUI settings panel exact location (Settings page vs Intelligence page section)
- Conversation-format split behaviour: whether `Name [HH:MM]` lines also trigger segment splits or only add meeting signal to classifier

### Deferred Ideas (OUT OF SCOPE)

- Extraction enrichment for regular `sb_capture`, `sb_capture_batch`, `sb_capture_link` calls — deferred to Phase 44.
</user_constraints>

---

## Summary

Phase 43 is a structural refactor of the smart capture pipeline — no new external libraries, no DB schema migrations beyond reading/writing to already-existing tables. The work is self-contained to the `engine/` Python layer and a single new frontend settings panel.

The current architecture in `segmenter.py` combines structural splitting, name-cluster detection, type classification, and entity extraction in one monolithic `segment_blob()` function (234 lines). `typeclassifier.py` has a hard-override at line 81 that returns `("link", 1.0)` immediately whenever any URL is found anywhere in the note, preventing a meeting note with a Zoom link from being classified as a meeting. These are the two concrete bugs driving the refactor.

The new `engine/passes/` package decomposes the pipeline into 5 serial passes. Each pass is independently importable and testable. The public surface is `decompose(content) -> DecomposedResult` which orchestrates all passes in sequence. After the refactor, `api.py` and `mcp_server.py` both call `decompose()` directly — currently they diverge: `api.py` calls `segment_blob()` but does NOT create person stubs, while `mcp_server.py` calls `segment_blob()` AND runs the stub creation loop. Pass 5 absorbs the stub creation, eliminating this divergence.

**Primary recommendation:** Plan the phase as 5–6 discrete plans mapped to the passes + caller wiring + GUI panel. All plans modify independent files except the final caller-wiring plan. Execute sequentially (direct mode, not multi-agent) because `api.py` and `mcp_server.py` will be touched by multiple plans.

---

## Standard Stack

No new dependencies required. All libraries are already installed.

### Core (already present)
| Library | Purpose | Location |
|---------|---------|----------|
| Python `re` | URL and pattern detection in all passes | stdlib |
| Python `dataclasses` or `TypedDict` | `DecomposedResult` type | stdlib |
| `tomllib` (stdlib 3.11+) | Read `config.toml` for custom markers | stdlib, used in `config_loader.py` |
| `tomli_w` | Write `config.toml` (markers settings persist) | already in deps, used by `PUT /config` |
| `engine.entities.extract_entities()` | Pass 1 entity extraction | existing |
| `engine.typeclassifier.classify_note_type()` | Pass 3 classification | existing, being modified |
| `engine.intelligence.extract_action_items()` | Pass 4 layer (b) intent extraction | existing |
| `engine.segmenter.resolve_entities()` | Pass 5 stub resolution | stays in segmenter.py |
| `engine.segmenter.dedup_segment()` | Called per-segment by assembly layer | stays in segmenter.py |
| `engine.capture.capture_note()` | Pass 5 stub creation and final saves | existing |
| `engine.config_loader.load_config()` | Read custom action-item markers | existing |

**No new pip installs needed.**

---

## Architecture Patterns

### Recommended Module Structure

```
engine/
├── passes/
│   ├── __init__.py          # decompose() public entry point + DecomposedResult type
│   ├── p1_entities.py       # extract people, links, dates unconditionally
│   ├── p2_urls.py           # extract URLs → link note dicts; strip from content
│   ├── p3_classify.py       # classify URL-stripped content; add conversation signal
│   ├── p4_actions.py        # keyword + intent-based action item extraction
│   └── p5_assemble.py       # build primary note + link notes + person stubs + action items
├── segmenter.py             # keeps only resolve_entities() + dedup_segment()
└── typeclassifier.py        # remove URL hard-override; add conversation-format signal
```

### Pattern 1: DecomposedResult as dataclass

```python
# engine/passes/__init__.py
from dataclasses import dataclass, field

@dataclass
class LinkNote:
    url: str
    title: str
    body: str  # description with URL stripped from primary content

@dataclass
class ActionItem:
    text: str
    owner: str | None
    due_date: str | None
    source: str  # "keyword" | "intent"

@dataclass
class DecomposedResult:
    primary_title: str
    primary_type: str
    primary_body: str
    confidence: float
    entities: dict              # {"people": [...], "topics": [...], ...}
    link_notes: list[LinkNote] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
    person_stubs: list[dict] = field(default_factory=list)   # from Pass 5 resolution
    existing_people: list[dict] = field(default_factory=list)
    # Multi-segment support: decompose() returns list[DecomposedResult]
```

Note: `decompose()` may return a list when content contains multiple structural segments (same as current `segment_blob()` behaviour). The exact return type — `DecomposedResult` vs `list[DecomposedResult]` — is planner's discretion (both are internally consistent). The context says "Segment blob + decompose" so returning a list is consistent with existing caller logic.

### Pattern 2: Pass 2 — URL extraction

The URL hard-override fix is the most critical correctness change. Current code (typeclassifier.py line 81):

```python
# CURRENT — hard override that discards all classification signals
if _URL_PAT.search(combined):
    return ("link", 1.0)
```

New approach: Pass 2 strips URLs from content before it ever reaches Pass 3. Typeclassifier's URL check becomes unreachable for `decompose()` callers. The line should be removed from `typeclassifier.py` entirely (or guarded) since direct `classify_note_type()` callers still use it — but this needs careful handling. Best approach: remove the hard-override from `typeclassifier.py` and let each caller (pass-based or direct) pass URL-stripped content.

**Pitfall:** Existing tests in `test_typeclassifier.py` test `test_url_gives_link` — that test will break if the URL override is removed. The test must be updated to reflect new behaviour (URLs no longer auto-classify as link at the classifier level).

### Pattern 3: Pass 3 — conversation-format signal

```python
# engine/passes/p3_classify.py
import re

_CONVO_TURN_PAT = re.compile(r'^[A-Za-z][A-Za-z\s\-]{1,30}\s*\[\d{1,2}:\d{2}\]', re.MULTILINE)

def _conversation_boost(body: str) -> float:
    """Return 0.85 if >= 2 conversation turns detected, else 0.0."""
    turns = _CONVO_TURN_PAT.findall(body)
    return 0.85 if len(turns) >= 2 else 0.0
```

The meeting signal replaces (or is combined with) existing keyword scores in `classify_note_type()`. Since Pass 3 calls `classify_note_type()` after URL stripping, the implementation adds conversation boost *inside* `classify_note_type()` or as a pre-check in Pass 3. The latter is cleaner (keeps classifier modular).

### Pattern 4: Pass 4 — keyword-first action item extraction

```python
# engine/passes/p4_actions.py
import re
from engine.config_loader import load_config
from engine.paths import CONFIG_PATH

DEFAULT_MARKERS = ["TODO", "AP", "action:", "@owner", "Action Point"]

def extract_keyword_actions(body: str) -> list[dict]:
    config = load_config(CONFIG_PATH)
    custom = config.get("action_items", {}).get("custom_markers", [])
    all_markers = DEFAULT_MARKERS + custom
    pattern = re.compile(
        r'(?:' + '|'.join(re.escape(m) for m in all_markers) + r')\s*[:\-]?\s*(.+)',
        re.IGNORECASE
    )
    results = []
    for m in pattern.finditer(body):
        results.append({"text": m.group(1).strip(), "owner": None, "due_date": None, "source": "keyword"})
    return results
```

Layer (b) — intent extraction via `extract_action_items()` — is already an LLM call in `intelligence.py`. That function currently writes directly to the DB (it takes a `note_path` and `conn`). For Pass 4, we need the extracted items as a return value before the note is saved (no path yet). Options:
1. Call it after the note is saved (during Pass 5 assembly, once paths are known)
2. Refactor `extract_action_items()` to also return items — currently it only writes to DB

**Recommendation:** Pass 4 does keyword extraction only (synchronous, no LLM). Intent-based extraction (`extract_action_items()`) is triggered by Pass 5 or the caller after note save, as it already works today. This avoids refactoring `intelligence.py` and keeps Pass 4 fast.

### Pattern 5: Config.toml extension for custom markers

```toml
# ~/SecondBrain/.meta/config.toml (addition)
[action_items]
custom_markers = ["AP", "DECISION"]
```

`load_config()` already handles missing sections via `DEFAULT_CONFIG` fallback. No change to `config_loader.py` needed — just add `[action_items]` to `DEFAULT_CONFIG`.

### Pattern 6: GUI settings panel for action-item markers

Existing pattern: `SettingsModal.tsx` already reads `GET /config` and writes `PUT /config`. It currently only exposes the `routing.*` and `ollama.*` sections.

Two options for the action-item markers panel:
- **Option A:** Extend `SettingsModal.tsx` with a new "Capture" section for markers. Uses existing `GET /config` + `PUT /config` endpoints (already handle arbitrary config.toml sections via merge logic).
- **Option B:** New dedicated settings section in `IntelligencePage.tsx`.

**Recommendation: Option A** — extend the existing SettingsModal. The existing `PUT /config` route in `api.py` (line 1141) already handles merging arbitrary sections into config.toml. No new API endpoint needed.

**Verification needed:** Check if `PUT /config` in `api.py` correctly persists arbitrary sections (not just `routing`/`ollama`). Current implementation may restrict to routing/ollama only.

### Anti-Patterns to Avoid

- **Don't put dedup logic in the passes.** `dedup_segment()` is called by the caller (api.py / mcp_server.py) after decompose, not inside any pass. Passes produce structured output; callers decide what to do with it.
- **Don't make passes stateful.** Each pass is a pure function taking a string/dict input and returning structured output. No global state, no DB connections inside passes.
- **Don't wire DB writes into pass modules.** DB operations (saving notes, writing action items) happen in api.py/mcp_server.py using the assembled result. Pass 5 produces the assembly blueprint; it doesn't call `capture_note()` directly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL detection | Custom regex | `_URL_PAT = re.compile(r'https?://\S+')` | Already exists in both segmenter.py and typeclassifier.py — consolidate into Pass 1/2 module |
| Entity extraction | Custom NER | `engine.entities.extract_entities()` | Already implemented, tested, handles people/topics/dates |
| Person stub resolution | Custom DB lookup | `segmenter.resolve_entities()` | Already implemented with FTS5 + fuzzy match |
| Config file reading | Direct `open()` | `engine.config_loader.load_config()` | Handles missing files, no caching, already established pattern |
| Action item DB insert | Raw SQL | Call `extract_action_items()` post-save or inline the existing `action_items` INSERT pattern from intelligence.py | Schema and upsert logic already tested |

---

## Common Pitfalls

### Pitfall 1: URL hard-override removal breaks existing classifier tests

**What goes wrong:** `test_url_gives_link` in `test_typeclassifier.py` asserts that a URL body returns `("link", 1.0)`. Remove the override from `typeclassifier.py` and this test fails immediately.

**Why it happens:** The test was written when the hard-override was the intended behaviour. It's now a regression test for the bug being fixed.

**How to avoid:** Update `test_typeclassifier.py` — replace `test_url_gives_link` with a test that verifies URL-containing content classifies by its actual content signals (e.g. a meeting note with a Zoom URL classifies as "meeting", not "link").

**Warning signs:** Red `test_typeclassifier.py` after removing the URL override. Expected failure — fix the test, not the code.

### Pitfall 2: `mcp_server.py` has more logic than `api.py` around smart capture

**What goes wrong:** `mcp_server.py`'s `sb_capture_smart` does: segment_blob → resolve_entities (stub creation) → dedup_segment → save. The GUI's `POST /smart-capture` does: segment_blob → save (no stubs, no dedup on the stub-resolution side). After the refactor, both must call `decompose()` + the same stub/dedup flow. If the planner doesn't read both callers, the GUI path will silently miss stubs.

**How to avoid:** Read both callers before writing the caller-wiring plan. The diff between them is the stub creation loop (lines 882–908 of mcp_server.py) — this moves into Pass 5.

### Pitfall 3: `extract_action_items()` signature expects a saved `note_path`

**What goes wrong:** `intelligence.py:extract_action_items()` signature is `(note_path, body_or_conn, sensitivity, conn)`. It writes to DB using `note_path` as the foreign key. Pass 4 needs items before the note is saved (no path yet). Calling it inside a pass will crash or produce DB rows with null `note_path`.

**How to avoid:** Keep intent-based extraction (`extract_action_items()`) as a post-save operation — call it after `capture_note()` returns the path, exactly as today. Pass 4 handles only keyword extraction. Document this explicitly in the Pass 4 plan.

**Warning signs:** `extract_action_items()` called before `capture_note()` — this is always wrong.

### Pitfall 4: `PUT /config` may not persist `[action_items]` section

**What goes wrong:** Current `PUT /config` in api.py says "Persist changes to routing.* and ollama.* in config.toml. Other sections untouched." The implementation may explicitly whitelist sections. If it does, writing `[action_items]` markers through the existing endpoint will silently discard them.

**How to avoid:** Read the `PUT /config` implementation (api.py ~line 1141) before deciding whether to extend it or add a new endpoint for markers. A new narrow endpoint (`GET/PUT /config/action-item-markers`) is cleaner and avoids risk of breaking routing config persistence.

### Pitfall 5: `segment_blob()` deletion may break test_smart_capture.py

**What goes wrong:** `tests/test_smart_capture.py` imports `from engine.segmenter import segment_blob` throughout the test class `TestSegmentStructuralMarkers`. Deleting `segment_blob` breaks all these tests immediately.

**How to avoid:** Migrate `test_smart_capture.py` tests to import from `engine.passes` and test `decompose()`. This is a Wave 0 task in the passes plan. Alternatively, keep the old tests as-is and add new tests for `decompose()` side-by-side — but the old imports will still break.

### Pitfall 6: `dedup_segment()` / `resolve_entities()` still in segmenter.py after deletion

**What goes wrong:** If `segmenter.py` is partially deleted or fully deleted, calls to `resolve_entities()` in mcp_server.py (line 856: `from engine.segmenter import dedup_segment, resolve_entities, segment_blob`) will break.

**How to avoid:** Keep `segmenter.py` alive with `resolve_entities()` and `dedup_segment()` intact. Only `segment_blob()` and its internal helpers (`_classify_segment`, `_derive_title`, `_mask_protected_regions`, etc.) are removed (or moved into passes). The import in mcp_server.py changes to remove `segment_blob` but keep `dedup_segment, resolve_entities`.

### Pitfall 7: Conversation-format regex misses non-ASCII names

**What goes wrong:** `Name [HH:MM]` pattern implemented as `[A-Za-z]...` will miss Finnish/Nordic names (Tuomas, Jöns, etc.) — the same issue flagged in Phase 30 for entity extraction (`[A-Z][a-z]+` regex in `entities.py`).

**How to avoid:** Use `\w` instead of `[A-Za-z]` for the name part, or use a Unicode-aware regex. Per Phase 30 decision, entity extraction now uses Unicode-aware patterns.

---

## Code Examples

### Current caller pattern (api.py) — to be replaced

```python
# Current api.py POST /smart-capture
from engine.segmenter import segment_blob
from engine.typeclassifier import CONFIDENCE_THRESHOLD

segments = segment_blob(content)
for seg in segments:
    confidence = seg.get("confidence", 1.0)
    if confidence < CONFIDENCE_THRESHOLD:
        pending_review.append({...})
        continue
    path = capture_note(note_type=seg["type"], ...)
    saved.append({...})
# NOTE: no person stub creation here — MCP does this, GUI does not
```

### Target caller pattern (api.py) — after refactor

```python
from engine.passes import decompose, CONFIDENCE_THRESHOLD

results = decompose(content)
for result in results:
    if result.confidence < CONFIDENCE_THRESHOLD:
        pending_review.append({...})
        continue
    # Save link notes from Pass 2
    for link in result.link_notes:
        capture_note(note_type="link", ...)
    # Create person stubs from Pass 5 (parity with MCP)
    for stub in result.person_stubs:
        capture_note(note_type=stub["type"], title=stub["name"], body="", ...)
    # Save primary note
    path = capture_note(note_type=result.primary_type, ...)
    # Post-save: intent-based action item extraction
    extract_action_items(path, body, sensitivity, conn)
    # Persist keyword-extracted action items
    for ai in result.action_items:
        conn.execute("INSERT OR IGNORE INTO action_items ...")
```

### `CONFIDENCE_THRESHOLD` re-export from passes package

```python
# engine/passes/__init__.py
from engine.typeclassifier import CONFIDENCE_THRESHOLD  # re-export so callers don't change
```

This keeps callers' `from engine.passes import decompose, CONFIDENCE_THRESHOLD` clean.

---

## Validation Architecture

`nyquist_validation` is enabled in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | none (uses defaults) |
| Quick run command | `uv run pytest tests/test_smart_capture.py tests/test_typeclassifier.py -x -q` |
| Full suite command | delegate to user: `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Area | Behavior | Test Type | Automated Command | File Exists? |
|------|----------|-----------|-------------------|-------------|
| Pass architecture | `decompose()` returns list of DecomposedResult | unit | `uv run pytest tests/test_decomposer.py -x` | No — Wave 0 gap |
| Pass 2 URL extraction | URL in meeting note → 2 results (meeting + link) | unit | `uv run pytest tests/test_decomposer.py::TestPass2 -x` | No — Wave 0 gap |
| Pass 3 URL-override fix | Meeting note with URL classifies as meeting | unit | `uv run pytest tests/test_decomposer.py::TestPass3 -x` | No — Wave 0 gap |
| Pass 3 conversation signal | `Name [HH:MM]` pattern → meeting type ≥ 0.85 | unit | `uv run pytest tests/test_decomposer.py::TestConversationSignal -x` | No — Wave 0 gap |
| Pass 4 keyword markers | TODO/AP lines extracted as action items | unit | `uv run pytest tests/test_decomposer.py::TestPass4 -x` | No — Wave 0 gap |
| Pass 4 custom markers | Custom marker from config.toml caught | unit | `uv run pytest tests/test_decomposer.py::TestCustomMarkers -x` | No — Wave 0 gap |
| GUI/MCP parity | POST /smart-capture creates person stubs | integration | `uv run pytest tests/test_smart_capture.py::TestGuiMcpParity -x` | No — Wave 0 gap |
| Typeclassifier update | `test_url_gives_link` updated/replaced | unit | `uv run pytest tests/test_typeclassifier.py -x` | Yes — needs update |
| Old segment_blob tests | Migrated to decompose() | unit | `uv run pytest tests/test_smart_capture.py -x` | Yes — needs migration |

### Wave 0 Gaps

- [ ] `tests/test_decomposer.py` — new test file covering all 5 passes and DecomposedResult shape
- [ ] `tests/test_typeclassifier.py` — update `test_url_gives_link` to reflect new URL behaviour
- [ ] `tests/test_smart_capture.py` — migrate `TestSegmentStructuralMarkers` imports from `segment_blob` to `decompose`

---

## Environment Availability

Step 2.6: SKIPPED — phase is pure Python code and config/frontend changes. No new external dependencies, no service probing required.

---

## Open Questions

1. **Does `PUT /config` support arbitrary config.toml sections?**
   - What we know: The route docstring says "routing.* and ollama.* only". Implementation at line 1141 was not fully read.
   - What's unclear: Whether writing `[action_items]` through it will work or be silently dropped.
   - Recommendation: Planner reads `PUT /config` implementation before deciding route. If restricted, add `GET /config/action-item-markers` + `PUT /config/action-item-markers` endpoints.

2. **Does `decompose()` return one result or a list?**
   - What we know: `segment_blob()` returns a list; callers iterate over it. The context says `decompose(content) -> DecomposedResult` (singular).
   - What's unclear: Whether the phase intends a single-segment simplification or multi-segment preservation.
   - Recommendation: Return `list[DecomposedResult]` to preserve the multi-segment semantics that callers already iterate over. Single-blob capture becomes `decompose(content)[0]`.

3. **Should `Name [HH:MM]` lines also split segments (structural marker) or only signal meeting type?**
   - Marked as Claude's discretion in CONTEXT.md.
   - Recommendation: Signal only (don't split). Adding them as structural markers would fragment conversational notes into per-turn segments, which is not useful.

4. **`test_smart_capture_golden_path` is already failing** (per Phase 45 in roadmap, pre-existing failure in `sb_capture_smart` relationship writing).
   - What this means: Some existing smart capture tests may already be red before Phase 43 starts.
   - Recommendation: Planner notes that Phase 45 will fix these. Phase 43 plans should not attempt to fix pre-existing failures — write tests for new behaviour and document any pre-existing failures with `xfail`.

---

## Sources

### Primary (HIGH confidence)

- Direct code reading: `engine/segmenter.py` — full understanding of `segment_blob()`, `resolve_entities()`, `dedup_segment()`
- Direct code reading: `engine/typeclassifier.py` — URL hard-override at line 81, `classify_note_type()` scoring, `CONFIDENCE_THRESHOLD = 0.75`
- Direct code reading: `engine/api.py` (lines 2195–2330) — `POST /smart-capture` and `POST /smart-capture/confirm` routes
- Direct code reading: `engine/mcp_server.py` (lines 840–1040) — `sb_capture_smart` with stub creation loop
- Direct code reading: `engine/intelligence.py` — `extract_action_items()` signature and LLM-write pattern
- Direct code reading: `engine/config_loader.py` — `load_config()` pattern, DEFAULT_CONFIG structure
- Direct code reading: `tests/test_smart_capture.py` — existing tests importing `segment_blob`
- Direct code reading: `tests/test_typeclassifier.py` — `test_url_gives_link` that will break
- Direct code reading: `frontend/src/components/SettingsModal.tsx` — existing settings panel using `GET/PUT /config`
- CONTEXT.md — locked decisions D-01 through D-13

### Secondary (MEDIUM confidence)

- LEARNINGS.md — project-specific test isolation patterns (patch both `engine.db.DB_PATH` and `engine.paths.DB_PATH`)
- STATE.md — accumulated decisions, particularly Phase 31 smart capture patterns

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all libraries confirmed present in codebase; no new installs
- Architecture: HIGH — callers read directly; pass boundaries clear from existing code structure
- Pitfalls: HIGH — all derived from direct code reading, not assumptions
- GUI panel: MEDIUM — existing SettingsModal pattern is clear; whether `PUT /config` supports arbitrary sections needs verification

**Research date:** 2026-03-29
**Valid until:** 2026-06-01 (stable domain, no fast-moving external deps)
