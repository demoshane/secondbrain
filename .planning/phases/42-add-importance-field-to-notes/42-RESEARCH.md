# Phase 42: Add Importance Field to Notes — Research

**Researched:** 2026-03-28
**Domain:** Full-stack feature addition — SQLite schema, Python capture/edit pipeline, MCP tools, Flask API, React frontend
**Confidence:** HIGH — all findings from direct source inspection; zero external dependencies

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** 3-tier categorical enum: `low` / `medium` / `high`
- **D-02:** Default value: `medium` — applied to new notes and existing notes via migration
- **D-03:** DB column: `importance TEXT NOT NULL DEFAULT 'medium'` — follow the existing idempotent `ALTER TABLE ADD COLUMN` migration pattern
- **D-04:** Field name: `importance` (matches DB column name)
- **D-05:** Written into YAML frontmatter by `build_post()` in `engine/capture.py`
- **D-06:** All existing notes on disk do NOT need rewriting — `medium` default is sufficient; frontmatter is added at next edit
- **D-07:** `sb_capture` and `sb_capture_batch` — accept optional `importance` param (default: `medium`)
- **D-08:** `sb_capture_smart` — LLM should infer importance from content; extend the existing classifier prompt to return an `importance` field alongside `type`, `title`, `tags`. User can override.
- **D-09:** `sb_edit` — accept optional `importance` param to update the field
- **D-10:** All capture paths write `importance` to both frontmatter and DB column
- **D-11:** All three importance levels show a badge in the sidebar note list
- **D-12:** Badge labels: `[HIGH]`, `[MED]`, `[LOW]`
- **D-13:** Badge color: use the existing Visily design tokens — high=red/accent, med=yellow/warning, low=grey/muted
- **D-14:** Badge position: before the note title (consistent with the existing `note-type-badge` pattern)
- **D-15:** Importance shown as an inline dropdown in the note detail/right panel metadata section
- **D-16:** Format: `Importance  [High ▾]` — consistent with how `Status` works on project notes
- **D-17:** Changing importance via the dropdown triggers a `PUT /notes/<path>/importance` API call and updates frontmatter on disk
- **D-18:** No ranking boost — importance does NOT affect search relevance scores
- **D-19:** Importance is available as a filter param in `sb_search` and the GUI search (filter by `importance=high`)
- **D-20:** `_apply_filters()` in `engine/search.py` extended to support `importance` filter (AND logic with existing filters)
- **D-21:** Default note list sort remains newest-first; "sort by importance (desc)" added as an opt-in sort option in the GUI

### Claude's Discretion

- Exact Tailwind color values for the three badge tiers (match Visily dark palette)
- Whether `importance-badge` reuses the existing `note-type-badge` component or is a new component
- LLM prompt wording for importance inference in `sb_capture_smart`
- API endpoint path: `PUT /notes/<path>/importance` vs patching via existing `sb_edit` route

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 42 threads a new `importance` field through all four layers of the application: database (single `ALTER TABLE ADD COLUMN` migration), Python capture/edit pipeline (`build_post`, `capture_note`, `write_note_atomic`, `sb_edit`, `sb_capture`, `sb_capture_batch`), Flask API (new `PUT /notes/<path>/importance` endpoint; notes list to expose the field), and React frontend (sidebar badge + RightPanel dropdown + sort option).

The codebase has strong idiomatic patterns for every required change. All six precedents — the `migrate_add_*_column()` migration pattern, `build_post()` field injection, `write_note_atomic()` DB column write, `PUT /projects/<path>/status` endpoint, `_apply_filters()` AND-logic filter, and `note-type-badge.tsx` badge component — are clean and consistent, making this a straightforward feature addition with low risk of regressions.

The one discretionary design decision with real implementation consequence is whether the RightPanel's importance dropdown uses `PUT /notes/<path>/importance` (preferred: a narrow endpoint like the existing status endpoint) or reuses the generic `PUT /notes/<path>` body-patch route. The status endpoint pattern is the better model since it validates the enum value server-side and fires `_broadcast`.

**Primary recommendation:** Follow every pattern already in the codebase exactly. No new patterns needed.

---

## Standard Stack

This is an internal feature addition. No new packages required.

| Layer | File | Existing Pattern to Follow |
|-------|------|---------------------------|
| DB migration | `engine/db.py` | `migrate_add_url_column()` — `try/except OperationalError: pass` style (not PRAGMA-based) |
| Frontmatter field | `engine/capture.py: build_post()` | `post["content_sensitivity"] = content_sensitivity` |
| DB write | `engine/capture.py: write_note_atomic()` | Explicit column list in `INSERT INTO notes (...)` — add `importance` here |
| Capture kwarg | `engine/capture.py: capture_note()` | `url` and `source_type` added as `*` kwargs |
| MCP tool param | `engine/mcp_server.py: sb_capture()` | Optional param with default: `sensitivity: str = "public"` |
| API endpoint | `engine/api.py` | `PUT /projects/<path>/status` — enum validation + `_broadcast` |
| Search filter | `engine/search.py: _apply_filters()` | `note_type` filter: `if note_type and r.get("type") != note_type: continue` |
| Frontend badge | `frontend/src/components/ui/badge.tsx` | `noteTypeColorMap` pattern — hex bg/text pair keyed by value |
| Frontend type | `frontend/src/types.ts: Note` | Add `importance?: string` |

---

## Architecture Patterns

### DB Migration Pattern (confirmed from source)

Two styles exist. Use the simpler `try/except` style (used for `url` column) since there is no populate-from-existing logic needed:

```python
# Source: engine/db.py: migrate_add_url_column()
def migrate_add_importance_column(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add 'importance' TEXT column to notes if absent."""
    try:
        conn.execute("ALTER TABLE notes ADD COLUMN importance TEXT NOT NULL DEFAULT 'medium'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
```

Call from `init_schema()` after existing migrations, before the index block.

### build_post() Extension Pattern

```python
# Source: engine/capture.py: build_post() — current signature has 6 params
def build_post(
    note_type: str,
    title: str,
    body: str,
    tags: list,
    people: list,
    content_sensitivity: str = "public",
    importance: str = "medium",          # NEW — add as keyword with default
) -> frontmatter.Post:
    ...
    post["importance"] = importance      # NEW — add after content_sensitivity
```

### write_note_atomic() DB Column Write

The INSERT statement in `write_note_atomic()` has an explicit column list. Add `importance` to both the column list and the values tuple:

```python
# Source: engine/capture.py lines 200-217
# Current: "(path, type, title, body, tags, people, created_at, updated_at, sensitivity, url, deadline, meeting_date)"
# Add:     importance column and post.get("importance", "medium") in VALUES
```

### capture_note() Kwarg Threading

```python
# Source: engine/capture.py: capture_note() — url and source_type are keyword-only args
def capture_note(
    ...,
    *,
    url: str | None = None,
    source_type: str | None = None,
    importance: str = "medium",    # NEW
) -> Path:
    ...
    post = build_post(..., importance=importance)
```

### API Endpoint Pattern (confirmed from source)

```python
# Source: engine/api.py lines 520-544 — PUT /projects/<path>/status
VALID_IMPORTANCE_VALUES = frozenset({"low", "medium", "high"})

@app.put("/notes/<path:note_path>/importance")
def update_note_importance(note_path):
    ...
    importance = data.get("importance", "")
    if importance not in VALID_IMPORTANCE_VALUES:
        return jsonify({"error": "importance must be low, medium, or high"}), 400
    # UPDATE notes SET importance=?, updated_at=... WHERE path=?
    # _broadcast({"type": "notes_changed"})
    # Also update frontmatter on disk (unlike status, importance must round-trip to disk)
```

**Note:** The `status` endpoint only updates the DB. For `importance`, frontmatter must also be updated (D-10 says "both frontmatter and DB column"). This means the endpoint needs to load the file, update the frontmatter field, and use `write_note_atomic(..., update=True)` — same pattern as the generic `PUT /notes/<path>` body-update route.

### _apply_filters() Extension

```python
# Source: engine/search.py lines 353-405
def _apply_filters(
    results, conn,
    person=None, tag=None, note_type=None, from_date=None, to_date=None,
    importance=None,    # NEW
) -> list[dict]:
    ...
    # In the loop:
    if importance and r.get("importance") != importance:
        continue
```

The filter works on the result dicts. Those dicts come from `search_notes()` / `search_hybrid()` which currently SELECT from the `notes` table. The `importance` column must be included in those SELECTs (or the filter falls back to a per-row DB lookup like the `person` filter does).

**Check required:** Verify whether `search_notes()` and `search_semantic()` SELECT the `importance` column. If not, the result dicts will lack it and the filter will silently not work. The safest fix is a single per-row DB lookup (same pattern as person filter) rather than assuming the SELECT covers importance.

### Frontend Badge: importance-badge Component

The existing `note-type-badge.tsx` wraps the `Badge` component which uses `noteTypeColorMap`. Importance badges should follow the same pattern as a separate, small component:

```tsx
// New file: frontend/src/components/ui/importance-badge.tsx
// Color tokens matching Visily dark palette:
// high  → red accent:    bg-[#3b1010] text-[#f87171]  (mirrors people/person badge red)
// med   → amber warning: bg-[#2d1f0a] text-[#fbbf24]
// low   → muted grey:    bg-[#1a1a1a] text-[#64748b]
```

Badge in sidebar: placed AFTER `NoteTypeBadge` (type badge is primary identity; importance is secondary).

```tsx
// Source: frontend/src/components/Sidebar.tsx line 59
<NoteTypeBadge type={note.type || 'note'} className="text-[10px] shrink-0" />
<ImportanceBadge importance={note.importance} className="text-[10px] shrink-0" />
<span className="truncate">...</span>
```

**Note:** D-14 says "before the note title" — `NoteTypeBadge` is already before the title, so importance badge goes between type badge and title, not before the type badge.

### RightPanel Importance Dropdown

The RightPanel currently has no inline metadata dropdown. The `Status` dropdown on ProjectsPage is the reference pattern. For RightPanel, importance needs:
1. A `useState<string>` to hold current importance (loaded from note meta or note object)
2. A `<select>` element styled to match dark palette
3. `onChange` fires `PUT /notes/<encoded>/importance` and updates local state

The note meta endpoint (`GET /notes/<path>/meta`) must be checked — it currently returns backlinks, people, tags. It does NOT return importance. Either:
- (a) Load importance from the `Note` object already in `NoteContext` (preferred — no extra fetch)
- (b) Add importance to the meta response

Option (a) is simpler: `NoteContext` loads notes from `GET /notes` which will include `importance` once the SQL SELECT is updated.

### Sort by Importance (GUI)

Sidebar currently renders notes in the order they arrive from `GET /notes` (newest-first). An opt-in sort by importance requires:
1. A sort toggle UI element in the sidebar header area
2. Client-side sort: `['high','medium','low']` priority order

This is pure frontend — no new API needed since all notes are already fetched.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Idempotent DB migration | Custom migration table/versioning | `try: ALTER TABLE ... except OperationalError: pass` — established pattern |
| Atomic frontmatter + DB write | Custom file write | `write_note_atomic()` with `update=True` |
| Enum validation in API | In-place if/else | `frozenset({"low","medium","high"})` membership check + 400 response |
| Badge styling | Hardcoded inline styles | `noteTypeColorMap` pattern in `badge.tsx` |

---

## Common Pitfalls

### Pitfall 1: write_note_atomic INSERT misses importance column
**What goes wrong:** `importance` added to `build_post()` but the INSERT statement in `write_note_atomic()` still has the old column list — importance is never persisted to DB even though it's in frontmatter.
**Why it happens:** The INSERT has an explicit column list that must be manually extended.
**How to avoid:** Update both `build_post()` AND the INSERT statement in `write_note_atomic()`. Test: after capture, verify `SELECT importance FROM notes WHERE path=?` returns the value.
**Warning signs:** `importance` in frontmatter but `notes.importance` is NULL or 'medium' for all notes.

### Pitfall 2: search result dicts don't include importance
**What goes wrong:** `_apply_filters(importance='high')` silently passes all notes because `r.get("importance")` returns None for all results.
**Why it happens:** `search_notes()` and related functions only SELECT specific columns; `importance` is not in their SELECT list.
**How to avoid:** Either add `importance` to the SELECT in `search_notes()` / `search_hybrid()` merge, or use a per-row DB lookup in `_apply_filters()` (like the `person` filter does). Verify with a test that filters to 'high' only.

### Pitfall 3: list_notes API doesn't expose importance to frontend
**What goes wrong:** Sidebar badge always shows nothing because `note.importance` is `undefined` in React.
**Why it happens:** `GET /notes` currently SELECTs `path, title, type, created_at, tags` — no `importance`.
**How to avoid:** Add `importance` to the SELECT in `list_notes()`. Also add `importance?: string` to the `Note` interface in `types.ts`.

### Pitfall 4: Frontmatter on disk not updated when importance changes via API
**What goes wrong:** DB has the new importance value after `PUT /notes/<path>/importance`, but re-reading the `.md` file shows the old value.
**Why it happens:** The `PUT /projects/<path>/status` endpoint (the reference pattern) only updates the DB, not the disk file. Importance must round-trip to disk (D-10).
**How to avoid:** The importance endpoint must load the file with `frontmatter.load()`, set `post["importance"] = new_value`, then call `write_note_atomic(path, post, conn, update=True)`. This is different from the status endpoint.

### Pitfall 5: sb_capture_smart importance inference prompt injection
**What goes wrong:** The LLM prompt for smart capture is extended to infer importance, but the output parser doesn't handle the new field — resulting in a KeyError or the field being silently dropped.
**Why it happens:** Smart capture uses `classify_smart` for PII (regex-only), but the note TYPE classification is in `engine/typeclassifier.py` (keyword-based, no LLM). The CONTEXT.md says "extend the existing classifier prompt" — but `typeclassifier.py` is NOT LLM-based. The smart capture flow in `mcp_server.py:sb_capture_smart` calls `segment_blob` then loops; type assignment comes from `classify_note_type()` (keyword rules).
**Key finding:** There is NO existing LLM prompt for smart capture classification. `sb_capture_smart` uses rule-based classification only (Phase 31 decision: "sb_capture_smart auto-saves (no confirm_token) — replaces Phase 28-02 stub contract"). D-08 says "extend the existing classifier prompt" — but the classifier is pure Python keyword rules, not an LLM prompt.
**How to handle:** For `sb_capture_smart`, a simple heuristic rule set (like `typeclassifier.py`) is more appropriate than adding an LLM call. Example: title/body contains URGENT/CRITICAL/P0/emergency → high; default → medium. This is consistent with the existing architecture and avoids adding an LLM dependency.

---

## Code Examples

### Full migration + init_schema call location

```python
# Source: engine/db.py: init_schema() lines 650-693
# Add after migrate_add_status_column(conn):
migrate_add_importance_column(conn)
# Add before the CREATE INDEX block
```

### Filter extension (confirmed safe pattern)

```python
# Source: engine/search.py lines 353-405
# The importance filter can query the DB directly (like person filter) if needed:
if importance:
    row = conn.execute(
        "SELECT importance FROM notes WHERE path=?", (r["path"],)
    ).fetchone()
    if not row or row[0] != importance:
        continue
```

### Frontend Note type extension

```typescript
// Source: frontend/src/types.ts line 1-11
export interface Note {
  path: string
  title: string
  type: string
  body: string
  tags: string[]
  people: string[]
  folder: string
  created_at: string
  updated_at: string
  importance?: string   // NEW — optional for backward compat
}
```

---

## Runtime State Inventory

Step 2.5: Rename/migration check — this phase adds a new field, not a rename.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | Existing notes in DB have no `importance` column | Migration adds column with DEFAULT 'medium' — no data migration needed |
| Frontmatter on disk | Existing `.md` files lack `importance` field | No rewrite needed — D-06 explicitly deferred this; field added at next edit |
| Live service config | None | — |
| OS-registered state | None | — |
| Secrets/env vars | None | — |
| Build artifacts | `uv tool install` cached wheel | `make dev` after changes |

---

## Environment Availability

Step 2.6: SKIPPED — this phase makes no use of external tools, services, or CLIs beyond the existing project stack.

---

## Validation Architecture

**nyquist_validation: true** (from config.json)

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/test_capture.py tests/test_db.py tests/test_api.py tests/test_search.py tests/test_mcp.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Behavior | Test Type | File |
|----------|-----------|------|
| `migrate_add_importance_column()` is idempotent | unit | `tests/test_db.py` |
| `build_post()` includes `importance` in frontmatter | unit | `tests/test_capture.py` |
| `write_note_atomic()` writes `importance` to DB | unit | `tests/test_capture.py` |
| `capture_note()` accepts and passes `importance` kwarg | unit | `tests/test_capture.py` |
| `sb_capture` MCP tool accepts `importance` param | unit | `tests/test_mcp.py` |
| `sb_edit` MCP tool accepts `importance` param | unit | `tests/test_mcp.py` |
| `_apply_filters(importance='high')` filters correctly | unit | `tests/test_search.py` |
| `PUT /notes/<path>/importance` updates DB + disk | integration | `tests/test_api.py` |
| `GET /notes` response includes `importance` field | integration | `tests/test_api.py` |
| Importance badge renders in sidebar | manual/visual | host GUI test |
| Importance dropdown in RightPanel updates correctly | manual/visual | host GUI test |

### Wave 0 Gaps

All existing test files exist. New tests need to be added to existing files (no new files required). Framework install: none needed.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|---|---|---|
| Status endpoint only updates DB | Importance endpoint must update DB + disk | Because frontmatter is authoritative for disk-based notes |
| `build_post()` has fixed 6-field signature | Will have 7-field signature | Keep `importance="medium"` as default to avoid breaking callers |

---

## Open Questions

1. **Does `sb_capture_smart` need LLM-based importance inference or rule-based?**
   - What we know: `typeclassifier.py` is pure keyword rules; there is no LLM prompt in the smart capture flow.
   - What's unclear: D-08 says "extend the existing classifier prompt" — there is no LLM prompt to extend.
   - Recommendation: Implement as keyword heuristics in a helper function mirroring `typeclassifier.py` style. Patterns: URGENT/CRITICAL/P0/asap/emergency → high; routine/fyi/note-to-self/low-priority → low; everything else → medium. Document this in the plan.

2. **Does `sb_capture_batch` accept `importance` per-note or as a batch-level param?**
   - What we know: `sb_capture_batch` takes `notes: list[dict]` where each dict supports `title, body, note_type, tags, people, sensitivity`.
   - Recommendation: Add `importance` as a per-note key (consistent with how other per-note fields work).

3. **Should `/api/search` POST body accept `importance` as a filter?**
   - What we know: D-19 says "available as a filter param in `sb_search` and the GUI search". The GUI search goes through `/search` POST endpoint which calls `_apply_filters()`.
   - Recommendation: Yes — add `importance = body.get("importance")` to the `/search` handler alongside the existing `person`, `tag`, `note_type` extractions.

---

## Sources

### Primary (HIGH confidence — direct source inspection)
- `/Users/tuomasleppanen/second-brain/engine/db.py` — migration patterns, `init_schema()` order
- `/Users/tuomasleppanen/second-brain/engine/capture.py` — `build_post()`, `write_note_atomic()`, `capture_note()`
- `/Users/tuomasleppanen/second-brain/engine/api.py` — `PUT /projects/<path>/status`, `GET /notes` SELECT columns
- `/Users/tuomasleppanen/second-brain/engine/search.py` — `_apply_filters()` implementation
- `/Users/tuomasleppanen/second-brain/engine/mcp_server.py` — `sb_capture`, `sb_edit`, `sb_capture_smart` implementations
- `/Users/tuomasleppanen/second-brain/frontend/src/components/ui/badge.tsx` — `noteTypeColorMap` color pattern
- `/Users/tuomasleppanen/second-brain/frontend/src/components/Sidebar.tsx` — `NoteTypeBadge` placement
- `/Users/tuomasleppanen/second-brain/frontend/src/types.ts` — `Note` interface
- `/Users/tuomasleppanen/second-brain/engine/typeclassifier.py` — classification architecture (keyword-based, no LLM)
- `/Users/tuomasleppanen/second-brain/engine/smart_classifier.py` — PII classifier (regex, no LLM)

---

## Metadata

**Confidence breakdown:**
- DB migration: HIGH — pattern directly copied from existing code
- Frontmatter/capture pipeline: HIGH — all code paths traced
- API endpoints: HIGH — status endpoint is exact template
- Search filter: HIGH — `_apply_filters` fully understood
- Frontend badge: HIGH — badge.tsx color system fully understood
- Frontend dropdown: HIGH — RightPanel structure traced
- Smart capture importance inference: MEDIUM — D-08 references "classifier prompt" that does not exist as an LLM prompt; recommendation is rule-based heuristics

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable internal codebase)
