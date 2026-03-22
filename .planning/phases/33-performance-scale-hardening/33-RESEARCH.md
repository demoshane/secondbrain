# Phase 33: Performance & Scale Hardening - Research

**Researched:** 2026-03-22
**Domain:** SQLite pagination, Python cooldown patterns, incremental file indexing, LLM token budget, SQL filter composition
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Pagination (PERF-01)**
- Default limit: 50, max: 200
- Backwards compatible: omitting limit/offset returns first 50 (not all)
- Response shape: adds `total`, `limit`, `offset` alongside existing list key
- MCP tools (sb_search, sb_files, sb_actions): add `page` param (1-based); add `page`, `total_pages`, `total` to response

**check_connections gate (PERF-02)**
- Gate type: time-based cooldown — skip check_connections if it ran within the last 30 minutes
- Storage: in-memory only (process-level timestamp); cooldown resets on process restart
- Threshold: existing similarity score 0.8 stays unchanged
- Both budget guard and cooldown apply (either can block)

**Reindex strategy (PERF-03)**
- "Unchanged" detection: file mtime vs DB `updated_at` — OS-level check, no per-file I/O
- Default behaviour: incremental by default — only reindex changed files
- Add `--full` flag for guaranteed clean state
- Orphan handling: DB rows with no corresponding file are pruned during incremental reindex
- Embeddings: incremental too — only regenerate embeddings for notes that changed

**Recap/digest token cap (PERF-04)**
- Primary strategy: time window — only include notes from last N days
- Default window: 7 days — configurable in `config.toml` (key: `recap.window_days`)
- CLI arg: `sb-recap --days N` overrides config for that call
- Body truncation: 500 chars per note (kept consistent with current)
- Hard cap: 50 notes max
- GUI settings deferred to Phase 34

**Entity filtering API (PERF-06)**
- Scope: add filter params to `sb_search` only
- Filter dimensions: `person`, `tag`, `type`, `from_date`/`to_date` — AND logic
- `person` filter: exact path OR name LIKE (same pattern as sb_person_context)
- MCP: optional params on `sb_search`
- Flask API: query params on search endpoint

### Claude's Discretion
- Exact cooldown state management (module-level variable vs class vs functools.lru_cache style)
- SQL query structure for combined AND filters (JOIN vs WHERE EXISTS vs json_each)
- config.toml key naming and section structure for recap settings
- Embedding staleness detection logic (mtime comparison approach)
- Which batched embedding worker pattern to use for PERF-05 (asyncio vs thread pool)

### Deferred Ideas (OUT OF SCOPE)
- Faceted search UI — Phase 34 GUI work
- GUI settings page for recap window_days — Phase 34
- Chrome extension capture — Phase 36
- Note count threshold for check_connections
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PERF-01 | Pagination on all list endpoints + MCP page param | SQL COUNT(*) + LIMIT/OFFSET; existing list endpoints in api.py and mcp_server.py identified |
| PERF-02 | check_connections cooldown gate (30-min in-memory) | Module-level timestamp pattern; existing budget_available() and check_stale_nudge() are reference patterns |
| PERF-03 | Incremental reindex using mtime detection | os.stat().st_mtime vs DB updated_at; existing reindex_brain() walkthrough shows insert-only architecture that needs mtime gating |
| PERF-04 | Recap/digest token cap via time window + config | generate_recap_on_demand() currently hardcodes 7 days / LIMIT 30; needs config.toml `[recap]` section and --days CLI arg |
| PERF-05 | Batched embedding worker (background, non-blocking) | embed_texts() already batch-capable; needs async/thread wrapper for non-blocking reindex pass |
| PERF-06 | Entity-based filtering on sb_search + Flask API | search_hybrid() currently takes query+limit only; SQL WHERE clause extension identified; json_each pattern established in Phase 30 |
| PERF-07 | sb_person_context query consolidation | Currently 4 separate DB queries per call; can be consolidated or at minimum deduplicated |
</phase_requirements>

---

## Summary

Phase 33 is backend-only performance work on a well-understood codebase. Every change targets a specific measured bottleneck: unbounded list queries, O(n) similarity scans on every capture, full-brain reindex on every `sb-reindex` call, unbounded LLM context windows, and scattered per-person DB roundtrips.

All changes are incremental additions to existing functions — no new modules needed. The risk profile is low because each fix is independently testable and the test suite already covers the affected functions (test_reindex, test_intelligence, test_search, test_mcp). The main implementation complexity is in PERF-06: composing multiple optional AND filters into safe, semgrep-clean SQL without dynamic string building.

**Primary recommendation:** Work strictly in the order of plans (33-01 through 33-05). Each plan targets specific functions with clear before/after signatures. The hardest plan is 33-04 (SQL filter composition); reference the existing tag-filter pattern in `api.py /search` (lines 164-213) which solved the same problem with note_tags junction table.

---

## Standard Stack

### Core (already installed, no new deps needed)
| Library | Purpose | Location |
|---------|---------|---------|
| SQLite3 stdlib | COUNT(*), LIMIT/OFFSET, json_each | All DB queries |
| `tomllib` stdlib (Python 3.11+) | config.toml parsing | `engine/config_loader.py` |
| `pathlib.Path.stat().st_mtime` | mtime-based staleness detection | Will be added to `engine/reindex.py` |
| `time.monotonic()` | In-process cooldown timestamp | Will be added to `engine/intelligence.py` |
| `sentence-transformers` | Embedding batches (already batch_size=32) | `engine/embeddings.py` |
| `threading.Thread` | Background embedding worker option | stdlib, no install |
| `concurrent.futures.ThreadPoolExecutor` | Alternative batched embedding worker | stdlib, no install |

### No new dependencies required for this phase.

---

## Architecture Patterns

### Pattern 1: SQL Pagination (PERF-01)

**What:** Add `LIMIT ? OFFSET ?` to all unbounded SELECT queries; add `COUNT(*)` for total.

**Current state of list_notes() in api.py:**
```python
# api.py line 143 — no limit
rows = conn.execute(
    "SELECT path, title, type, created_at, tags FROM notes ORDER BY created_at DESC"
).fetchall()
```

**After:**
```python
limit = min(int(request.args.get("limit", 50)), 200)
offset = int(request.args.get("offset", 0))
total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
rows = conn.execute(
    "SELECT path, title, type, created_at, tags FROM notes ORDER BY created_at DESC LIMIT ? OFFSET ?",
    (limit, offset),
).fetchall()
return jsonify({"notes": notes, "total": total, "limit": limit, "offset": offset})
```

**MCP 1-based page convention:**
```python
# page=1 → offset=0, page=2 → offset=limit, etc.
page = max(1, page)
offset = (page - 1) * limit
total_pages = math.ceil(total / limit) if limit else 1
```

**Affected endpoints:**
- `GET /notes` — add limit/offset query params
- `GET /notes/search` or `POST /search` — already has results list, add pagination
- `GET /notes/actions` (if exists) — check api.py
- MCP `sb_search`, `sb_files`, `sb_actions` — add `page` param

### Pattern 2: Module-level Cooldown (PERF-02)

**What:** A process-global monotonic timestamp. Two guard patterns already exist in intelligence.py — use the same `_load_state()` / `_save_state()` flow but keep cooldown in-memory (not persisted).

**Recommended:** module-level variable is the simplest correct answer; class/lru_cache is over-engineering for a single timestamp.

```python
# engine/intelligence.py — add at module level
import time
_check_connections_last_run: float = 0.0  # monotonic seconds
_CHECK_CONNECTIONS_COOLDOWN_SECS: int = 30 * 60  # 30 minutes

def check_connections(note_path, conn, brain_root):
    global _check_connections_last_run
    now = time.monotonic()
    if (now - _check_connections_last_run) < _CHECK_CONNECTIONS_COOLDOWN_SECS:
        return  # cooldown active
    if not budget_available(conn):
        return  # daily budget gate also applies
    # ... existing logic ...
    _check_connections_last_run = time.monotonic()
```

**Test pattern:** monkeypatch `engine.intelligence._check_connections_last_run` to a past/future value.

### Pattern 3: Incremental Reindex via mtime (PERF-03)

**Current:** `reindex_brain()` reads every .md file from disk on every call (lines 107-158). The `embed_pass()` already uses content hash to skip unchanged embeddings. The gap is in the note upsert pass — every file gets `frontmatter.load()` regardless.

**Fix strategy:**
1. Before calling `frontmatter.load()`, check `md_path.stat().st_mtime`
2. Compare against `notes.updated_at` stored in DB (already populated as `utcnow()` on upsert)
3. Convert DB `updated_at` ISO string to a comparable timestamp

**Important caveat:** DB `updated_at` is set to `utcnow()` on every upsert, not to the file's mtime. So the comparison is: "has the file been touched since we last indexed it?" For correctness, the incremental check should use the mtime of the file versus the timestamp stored when we last indexed it. The simplest reliable approach: store the file mtime in DB as a new column OR compare file mtime against DB `updated_at` (will work if we only write DB `updated_at` when file actually changed — which we do via the CONTEXT.md decision).

**Recommended:** Use `Path.stat().st_mtime_ns` (nanoseconds, avoids float precision issues) stored as INTEGER in DB. Add column `file_mtime_ns INTEGER` to notes table via migration.

**Alternative (simpler, good enough):** Convert DB `updated_at` to a timestamp and compare directly to file mtime. Will have false positives (DB written more recently than file), but that just means a few extra re-reads — acceptable.

**Orphan pruning:** already done in current `reindex_brain()` (lines 164-177). Works correctly for incremental too since `disk_paths` set is always built.

### Pattern 4: Config-driven Recap Window (PERF-04)

**Current `generate_recap_on_demand()`:** hardcodes `'-7 days'` and `LIMIT 30` (lines 526-529).

**Config structure to add to config.toml:**
```toml
[recap]
window_days = 7
max_notes = 50
body_truncation = 500
```

**Load pattern** (consistent with existing `load_config()` usage):
```python
from engine.config_loader import load_config
from engine.paths import CONFIG_PATH
cfg = load_config(CONFIG_PATH)
window_days = cfg.get("recap", {}).get("window_days", 7)
max_notes = cfg.get("recap", {}).get("max_notes", 50)
```

**CLI override for `sb-recap --days N`:** already has `argparse` in `recap_main()`. Add `--days` arg, pass through to `generate_recap_on_demand()` (add `window_days` parameter).

### Pattern 5: SQL AND-filter Composition (PERF-06)

**The challenge:** Multiple optional filter params (person, tag, type, from_date, to_date) that must compose with AND logic without dynamic SQL string building (semgrep requirement).

**Reference implementation:** The existing `POST /search` in `api.py` (lines 164-213) handles tag+query combinations using post-filter in Python. For PERF-06 we can do the same: run `search_hybrid()` first, then Python-filter results by person/tag/type/date. This avoids all dynamic SQL.

**Python post-filter approach (recommended for correctness + semgrep safety):**
```python
def _apply_filters(results, conn, person=None, tag=None, note_type=None, from_date=None, to_date=None):
    if not any([person, tag, note_type, from_date, to_date]):
        return results
    filtered = []
    for r in results:
        path = r["path"]
        if note_type and r.get("type") != note_type:
            continue
        if from_date and r.get("created_at", "") < from_date:
            continue
        if to_date and r.get("created_at", "") > to_date + "T23:59:59":
            continue
        if tag:
            tags_set = {row[0] for row in conn.execute(
                "SELECT tag FROM note_tags WHERE note_path=?", (path,)
            ).fetchall()}
            if tag not in tags_set:
                continue
        if person:
            people = conn.execute(
                "SELECT people FROM notes WHERE path=?", (path,)
            ).fetchone()
            # json_each-style check in Python
            import json
            plist = json.loads(people[0] or "[]") if people else []
            if not any(person in p or p == person for p in plist):
                continue
        filtered.append(r)
    return filtered
```

**Note:** `type` filter can be pushed into `search_notes()` (already supports `note_type` param). Push what you can into SQL, Python-filter the rest.

### Pattern 6: PERF-05 Background Embedding Worker

**Context decision says:** Claude's discretion on asyncio vs thread pool.

**Recommendation: `concurrent.futures.ThreadPoolExecutor` with max_workers=1**

- Sentence-transformers releases the GIL during encode (numpy operations)
- One worker prevents multiple concurrent embedding batches fighting for RAM
- Works in the same process without asyncio/event loop complexity
- Already used in Flask context (threading=True is Flask's default)

```python
# engine/reindex.py — wrap embed_pass in background thread
from concurrent.futures import ThreadPoolExecutor
_embed_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sb-embed")

def embed_pass_async(conn_factory, provider, batch_size, force=False):
    """Submit embed_pass to background thread. Returns Future."""
    def _run():
        conn = conn_factory()
        try:
            return embed_pass(conn, provider, batch_size, force)
        finally:
            conn.close()
    return _embed_executor.submit(_run)
```

**Caution:** The worker needs its own connection (SQLite connections are not thread-safe). Pass a `conn_factory` callable, not a live connection.

### Pattern 7: sb_person_context Query Consolidation (PERF-07)

**Current:** 4 separate queries (person row, meetings, mentions, actions). Each is a full table scan over notes with json_each.

**Consolidation options:**
1. Merge meetings + mentions into a single query with type discrimination — saves 1 roundtrip
2. Use `WITH` CTE to resolve person once and reuse across sub-queries
3. Add indexes on `notes.type` and `note_people.person` (Phase 32 added note_people junction table)

**Best option given Phase 32 added `note_people` junction table:**
```sql
-- Use note_people for meetings/mentions instead of json_each on every row
SELECT n.path, n.title, n.type, n.created_at
FROM note_people np
JOIN notes n ON np.note_path = n.path
WHERE np.person = ? OR np.person LIKE ?
ORDER BY n.created_at DESC
```

This replaces the `json_each(COALESCE(n.people, '[]'))` fan-out scan with an indexed lookup, provided `note_people` is kept in sync (Phase 32-03 added this table; Phase 32-06 ensures write-back correctness).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cursor-based pagination | Custom cursor serialization | Simple LIMIT/OFFSET | Scale target is thousands, not millions; offset is fine |
| Persistent cooldown across restarts | Write cooldown to STATE_PATH | In-memory monotonic timestamp | CONTEXT.md decision: reset on restart is acceptable |
| Dynamic SQL for AND filters | String-building WHERE clauses | Python post-filter + existing parameterised SQL | Semgrep blocks dynamic SQL; post-filter is correct for post-RRF results anyway |
| LLM token counting | tiktoken or tokenizer | Character truncation at 500 chars/note + note count cap | Sufficient approximation; avoids tokenizer dependency |
| Async event loop for embeddings | asyncio + aiofiles | ThreadPoolExecutor(max_workers=1) | Sentence-transformers is not async-native; thread is simpler and correct |

---

## Common Pitfalls

### Pitfall 1: Pagination breaks MCP tool return type
**What goes wrong:** MCP tools currently return `list[dict]`. Adding pagination changes the return to a dict with a nested list. FastMCP infers return schema from type hint — if you change `-> list[dict]` to `-> dict`, all callers that iterate the result directly will break.
**How to avoid:** Change return type to `dict` and document that results are in a key (e.g., `{"results": [...], "total": N}`). Update any callers in tests. The CONTEXT.md decision specifies the shape explicitly.

### Pitfall 2: COUNT(*) + LIMIT/OFFSET race condition
**What goes wrong:** `COUNT(*)` query and the paginated SELECT are two separate transactions. Between them, a new note could be captured — total could be stale.
**How to avoid:** Acceptable for this use case (not an e-commerce cart). Document that `total` is approximate. Do not wrap in a transaction — it would hold a read lock unnecessarily.

### Pitfall 3: mtime comparison with timezone-naive DB timestamps
**What goes wrong:** `notes.updated_at` is stored as `datetime.utcnow().isoformat()` (no timezone). `Path.stat().st_mtime` is a Unix timestamp in local time on macOS. Direct comparison will be wrong if the user is not in UTC.
**How to avoid:** Convert file mtime to UTC: `datetime.utcfromtimestamp(mtime)`. Compare against the DB ISO string parsed as UTC. Or store `st_mtime_ns` as INTEGER and compare as integers.

### Pitfall 4: check_connections cooldown test isolation
**What goes wrong:** Module-level `_check_connections_last_run` is global state. Tests that call `check_connections()` will affect each other if run in the same process.
**How to avoid:** In test teardown (or via monkeypatch fixture), reset `engine.intelligence._check_connections_last_run = 0.0` after each test.

### Pitfall 5: Incremental reindex misses entity/people changes
**What goes wrong:** If a user manually edits frontmatter (people, tags) in a file without changing the body, the file mtime changes but the content hash does not. The incremental pass re-indexes the file but `embed_pass` skips it (hash unchanged). This is correct behaviour, but the operator must understand that `--full` is needed to force embedding regeneration even when hash is unchanged.
**How to avoid:** Document clearly in --help. The `--full` flag already triggers `force=True` in `embed_pass()`.

### Pitfall 6: search_hybrid filter params need to thread through all three search modes
**What goes wrong:** `search_hybrid` calls `search_notes` and `search_semantic` internally. If filters are added to `search_hybrid`'s signature but only applied via post-filter after RRF merge, they work correctly. If instead you try to push filters into `search_notes` and `search_semantic`, you need to update both call sites inside `search_hybrid`, and the semantic search has no SQL filter capability (it's KNN vector distance).
**How to avoid:** Apply all filters as Python post-filter after `_rrf_merge()`. Push `note_type` filter into `search_notes()` only (it already supports `note_type` param). Do not attempt to filter inside `search_semantic()`.

---

## Code Examples

### Existing budget guard pattern to extend for cooldown
```python
# engine/intelligence.py lines 70-84
def budget_available(conn) -> bool:
    """True if vault has 20+ notes and no offer has been made today."""
    note_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    if note_count < VAULT_GATE:
        return False
    state = _load_state()
    today = datetime.date.today().isoformat()
    return state.get("last_offer_date") != today
```

### Existing json_each people lookup pattern (Phase 30)
```python
# engine/mcp_server.py line 1163
meeting_rows = conn.execute("""
    SELECT DISTINCT n.path, n.title, n.created_at
    FROM notes n, json_each(COALESCE(n.people, '[]')) pe
    WHERE (pe.value = ? OR pe.value LIKE ?)
      AND n.type = 'meeting'
    ORDER BY n.created_at DESC
""", (person_path, f"%{person_title}%")).fetchall()
```

### Existing embed_pass staleness detection pattern
```python
# engine/reindex.py lines 38-49 — content hash already used
existing = {
    r[0]: r[1]
    for r in conn.execute("SELECT note_path, content_hash FROM note_embeddings").fetchall()
}
for path, body in rows:
    h = hashlib.sha256(body.encode()).hexdigest()
    if force or existing.get(path) != h:
        to_embed.append((path, body, h))
```

### Existing tag filter post-processing (safe SQL pattern)
```python
# engine/api.py lines 200-211 — post-filter after FTS
if tags_filter:
    tags_set = set(tags_filter)
    filtered = []
    for r in results:
        note_tags_rows = conn.execute(
            "SELECT tag FROM note_tags WHERE note_path=?", (r["path"],)
        ).fetchall()
        note_tag_set = {nt["tag"] for nt in note_tags_rows}
        if tags_set.issubset(note_tag_set):
            filtered.append(r)
    results = filtered
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact for Phase 33 |
|--------------|------------------|--------------|---------------------|
| Body-scan for people | `json_each(people)` column lookup | Phase 30 | Person filter in PERF-06 uses this pattern directly |
| Tags as JSON TEXT full scan | `note_tags` junction table | Phase 32-03 | Tag filter in PERF-06 can use `note_tags` for indexed lookup |
| `note_people` populated only at capture | `note_people` kept in sync via Phase 32-06 | Phase 32 | PERF-07 can use `note_people` as faster alternative to json_each scan |
| `sb-reindex` full rebuild always | Incremental by default (Phase 33) | This phase | Reduces reindex from O(n) I/O to O(changed) |

---

## Open Questions

1. **Does Phase 32 `note_people` table actually get written during `reindex_brain()`?**
   - What we know: Phase 32-06 added people-graph correctness work and note_people junction table. `reindex_brain()` entities pass writes to `note_people` (line 201-205), but only when `--entities` flag is passed.
   - What's unclear: Is `note_people` populated for all notes after Phase 32, or only for notes reindexed with `--entities`?
   - Recommendation: PERF-07 planner should check whether to use `note_people` directly or fall back to `json_each`. Both are semgrep-safe. If `note_people` is unreliable, keep json_each — the performance gain from PERF-07 is secondary.

2. **Is there a `GET /notes/actions` Flask endpoint, or only MCP `sb_actions`?**
   - What we know: `api.py` imports `list_actions` from intelligence.py. Did not find a `/notes/actions` route in the first 220 lines of api.py.
   - Recommendation: 33-01 planner should grep for action-related routes in api.py before assuming the endpoint needs creating vs pagination-extending.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, no install needed) |
| Config file | none — run via `uv run pytest` |
| Quick run command | `uv run pytest tests/test_intelligence.py tests/test_reindex.py tests/test_search.py tests/test_mcp.py -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERF-01 | GET /notes returns paginated response with total/limit/offset | unit | `uv run pytest tests/test_api.py -k pagination -x` | ❌ Wave 0 |
| PERF-01 | sb_search/sb_files/sb_actions accept page param, return total_pages | unit | `uv run pytest tests/test_mcp.py -k pagination -x` | ❌ Wave 0 |
| PERF-02 | check_connections skips if cooldown active, runs if elapsed | unit | `uv run pytest tests/test_intelligence.py -k cooldown -x` | ❌ Wave 0 |
| PERF-03 | reindex_brain incremental only processes changed files | unit | `uv run pytest tests/test_reindex.py -k incremental -x` | ❌ Wave 0 |
| PERF-03 | reindex_brain --full processes all files | unit | `uv run pytest tests/test_reindex.py -k full -x` | ✅ (test_reindex.py exists) |
| PERF-04 | generate_recap_on_demand respects window_days from config | unit | `uv run pytest tests/test_intelligence.py -k window_days -x` | ❌ Wave 0 |
| PERF-04 | sb-recap --days N overrides config | unit | `uv run pytest tests/test_intelligence.py -k recap_days -x` | ❌ Wave 0 |
| PERF-05 | embed_pass_async returns Future, does not block main thread | unit | `uv run pytest tests/test_reindex.py -k embed_async -x` | ❌ Wave 0 |
| PERF-06 | sb_search with person/tag/type/date filters returns filtered results | unit | `uv run pytest tests/test_search.py -k filter -x` | ❌ Wave 0 |
| PERF-07 | sb_person_context returns correct data using consolidated query | unit | `uv run pytest tests/test_mcp.py -k person_context -x` | ✅ (test_mcp.py exists) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_intelligence.py tests/test_reindex.py tests/test_search.py tests/test_mcp.py tests/test_api.py -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Test stubs in `tests/test_api.py` — pagination tests (PERF-01)
- [ ] Test stubs in `tests/test_mcp.py` — pagination tests (PERF-01)
- [ ] Test stubs in `tests/test_intelligence.py` — cooldown tests (PERF-02), recap window_days tests (PERF-04)
- [ ] Test stubs in `tests/test_reindex.py` — incremental reindex tests (PERF-03), embed_async test (PERF-05)
- [ ] Test stubs in `tests/test_search.py` — entity filter tests (PERF-06)

---

## Sources

### Primary (HIGH confidence)
- Direct code read: `engine/intelligence.py` — budget_available, check_connections, generate_recap_on_demand, recap_main
- Direct code read: `engine/reindex.py` — reindex_brain, embed_pass (full file)
- Direct code read: `engine/search.py` — search_notes, search_hybrid, search_semantic (full file)
- Direct code read: `engine/api.py` — list_notes, search endpoint (lines 138-214)
- Direct code read: `engine/mcp_server.py` — sb_search, sb_files, sb_actions, sb_person_context
- Direct code read: `engine/embeddings.py` — embed_texts (full file)
- Direct code read: `engine/config_loader.py` — load_config, DEFAULT_CONFIG
- Direct code read: `.planning/phases/33-performance-scale-hardening/33-CONTEXT.md` — all locked decisions

### Secondary (MEDIUM confidence)
- Python stdlib `time.monotonic()` — appropriate for process-lifetime cooldown (no drift, no timezone issues)
- Python `concurrent.futures.ThreadPoolExecutor` — thread-safe, GIL-releasing for numpy ops
- SQLite `LIMIT/OFFSET` pagination — well-established, appropriate for thousands-of-rows scale

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already in use; no new dependencies
- Architecture patterns: HIGH — based on direct code reading of production files
- Pitfalls: HIGH — derived from existing code patterns and known SQLite/threading constraints

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable codebase)
