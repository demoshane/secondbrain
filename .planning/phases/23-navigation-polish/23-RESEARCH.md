# Phase 23: Navigation Polish - Research

**Researched:** 2026-03-16
**Domain:** Vanilla JS/Flask GUI — sidebar hierarchy, inline DOM editing, client-side filter state
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Sidebar hierarchy: hybrid folder-first, then note type inside (e.g. `projects/ → note (3), idea (2)`)
- Top level = brain folder (people/, meetings/, projects/, etc.)
- Second level = note type within that folder
- Count shown per section: `people/ (8)`, `person (8)`
- "Recent" section at top — flat list of most-recently-modified notes, collapsible like other sections
- Both folder-level and type-level collapse states persisted independently
- Collapse start state: restore from localStorage; first visit = all expanded
- Tag chips displayed below the note title, before the body — layout: `#idea  #work  #urgent  [+ Add tag]`
- Click tag chip → chip transforms into inline text input in-place; Enter to save, Escape to cancel
- `[+ Add tag]` at end of chips — click to open a new inline input
- Silent save: optimistic update, chip snaps back immediately; red flash on failure; no toast
- Save updates both frontmatter file AND database — targeted UPDATE, no full reindex
- Tag filter activated by clicking any tag chip in the note viewer (not a separate filter UI)
- Sidebar switches to flat filtered list (same as search results) showing all notes with that tag
- Filter banner above note list: `Filtering: #work  x` — click x to clear
- Tag filter + text search: AND logic — both must match
- Both search results and tag-filtered results use the same flat list (no grouping)
- Grouped hierarchy only in default "all notes" browse mode

### Claude's Discretion
- Exact CSS styling for chips (colors, font size, border-radius)
- Transition/animation for chip-to-input transform
- How to handle very long folder names in sidebar
- Exact localStorage key schema for collapse state

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GNAV-01 | Sidebar shows notes grouped by type/folder with collapse/expand toggle per section | renderSidebar() refactor; localStorage pattern; folder extraction from path |
| GNAV-02 | User can click a tag chip and edit inline; saves to frontmatter + DB without full reindex | PUT /notes/<path> tags extension; python-frontmatter patch; optimistic DOM update |
| GNAV-03 | User can filter sidebar/search results to show only notes with a specific tag | POST /search tags param; filter banner; AND logic with existing runSearch() |
</phase_requirements>

---

## Summary

Phase 23 is a pure GUI polish phase. All work touches three files: `engine/api.py` (two endpoint extensions), `engine/gui/static/app.js` (sidebar refactor + tag chip logic + filter state), and `engine/gui/static/style.css` (new component classes). The `index.html` needs a filter banner slot.

The database schema already has a `tags TEXT NOT NULL DEFAULT '[]'` column on the `notes` table (confirmed in `engine/db.py` SCHEMA_SQL). No migration is needed. The `tags` column stores a JSON array string — parsing with `json.loads` in Python and `JSON.parse` in JS is the correct approach.

The existing `renderSidebar(notes)` is 25 lines and already groups by type. It will be replaced with a 2-level hierarchy version. The existing `runSearch(query)` renders a flat list and is reused for both search and tag-filtered modes. The `PUT /notes/<path>` endpoint only accepts `content` today; it needs a `tags`-only update path. The `POST /search` endpoint needs an optional `tags` array for AND-filtering.

**Primary recommendation:** Implement in four sequential tasks — (1) sidebar hierarchy + collapse, (2) tag chip display, (3) inline tag edit + API save, (4) tag filter + banner.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vanilla JS (ES module) | — | All GUI logic | Already the project standard; no framework introduced |
| Flask | installed | API endpoints | Already the sidecar server |
| python-frontmatter | installed | Parse/write YAML frontmatter | Already used in `save_note`; `_fm.loads()` / `post.metadata` pattern established |
| localStorage | browser API | Persist collapse state | Zero-dependency, synchronous, well-suited to per-key UI state |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite3 (stdlib) | — | Tag UPDATE query | Already used for all DB writes in api.py |
| json (stdlib) | — | Parse/serialize tags JSON array | Tags stored as JSON string in DB |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| localStorage for collapse | sessionStorage | sessionStorage resets on tab close — user expectation is persistence across sessions |
| Optimistic DOM update | Wait for server response | Waiting creates visible lag; established delete pattern uses optimistic approach |
| `json.loads` for tag parsing | Split on comma | Split is fragile with quotes/spaces; JSON array is the canonical format already used |

**Installation:** No new dependencies. All libraries already present.

---

## Architecture Patterns

### Recommended Project Structure
No new files needed. Changes are confined to:
```
engine/
├── api.py                   # PUT /notes/<path> tags extension + POST /search tags filter
gui/static/
├── app.js                   # renderSidebar() refactor, tag chip logic, filter state
├── index.html               # filter banner slot above note list
└── style.css                # .tag-chip, .tag-chip-input, .tag-chip-editing, .filter-banner
```

### Pattern 1: 2-Level Sidebar Hierarchy

**What:** Build a nested data structure `{ folder: { type: [notes] } }` from the flat notes array, then render folder headers, type sub-headers, and note items with independent collapse toggles.

**When to use:** Default "all notes" browse mode only. Search and tag-filter results use flat `renderSidebar()` path.

**Folder extraction from path:** Each note has an absolute path like `/Users/.../SecondBrain/projects/2026-03-16-mvp.md`. The folder name is the parent directory's basename.

```javascript
// Source: existing app.js brainPath derivation pattern
function _folderName(notePath) {
    const parts = notePath.split('/');
    // parent dir of the file = parts[parts.length - 2]
    return parts[parts.length - 2] || 'other';
}
```

**Recent section:** Query the notes array already sorted by `created_at DESC` (server returns this order). Slice first N (e.g. 10) for "Recent".

### Pattern 2: localStorage Collapse State

**What:** Read/write a single JSON object keyed by `sb-collapse-state`. Each entry is a string key (e.g. `"projects"` for folder, `"projects::note"` for type-within-folder) mapped to `true` (collapsed) or `false` (expanded).

```javascript
// Source: MDN localStorage — HIGH confidence
const COLLAPSE_KEY = 'sb-collapse-state';

function getCollapseState() {
    try { return JSON.parse(localStorage.getItem(COLLAPSE_KEY) || '{}'); }
    catch { return {}; }
}

function setCollapseState(key, collapsed) {
    const state = getCollapseState();
    state[key] = collapsed;
    localStorage.setItem(COLLAPSE_KEY, JSON.stringify(state));
}
```

**Key schema:** `"folder"` for folder level; `"folder::type"` for type-within-folder level. Double-colon separator is safe because folder/type names don't contain `::`.

### Pattern 3: Inline Tag Chip Edit (In-Place DOM Transform)

**What:** Replace a `.tag-chip` element with a text `<input>` element in-place. On Enter/blur, call the save API and replace input back with updated chip.

```javascript
// Source: established optimistic update pattern from delete flow in app.js
function makeChipEditable(chipEl, tagIndex, allTags) {
    const input = document.createElement('input');
    input.type = 'text';
    input.value = allTags[tagIndex];
    input.className = 'tag-chip-input';
    chipEl.replaceWith(input);
    input.focus();
    input.select();

    function commit() {
        const newVal = input.value.trim();
        if (newVal && newVal !== allTags[tagIndex]) {
            const updated = [...allTags];
            updated[tagIndex] = newVal;
            saveTagsOptimistic(updated, input);
        } else {
            // Revert — rebuild chips from current tags
            renderTagChips(allTags);
        }
    }

    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') { e.preventDefault(); commit(); }
        if (e.key === 'Escape') { renderTagChips(allTags); }
    });
    input.addEventListener('blur', commit);
}
```

**Optimistic update:** Replace input with new chip immediately. If API fails, flash chip red and revert to old value.

### Pattern 4: Tag-Filter State Machine

**What:** A module-level variable `activeTagFilter = null` controls which display mode the sidebar is in. Three modes: `null` (hierarchy), `string` (tag filter), and the existing search query state.

```javascript
let activeTagFilter = null;

function activateTagFilter(tag) {
    activeTagFilter = tag;
    renderFilterBanner(tag);
    runTagFilter(tag);
}

function clearTagFilter() {
    activeTagFilter = null;
    document.getElementById('filter-banner').style.display = 'none';
    // Restore sidebar to current state (search or full hierarchy)
    const q = document.getElementById('search-input').value.trim();
    if (q) runSearch(q); else loadNotes();
}
```

**AND logic:** When `activeTagFilter` is set and a search query is also present, the search API call includes `tags: [activeTagFilter]`. The server filters by both.

### Pattern 5: API — Tags-Only Save

**What:** Extend `PUT /notes/<path>` to accept an optional `tags` array. When `tags` is present and `content` is absent, perform a targeted tags-only update: parse frontmatter, set `post.metadata['tags']`, write file, update DB.

```python
# Source: existing save_note pattern in api.py
body = request.get_json(force=True) or {}
tags = body.get("tags")  # list[str] | None

if tags is not None and "content" not in body:
    # Tags-only update path
    raw = p.read_text(encoding="utf-8")
    post = _fm.loads(raw)
    post.metadata["tags"] = tags
    new_content = _fm.dumps(post)
    with tempfile.NamedTemporaryFile("w", dir=p.parent, delete=False,
                                     suffix=".tmp", encoding="utf-8") as f:
        f.write(new_content)
        tmp = f.name
    os.replace(tmp, p)
    suppress_next_delete(str(p))
    # Targeted DB update — no reindex needed
    conn = get_connection()
    conn.execute(
        "UPDATE notes SET tags=?, updated_at=? WHERE path=?",
        (json.dumps(tags), datetime.datetime.utcnow().isoformat(), str(p.resolve()))
    )
    conn.commit()
    conn.close()
    return jsonify({"saved": True, "path": str(p)})
```

### Pattern 6: API — Tag-Filtered Search

**What:** Extend `POST /search` to accept optional `tags` array. Apply an AND filter: results must match the text query AND contain all specified tags. Tags are stored as JSON in the `tags` column; use SQLite's `LIKE` or `json_each` for filtering.

```python
# Source: existing search endpoint + SQLite json_each virtual table (available since SQLite 3.38)
tags_filter = body.get("tags")  # list[str] | None

if tags_filter:
    # After FTS5 results, apply in-Python filter using JSON.loads on tags column
    # OR use SQL: WHERE EXISTS (SELECT 1 FROM json_each(n.tags) WHERE value = ?)
    # Python-side filter is simpler and fast enough for typical note counts (< 10k)
    results = [r for r in results if _note_has_tags(r["path"], tags_filter, conn)]
```

**Alternative:** Pure SQL with `json_each`. Use Python-side filtering (post-process results) — it avoids SQLite version dependency and the note set is small.

### Anti-Patterns to Avoid

- **Re-fetching all notes on every tag edit:** The sidebar already has the notes array in memory. After a tags save, patch the in-memory note object and re-render rather than calling `loadNotes()`.
- **Triggering full reindex via SSE after tag save:** The tags-only save will fire a `modified` SSE event via watchdog. The `handleNoteEvent` function will call `loadNotes()` (sidebar refresh) and `openNote()` (viewer refresh). This is correct — do NOT suppress the SSE event for tag edits.
- **Using innerHTML for tag chip rendering with user-supplied tag values:** Use `textContent` for tag values to prevent XSS from user-created tags.
- **Storing collapse state as one key per section:** Store all collapse state in a single JSON blob under one localStorage key to avoid localStorage bloat.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Frontmatter read/write | Custom YAML parser | `python-frontmatter` (`_fm`) | Already used in `save_note`; handles edge cases (multiline, special chars) |
| Tag persistence across sessions | Custom sync mechanism | `localStorage` | Browser-native, synchronous, zero overhead |
| Markdown rendering in viewer | Custom renderer | `marked.js` (already vendored) | Already used for body rendering; consistent output |

**Key insight:** Every "hard" part of this phase (frontmatter parsing, markdown rendering, optimistic HTTP updates, SSE refresh) already has an established implementation pattern in the codebase. This phase is primarily wiring existing patterns together in new configurations.

---

## Common Pitfalls

### Pitfall 1: `python-frontmatter` dumps format changes
**What goes wrong:** `_fm.dumps(post)` may reorder frontmatter keys or change spacing, which some text tools notice as a spurious diff.
**Why it happens:** PyYAML serializes dict keys in insertion order (Python 3.7+) but may differ from the original YAML formatting.
**How to avoid:** Acceptable for this project — the file content is functionally identical. Document in plan that key order may change on first tag edit.
**Warning signs:** User reports "my git diff shows every key changed order" — note as known behavior.

### Pitfall 2: SSE fires a `modified` event after tag save → viewer reloads mid-edit
**What goes wrong:** Tag save writes to disk → watchdog fires `modified` → `handleNoteEvent` calls `openNote()` → viewer re-renders, destroying any in-progress edits.
**Why it happens:** `suppress_next_delete` only suppresses delete events; there is no analog for modify events during tag saves.
**How to avoid:** The existing `easyMDE !== null` guard in `handleNoteEvent` already protects open editor sessions. For tag chip editing (not EasyMDE), a short flag `_suppressNextModified = true` set before the fetch and cleared in the `modified` handler is sufficient. Alternatively, since tag chip inputs are inline DOM elements (not EasyMDE), the `openNote()` re-render will simply re-fetch and re-render tags from the updated DB — which is the correct end state.
**Warning signs:** Tag input disappears immediately after typing Enter.

### Pitfall 3: Folder name derived from path contains absolute path prefix
**What goes wrong:** Folder key `"/Users/tuomas/SecondBrain/projects"` is used as localStorage key — ugly and fragile.
**Why it happens:** `notePath.split('/').slice(-2, -1)[0]` gives the basename correctly, but only if split logic is consistent.
**How to avoid:** Always use `notePath.split('/').at(-2)` (or `parts[parts.length - 2]`) to extract just the directory basename.

### Pitfall 4: Tag filter state not cleared when navigating away
**What goes wrong:** User clicks a tag to filter, then types a new search — filter banner disappears but `activeTagFilter` is still set, so AND logic silently restricts results.
**Why it happens:** Tag filter and search are independent state variables that must be explicitly coordinated.
**How to avoid:** The filter banner X button clears `activeTagFilter`. Additionally, when the search input is cleared back to empty, call `clearTagFilter()` if active, then `loadNotes()`.

### Pitfall 5: Tags column returns JSON string from `/notes` endpoint — needs parsing
**What goes wrong:** `note.tags` arrives from `GET /notes` as the string `"[\"work\", \"idea\"]"` not a JS array.
**Why it happens:** SQLite stores tags as `TEXT`; the `/notes` endpoint returns `dict(row)` without parsing JSON fields.
**How to avoid:** Either parse in JS (`JSON.parse(note.tags || '[]')`) or extend the `/notes` endpoint to parse tags server-side before returning. Recommend parsing server-side for consistency — the endpoint returns `[dict(r) for r in rows]`; add `r["tags"] = json.loads(r["tags"] or "[]")` in the list comprehension.

---

## Code Examples

### Extract folder basename from absolute note path
```javascript
// Source: derived from existing brainPath derivation pattern in app.js
function folderName(notePath) {
    const parts = notePath.split('/');
    return parts[parts.length - 2] || 'other';
}
```

### Render tags row in viewer (safe against XSS)
```javascript
// Source: established DOM pattern in app.js
function renderTagChips(tags, container) {
    container.innerHTML = '';
    tags.forEach((tag, i) => {
        const chip = document.createElement('span');
        chip.className = 'tag-chip';
        chip.textContent = '#' + tag;
        chip.addEventListener('click', () => activateTagFilter(tag));
        chip.addEventListener('dblclick', () => makeChipEditable(chip, i, tags));
        container.appendChild(chip);
    });
    const addBtn = document.createElement('button');
    addBtn.className = 'tag-add-btn';
    addBtn.textContent = '+ Add tag';
    addBtn.addEventListener('click', () => addNewTag(tags, container));
    container.appendChild(addBtn);
}
```

### PUT /notes/<path> — tags-only save (Python)
```python
# Source: extends existing save_note() in api.py
import json as _json
# In save_note():
tags_val = body.get("tags")
if tags_val is not None and "content" not in body:
    raw = p.read_text(encoding="utf-8")
    post = _fm.loads(raw)
    post.metadata["tags"] = tags_val
    new_content = _fm.dumps(post)
    with tempfile.NamedTemporaryFile("w", dir=p.parent, delete=False,
                                     suffix=".tmp", encoding="utf-8") as f:
        f.write(new_content)
        tmp = f.name
    os.replace(tmp, p)
    suppress_next_delete(str(p))
    now = datetime.datetime.utcnow().isoformat()
    conn = get_connection()
    conn.execute(
        "UPDATE notes SET tags=?, updated_at=? WHERE path=?",
        (_json.dumps(tags_val), now, str(p.resolve()))
    )
    conn.commit()
    conn.close()
    return jsonify({"saved": True, "path": str(p)})
```

### POST /search — tag AND filter (Python)
```python
# Source: extends existing search() in api.py
tags_filter = body.get("tags")  # list[str] | None, e.g. ["work"]
# After getting results from search_notes():
if tags_filter:
    conn2 = get_connection()
    conn2.row_factory = sqlite3.Row
    filtered = []
    for r in results:
        row = conn2.execute(
            "SELECT tags FROM notes WHERE path=?", (r["path"],)
        ).fetchone()
        if row:
            note_tags = _json.loads(row["tags"] or "[]")
            if all(t in note_tags for t in tags_filter):
                filtered.append(r)
    conn2.close()
    results = filtered
```

### GET /notes — parse tags server-side
```python
# Source: extends list_notes() in api.py
import json as _json
rows = conn.execute(
    "SELECT path, title, type, tags, created_at FROM notes ORDER BY created_at DESC"
).fetchall()
notes = []
for r in rows:
    d = dict(r)
    d["tags"] = _json.loads(d.get("tags") or "[]")
    notes.append(d)
return jsonify({"notes": notes})
```

### localStorage collapse key schema
```javascript
// Key: "sb-sidebar-collapse"
// Value: JSON object, e.g.:
// { "projects": false, "projects::note": true, "recent": false }
// false = expanded (default), true = collapsed
const COLLAPSE_KEY = 'sb-sidebar-collapse';
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sidebar groups by type only | Sidebar groups by folder > type | Phase 23 | Users see hierarchy matching their brain folder structure |
| Tags displayed only in raw editor | Tags shown as interactive chips below title | Phase 23 | Tags become navigable, filterable, editable without opening editor |

**Deprecated/outdated:**
- `renderSidebar()` flat type-grouping: replaced by 2-level hierarchy; keep as `renderFlatList()` helper for search/filter modes

---

## Open Questions

1. **`_fm.dumps()` format for tags array**
   - What we know: python-frontmatter uses PyYAML to serialize; tags should render as `tags: [work, idea]` (flow style) or `tags:\n- work\n- idea` (block style)
   - What's unclear: which style the existing notes use; mismatch causes spurious diffs
   - Recommendation: Accept either style — python-frontmatter preserves existing style when updating metadata in place if the `Handler` supports it. Test with a real note during Wave 1. If style changes are disruptive, use `yaml.dump` with `default_flow_style=True` directly.

2. **"Recent" section size**
   - What we know: server returns notes sorted `created_at DESC`; first N form the Recent list
   - What's unclear: what N feels right (5? 10? 15?)
   - Recommendation: Default to 10; this is Claude's discretion per CONTEXT.md

3. **Tag filter interaction with search mode dropdown (keyword/semantic)**
   - What we know: tag filter calls `POST /search` with `tags` param
   - What's unclear: which search mode to use when filtering by tag with no text query
   - Recommendation: When tag filter is active with no text query, skip `POST /search` entirely and instead call `GET /notes` then filter client-side by tag (simpler, no FTS5 interaction). Only invoke `POST /search` when both text query and tag filter are active simultaneously.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, configured via pyproject.toml) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_api_tags.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GNAV-01 | Sidebar renders folder > type hierarchy from notes array | unit (JS logic via Python proxy test not applicable; verify via manual) | manual | — |
| GNAV-01 | localStorage collapse state persisted and restored | unit (JS; manual verify) | manual | — |
| GNAV-02 | PUT /notes/<path> with `tags` param updates frontmatter and DB | unit | `uv run pytest tests/test_api_tags.py::TestTagsOnlySave -x -q` | Wave 0 |
| GNAV-02 | PUT /notes/<path> returns 200 and note tags column updated | unit | `uv run pytest tests/test_api_tags.py::TestTagsOnlySave -x -q` | Wave 0 |
| GNAV-03 | POST /search with `tags` filter returns only matching notes | unit | `uv run pytest tests/test_api_tags.py::TestTagSearch -x -q` | Wave 0 |
| GNAV-03 | POST /search with `tags` + query applies AND logic | unit | `uv run pytest tests/test_api_tags.py::TestTagSearch -x -q` | Wave 0 |
| GNAV-02/03 | GET /notes returns tags as parsed array (not raw JSON string) | unit | `uv run pytest tests/test_api_tags.py::TestListNotesTags -x -q` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_api_tags.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api_tags.py` — covers GNAV-02 (tags save), GNAV-03 (tag search filter), GET /notes tags parsing
- [ ] No framework changes needed; `tests/conftest.py` fixtures (`client`, `tmp_path`, `monkeypatch`) already sufficient

---

## Sources

### Primary (HIGH confidence)
- `engine/db.py` — confirmed `tags TEXT NOT NULL DEFAULT '[]'` column exists in SCHEMA_SQL; no migration needed
- `engine/api.py` — confirmed `PUT /notes/<path>` accepts only `content` today; `_fm.loads`/`_fm.dumps` pattern established
- `engine/gui/static/app.js` — confirmed `renderSidebar()`, `runSearch()`, `handleNoteEvent()`, optimistic update pattern, `localStorage` is standard browser API
- `engine/search.py` — confirmed `search_notes()` signature; `tags` param not yet supported
- `tests/conftest.py` — confirmed fixture patterns (`client`, `tmp_path`, `monkeypatch`) for new test file

### Secondary (MEDIUM confidence)
- MDN Web Docs: `localStorage.setItem/getItem` — standard browser API, synchronous, per-origin persistence
- MDN Web Docs: `Element.replaceWith()` — standard DOM API for in-place chip-to-input transform
- python-frontmatter PyPI/GitHub: `_fm.loads()` returns `Post` object; `post.metadata` is a dict; `_fm.dumps(post)` serializes back to YAML frontmatter + body

### Tertiary (LOW confidence)
- None — all claims verified from codebase or well-known APIs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed present in codebase
- Architecture: HIGH — patterns derived directly from existing code, not assumptions
- Pitfalls: HIGH — derived from known project decisions (SSE suppress behavior, frontmatter format, localStorage)
- API extensions: HIGH — confirmed existing endpoint signatures and DB schema

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable stack; no fast-moving dependencies)
