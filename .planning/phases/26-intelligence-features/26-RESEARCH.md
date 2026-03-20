# Phase 26: Intelligence Features - Research

**Researched:** 2026-03-17
**Domain:** Python/Flask backend intelligence features + frontend GUI panel
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GUIF-02 | User can trigger on-demand weekly recap generation from the Intelligence panel | `/intelligence` route exists; `generate_digest()` in `engine/digest.py` can be called on demand; need POST endpoint + spinner/result UI |
| ENGL-03 | AI recap and action extraction quality improved (better prompts, deduplication, accuracy) | `RECAP_SYSTEM_PROMPT` in `intelligence.py`; digest uses 7-day window; action items insert without dedup check — both need improvements |
| ENGL-04 | Brain health dashboard shows orphan notes, broken links, and potential duplicates | `engine/links.py:check_links()` covers broken links; orphan notes = notes with no backlinks (query on `notes` LEFT JOIN `relationships`); duplicates = `find_similar()` with lower threshold |
| ENGL-05 | Brain health score visible via CLI (sb-health) or GUI | `engine/health.py:main()` exists but is component/system-health only (not brain content health); needs new `brain_health_score()` function + score formula + GUI panel section |
</phase_requirements>

---

## Summary

Phase 26 adds two capability clusters: on-demand recap generation in the GUI (GUIF-02, ENGL-03) and a brain content health dashboard (ENGL-04, ENGL-05). Both clusters sit squarely within the existing engine/GUI architecture — no new dependencies are needed.

The on-demand recap path reuses `generate_digest()` from `engine/digest.py`, but `generate_digest()` is idempotent (skips if this week's file exists). A new `generate_recap_on_demand()` wrapper must bypass that guard and always regenerate, returning the text to the caller rather than only writing a file. The existing `/intelligence` GET endpoint returns `{"recap": None, "nudges": [...]}` — a new `POST /intelligence/recap` endpoint is the correct addition; it triggers generation and streams or returns the result.

The brain content health dashboard is a new concept distinct from the existing `sb-health` (which checks system components: Ollama, launchd, CLI). A new `engine/brain_health.py` module should implement: orphan notes (notes with no inbound relationships), broken links (delegate to `engine/links.check_links()`), potential duplicates (reuse `find_similar()` with threshold ~0.75), and a 0-100 score formula. The existing `sb-health` CLI entry point should gain a `--brain` flag (or a new `sb-brain-health` entry point) to surface the content score. The GUI Intelligence panel gets a new "Health" sub-section.

**Primary recommendation:** New `engine/brain_health.py` module + `POST /intelligence/recap` + `GET /brain-health` Flask routes + minimal HTML/JS additions to the existing `#intelligence-panel`.

---

## Standard Stack

### Core (already in project — no new installs)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | existing | `POST /intelligence/recap` + `GET /brain-health` routes | All API routes live here |
| SQLite3 / `engine/db.py` | existing | Orphan/duplicate queries | Established DB layer |
| `engine/links.py:check_links()` | existing | Broken link detection | Already tested, already correct |
| `engine/intelligence.py:find_similar()` | existing | Duplicate candidate detection via cosine similarity | sqlite-vec already wired |
| `engine/digest.py:generate_digest()` | existing | Weekly recap content generation | AI prompts + DB queries already wired |

### No New Dependencies
All required capabilities exist in the codebase. Do NOT add new packages for this phase.

---

## Architecture Patterns

### Recommended Module Structure
```
engine/
├── brain_health.py      # NEW: orphan/broken-link/duplicate checks + score formula
├── health.py            # EXISTING: system component checks — add --brain flag or keep separate
├── intelligence.py      # EXISTING: add generate_recap_on_demand()
├── digest.py            # EXISTING: no changes needed
api.py                   # EXISTING: add POST /intelligence/recap + GET /brain-health
engine/gui/static/
├── app.js               # EXISTING: add generateRecap() + loadBrainHealth() functions
├── index.html           # EXISTING: add button + health sub-section to #intelligence-panel
```

### Pattern 1: On-Demand Recap (GUIF-02, ENGL-03)

**What:** POST endpoint that calls recap logic without the "already exists this week" guard, returns JSON with recap text.

**Backend:**
```python
# engine/intelligence.py — new function
def generate_recap_on_demand(conn) -> str:
    """Generate recap from last 7 days of notes. Always regenerates (no idempotency guard).
    Returns the summary string. Best-effort — returns fallback string on error."""
    from engine.paths import CONFIG_PATH
    rows = conn.execute(
        "SELECT title, body, sensitivity FROM notes "
        "WHERE created_at >= datetime('now', '-7 days') "
        "ORDER BY created_at DESC LIMIT 30"
    ).fetchall()
    if not rows:
        return "No notes captured in the last 7 days."
    # Split pii vs public, generate with appropriate adapter
    ...
    return summary

# api.py — new route
@app.post("/intelligence/recap")
def intelligence_recap():
    conn = get_connection()
    try:
        from engine.intelligence import generate_recap_on_demand
        text = generate_recap_on_demand(conn)
        return jsonify({"recap": text})
    except Exception as exc:
        return jsonify({"recap": f"Error: {exc}"}), 500
    finally:
        conn.close()
```

**Frontend:**
```javascript
// app.js — add to Intelligence panel
document.getElementById('generate-recap-btn').addEventListener('click', async () => {
    const btn = document.getElementById('generate-recap-btn');
    const content = document.getElementById('recap-content');
    btn.disabled = true;
    content.textContent = 'Generating...';
    const res = await fetch(`${API}/intelligence/recap`, { method: 'POST' });
    const { recap } = await res.json();
    content.textContent = recap || 'No recap available.';
    btn.disabled = false;
});
```

**HTML addition (inside `#intelligence-panel`):**
```html
<button id="generate-recap-btn">Generate Recap</button>
<div id="recap-content"></div>
```

### Pattern 2: Brain Health Dashboard (ENGL-04, ENGL-05)

**What:** New `engine/brain_health.py` with three checks + score formula. Exposed via `GET /brain-health` API endpoint.

**Orphan notes query** — notes with no inbound `relationships` rows:
```python
def get_orphan_notes(conn) -> list[dict]:
    rows = conn.execute("""
        SELECT n.path, n.title FROM notes n
        LEFT JOIN relationships r ON n.path = r.target_path
        WHERE r.target_path IS NULL
          AND n.type NOT IN ('digest', 'memory')
        ORDER BY n.created_at DESC
    """).fetchall()
    return [{"path": r[0], "title": r[1]} for r in rows]
```

**Broken links** — delegate to existing `check_links()`:
```python
from engine.links import check_links
broken = check_links(brain_root, conn)
```

**Duplicate candidates** — scan embeddings pairwise via `find_similar()`:
```python
def get_duplicate_candidates(conn, threshold: float = 0.92) -> list[dict]:
    """Return pairs of notes with cosine similarity above threshold."""
    paths = [r[0] for r in conn.execute("SELECT note_path FROM note_embeddings").fetchall()]
    seen = set()
    pairs = []
    for path in paths:
        matches = find_similar(path, conn, threshold=threshold, limit=5)
        for m in matches:
            key = tuple(sorted([path, m["note_path"]]))
            if key not in seen:
                seen.add(key)
                pairs.append({"a": path, "b": m["note_path"], "similarity": m["similarity"]})
    return pairs
```

**Score formula (0-100):**
```python
def compute_health_score(total_notes: int, orphans: int, broken: int, duplicates: int) -> int:
    if total_notes == 0:
        return 100
    orphan_ratio = orphans / total_notes
    broken_ratio = broken / max(total_notes, 1)
    dup_ratio = duplicates / max(total_notes, 1)
    penalty = (orphan_ratio * 30) + (broken_ratio * 40) + (dup_ratio * 20)
    return max(0, round(100 - penalty * 100))
```

**API endpoint:**
```python
@app.get("/brain-health")
def brain_health():
    from engine.brain_health import get_orphan_notes, get_duplicate_candidates, compute_health_score
    from engine.links import check_links
    from engine.paths import BRAIN_ROOT
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        orphans = get_orphan_notes(conn)
        broken = check_links(BRAIN_ROOT, conn)
        duplicates = get_duplicate_candidates(conn)
        score = compute_health_score(total, len(orphans), len(broken), len(duplicates))
        return jsonify({
            "score": score,
            "total_notes": total,
            "orphans": orphans[:20],
            "broken_links": broken[:20],
            "duplicate_candidates": duplicates[:20],
        })
    finally:
        conn.close()
```

**HTML addition (inside `#intelligence-panel`):**
```html
<section id="health-panel">
  <h3>Brain Health</h3>
  <div id="health-score"></div>
  <div id="health-details"></div>
  <button id="refresh-health-btn">Refresh</button>
</section>
```

### Pattern 3: Improved Recap Prompts (ENGL-03)

**What:** Deduplicate action items on extraction; improve recap prompt to be more concrete.

**Key issues with current code:**
1. `extract_action_items()` inserts without checking for duplicate text — same item appears multiple times if note is re-captured
2. `RECAP_SYSTEM_PROMPT` produces vague output; no explicit instruction to avoid repeating previous recap content
3. `generate_digest()` is idempotent on file (skips if week's file exists) — on-demand version must not check file existence

**Fix for action item deduplication:**
```python
# engine/intelligence.py — modify extract_action_items()
# Before inserting, check if (note_path, text) already exists
existing = conn.execute(
    "SELECT COUNT(*) FROM action_items WHERE note_path=? AND text=?",
    (str(note_path.resolve()), line)
).fetchone()[0]
if existing == 0:
    conn.execute("INSERT INTO action_items ...", ...)
```

**Improved RECAP_SYSTEM_PROMPT:**
```python
RECAP_SYSTEM_PROMPT = (
    "You are a personal assistant reviewing a week of notes. "
    "Write a 3-5 sentence summary covering: (1) what was worked on, "
    "(2) key decisions made, (3) open threads or risks. "
    "Be specific — mention note titles or topics by name. "
    "Output plain prose, no bullet points, no headers."
)
```

### Anti-Patterns to Avoid
- **Rewriting `health.py`:** The existing `sb-health` checks system components (Ollama, launchd, DB). Brain content health is a separate concern — put it in `engine/brain_health.py`, not in `health.py`.
- **Blocking the Flask thread on AI generation:** `POST /intelligence/recap` will call the AI adapter (potentially slow). Use `timeout` parameter if available. Do NOT use background threads — the existing pattern is synchronous; just ensure the frontend shows a spinner and disables the button.
- **Running pairwise embedding scan on every page load:** Duplicate detection is O(N) queries against sqlite-vec. Only run on explicit `GET /brain-health` request, never on startup or passively.
- **Breaking `generate_digest()` idempotency:** The launchd weekly digest job calls `generate_digest()` and depends on it being idempotent. Create a separate `generate_recap_on_demand()` — do NOT modify `generate_digest()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Broken link detection | Custom file-existence checker | `engine/links.check_links()` | Already tested with 3 test cases in `tests/test_links.py` |
| Cosine similarity / duplicate detection | Custom vector math | `engine/intelligence.find_similar()` + sqlite-vec | Already handles sqlite-vec loading, fallback if unavailable |
| Note body truncation for AI | Custom chunking | Use existing `body[:500]` pattern from `recap_entity()` | Consistent with existing patterns |
| AI routing (PII vs public) | Direct adapter calls | `_router.get_adapter(sensitivity, CONFIG_PATH)` | Handles PII routing to Ollama, public to Claude |

---

## Common Pitfalls

### Pitfall 1: `generate_digest()` idempotency guard blocks on-demand recap
**What goes wrong:** Calling `generate_digest()` from the new POST endpoint returns immediately with "already exists" when the week's file is present.
**Why it happens:** `generate_digest()` checks `if out_path.exists(): return out_path` at line 39.
**How to avoid:** Create `generate_recap_on_demand(conn) -> str` in `engine/intelligence.py` that runs the query + AI call directly without file existence check. Do NOT call `generate_digest()`.
**Warning signs:** POST endpoint returns instantly with old recap text.

### Pitfall 2: Orphan query includes digest/memory notes as "orphans"
**What goes wrong:** Digest files and memory files have no inbound backlinks by design — they'll appear as orphans and inflate the orphan count.
**How to avoid:** Add `WHERE n.type NOT IN ('digest', 'memory')` to orphan query. Also consider excluding `files/` paths.
**Warning signs:** Health score is 0 on a healthy brain with many digests.

### Pitfall 3: `find_similar()` throws when sqlite-vec is unavailable
**What goes wrong:** `find_similar()` returns `[]` silently when sqlite-vec isn't loaded (Intel Mac without Ollama running). Duplicate detection returns empty — that's correct behavior, but must not raise.
**How to avoid:** `find_similar()` already returns `[]` on exception. The `get_duplicate_candidates()` wrapper must also catch exceptions from `find_similar()`.
**Warning signs:** `/brain-health` returns 500 on machines without sqlite-vec.

### Pitfall 4: Action item dedup breaks existing action item tests
**What goes wrong:** Adding `SELECT COUNT(*) FROM action_items WHERE note_path=? AND text=?` guard requires the `action_items` table to exist at test time.
**How to avoid:** Tests call `init_schema(conn)` which creates the table via `SCHEMA_SQL`. Verify fixture uses `init_schema()`.
**Warning signs:** `OperationalError: no such table: action_items` in tests.

### Pitfall 5: Frontend button enabled before note is open
**What goes wrong:** "Generate Recap" button could be shown/clickable at all times, but recap is not note-specific — it's always available.
**How to avoid:** Unlike the upload button (which requires a note), the recap button is always enabled. No `openNote()` guard needed.

### Pitfall 6: `action_items` table schema mismatch in `digest.py`
**What goes wrong:** `engine/digest.py` queries `action_items` with `action_text` and `status` columns (lines 59-61), but `engine/db.py` schema uses `text` and `done` columns. The digest open actions section always shows "No open actions."
**How to avoid:** If fixing ENGL-03 quality touches the digest, fix the column name mismatch in `digest.py`. Do NOT change the schema — fix the query in `digest.py` to use `text` and `done=0`.
**Warning signs:** `OperationalError: no such column: action_text` in `generate_digest()`.

---

## Code Examples

### Existing: `check_links()` return format (HIGH confidence — read from source)
```python
# engine/links.py:56-78
# Returns list of dicts: [{"source": str, "target": str, "issue": str}, ...]
# issue values: "source missing" | "target missing" | "target does not reference source"
orphans = check_links(BRAIN_ROOT, conn)  # list[dict]
```

### Existing: `find_similar()` call signature (HIGH confidence — read from source)
```python
# engine/intelligence.py:232
find_similar(note_path: str, conn, threshold: float = 0.8, limit: int = 3) -> list[dict]
# Returns [{"note_path": str, "similarity": float}, ...]
# Returns [] if sqlite-vec unavailable or note has no embedding
```

### Existing: PII-aware adapter routing (HIGH confidence — read from source)
```python
# engine/intelligence.py:380-390 (recap_entity pattern)
from engine.paths import CONFIG_PATH
adapter = _router.get_adapter(sensitivity, CONFIG_PATH)  # "pii" or "public"
result = adapter.generate(user_content=text, system_prompt=SOME_PROMPT)
```

### Existing: Intelligence panel HTML (HIGH confidence — read from source)
```html
<!-- engine/gui/static/index.html:56-61 -->
<section id="intelligence-panel">
    <h3>Intelligence</h3>
    <div id="recap-content"></div>
    <ul id="nudges-list"></ul>
</section>
```

### Existing: `startup()` calls `init_schema()` (HIGH confidence — read from source)
```python
# api.py:689-695
def startup() -> None:
    from engine.db import init_schema
    conn = get_connection()
    try:
        init_schema(conn)
    finally:
        conn.close()
```
New routes can assume schema exists; no migration needed for brain_health (pure queries on existing tables).

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `sb-health` = system component checks only | Phase 26 adds brain content health (orphans, broken links, duplicates) | Two distinct health concepts — keep separate |
| `generate_digest()` idempotent, file-based | `generate_recap_on_demand()` always regenerates, returns string | On-demand GUI trigger works correctly |
| Action items inserted without dedup | Add `(note_path, text)` existence check before insert | No repeated items across consecutive recaps |
| `recap_main()` requires git context or entity name | On-demand recap uses 7-day sliding window, no context detection required | Works regardless of CWD or git repo |

**Known bug to fix during ENGL-03:**
- `engine/digest.py` lines 59-61 query `action_items.action_text` and `status='open'` — but the actual column names are `text` and `done=0`. This causes the "Open Actions" section to always show "No open actions." Fix the query in `digest.py`.

---

## Open Questions

1. **Health score weighting**
   - What we know: Orphan ratio, broken link ratio, duplicate ratio are the inputs
   - What's unclear: Exact penalty weights (30/40/20 are proposed; no user preference stated)
   - Recommendation: Use proposed weights; easy to tune later

2. **sb-health flag vs new entry point for brain health**
   - What we know: `sb-health` entry point exists in `pyproject.toml`; it runs system checks
   - What's unclear: Should brain health be `sb-health --brain` or a new `sb-brain-health` command?
   - Recommendation: Add `--brain` flag to `sb-health` for discoverability; fallback to full system check if flag absent. Avoids new entry point and new `uv tool install` step.

3. **Duplicate threshold**
   - What we know: `find_similar()` default threshold is 0.8; duplicate detection should be higher (fewer false positives)
   - What's unclear: Right threshold for "likely duplicate" vs "related"
   - Recommendation: Use 0.92 for duplicate candidates; documents as configurable

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_brain_health.py tests/test_intelligence.py -x -q` |
| Full suite command | `uv run pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GUIF-02 | POST /intelligence/recap returns `{"recap": "..."}` | unit (API) | `pytest tests/test_api.py -k recap -x` | ❌ Wave 0 stub needed |
| GUIF-02 | Frontend "Generate Recap" button triggers POST and shows result | e2e (Playwright) | `pytest tests/test_gui.py -k recap -x` | ❌ Wave 0 stub needed |
| ENGL-03 | Action items not duplicated when note captured twice | unit | `pytest tests/test_intelligence.py -k dedup -x` | ❌ Wave 0 stub needed |
| ENGL-03 | `generate_recap_on_demand()` returns non-empty string | unit | `pytest tests/test_intelligence.py -k on_demand -x` | ❌ Wave 0 stub needed |
| ENGL-04 | `get_orphan_notes()` returns notes with no inbound backlinks | unit | `pytest tests/test_brain_health.py -k orphan -x` | ❌ Wave 0 |
| ENGL-04 | `get_duplicate_candidates()` returns pairs above threshold | unit | `pytest tests/test_brain_health.py -k duplicate -x` | ❌ Wave 0 |
| ENGL-04 | GET /brain-health returns orphans, broken_links, duplicate_candidates | unit (API) | `pytest tests/test_brain_health.py -k api -x` | ❌ Wave 0 |
| ENGL-05 | `compute_health_score()` returns 100 for clean brain, lower when issues present | unit | `pytest tests/test_brain_health.py -k score -x` | ❌ Wave 0 |
| ENGL-05 | GUI health panel displays score and issue counts | e2e (Playwright) | `pytest tests/test_gui.py -k health -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_brain_health.py tests/test_intelligence.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_brain_health.py` — covers ENGL-04, ENGL-05 (new file)
- [ ] Stubs in `tests/test_intelligence.py` for GUIF-02, ENGL-03 dedup, ENGL-03 on-demand
- [ ] Stub in `tests/test_gui.py` for recap button + health panel e2e
- [ ] `engine/brain_health.py` — stub module (new file)

---

## Sources

### Primary (HIGH confidence)
- `/Users/tuomasleppanen/second-brain/engine/brain_health.py` — does not exist yet; confirmed from `ls engine/`
- `/Users/tuomasleppanen/second-brain/engine/health.py` — read directly; confirms current scope is system checks only
- `/Users/tuomasleppanen/second-brain/engine/intelligence.py` — read directly; confirms `find_similar()`, `RECAP_SYSTEM_PROMPT`, `generate_recap_on_demand` does not exist
- `/Users/tuomasleppanen/second-brain/engine/digest.py` — read directly; confirms idempotency guard + column name bug
- `/Users/tuomasleppanen/second-brain/engine/links.py` — read directly; confirms `check_links()` return format
- `/Users/tuomasleppanen/second-brain/engine/db.py` — read directly; confirms `action_items` uses `text`/`done` columns
- `/Users/tuomasleppanen/second-brain/engine/api.py` — read directly; confirms `/intelligence` GET returns `recap: null`
- `/Users/tuomasleppanen/second-brain/engine/gui/static/index.html` — read directly; confirms `#intelligence-panel` structure
- `/Users/tuomasleppanen/second-brain/pyproject.toml` — confirmed `sb-health` entry point

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in codebase, read directly
- Architecture: HIGH — all integration points confirmed from source reading
- Pitfalls: HIGH — bugs identified from direct source reading (digest column mismatch confirmed)
- Validation: HIGH — existing pytest infrastructure confirmed

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (stable codebase, no fast-moving deps)
