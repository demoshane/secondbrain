# Phase 31: Smart Capture & Multi-Context Intelligence - Research

**Researched:** 2026-03-20
**Domain:** MCP tool enhancement, NLP segmentation, dedup/entity-resolution, async background hooks, sensitivity classification
**Confidence:** HIGH (all findings from direct codebase inspection)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Segmentation strategy**
- Two-pass heuristic: structural markers first (headings, `---`, date/time stamps, `RE:`, `Subject:` patterns, bullet list starts), then name-cluster detection for unstructured prose
- Short segments (<50 chars or <2 lines) merge into previous segment
- Maximum 20 notes per `sb_capture_smart` call; if more, merge smallest until under limit
- URLs detected in blob become `type='link'` notes via existing `link_capture.py`; code blocks and tables stay inline in parent segment

**Entity resolution**
- Link to existing notes, don't create duplicates — FTS5 + fuzzy match against existing person/project notes
- Auto-create minimal stub notes (title + type + empty body) for genuinely new entities
- All segments share `capture_session: <uuid>` frontmatter + `co-captured` relationships between them

**Save policy**
- Auto-save via MCP: no confirm token round-trip. Segments + stubs + links saved atomically
- Action items found in segments: inline in note body AND extracted to `action_items` table

**Dedup policy**
- Three-path heuristic on near-duplicate found (>threshold):
  1. Superset (new is longer, contains existing key phrases) → update existing + append changelog
  2. Complementary → save as new + `similar` relationship
  3. Ambiguous → return both options for caller to decide
- Changelog format: `## Changelog` section with date, action, previous content hash
- `sb_capture_batch` checks each note against brain AND earlier notes in same batch (intra-batch)
- Similarity threshold in `.meta/config.toml` (default 0.92)

**Dormant resurfacing**
- MCP response only (`sb_capture` + `sb_capture_smart`). Not in GUI inbox/recap
- Dormant = `updated_at` older than 30 days
- Ranked by semantic similarity (embedding cosine) to just-captured content
- Up to 3 dormant notes per capture call

**Sensitivity auto-classify**
- Three tiers: `public` / `private` / `pii`
- Entity-based PII detection only: phone numbers, email, national ID patterns (Finnish hetu, SSN), credit cards. No keyword scanning
- Classify per-segment individually
- Never-downgrade rule: `pii` beats `public`; silent upgrade + note in response

**Async intelligence hooks (CAP-06)**
- Background daemon thread spawned after capture returns
- Runs action item extraction + connection detection on just-saved notes
- Error isolation: catch all, log to `audit_log` with `type='intelligence_error'`. Never surface to user

**Configuration**
- Segmentation config in `.meta/config.toml` with sensible defaults
- Dedup similarity threshold in same file
- GUI settings page deferred

**Performance**
- Target: <5s total for `sb_capture_smart`
- Performance regression test with synthetic brain (~500 notes + embeddings)

**Testing**
- Synthetic test fixtures for unit tests (each heuristic path in isolation)
- Golden path end-to-end test with flexible assertions (3-5 notes, ≥1 relationship, ≥2 action items)
- Performance regression test

### Claude's Discretion
- Exact heuristic weights for topic-shift detection
- Fuzzy match threshold for entity resolution
- Internal data structures for segment processing
- Background thread implementation details

### Deferred Ideas (OUT OF SCOPE)
- GUI settings page: expose `.meta/config.toml` settings in a GUI settings tab
- Brain consolidation / "brain sleep" (Phase 35): periodic near-duplicate merging, orphan cleanup
- Performance optimization of existing tools beyond Phase 31 smart capture path (Phase 33)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CAP-01 | `sb_capture_smart` accepts raw freeform text → N typed note suggestions with inferred titles, types, cross-links; user confirms before saving | Existing `sb_capture_smart` stub in mcp_server.py (lines 539-614) needs major rewrite; `_classify_segment` + `_derive_title` helpers are reusable scaffolding |
| CAP-02 | Multi-context parsing: single large input → N linked notes saved atomically; one meeting note + participant person notes + action items | `capture_note()` + `sb_capture_batch` per-note try/except pattern; `relationships` table for co-captured links; `action_items` table for extracted items |
| CAP-03 | `sb_capture_smart` dedup-aware: before proposing new notes, checks near-duplicates; merges or proposes link | `check_capture_dedup()` already implemented; `find_similar()` at threshold 0.8; new three-path logic needed |
| CAP-04 | After every `sb_capture` or `sb_capture_smart`, MCP response includes ≤3 semantically related dormant notes (>30 days since access) | `find_similar()` in intelligence.py + `note_embeddings` table; `updated_at` column for dormant filter; new `_find_dormant_related()` helper needed |
| CAP-05 | Near-duplicate confirmed saved → `similar` relationship created automatically | `relationships` table with `rel_type='similar'`; `PRIMARY KEY (source_path, target_path, rel_type)` prevents duplicates |
| CAP-06 | After `sb_capture` + `sb_capture_batch`, intelligence hooks run async; no blocking | Background threading pattern already in `capture_note()` lines 445-477; extend to `sb_capture_batch` |
| CAP-07 | Bidirectional relationship queries: both directions from single row; `sb_link` optionally accepts `bidirectional=True` | `relationships` table schema; current queries are unidirectional; need `OR (target_path=? AND source_path=?)` pattern |
| CAP-08 | Existing note resolution: check for existing person/project notes before suggesting new; FTS5 + fuzzy match; stubs for genuinely new | `search_notes()` for FTS5 lookup; `difflib.get_close_matches()` already used in `sb_tag`; `capture_note()` for stub creation |
| CAP-09 | `sb_capture_batch` processes `links` field per note dict; after all saves, creates bidirectional relationships using slug→path resolution | `sb_capture_batch` save loop + relationship insert post-loop; slug→path lookup via DB `path LIKE '%slug%'` or title match |
| CAP-10 | `sb_capture` + `sb_capture_batch` auto-classify sensitivity via same `classify()` function; user-supplied never downgrades | `engine/classifier.py:classify()` exists but is keyword-based; CONTEXT.md requires entity-based PII detection; new `classify_smart()` needed with phone/email/SSN/hetu patterns |
| CAP-11 | `sb_capture_batch` runs dedup check per note; near-duplicates flagged in response with `dedup_warnings`; intra-batch dedup | Extend `check_capture_dedup()` call per note in batch loop; collect warnings instead of blocking |
</phase_requirements>

---

## Summary

Phase 31 replaces the minimal `sb_capture_smart` stub with a real segmentation + entity-resolution + dedup-aware multi-note save pipeline. The existing codebase provides almost all required building blocks: the segmentation logic, dedup check, similarity search, relationship table, async hook threading, and sensitivity classifier are all present. The work is integration and orchestration, not greenfield.

The most complex new work is the three-path dedup heuristic (superset/complementary/ambiguous), the entity resolution loop (FTS5 + fuzzy match against existing notes before creating stubs), bidirectional relationship query support, and wiring dormant resurfacing into every capture response. The GUI task (31-05) adds a Smart Capture modal to the React frontend using the existing Dialog/shadcn pattern.

**Primary recommendation:** Build atop existing `check_capture_dedup`, `find_similar`, `search_notes`, `capture_note`, and the async hook threading pattern already in `capture.py`. Do not hand-roll any of these; extend them.

---

## Standard Stack

### Core (all already in pyproject.toml)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `python-frontmatter` | existing | Read/write YAML frontmatter on note files | All note I/O flows through this |
| `sqlite3` (stdlib) | 3.x | Relationships, action_items, notes tables | Existing schema; no new deps |
| `sqlite-vec` | existing | KNN cosine similarity for dedup + dormant | Already used by `check_capture_dedup` + `search_semantic` |
| `difflib` (stdlib) | 3.x | Fuzzy title matching for entity resolution | Already used in `sb_tag` (cutoff 0.8) |
| `re` (stdlib) | 3.x | Structural segmentation heuristics | Already used in classifier, entities, capture |
| `threading` (stdlib) | 3.x | Async intelligence hooks post-capture | Pattern already in `capture_note()` lines 445-477 |
| `uuid` (stdlib) | 3.x | `capture_session` UUID for co-captured grouping | Stdlib, no install |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `engine.embeddings.embed_texts` | existing | Embed note text for dormant similarity | Dormant resurfacing + dedup |
| `engine.intelligence.find_similar` | existing | Cosine KNN against note_embeddings | Dormant lookup after capture |
| `engine.intelligence.extract_action_items` | existing | Post-capture async action extraction | CAP-06 hook |
| `engine.search.search_notes` | existing | FTS5 person/project lookup for entity resolution | CAP-08 |
| `engine.link_capture.fetch_link_metadata` | existing | URL → link note | URL segments in blob |
| `engine.capture.check_capture_dedup` | existing | Embedding similarity check before save | CAP-03, CAP-11 |

### No New Dependencies
Phase 31 requires zero new packages. All required capabilities exist in the current stack.

---

## Architecture Patterns

### Recommended Module Layout
```
engine/
├── segmenter.py         # NEW: two-pass segmentation logic (_segment_blob, _merge_short, etc.)
├── smart_classifier.py  # NEW: entity-based PII classify_smart(); upgrades classifier.py logic
├── capture.py           # EXTEND: _find_dormant_related(), async hook on sb_capture_batch
├── mcp_server.py        # EXTEND: sb_capture_smart (full rewrite), sb_capture_batch (links+dedup),
│                        #          sb_capture (dormant resurfacing), sb_link (bidirectional param)
frontend/src/
├── components/
│   └── SmartCaptureModal.tsx  # NEW: paste area → suggestions list → confirm → save
```

### Pattern 1: Two-Pass Segmentation
**What:** First pass splits on structural markers (markdown headings, `---`, date stamps, `RE:`, `Subject:`); second pass detects topic shifts by name-cluster changes in unstructured prose blocks.
**When to use:** Input to `sb_capture_smart`.
**Implementation notes:**
- Short segment merge: if `len(seg.strip()) < 50 or seg.count('\n') < 2` → append to previous
- Max 20 note cap: after initial split, sort by len ascending, merge smallest pairs until ≤20
- URL detection: `re.search(r'https?://', seg)` → hand off to `fetch_link_metadata()`
- Code blocks and tables: detect ` ``` ` fences and `|---|` patterns → keep inline in parent

### Pattern 2: Entity Resolution with FTS5 + Fuzzy
**What:** For each extracted person/project entity in a segment, query `search_notes(conn, name, note_type='person')` first; if hit, link to existing path. If miss, try `difflib.get_close_matches(name, all_person_titles, cutoff=0.75)`. Only create stub if both miss.
**Stub format:** `capture_note(note_type='person', title=name, body='', tags=[], people=[], ...)`
**Dedup note:** Stubs must also flow through `check_capture_dedup` to avoid duplicate stubs.

### Pattern 3: Three-Path Dedup Heuristic
**What:** When `check_capture_dedup` finds similarity ≥ threshold:
1. **Superset check:** `len(new_body) > len(existing_body) * 1.2 AND all(kw in new_body for kw in extract_key_phrases(existing_body[:200]))` → update existing, append changelog
2. **Complementary:** Does not satisfy superset → save as new note + INSERT `similar` relationship
3. **Ambiguous:** Cannot determine (e.g., both long, ≥3 near-duplicate hits) → return options dict in response without saving

**Changelog append format:**
```markdown
## Changelog
- 2026-03-20: Updated via sb_capture_smart. Previous hash: {sha256[:8}}
```

### Pattern 4: Dormant Resurfacing
**What:** After every `sb_capture` / `sb_capture_smart` save, run embedding similarity against just-saved note content, filter to `updated_at < (now - 30 days)`, return top 3.
**Implementation:**
```python
def _find_dormant_related(note_path: str, conn, limit: int = 3) -> list[dict]:
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    similar = find_similar(note_path, conn, threshold=0.5, limit=20)
    dormant = [s for s in similar
               if conn.execute("SELECT updated_at FROM notes WHERE path=?", (s["note_path"],))
                             .fetchone()[0] < cutoff]
    return dormant[:limit]
```
**Key:** threshold 0.5 (wider net for dormant vs 0.92 for dedup). Filter by `updated_at` after similarity fetch.

### Pattern 5: Bidirectional Relationship Queries
**What:** Add `OR` clause to all relationship lookups. For `sb_link(bidirectional=True)`, insert two rows.
**Example query:**
```python
conn.execute(
    "SELECT source_path, target_path, rel_type FROM relationships "
    "WHERE source_path=? OR target_path=?",
    (path, path)
)
```
**`sb_link` extension:**
```python
@mcp.tool()
def sb_link(source: str, target: str, rel_type: str = "link", bidirectional: bool = False) -> dict:
    conn.execute("INSERT OR IGNORE INTO relationships VALUES (?,?,?,?)", (source, target, rel_type, now))
    if bidirectional:
        conn.execute("INSERT OR IGNORE INTO relationships VALUES (?,?,?,?)", (target, source, rel_type, now))
```

### Pattern 6: Co-Captured Session Grouping
**What:** All notes from a single `sb_capture_smart` call share a UUID in frontmatter and get `co-captured` relationships to each other.
```python
import uuid
session_id = str(uuid.uuid4())
# In build_post():
post["capture_session"] = session_id
# After all notes saved:
for a, b in itertools.combinations(saved_paths, 2):
    conn.execute("INSERT OR IGNORE INTO relationships VALUES (?,?,'co-captured',?)", (a, b, now))
```

### Pattern 7: Sensitivity Auto-Classify (CAP-10)
**What:** New `classify_smart(body: str) -> str` function using entity-based detection (not keyword scan). The existing `classifier.py` uses keyword scanning — CONTEXT.md mandates entity-based only.

**Entity-based PII patterns to detect:**
```python
_PII_PATTERNS = [
    re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),           # SSN
    re.compile(r'\b\d{6}[+-A]\d{3}[A-Z0-9]\b'),     # Finnish hetu
    re.compile(r'\b4\d{15}\b|\b5[1-5]\d{14}\b'),     # Visa/MC card
    re.compile(r'\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b'),   # email
    re.compile(r'\+?[\d\s\-().]{10,15}'),              # phone number
]
```
**Never-downgrade rule:** `result = max(classifier_level, user_level)` where `'pii' > 'private' > 'public'`

### Anti-Patterns to Avoid
- **Blocking capture on dedup:** `check_capture_dedup` has an 8s timeout + ThreadPoolExecutor; never block the capture response path on embedding computation. If dedup check times out, proceed with save.
- **Confirm-token round-trip for smart capture:** CONTEXT.md explicitly removed this. Auto-save, return what was created.
- **Modifying `capture_note()` signature:** It's the single write path called by CLI, MCP, batch, and GUI. Add helpers alongside it, don't change its signature.
- **Intra-batch connection sharing:** Each note in `sb_capture_batch` uses the same open `conn`. Do not open multiple connections per note — the existing per-note try/except isolation pattern handles errors without connection proliferation.
- **Writing entities column before build_post:** Phase 30 established critical order: extract → build_post(merged) → write. Never reverse this.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cosine similarity lookup | Custom vector math | `find_similar()` + `vec_distance_cosine()` | sqlite-vec KNN already optimized and loaded |
| Note dedup detection | Hash comparison or Levenshtein | `check_capture_dedup()` with 8s timeout guard | Handles model unavailability, timeout, empty table gracefully |
| Fuzzy name matching | Custom edit-distance | `difflib.get_close_matches(cutoff=0.75)` | Already used in `sb_tag`; consistent across tools |
| Atomic file write | Direct `open().write()` | `write_note_atomic()` | Temp file + os.replace + DB commit in single transaction |
| FTS5 search | Direct SQL LIKE | `search_notes(conn, query, note_type=)` | Handles FTS5 phrase quoting, BM25 weights, audit log |
| Relationship inserts | Raw INSERT | `INSERT OR IGNORE INTO relationships` | PRIMARY KEY constraint prevents duplicates silently |
| Background hooks | asyncio tasks | `threading.Thread(daemon=True).start()` | FastMCP runs in its own event loop; daemon threads are the established pattern |
| Tag fuzzy matching | Custom matcher | `difflib.get_close_matches` + `sb_tag` pattern | Already battle-tested in Phase 28 |

**Key insight:** Every complex capability in this phase has a working implementation already. The work is connecting existing functions in the right order, not building new algorithms.

---

## Common Pitfalls

### Pitfall 1: FTS5 Rejects Empty Queries
**What goes wrong:** `search_notes(conn, "")` raises `sqlite3.OperationalError: fts5: syntax error near ""`.
**Why it happens:** FTS5 phrase query `""` is invalid.
**How to avoid:** Guard entity resolution: `if name.strip(): search_notes(...)`. Phase 23 decision: empty query bypasses FTS5, use direct SELECT.
**Warning signs:** OperationalError in test logs during entity resolution.

### Pitfall 2: sqlite-vec Extension Not Loaded on Every Connection
**What goes wrong:** `vec_distance_cosine` function not found on new connections.
**Why it happens:** `conn.enable_load_extension(True); sqlite_vec.load(conn)` must be called per connection. `get_connection()` does NOT auto-load it.
**How to avoid:** Follow `search_semantic()` pattern — load extension at top of any function that uses vec functions.

### Pitfall 3: Entities Column Write Order
**What goes wrong:** `people` frontmatter field is empty despite entity extraction succeeding.
**Why it happens:** `build_post()` is called BEFORE `extract_entities()`, so `merged_people` is never included in the post.
**How to avoid:** Phase 30 locked order: extract → merge → build_post(merged). Enforce this in segmenter when building per-segment posts.

### Pitfall 4: `conn.row_factory` Not Set Globally
**What goes wrong:** `dict(row)` fails with `TypeError` when accessing named columns.
**Why it happens:** `get_connection()` does NOT set `row_factory=sqlite3.Row`. Phase 28 decision: set it locally per function.
**How to avoid:** Set `conn.row_factory = sqlite3.Row` at the top of any function that needs dict-like row access.

### Pitfall 5: Background Thread Holds Open Connection
**What goes wrong:** SQLite `database is locked` errors on subsequent captures.
**Why it happens:** Background thread opens a connection and doesn't close it on exception.
**How to avoid:** Always use try/finally in daemon thread functions (see capture.py lines 451-476 — each hook uses its own connection with close in finally).

### Pitfall 6: Intra-Batch Dedup False Positives
**What goes wrong:** Two legitimately different notes in the same batch (e.g., two different person stubs) flagged as near-duplicates.
**Why it happens:** Stub notes with short/empty bodies get high embedding similarity.
**How to avoid:** Skip dedup check if `len(body.strip()) < 50` — no meaningful embedding for near-empty bodies. Document this in batch dedup logic.

### Pitfall 7: `capture_session` UUID in Frontmatter Not in DB Schema
**What goes wrong:** `capture_session` field written to frontmatter but not queryable from DB for session-based backlink queries.
**Why it happens:** `notes` table has no `capture_session` column.
**How to avoid:** Either add migration `migrate_add_capture_session_column()` or store session grouping only in frontmatter + relationships table (preferred — avoids schema change and `co-captured` relationships are queryable).

### Pitfall 8: `sb_capture_smart` Token No Longer Needed — But Still Issued
**What goes wrong:** The existing stub issues a `confirm_token` in its response. New implementation is auto-save with no confirm round-trip.
**Why it happens:** Phase 28 originally had confirm-token; CONTEXT.md reversed this for Phase 31.
**How to avoid:** Remove `_issue_token()` from `sb_capture_smart`. The token in the existing stub at line 609 must be deleted. `sb_capture` and `sb_forget` still use tokens.

---

## Code Examples

Verified patterns from existing codebase:

### Async hook pattern (from capture.py lines 445-477)
```python
# Source: engine/capture.py
import threading

def _run_intelligence_hooks():
    try:
        from engine.db import get_connection as _get_conn
        from engine.intelligence import check_connections, extract_action_items
        _conn = _get_conn()
        try:
            check_connections(Path(_target_str), _conn, _brain_root)
            _conn.commit()
        finally:
            _conn.close()
    except Exception:
        pass
    try:
        from engine.db import get_connection as _get_conn
        _conn2 = _get_conn()
        try:
            extract_action_items(Path(_target_str), _body, _sensitivity, _conn2)
        finally:
            _conn2.close()
    except Exception:
        pass

threading.Thread(target=_run_intelligence_hooks, daemon=True).start()
```

### Relationship insert (idempotent)
```python
# Source: engine/db.py schema
conn.execute(
    "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type, created_at) "
    "VALUES (?, ?, ?, ?)",
    (source, target, rel_type, datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
)
```

### FTS5 + fuzzy entity resolution pattern (from sb_tag in mcp_server.py)
```python
# Source: engine/mcp_server.py:sb_tag
import difflib
rows = conn.execute(
    "SELECT path, title FROM notes WHERE type IN ('person', 'people') LIMIT 200"
).fetchall()
all_titles = [r[1] for r in rows]
matches = difflib.get_close_matches(name, all_titles, n=1, cutoff=0.75)
if matches:
    # Link to existing note
    existing_path = dict(rows)[matches[0]]
else:
    # Create stub
    capture_note(note_type='person', title=name, body='', ...)
```

### Dedup check with timeout guard (from capture.py)
```python
# Source: engine/capture.py:check_capture_dedup
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
try:
    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(_run_dedup)
        return future.result(timeout=8)
except (FuturesTimeout, Exception):
    return []  # Best-effort — never blocks capture
```

### find_similar (from intelligence.py)
```python
# Source: engine/intelligence.py:find_similar
def find_similar(note_path: str, conn, threshold: float = 0.8, limit: int = 3) -> list[dict]:
    row = conn.execute("SELECT embedding FROM note_embeddings WHERE note_path=?", (note_path,)).fetchone()
    if not row or not row[0]:
        return []
    # ... sqlite-vec KNN query ...
    return [{"note_path": r[0], "similarity": 1.0 - r[1]} for r in rows]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `sb_capture_smart` returns suggestions, needs confirm token | Auto-save, no confirm round-trip | Phase 31 CONTEXT.md decision | Simpler MCP caller flow; all N notes saved atomically |
| PII classify via keyword scan in `classifier.py` | Entity-based detection (phone, email, hetu, SSN, CC) per-segment | Phase 31 | Fewer false positives on "health" keyword; more precise |
| Body-mention fallback in `note_meta()` for people | `people` column as single source of truth | Phase 30 | Entity resolution must use `people` column, not body scan |
| Unidirectional relationship queries | Both-direction OR queries | Phase 31 | `person_context`, backlinks panel, connections all become consistent |
| Dedup blocks capture until user confirms | Three-path automatic resolution | Phase 31 | No interactive round-trip in MCP context |

**Deprecated/outdated:**
- `_issue_token()` in `sb_capture_smart`: remove — auto-save model doesn't need it
- `confirm_token` param on `sb_capture_smart`: remove or ignore — CONTEXT.md removed this flow
- Keyword-only PII detection in `classify()` for smart capture: new `classify_smart()` uses entity-based patterns instead

---

## Open Questions

1. **`classify_smart` vs `classify` naming**
   - What we know: `classify()` in `classifier.py` uses keyword scan. CONTEXT.md says entity-based only for Phase 31.
   - What's unclear: Should `classify_smart` replace or extend `classify`? Replacing would break existing CLI path.
   - Recommendation: Add `classify_smart(body: str) -> str` as a new function in `classifier.py`. Wire it into `sb_capture_smart` and the new batch dedup path. Leave existing `classify()` intact for CLI.

2. **Changelog section for superset updates: hash of what?**
   - What we know: CONTEXT.md says "previous content hash" in changelog.
   - What's unclear: Hash of raw body string (fast) or of normalized content (more robust)?
   - Recommendation: `hashlib.sha256(existing_body.encode()).hexdigest()[:8]` — fast, deterministic, no normalization complexity.

3. **Intra-batch dedup: compare against already-saved batch notes or just brain?**
   - What we know: CONTEXT.md says "each note against brain AND earlier notes in same batch".
   - What's unclear: Embedding intra-batch notes requires saving them first (embeddings are in `note_embeddings`, populated by `sb-reindex` not by `capture_note`).
   - Recommendation: Intra-batch dedup compares titles only (not embeddings) using `difflib.get_close_matches` against batch title list. Cross-brain dedup uses `check_capture_dedup` as now.

4. **`capture_session` UUID: frontmatter only or also DB column?**
   - What we know: CONTEXT.md says frontmatter field + `co-captured` relationships.
   - Recommendation: Frontmatter only + relationships table. No DB migration needed. Queryable via `SELECT * FROM relationships WHERE rel_type='co-captured' AND source_path=?`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, no version change) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_capture.py tests/test_mcp.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAP-01 | `sb_capture_smart` returns typed suggestions with title/type/body/links | unit | `uv run pytest tests/test_smart_capture.py::test_capture_smart_returns_suggestions -x` | ❌ Wave 0 |
| CAP-02 | Single blob → N linked notes saved atomically with co-captured relationships | integration | `uv run pytest tests/test_smart_capture.py::test_multi_context_atomic_save -x` | ❌ Wave 0 |
| CAP-03 | Near-duplicate detected → three-path resolution: superset/complementary/ambiguous | unit | `uv run pytest tests/test_smart_capture.py::test_dedup_three_path -x` | ❌ Wave 0 |
| CAP-04 | Dormant notes (>30d) returned in capture response ≤3 | unit | `uv run pytest tests/test_smart_capture.py::test_dormant_resurfacing -x` | ❌ Wave 0 |
| CAP-05 | Near-duplicate saved → `similar` relationship created | unit | `uv run pytest tests/test_smart_capture.py::test_similar_relationship_created -x` | ❌ Wave 0 |
| CAP-06 | Intelligence hooks run async; capture response returns before hooks complete | unit | `uv run pytest tests/test_smart_capture.py::test_async_hooks_nonblocking -x` | ❌ Wave 0 |
| CAP-07 | Bidirectional relationship query returns both directions | unit | `uv run pytest tests/test_smart_capture.py::test_bidirectional_relationships -x` | ❌ Wave 0 |
| CAP-08 | Entity resolution links to existing person note instead of creating duplicate | integration | `uv run pytest tests/test_smart_capture.py::test_entity_resolution_links_existing -x` | ❌ Wave 0 |
| CAP-09 | `sb_capture_batch` processes `links` field and creates relationships post-save | unit | `uv run pytest tests/test_smart_capture.py::test_batch_links_field -x` | ❌ Wave 0 |
| CAP-10 | Sensitivity auto-classify detects phone/email/hetu; never-downgrade rule enforced | unit | `uv run pytest tests/test_smart_capture.py::test_sensitivity_classify_smart -x` | ❌ Wave 0 |
| CAP-11 | `sb_capture_batch` flags near-duplicates as `dedup_warnings` without blocking | unit | `uv run pytest tests/test_smart_capture.py::test_batch_dedup_warnings -x` | ❌ Wave 0 |
| PERF | `sb_capture_smart` with 500-note synthetic brain completes in <5s | perf | `uv run pytest tests/test_smart_capture.py::test_smart_capture_performance -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_smart_capture.py tests/test_mcp.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_smart_capture.py` — all 12 test stubs above (xfail(strict=False) pattern)
- [ ] `tests/conftest.py` — check if `client` fixture + `tmp_brain` fixture cover isolation needs (existing pattern: patch `engine.db.DB_PATH` + `engine.paths.DB_PATH` + `BRAIN_PATH` env var)
- [ ] `engine/segmenter.py` — new module, needs `__init__` import registration in `pyproject.toml` if added as entry point (likely not needed)

*(Existing test infrastructure: `tests/` directory, `pytest` via `uv run`, `xfail(strict=False)` stub pattern, `tmp_path` + monkeypatch fixtures — all available.)*

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `engine/mcp_server.py`, `engine/capture.py`, `engine/intelligence.py`, `engine/search.py`, `engine/entities.py`, `engine/classifier.py`, `engine/db.py`
- `.planning/phases/31-smart-capture-multi-context-intelligence/31-CONTEXT.md` — locked decisions
- `.planning/STATE.md` — accumulated patterns and known gotchas

### Secondary (MEDIUM confidence)
- `difflib.get_close_matches` stdlib docs — fuzzy matching API confirmed in Python 3.13
- `uuid.uuid4()` stdlib — confirmed in Python 3.13

### Tertiary (LOW confidence)
- None — all findings from direct code inspection

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed present and in use
- Architecture: HIGH — patterns traced from existing working code
- Pitfalls: HIGH — sourced from STATE.md accumulated decisions and code-level inspection
- Test map: HIGH — follows established xfail(strict=False) stub pattern used in phases 26-30

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable codebase; no external deps to track)
