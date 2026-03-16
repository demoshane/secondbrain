# Phase 20: Frontend Bug Fixes - Research

**Researched:** 2026-03-16
**Domain:** Flask API (Python) + vanilla JS/CSS GUI (pywebview)
**Confidence:** HIGH — all fixes target existing, fully-readable code; no new dependencies

## Summary

Phase 20 consists of four isolated bug fixes in the GUI viewer. All bugs are caused by straightforward omissions in the existing code, not architectural deficiencies. The fixes are: strip YAML frontmatter in the API before returning content, debug a CSS scroll constraint, fix the save path to also update SQLite, and replace the fuzzy filename backlink query with an FTS5/LIKE content search. No new libraries are required.

Each fix is small (under 20 lines of Python or JS). The four bugs are independent and can be planned as four separate tasks. The existing pytest + Flask test client infrastructure in `tests/test_api.py` and `tests/conftest.py` covers API-level assertions directly.

**Primary recommendation:** Fix in API-first order — frontmatter strip (GUIX-03) unlocks correct markdown rendering; the other three fixes (GUIX-04 scroll, GUIX-02 title sync, GUIX-05 backlinks) are fully independent.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Frontmatter display**
- Strip YAML frontmatter in the API before returning content — server returns body-only
- Viewer shows clean rendered HTML with no frontmatter visible
- Stripping in the API benefits all consumers (GUI, MCP, future CLI)
- The `/notes/<path>` GET endpoint should strip the `---...---` block before returning `content`

**Editor (interim, until Phase 23)**
- EasyMDE editor shows body only — frontmatter is read-only for now
- Frontmatter fields (tags, type, date) are not editable in Phase 20
- Phase 23 will replace this with proper metadata form fields

**Save + reindex UX**
- Silent save: Ctrl+S saves, no toast or banner on success
- Instant sidebar refresh: After save, update the sidebar title immediately (parse new title from saved content)
- SQLite updated immediately: After save, re-index the single note — update `notes` row (title, updated_at) by parsing frontmatter from the saved file. No stale DB state.
- Save failure: Inline red error message in the viewer toolbar — stays visible until user retries

**Backlinks accuracy**
- Replace the fuzzy filename substring match with FTS5 content search: find notes whose body contains the current note's title (case-insensitive)
- Use SQLite FTS5 MATCH or `LIKE '%title%'` (case-insensitive via `LOWER()`) — no schema migration required
- Empty backlinks: show `None` text (keep section visible, consistent structure)
- Case-insensitive matching

### Claude's Discretion
- Exact CSS fix for scroll (overflow constraints vs height fix — whichever is cleaner)
- How to efficiently parse frontmatter in Python for the single-note re-index (yaml.safe_load or regex)
- Exact FTS5 query formulation for backlinks

### Deferred Ideas (OUT OF SCOPE)
- Smart backlink disambiguation on capture: Phase 24+ scope
- Separate metadata form fields (tags, type, date) in editor: Phase 23 scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GUIX-02 | Title edits made in the GUI are reflected immediately without restart | After save: parse `title:` from frontmatter in saved file, run `UPDATE notes SET title=?, updated_at=? WHERE path=?`, then update the matching `li[data-path]` text in JS sidebar |
| GUIX-03 | Note content renders as formatted HTML (not raw markdown text) | `read_note` returns raw file text including frontmatter; `marked.parse()` already called in `renderMarkdown()`; fix is to strip frontmatter block before the `content` key is populated |
| GUIX-04 | User can scroll the note content area with the mouse wheel | `#viewer { flex: 1; overflow-y: auto }` is already set; bug is likely `#center { overflow: hidden }` preventing scroll propagation — remove `overflow: hidden` or set `min-height: 0` on `#viewer` |
| GUIX-05 | Backlinks display correctly in the note viewer | `note_meta` query uses `path LIKE '%' || fname[:20] || '%'` (filename substring match) — replace with `LOWER(body) LIKE LOWER('%' || title || '%')` FTS5 content search against `notes` table |
</phase_requirements>

## Standard Stack

### Core (already present — no new installs)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-frontmatter | installed | Parse YAML frontmatter from .md files | Already used in `engine/reindex.py` |
| Flask | installed | HTTP API sidecar | Already used in `engine/api.py` |
| marked.js | vendored | Markdown → HTML in browser | Already bundled with EasyMDE, already called in `renderMarkdown()` |
| pytest | installed | Test runner | Already used across entire test suite |

### No new dependencies required
All four fixes use only what already exists in the codebase.

**Installation:** none needed.

## Architecture Patterns

### How frontmatter stripping works in the existing codebase

`engine/reindex.py` already does this correctly via `python-frontmatter`:

```python
# Source: engine/reindex.py lines 100-101
post = frontmatter.load(str(md_path))
meta = post.metadata   # dict of YAML fields
body = post.content    # everything after the closing ---
```

The `api.py` `read_note` endpoint currently returns `p.read_text()` (raw file). The fix is to apply `frontmatter.loads()` and return `post.content` instead.

**API response key:** Return as `body` (not `content`) so callers know they receive stripped text. JS side reads `const { content } = await res.json()` — change key name in both places, or add `body` alongside `content` and update JS to prefer `body`.

### How save + SQLite re-index should work

The pattern from `reindex.py` is the reference. For a single-note update after save:

```python
# Pattern (not yet in api.py — needs to be added to save_note)
import frontmatter as _fm
post = _fm.loads(content)          # content = string just written to disk
title = post.metadata.get("title", p.stem)
now = datetime.datetime.utcnow().isoformat()
conn = get_connection()
conn.execute(
    "UPDATE notes SET title=?, updated_at=? WHERE path=?",
    (title, now, str(p))
)
conn.commit()
conn.close()
```

This is a lightweight subset of `reindex_brain` — no embedding update, no FTS5 rebuild. The `notes_au` trigger in `db.py` (line 34) already keeps FTS5 in sync on UPDATE automatically.

### How backlinks query should change

Current (buggy) query in `note_meta` (api.py line 150-153):

```python
rows = conn.execute(
    "SELECT path, title FROM notes WHERE path != ? AND path LIKE '%' || ? || '%'",
    (str(p), fname[:20]),
)
```

This matches on the *path* (filename), not on who links *to* this note.

Replacement — find notes whose *body text* mentions the current note's title:

```python
# Case-insensitive LIKE on body column (no schema change needed)
title_row = conn.execute("SELECT title FROM notes WHERE path=?", (str(p),)).fetchone()
if title_row and title_row[0]:
    rows = conn.execute(
        "SELECT path, title FROM notes WHERE path != ? AND LOWER(body) LIKE LOWER(?)",
        (str(p), f"%{title_row[0]}%"),
    )
else:
    rows = []
```

**Alternative (FTS5 MATCH):**

```python
# FTS5 full-text search against notes_fts
rows = conn.execute(
    'SELECT n.path, n.title FROM notes n '
    'JOIN notes_fts ON notes_fts.rowid = n.id '
    'WHERE notes_fts MATCH ? AND n.path != ?',
    (f'"{title_row[0]}"', str(p)),
)
```

**Recommendation:** Use the LIKE approach. It is simpler, handles special characters without FTS5 tokenizer escaping issues, and is fast enough for typical brain sizes (hundreds of notes). FTS5 MATCH requires escaping quotes and special chars in the title.

### CSS scroll diagnosis

The CSS for the center column (style.css line 14):

```css
#center { background: #fff; display: flex; flex-direction: column; overflow: hidden; }
#viewer { flex: 1; overflow-y: auto; padding: 20px 24px; line-height: 1.6; }
```

`overflow: hidden` on `#center` clips the scroll region. Combined with `flex: 1` on `#viewer`, the viewer element will grow to fill available height correctly, but if an ancestor collapses its height, `overflow-y: auto` on `#viewer` has nothing to scroll against.

**Fix option A (minimal):** Add `min-height: 0` to `#viewer`. In a flex column, `flex: 1` can cause the child to overflow its parent rather than scroll — `min-height: 0` forces the browser to respect the flex container boundary and triggers actual scrolling.

**Fix option B (alternative):** Remove `overflow: hidden` from `#center`. This is less safe (may cause layout shifts elsewhere) but worth trying first.

**Recommendation:** Apply `min-height: 0` to `#viewer` — this is the canonical fix for "flex child doesn't scroll" bugs. Confidence HIGH (well-documented CSS flexbox behavior).

### JS sidebar title update after save

After save completes, update the active sidebar item without a full reload:

```javascript
// In saveNote(), after res.ok check — parse title from first # heading or YAML
// Simple approach: re-fetch /notes to get updated title
await loadNotes();
// Then re-select the current note without re-opening it
document.querySelectorAll('#note-list li[data-path]').forEach(el => {
    el.classList.toggle('active', el.dataset.path === currentPath);
});
```

**Lighter approach (no reload):** Parse the `title:` field directly in the JS from the saved content string. But since `easyMDE.value()` returns body-only (after Phase 20's frontmatter strip), the title isn't in the editor value. The safest approach is to call `loadNotes()` after save — it's already fast and updates the full sidebar title list in one fetch.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parse YAML frontmatter | Custom regex `---[\s\S]+?---` splitter | `python-frontmatter` (already installed) | Handles edge cases: no trailing newline, YAML with colons, nested maps |
| Strip frontmatter for API response | Duplicate parsing logic in api.py | `import frontmatter; post = frontmatter.loads(text); return post.content` | Reuses exact same pattern already in reindex.py |

**Key insight:** `python-frontmatter` is already a dependency and used in `reindex.py`. Using it in `api.py` adds zero new risk.

## Common Pitfalls

### Pitfall 1: API returns `body` but JS still reads `content`
**What goes wrong:** After changing the API to return `{ "body": ... }`, the JS `const { content } = await res.json()` silently gets `undefined`, viewer renders empty.
**Why it happens:** JS destructuring doesn't throw on missing keys.
**How to avoid:** Change the key in both places simultaneously (API response + JS consumer), or add `body` alongside `content` for a safe transition. The `enterEditMode()` function also fetches the note separately (line 86 of app.js) — update both fetch consumers.
**Warning signs:** Viewer shows blank panel after opening a note.

### Pitfall 2: Save re-index doesn't find the note in SQLite
**What goes wrong:** After save, `UPDATE notes SET title=? WHERE path=?` matches 0 rows because the path format differs (e.g., relative vs absolute).
**Why it happens:** `reindex.py` stores `str(md_path.resolve())` (absolute path). The save endpoint constructs `_Path(note_path)` which may or may not be absolute depending on the URL encoding.
**How to avoid:** Use `str(p.resolve())` in the UPDATE WHERE clause, same as the reindex pattern.
**Warning signs:** Sidebar title doesn't update even though save succeeds.

### Pitfall 3: FTS5 LIKE with special characters in title
**What goes wrong:** A note titled `C++ Notes` or `Alice & Bob` causes the LIKE to return wrong results or SQL errors.
**Why it happens:** `%` and `_` are LIKE wildcards; `'` causes syntax errors.
**How to avoid:** Use parameterized queries (already done), and consider LIKE pattern is `f"%{title}%"` — the `%` wildcards are added by Python, not the title itself. The title value is passed as a bind parameter so `'` is safe. The only remaining risk is if the title contains `%` or `_` characters; for Phase 20, this is acceptable.

### Pitfall 4: EasyMDE editor shows frontmatter after Phase 20 strip
**What goes wrong:** `enterEditMode()` re-fetches the note content (app.js line 86-87). After Phase 20, the API returns body-only. When saved, the editor content (body only) is PUT back — the file loses its frontmatter.
**Why it happens:** The PUT saves `easyMDE.value()` which is now body-only, overwriting the whole file.
**How to avoid:** The `save_note` endpoint currently writes `body.get("content", "")` directly. Before Phase 20, the editor showed full file text including frontmatter, so save was safe. After stripping, the editor must NOT be used to overwrite the file with body-only content. Two options:
  - Keep `enterEditMode()` fetching raw content (add a separate `?raw=1` query param or `/raw` endpoint), and let the editor show body-only for UX but save the reconstructed full file.
  - Or: store the raw frontmatter block in a JS variable when opening a note, and prepend it on save.
**Recommendation (Claude's discretion applied):** Add a `?raw=true` query parameter to `read_note` that bypasses frontmatter stripping. The editor uses `?raw=true`; the viewer uses the default (stripped). This is the cleanest separation. Alternatively, store raw file text in a `currentRaw` variable and prepend on save.
**Warning signs:** Notes lose their `title:`, `type:`, `tags:` fields after being edited and saved.

### Pitfall 5: CSS min-height fix breaks EasyMDE editor layout
**What goes wrong:** Adding `min-height: 0` to `#viewer` may interact with `.EasyMDEContainer { flex: 1 }` when switching to edit mode.
**Why it happens:** Both `#viewer` and `#editor-area` share the same flex slot in `#center`.
**How to avoid:** Apply `min-height: 0` to `#center` itself (the flex container), not `#viewer`. This is the standard fix that affects all flex children uniformly.

## Code Examples

### Frontmatter stripping in API (Python)
```python
# Source: pattern from engine/reindex.py — adapt for api.py
import frontmatter as _fm

@app.get("/notes/<path:note_path>")
def read_note(note_path):
    p = Path(note_path) if note_path.startswith("/") else Path("/") / note_path
    if not p.exists():
        return jsonify({"error": "Not found"}), 404
    raw = p.read_text(encoding="utf-8")
    post = _fm.loads(raw)
    return jsonify({"body": post.content, "path": str(p)})
```

### Single-note SQLite update after save (Python)
```python
# In save_note() after os.replace(tmp, p):
import frontmatter as _fm
import datetime
saved_text = p.read_text(encoding="utf-8")
post = _fm.loads(saved_text)
title = post.metadata.get("title", p.stem)
now = datetime.datetime.utcnow().isoformat()
conn = get_connection()
conn.execute(
    "UPDATE notes SET title=?, updated_at=? WHERE path=?",
    (title, now, str(p.resolve()))
)
conn.commit()
conn.close()
```

### Backlinks LIKE query (Python)
```python
# Replacement for note_meta fuzzy query in api.py
title_row = conn.execute("SELECT title FROM notes WHERE path=?", (str(p),)).fetchone()
if title_row and title_row["title"]:
    rows = conn.execute(
        "SELECT path, title FROM notes WHERE path != ? AND LOWER(body) LIKE LOWER(?)",
        (str(p), f"%{title_row['title']}%"),
    ).fetchall()
    backlinks = [dict(r) for r in rows]
else:
    backlinks = []
```

### CSS scroll fix
```css
/* Add to style.css — canonical flex scroll fix */
#center { min-height: 0; }        /* allow flex children to scroll */
#viewer { min-height: 0; }        /* belt-and-suspenders */
```

### JS: update sidebar title after save (app.js)
```javascript
// In saveNote(), after res.ok — reload sidebar and restore active state
await loadNotes();
document.querySelectorAll('#note-list li[data-path]').forEach(el => {
    el.classList.toggle('active', el.dataset.path === currentPath);
});
```

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Raw file returned from API | Body-only API response | Frontmatter stripped server-side, benefits all consumers |
| Save overwrites file only | Save + SQLite UPDATE | Keeps index in sync without full reindex |
| Fuzzy filename backlinks | Content-based backlinks | FTS5 body text, case-insensitive |

## Open Questions

1. **Editor save safety (frontmatter preservation)**
   - What we know: After strip, `enterEditMode()` will receive body-only content. Saving body-only to disk loses frontmatter.
   - What's unclear: Best approach — `?raw=true` param vs. JS-side `currentRaw` variable.
   - Recommendation: Add `raw=true` query param to `read_note` as the cleanest solution. `enterEditMode()` fetches with `?raw=true`; the editor `initialValue` is body-only (strip frontmatter in JS before passing to EasyMDE); on save, prepend stored raw frontmatter. OR: pass raw to editor, accept that frontmatter is visible in editor (matches current behavior, easiest to implement).

2. **`people` column in notes table**
   - What we know: `db.py` adds `people` via `migrate_add_people_column()` — it may not be in the base schema CREATE TABLE statement.
   - What's unclear: Whether a fresh DB install includes it in `SCHEMA_SQL` or only via migration.
   - Recommendation: Not Phase 20 scope, but worth noting for `UPDATE notes SET title=?` — the UPDATE only touches `title` and `updated_at`, so missing columns are irrelevant.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pyproject.toml |
| Quick run command | `python -m pytest tests/test_api.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GUIX-03 | `/notes/<path>` returns `body` without frontmatter | unit | `pytest tests/test_api.py::TestReadNote -x` | ✅ (extend existing class) |
| GUIX-02 | `PUT /notes/<path>` updates SQLite title after save | unit | `pytest tests/test_api.py::TestSaveNote -x` | ❌ Wave 0 |
| GUIX-05 | `/notes/<path>/meta` backlinks use body content search | unit | `pytest tests/test_api.py::TestNoteMeta -x` | ❌ Wave 0 |
| GUIX-04 | `#viewer` scrolls in browser (CSS) | manual | open GUI, load a long note, scroll | manual-only |

GUIX-04 (CSS scroll) cannot be automated — it requires a real browser/pywebview rendering context. The fix is a 1-2 line CSS change with no logic path to assert.

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_api.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api.py` — add `TestSaveNote` class: covers GUIX-02 (title in SQLite after PUT)
- [ ] `tests/test_api.py` — add `TestNoteMeta` class: covers GUIX-05 (backlinks content match, no false positives)
- [ ] `tests/test_api.py` — extend `TestReadNote`: assert `body` key present and no `---` frontmatter block in response

## Sources

### Primary (HIGH confidence)
- Direct code reading: `engine/api.py` — all four bugs identified by inspection
- Direct code reading: `engine/reindex.py` — `python-frontmatter` usage pattern confirmed
- Direct code reading: `engine/db.py` — schema, triggers, FTS5 table confirmed
- Direct code reading: `engine/gui/static/app.js` — JS fetch patterns, editor flow confirmed
- Direct code reading: `engine/gui/static/style.css` — `#center { overflow: hidden }` confirmed

### Secondary (MEDIUM confidence)
- CSS flexbox `min-height: 0` fix — well-established pattern for "flex child doesn't scroll"; standard web platform behavior (not version-specific)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all libraries already in use
- Architecture: HIGH — all patterns derived from existing codebase, not speculation
- Pitfalls: HIGH — identified directly from code inspection (not theoretical)
- CSS fix: MEDIUM — `min-height: 0` is well-known but exact interaction with EasyMDE requires manual verification

**Research date:** 2026-03-16
**Valid until:** Stable — no external dependencies; valid until code changes
