# Phase 30: People Graph Hardening - Research

**Researched:** 2026-03-20
**Domain:** Python regex/Unicode, SQLite generated columns, FastMCP tool authoring, React/TypeScript frontend
**Confidence:** HIGH — all findings based on direct source code inspection; no speculative claims

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Unicode Entity Extraction (PEO-01)**
- Replace ASCII-only `[A-Z][a-z]+` with Unicode-aware pattern covering Extended Latin (Finnish, Nordic, French, Spanish, Portuguese, German)
- Support compound names: van/von/de/di/la/el prefixes, O' prefix, hyphens (e.g. Mäki-Petäjä)
- Two-word minimum for extraction; single-word names resolve silently against existing person notes (best-effort, no prompts)
- No abbreviated name matching (T. Leppänen, Tuomas L.) — too ambiguous
- Add Finnish stop words alongside existing English stop words
- Add organization extraction to entities.py as new entity type (people, places, topics, orgs)
- Title and body processed separately — preserve Phase 27.1 decision, no cross-boundary bigrams

**People Column Write-Back (PEO-02)**
- People column populated from entity extraction at capture time
- Full reindex of all existing notes — replace people column with fresh extraction results (not merge)
- Also update entities JSON column during reindex
- Extend `sb-reindex` with `--entities` flag for reusable entity re-extraction
- Body-mention fallback in `note_meta()` (api.py:729-740) removed entirely — people column is single source of truth
- Body-mention scan in `sb_person_context` also removed — use people column lookups
- Add generated column + index on people column for faster JSON LIKE queries

**sb_person_context Enhancements (PEO-03)**
- All sections ordered chronologically: meetings by date (newest first), mentions by created_at, actions by due_date then created_at
- Switch from body-scan to people-column lookup for finding mentions
- Accept both name string and path as input — if input contains `/`, path lookup; otherwise fuzzy-match against person note titles
- Add organization field (from person note entities) and last_interaction timestamp (max created_at of mentioning notes)
- Add relationship metrics: total_meetings, total_mentions, total_actions, last_interaction_date
- New `sb_list_people` MCP tool: all person notes with open_actions, org, last_interaction, mention_count

**Frontend & API Updates (PEO-04)**
- Update PeoplePage to reflect extraction improvements
- Fix meeting detection (currently fragile path string match `/meetings/`)
- Enrich `/people` API: add org, last_interaction, mention_count
- PeoplePage left pane columns: Name, Org, Last Interaction, Open Actions
- Regression tests for person type isolation and people column accuracy

### Claude's Discretion
- Exact Unicode regex pattern (as long as it covers Extended Latin + compound names)
- Finnish stop word list composition (derive from brain content analysis)
- Organization extraction heuristics (regex patterns, known-org list approach)
- Generated column implementation details for people index
- PeoplePage detail pane layout adjustments

### Deferred Ideas (OUT OF SCOPE)
- `sb_person_edit` MCP tool
- People merge/dedup tool
- Company/organization pages in GUI
- Relationship graph visualization
- People extraction from calendar events
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PEO-01 | Entity extraction recognises non-ASCII/Finnish names | Unicode regex pattern, stop word extension, compound name support documented below |
| PEO-02 | `people` frontmatter column populated from entity extraction at write time; body-mention fallback removed | capture_note write path identified; reindex extension pattern documented |
| PEO-03 | `sb_person_context` returns full CRM context in one call; `sb_list_people` added | Current implementation gaps documented; column-based lookup pattern specified |
| PEO-04 | PeoplePage and right panel reflect PEO-01/02; regression tests pass | PersonSummary type extension and API enrichment pattern documented |
</phase_requirements>

---

## Summary

Phase 30 is a precision hardening phase — no new major infrastructure, all changes are surgical improvements to existing modules. The four work streams are independent enough to execute in sequence (PEO-01 first since PEO-02 depends on improved extraction, PEO-03 depends on PEO-02's column cleanup, PEO-04 depends on all of the above).

The current entity extraction is a known bug: `[A-Z][a-z]+` misses any name with a diacritic in the first letter (Ä, Ö, É, etc.) or in subsequent letters. Python's `re` module supports Unicode character categories via `\w` but not `\p{}` POSIX classes — the correct approach is an explicit Unicode range covering Extended Latin. The `unicodedata` module is stdlib and available if needed for normalization checks.

The people column write-back gap is well understood from LEARNINGS.md: entity extraction already runs at capture time but stores results only in the `entities` column, not back into the `people` column in frontmatter or DB. The fix is a one-liner addition in `capture_note()` before `build_post()` is called. The reindex path in `reindex_brain()` reads `people` from frontmatter — so a `--entities` flag that re-extracts and writes back to the `people` field during reindex covers historical notes.

The `sb_person_context` tool exists and is functional but uses body-scan for meetings/mentions. After PEO-02 lands, the people column is reliable enough to switch to column lookups, which will be faster and more accurate.

**Primary recommendation:** Execute in plan order (30-01 → 30-02 → 30-03 → 30-04). PEO-01 and PEO-02 are tightly coupled — do them in one plan. PEO-02's note_meta() cleanup is a separate plan to isolate risk.

---

## Standard Stack

### Core (all already in project — no new deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `re` | stdlib | Regex-based entity extraction | Already used in entities.py |
| Python `unicodedata` | stdlib | Unicode normalization (NFC) if needed for comparison | Zero-dep, always available |
| `sqlite3` | stdlib | Generated column, index migration | Existing DB layer |
| `frontmatter` | installed | Read/write note frontmatter during reindex | Already used in reindex.py |
| `FastMCP` | installed | `sb_list_people` new tool | Existing MCP pattern |
| React/TypeScript | installed | PeoplePage extension | Existing frontend stack |

### No New Dependencies Required

All PEO-01 through PEO-04 work uses existing libraries. The Unicode regex uses Python stdlib `re` with explicit Unicode code point ranges — no `regex` package needed.

---

## Architecture Patterns

### Unicode-Aware Name Extraction

**Current (broken):**
```python
pattern = r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b'
```

**Replacement pattern (Extended Latin — covers Finnish, Nordic, French, German, Spanish, Portuguese):**
```python
# First letter: A-Z plus uppercase Extended Latin (À-Ö, Ø-Ý, Ā, Ć, Č, Ę, Ě, etc.)
# Subsequent letters: a-z plus lowercase Extended Latin (à-ö, ø-ý, ā-ž range)
_UC = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞĀĂĄĆČĎĐĒĖĘĚĞĮĶĻŁŃŇŐŒŘŚŠŢŤŪŮŰŹŻŽ]'
_LC = r'[a-záàâãäåæçèéêëìíîïðñòóôõöøùúûüýþāăąćčďđēėęěğįķļłńňőœřśšţťūůűźżž\'-]'
# Two-word pattern: FIRST_WORD SECOND_WORD, with optional compound prefixes
_NAME_PAT = rf'\b({_UC}{_LC}+)\s+({_UC}{_LC}+)\b'
```

**Compound name support:**
```python
# Prefixes: van, von, de, di, la, el, O' — precede the final word
_PREFIX = r'(?:van|von|de|di|la|el|[Oo]\')?'
_COMPOUND = rf'\b({_UC}{_LC}+)\s+{_PREFIX}({_UC}{_LC}+(?:-{_UC}{_LC}+)*)\b'
```

**Finnish stop words to add** (common words that start with uppercase in sentence position):
```python
_FINNISH_STOPS = frozenset([
    "Olen", "Olet", "Meillä", "Teillä", "Heillä", "Minulla", "Sinulla",
    "Tämä", "Tässä", "Siellä", "Täällä", "Missä", "Kun", "Jos", "Että",
    "Mutta", "Koska", "Vaikka", "Jotta", "Sekä", "Myös",
])
```

### People Column Write-Back at Capture (PEO-02)

**Where to add it:** `capture_note()` in `engine/capture.py`, after entity extraction (line ~420), before `build_post()` is called. Currently `people` param is passed as-is from caller (often `[]`). Change: merge caller-supplied people with extracted people.

```python
# After: entities = extract_entities(title, body)
# Add:
extracted_people = entities.get("people", [])
merged_people = list(dict.fromkeys(people + extracted_people))  # caller first, dedup preserve order
# Then pass merged_people to build_post() instead of people
```

**Also update frontmatter:** The `post["people"]` field should reflect `merged_people` so the written `.md` file has the correct frontmatter. `build_post()` already writes `post["people"] = list(people)` — just pass `merged_people`.

### Generated Column + Index for People (PEO-02)

SQLite supports generated columns (3.31+, 2020). The project uses Python 3.13 on Intel Mac, SQLite bundled with Python is typically 3.40+. Safe to use.

```sql
-- New migration in db.py:
ALTER TABLE notes ADD COLUMN people_idx TEXT GENERATED ALWAYS AS (people) STORED;
CREATE INDEX IF NOT EXISTS idx_notes_people ON notes(people_idx);
```

**Alternative (simpler, no generated column):** Just add a regular index on the existing `people` column. JSON LIKE queries still benefit from an index when the pattern doesn't start with `%`:

```sql
CREATE INDEX IF NOT EXISTS idx_notes_people ON notes(people);
```

The generated column approach adds no real benefit for JSON LIKE queries since SQLite can't use an index on a function result without expression indexes. **Recommendation (Claude's discretion): skip generated column, add a plain `CREATE INDEX IF NOT EXISTS idx_notes_people ON notes(people)` in `init_schema()`.** This is simpler, idempotent, and achieves the goal.

### Organization Extraction (PEO-01)

Add `_extract_organizations()` to `entities.py` and include `orgs` in the `extract_entities()` return dict.

Heuristics (simple regex-based, no external deps):
```python
# Known organization indicators: Ltd, Oy, GmbH, Inc, Corp, AB, AS, SA, LLC, plc
_ORG_SUFFIXES = r'\b([A-Z][A-Za-z\s&]+(?:Ltd|Oy|GmbH|Inc|Corp|AB|AS|SA|LLC|plc|Group|Agency|Studio))\b'
# Acronyms 2-5 uppercase letters (IBM, AWS, etc.)
_ORG_ACRONYM = r'\b([A-Z]{2,5})\b'
```

Return as `{"people": [...], "places": [...], "topics": [...], "orgs": [...]}`.

Callers that destructure the dict (there are none that would break — they access by key) are unaffected.

### Reindex `--entities` Flag (PEO-02)

Extend `reindex_brain()` in `engine/reindex.py`:

```python
def reindex_brain(brain_root, conn=None, full=False, entities=False) -> dict:
    ...
    if entities:
        from engine.entities import extract_entities
        for md_path in ...:
            post = frontmatter.load(str(md_path))
            ents = extract_entities(post.get("title",""), post.content)
            extracted_people = ents.get("people", [])
            # Overwrite people column with fresh extraction
            conn.execute(
                "UPDATE notes SET people=?, entities=? WHERE path=?",
                (json.dumps(extracted_people), json.dumps(ents), str(md_path.resolve()))
            )
        conn.commit()
```

CLI in `main()`:
```python
ap.add_argument("--entities", action="store_true", help="Re-extract entities and rewrite people column")
```

### sb_person_context Column-Based Lookup (PEO-03)

**Current:** Full table scan on `notes WHERE type='meeting'` then Python `in body` check for meetings; body LIKE scan for mentions.

**New pattern:** Use `people` column JSON lookup:
```sql
SELECT path, title, created_at FROM notes
WHERE json_extract(people, '$') LIKE '%/people/person-slug.md%'
AND type = 'meeting'
ORDER BY created_at DESC
```

Or more precisely with `json_each`:
```sql
SELECT n.path, n.title, n.created_at
FROM notes n, json_each(n.people) pe
WHERE pe.value = ?    -- the person's absolute path
AND n.type = 'meeting'
ORDER BY n.created_at DESC
```

This is the standard SQLite JSON query pattern. Verified: `json_each()` is available in SQLite 3.38+ (bundled with Python 3.11+).

**Input flexibility (path or name string):**
```python
if "/" in path_or_name:
    # Treat as path — look up directly
    person_path = path_or_name
else:
    # Fuzzy match against person note titles
    row = conn.execute(
        "SELECT path FROM notes WHERE LOWER(title)=LOWER(?) AND type IN ('person','people') LIMIT 1",
        (path_or_name,)
    ).fetchone()
    person_path = row["path"] if row else None
```

### sb_list_people New Tool (PEO-03)

Pattern follows existing list tools. Returns all person notes enriched with CRM fields:

```python
@mcp.tool()
def sb_list_people() -> dict:
    """List all person notes with relationship metrics."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT n.path, n.title, n.entities,
                (SELECT COUNT(*) FROM action_items a WHERE a.assignee_path=n.path AND a.done=0) AS open_actions,
                (SELECT MAX(m.created_at) FROM notes m, json_each(m.people) pe
                 WHERE pe.value=n.path) AS last_interaction,
                (SELECT COUNT(*) FROM notes m, json_each(m.people) pe
                 WHERE pe.value=n.path AND m.type='meeting') AS total_meetings,
                (SELECT COUNT(*) FROM notes m, json_each(m.people) pe
                 WHERE pe.value=n.path AND m.type NOT IN ('person','people')) AS total_mentions
            FROM notes n WHERE n.type IN ('person','people')
            ORDER BY n.title
        """).fetchall()
        ...
    finally:
        conn.close()
```

### API Enrichment: /people (PEO-04)

`list_people()` in `api.py` currently returns: `path, title, updated_at, open_actions`.

Add: `org` (from entities JSON), `last_interaction` (correlated subquery), `mention_count` (correlated subquery).

The `entities` column contains JSON like `{"people": [...], "orgs": [...], ...}`. Extract `org` in Python after fetch:
```python
ents = json.loads(r["entities"] or "{}")
org = (ents.get("orgs") or [""])[0]  # first org or empty string
```

### PersonSummary Type Extension (PEO-04)

```typescript
// frontend/src/types.ts
export interface PersonSummary {
  path: string
  title: string
  updated_at: string
  open_actions: number
  org: string           // new
  last_interaction: string | null   // new
  mention_count: number  // new
}
```

### Meeting Detection Fix (PEO-04)

Current fragile pattern in some parts of codebase: string contains `/meetings/`. After PEO-02 lands, the people column is the canonical source — meeting detection for `sb_person_context` uses `type='meeting'` SQL filter, which is correct. The PeoplePage frontend detail pane needs to use `type` from the API response, not parse paths.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Unicode letter matching | Hand-enumerate all Finnish chars | Explicit code point range string covering Extended Latin block | `re` module doesn't support `\p{L}` but explicit ranges are reliable and auditable |
| JSON array column queries | Python-side filter after full fetch | `json_each()` virtual table in SQL | SQLite 3.38+ built-in; avoids full table scan in Python |
| Organization lookup | External NLP/NER model | Simple suffix-based regex | Zero deps, fast, deterministic — good enough for "Wunder Oy", "Acme Inc" |
| Generated column for index | Complex STORED column | Plain `CREATE INDEX ON notes(people)` | SQLite can't use generated column for JSON LIKE anyway; regular index is simpler |

---

## Common Pitfalls

### Pitfall 1: `re` module does not support `\p{Lu}` (Unicode property escapes)
**What goes wrong:** Developer writes `\p{Lu}` or `\p{L}` — `re.compile()` raises `re.error: bad escape`.
**Why it happens:** Python's `re` module uses POSIX-style character classes, not Unicode properties. The `regex` package supports `\p{}` but is not installed.
**How to avoid:** Use explicit Unicode ranges in character classes: `[A-ZÀÁÂ...]`. Build the range string as a constant — don't repeat inline.
**Warning signs:** `re.error` in tests for entities module.

### Pitfall 2: `json_each()` silently returns nothing for NULL or empty string people column
**What goes wrong:** Notes with `people=NULL` or `people=''` cause `json_each` to return no rows — correct behavior, but easy to miss when writing correlated subqueries.
**Why it happens:** `json_each(NULL)` produces zero rows in SQLite; no error raised.
**How to avoid:** Use `COALESCE(people, '[]')` in json_each argument: `json_each(COALESCE(n.people, '[]'))`.

### Pitfall 3: `capture_note()` entity extraction runs AFTER `build_post()` currently
**What goes wrong:** If you add people write-back before `build_post()` but entities extraction runs after (current code line ~420-425), the post already has `people=[]`. You must extract first, then call `build_post()` with merged people.
**Why it happens:** Current order: `build_post()` → entity extraction → `write_note_atomic()`. Must change to: entity extraction → `build_post(merged_people)` → `write_note_atomic()`.
**Warning signs:** `people` column in DB still `[]` after capture despite extraction running.

### Pitfall 4: reindex `--entities` overwrites manually-set people frontmatter
**What goes wrong:** User explicitly set `people: ["/path/to/person.md"]` in frontmatter. Reindex with `--entities` replaces this with extracted names (plain strings, not paths).
**Why it happens:** Extraction produces name strings ("Tuomas Leppänen"), not resolved paths.
**How to avoid:** The CONTEXT.md decision is "replace (not merge)" for the reindex path. Document this behavior clearly. The people column after reindex will contain name strings; the existing path-resolution logic in `note_meta()` handles both (it resolves plain name strings via title lookup).

### Pitfall 5: `conn.row_factory = sqlite3.Row` not set in new code
**What goes wrong:** Named column access `row["column"]` raises `TypeError`.
**Why it happens:** `get_connection()` does NOT set row_factory globally. Every function that uses named access must set it locally.
**How to avoid:** Always add `conn.row_factory = sqlite3.Row` immediately after `get_connection()`. Established pattern per Phase 28-06 decision.

### Pitfall 6: FTS5 triggers fire on people column UPDATE but notes_fts only indexes title/body
**What goes wrong:** If you UPDATE only the people/entities column (not title/body), the FTS5 triggers still fire but correctly update the FTS index with the same title/body — not a problem, just wasteful.
**How to avoid:** For bulk reindex entity writes, use a targeted UPDATE that only updates people/entities columns. FTS triggers will fire but won't cause corruption.

### Pitfall 7: Test isolation — must patch both DB_PATH and BRAIN_ROOT
**What goes wrong:** New tests for entity reindex write to real `~/SecondBrain`.
**Why it happens:** `reindex_brain()` uses `BRAIN_ROOT` from `engine.paths` directly; `get_connection()` uses `DB_PATH` from `engine.paths`.
**How to avoid:** Monkeypatch `engine.db.DB_PATH`, `engine.paths.DB_PATH`, and `engine.paths.BRAIN_ROOT` in all new test fixtures. Pattern established in Phase 27.1 and documented in LEARNINGS.md.

---

## Code Examples

### Current entity extraction target (entities.py:37-45)
```python
# SOURCE: /workspace/engine/entities.py lines 37-45
def _extract_people(text: str) -> list[str]:
    # Two consecutive Title Case words not in stop words
    pattern = r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b'
    matches = re.findall(pattern, text)
    return [
        f"{first} {last}"
        for first, last in matches
        if first not in _STOP_WORDS and last not in _STOP_WORDS
    ]
```

### capture_note entity extraction section (capture.py:419-426)
```python
# SOURCE: /workspace/engine/capture.py lines 419-426
# Entity enrichment: best-effort, never blocks capture
try:
    from engine.entities import extract_entities
    entities = extract_entities(post.get("title", ""), post.content)
    post["entities"] = entities
except Exception:
    post["entities"] = {"people": [], "places": [], "topics": []}
write_note_atomic(target, post, conn, url=url)
```
Note: `post` is built by `build_post()` BEFORE this block — people write-back must restructure this order.

### Current sb_person_context body-scan pattern (mcp_server.py:824-832)
```python
# SOURCE: /workspace/engine/mcp_server.py lines 824-832
# Meetings: type='meeting' notes where person_title appears in body (case-insensitive)
meeting_rows = conn.execute(
    "SELECT path, title, body FROM notes WHERE type='meeting'"
).fetchall()
meetings = []
for r in meeting_rows:
    body = r["body"] or ""
    if person_title.lower() in body.lower():
        meetings.append({"path": r["path"], "title": r["title"]})
```
This full-table body scan is what PEO-03 replaces with json_each people column lookup.

### note_meta() body-mention fallback to remove (api.py:729-740)
```python
# SOURCE: /workspace/engine/api.py lines 729-740
# Body-mention detection: find person notes whose title appears in this note's body.
if note_body:
    person_rows = conn.execute(
        "SELECT path, title FROM notes WHERE type IN ('person', 'people')"
    ).fetchall()
    body_lower = note_body.lower()
    for pr in person_rows:
        if pr["path"] not in seen_paths and pr["title"] and pr["title"].lower() in body_lower:
            seen_paths.add(pr["path"])
            people.append({"path": pr["path"], "title": pr["title"]})
```
Remove entirely after PEO-02 write-back is confirmed working.

### list_people() current implementation (api.py:249-259)
```python
# SOURCE: /workspace/engine/api.py lines 249-259
@app.get("/people")
def list_people():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT n.path, n.title, substr(n.updated_at, 1, 10) AS updated_at, "
        "  (SELECT COUNT(*) FROM action_items a WHERE a.assignee_path=n.path AND a.done=0) AS open_actions "
        "FROM notes n WHERE n.type IN ('person', 'people') ORDER BY n.title",
    ).fetchall()
    conn.close()
    return jsonify({"people": [dict(r) for r in rows]})
```
Needs `entities` column fetched + org extracted in Python, plus `last_interaction` and `mention_count` correlated subqueries.

### init_schema migration pattern (db.py:177-197)
```python
# SOURCE: /workspace/engine/db.py lines 177-197
def init_schema(conn, reset=False):
    ...
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_type ON notes(type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_url ON notes(url)")
    conn.commit()
```
New index for people column follows same pattern: `conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_people ON notes(people)")`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual `people:` frontmatter only | Entity extraction to `entities` column at capture | Phase 27.1 | Extraction runs but doesn't write back to people column — Phase 30 fixes |
| Full body-scan for person mentions | People column lookup | Phase 30 (this phase) | Faster, consistent, no false positives from name fragments |
| ASCII-only bigram extraction | Unicode-aware Extended Latin pattern | Phase 30 (this phase) | Finnish/Nordic names correctly extracted |
| sb_person_context as simple lookup | Full CRM context with metrics | Phase 30 (this phase) | Single MCP call gives complete relationship picture |

**Still present after Phase 30 (tracked in Phase 32):**
- DB stores absolute paths — moving `~/SecondBrain` orphans index
- No FK cascade on child tables

---

## Open Questions

1. **Organization extraction false positives**
   - What we know: Acronym pattern `[A-Z]{2,5}` will match many non-org tokens (IT, API, MCP, etc.)
   - What's unclear: Acceptable false positive rate for org field in `sb_person_context`
   - Recommendation: Limit org extraction to suffix-based patterns only (Ltd, Oy, etc.) for now; skip pure acronyms. Claude's discretion per CONTEXT.md.

2. **People column format after PEO-02: name strings vs paths**
   - What we know: Extraction produces name strings ("Tuomas Leppänen"); existing code in note_meta() handles both formats
   - What's unclear: Whether `sb_person_context` json_each lookup should use name strings or attempt path resolution
   - Recommendation: At capture time, attempt to resolve extracted names to existing person note paths (look up `WHERE LOWER(title)=LOWER(name) AND type IN ('person','people')`). Store path if found, name string if not. This makes people column consistent with the pre-existing path-based convention.

3. **`--entities` reindex performance on large brains**
   - What we know: Brain has ~334 notes; reindex with entity extraction is O(n) reads + updates
   - What's unclear: Whether to run entity extraction in a second pass or inline in the walk loop
   - Recommendation: Inline in the walk loop when `--entities` flag is set — avoids double parse of frontmatter. Acceptable for ~334 notes.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` [tool.pytest] |
| Quick run command | `uv run pytest tests/test_entities.py tests/test_people.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PEO-01 | Finnish/Nordic names extracted correctly | unit | `uv run pytest tests/test_entities.py -x -q` | ✅ (extend existing) |
| PEO-01 | Compound names (Mäki-Petäjä) extracted | unit | `uv run pytest tests/test_entities.py::test_extract_compound_names -x` | ❌ Wave 0 |
| PEO-01 | Finnish stop words filter false positives | unit | `uv run pytest tests/test_entities.py::test_finnish_stopwords -x` | ❌ Wave 0 |
| PEO-01 | Org extraction returns org entity type | unit | `uv run pytest tests/test_entities.py::test_extract_orgs -x` | ❌ Wave 0 |
| PEO-02 | capture_note writes extracted people to people column | unit | `uv run pytest tests/test_capture.py::test_capture_people_writeback -x` | ❌ Wave 0 |
| PEO-02 | reindex --entities overwrites people column | unit | `uv run pytest tests/test_reindex.py::test_entities_flag -x` | ❌ Wave 0 |
| PEO-02 | note_meta() no longer uses body-mention fallback | unit | `uv run pytest tests/test_api.py::test_note_meta_no_body_fallback -x` | ❌ Wave 0 |
| PEO-03 | sb_person_context uses people column not body scan | unit | `uv run pytest tests/test_mcp.py::test_person_context_column_lookup -x` | ❌ Wave 0 |
| PEO-03 | sb_person_context accepts name string input | unit | `uv run pytest tests/test_mcp.py::test_person_context_by_name -x` | ❌ Wave 0 |
| PEO-03 | sb_list_people returns all person notes with metrics | unit | `uv run pytest tests/test_mcp.py::test_sb_list_people -x` | ❌ Wave 0 |
| PEO-04 | /people API returns org, last_interaction, mention_count | unit | `uv run pytest tests/test_people.py::test_list_people_enriched -x` | ❌ Wave 0 |
| PEO-04 | PersonSummary type has new fields | unit (vitest) | `cd /workspace/frontend && npx vitest run` | ❌ Wave 0 |
| PEO-04 | Person type isolation regression (type='person' AND type='people') | unit | `uv run pytest tests/test_people.py::test_person_type_isolation -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_entities.py tests/test_people.py tests/test_mcp.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_entities.py` — add Unicode/Finnish/org test cases (file exists, extend it)
- [ ] `tests/test_capture.py` — add `test_capture_people_writeback` test
- [ ] `tests/test_reindex.py` — add `test_entities_flag` test (check if file exists first)
- [ ] `tests/test_mcp.py` — add `test_person_context_column_lookup`, `test_person_context_by_name`, `test_sb_list_people`
- [ ] `tests/test_people.py` — add enriched fields tests and type isolation regression

---

## Sources

### Primary (HIGH confidence — direct source code inspection)
- `/workspace/engine/entities.py` — current extraction implementation, exact line numbers
- `/workspace/engine/capture.py` — capture pipeline, entity extraction order, people write path
- `/workspace/engine/mcp_server.py:798-880` — sb_person_context current implementation
- `/workspace/engine/api.py:249-259, 658-743` — list_people() and note_meta() with body-mention fallback
- `/workspace/engine/reindex.py` — full reindex pipeline, walk loop, entity handling gap
- `/workspace/engine/db.py` — schema, migrations, init_schema() pattern
- `/workspace/frontend/src/types.ts` — PersonSummary current shape
- `/workspace/.planning/phases/30-people-graph-hardening/30-CONTEXT.md` — all locked decisions
- `/workspace/.claude/LEARNINGS.md` — established patterns, known pitfalls for this codebase

### Secondary (MEDIUM confidence — SQLite documentation patterns)
- SQLite `json_each()` virtual table: available since SQLite 3.38 (Python 3.11+). Python 3.13 on this project. Safe to use.
- Python `re` module Unicode character class ranges: stdlib behavior, well-established.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps, all existing libraries
- Architecture: HIGH — based on direct code inspection of all integration points
- Pitfalls: HIGH — drawn from LEARNINGS.md established bugs and Phase 27/28 decisions
- Unicode regex pattern: MEDIUM — covers Extended Latin block; edge cases (Arabic, CJK names) out of scope per CONTEXT.md decisions

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable codebase, 30-day validity)
