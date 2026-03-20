# Phase 29: Add Link Capture — Research

**Researched:** 2026-03-19
**Domain:** URL metadata fetching, note type extension, Flask API, React page, MCP tool
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Auto-fetch page metadata at capture time: `og:title`, `og:description`, HTML `<title>` fallback
- Note title = fetched page title (fallback: URL domain if fetch fails)
- Note body = fetched `og:description` + optional user-provided annotation appended below
- URL stored as dedicated `url:` field in YAML frontmatter
- Fetch is best-effort: if it fails, capture the link anyway with URL as title — never blocks capture
- Phase 29 scope: MCP tool only (`sb_capture_link`)
- Signature: `sb_capture_link(url, tags=[], people=[], notes='')`
  - `notes` is optional user annotation appended to body after fetched description
- Return rich confirmation: fetched title + domain + saved note path
  - e.g., `"Saved: 'React Docs' (react.dev) → links/2026-03-19-react-docs.md"`
- Duplicate URL handling: warn in confirmation but save anyway
- New `links/` subfolder in `~/SecondBrain/`
- Note_type = `"link"` (new type; add to `TYPE_TO_DIR` mapping)
- Filename pattern: `YYYY-MM-DD-title-slug.md` — consistent with all other note types
- YAML frontmatter includes `url:` field alongside standard fields
- Dedicated "Links" tab in sidebar (same level as Meetings, People)
- List view per link: title + domain + date + tags + description snippet
- Clicking a link opens right-panel note detail (same pattern as other notes)
- Note detail panel shows a prominent "Visit Link" button that opens the URL in browser
- In-page search bar + tag filter (same pattern as Meetings/Notes pages)

### Claude's Discretion
- HTTP fetch implementation (requests lib, httpx, or urllib — whichever fits Python 3.13 best)
- Fetch timeout value and retry count
- Exact frontmatter field ordering
- How domain is extracted from URL for display (just the hostname)
- Loading/skeleton states in GUI
- Empty state for Links page ("No links saved yet — use sb_capture_link in Claude")

### Deferred Ideas (OUT OF SCOPE)
- CLI `sb-capture --type link` — out of scope for Phase 29
- `sb_capture_smart` URL detection — Phase 31's job
- GUI "New Link" button in the Links page header — could be added but depends on GUI complexity budget; Claude's discretion
- Browser extension / share sheet integration — future phase
</user_constraints>

---

## Summary

Phase 29 adds a first-class `link` note type to the second brain. The core work splits into three tracks: (1) a Python HTTP metadata fetcher, (2) extending the engine's capture pipeline and MCP server with `sb_capture_link`, and (3) a new Links page in the React GUI with its backing Flask API endpoint.

The stack is already complete — no new dependencies are required. Python's stdlib `urllib.request` handles HTTP metadata fetching adequately for Python 3.13 on Intel Mac; the `requests` library is not installed but `urllib` handles redirects, timeouts, and HTML parsing with `html.parser`. The `build_post()` + `capture_note()` + `write_note_atomic()` pipeline in `engine/capture.py` is the proven write path and must be reused. The GUI pattern established by MeetingsPage (list-left + detail-right, `fetch()` to Flask API) is the exact template for LinksPage.

**Primary recommendation:** Use `urllib.request` (stdlib) for metadata fetching — zero new deps, Python 3.13 compatible, handles redirects. Parse HTML with `html.parser` (stdlib). Store `url:` in frontmatter as an extra field on the Post object before calling `write_note_atomic()`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `urllib.request` | stdlib | HTTP GET for metadata fetch | No new dep; handles redirects; Python 3.13 |
| `html.parser` | stdlib | Parse `<title>` and `<meta og:*>` from HTML | No new dep; sufficient for head-tag extraction |
| `python-frontmatter` | >=1.0 (installed) | Add `url:` field to Post object | Already used by entire capture pipeline |
| `flask` | >=3.0 (installed) | New `/links` and `/links/<path>` routes | Existing API framework |
| React + shadcn/ui + Tailwind | installed | LinksPage component | Existing frontend stack |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `engine.capture.capture_note()` | project | Single write path | Always — never bypass |
| `engine.capture.build_post()` | project | Construct frontmatter Post | Build base post, then add `url:` key |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `urllib.request` | `requests` | requests not installed; adding a dep is unnecessary overhead |
| `urllib.request` | `httpx` | httpx not installed; async adds complexity for sync MCP tool |
| `html.parser` | `beautifulsoup4` | Not installed; stdlib parser is sufficient for head-only extraction |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Project Structure
```
engine/
├── link_fetcher.py     # fetch_link_metadata(url) → {title, description, domain}
├── capture.py          # TYPE_TO_DIR: add "link": "links"
├── mcp_server.py       # add sb_capture_link() tool
├── api.py              # add GET /links, GET /links/<path>
frontend/src/
├── components/LinksPage.tsx    # new page component
├── components/TabBar.tsx       # add 'links' tab
├── contexts/UIContext.tsx       # add 'links' to View union
├── types.ts                     # add LinkSummary interface
frontend/src/App.tsx             # import LinksPage, handle 'links' view
tests/
├── test_link_fetcher.py         # unit tests for metadata extraction
├── test_links.py                # already exists (empty); use for API tests
```

### Pattern 1: Metadata Fetcher Module
**What:** Isolated `engine/link_fetcher.py` with `fetch_link_metadata(url) -> dict`
**When to use:** Called by `sb_capture_link` before capture; wrapped in try/except so failure never blocks capture

```python
# engine/link_fetcher.py
import urllib.request
import urllib.parse
from html.parser import HTMLParser

_TIMEOUT = 10  # seconds

class _MetaParser(HTMLParser):
    """Extract <title> and <meta property="og:*"> from HTML head."""
    def __init__(self):
        super().__init__()
        self.og_title = None
        self.og_description = None
        self.page_title = None
        self._in_title = False
        self._done = False

    def handle_starttag(self, tag, attrs):
        if self._done:
            return
        attrs_d = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            prop = attrs_d.get("property", "") or attrs_d.get("name", "")
            content = attrs_d.get("content", "")
            if prop == "og:title":
                self.og_title = content
            elif prop == "og:description":
                self.og_description = content
        elif tag == "body":
            self._done = True  # stop parsing past <head>

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and self.page_title is None:
            self.page_title = data.strip()


def fetch_link_metadata(url: str) -> dict:
    """Fetch og:title, og:description, <title> from URL.

    Returns:
        {
          "title": str,        # og:title or <title> or domain
          "description": str,  # og:description or ""
          "domain": str,       # hostname only, e.g. "react.dev"
        }

    Never raises — returns domain-only fallback on any error.
    """
    domain = urllib.parse.urlparse(url).hostname or url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (second-brain)"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            charset = resp.headers.get_content_charset("utf-8")
            html = resp.read(65536).decode(charset, errors="replace")
        parser = _MetaParser()
        parser.feed(html)
        title = parser.og_title or parser.page_title or domain
        description = parser.og_description or ""
        return {"title": title.strip(), "description": description.strip(), "domain": domain}
    except Exception:
        return {"title": domain, "description": "", "domain": domain}
```

### Pattern 2: MCP Tool — sb_capture_link
**What:** New MCP tool following exact `sb_capture` pattern; calls fetcher then `capture_note()`
**When to use:** User invokes from Claude to save a URL

```python
@mcp.tool()
def sb_capture_link(
    url: str,
    tags: list[str] | None = None,
    people: list[str] | None = None,
    notes: str = "",
) -> dict:
    """Capture a URL as a link note with auto-fetched page metadata.

    Fetches og:title and og:description from the page.
    Falls back to URL domain as title if fetch fails.
    Saves into links/ subfolder with url: field in frontmatter.
    """
    _ensure_ready()
    from engine.link_fetcher import fetch_link_metadata
    meta = fetch_link_metadata(url)
    title = meta["title"]
    body = meta["description"]
    if notes:
        body = f"{body}\n\n{notes}" if body else notes

    conn = get_connection()
    try:
        # Duplicate URL check — warn but always save
        existing = conn.execute(
            "SELECT path FROM notes WHERE type='link' AND body LIKE ?",
            (f"%{url}%",)
        ).fetchone()
        dup_warning = None
        if existing:
            dup_warning = f"Already captured this URL as {existing[0]} — saving new copy"

        # Add url field to post BEFORE capture_note writes it
        # capture_note builds post internally, so we use a wrapper approach:
        # build post manually, inject url:, then call write_note_atomic directly
        from engine.capture import build_post, write_note_atomic, log_audit
        from engine.db import init_schema
        import datetime
        from engine.paths import BRAIN_ROOT as _BRAIN_ROOT
        init_schema(conn)

        slug = datetime.date.today().isoformat() + "-" + title[:40].replace(" ", "-").lower()
        # sanitize slug
        import re
        slug = re.sub(r"[^a-z0-9-]", "", slug.replace(" ", "-"))
        target = _BRAIN_ROOT / "links" / f"{slug}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        counter = 2
        while target.exists() or conn.execute("SELECT 1 FROM notes WHERE path=?", (str(target.resolve()),)).fetchone():
            target = _BRAIN_ROOT / "links" / f"{slug}-{counter}.md"
            counter += 1

        post = build_post("link", title, body, tags or [], people or [])
        post["url"] = url
        write_note_atomic(target, post, conn)
        conn.commit()

        confirmation = f"Saved: '{title}' ({meta['domain']}) → {target.relative_to(_BRAIN_ROOT)}"
        if dup_warning:
            confirmation = f"{dup_warning}\n{confirmation}"
        return {"status": "created", "path": str(target), "confirmation": confirmation}
    finally:
        conn.close()
```

**Note:** The duplicate-URL check uses `body LIKE ?` as a pragmatic approach since the `url:` field ends up in the note body blob in the DB notes table. A cleaner alternative is a DB migration to add a `url` column to `notes` and index it — see pitfalls section.

### Pattern 3: Flask API — GET /links
**What:** New endpoint mirroring `/meetings` pattern exactly; queries `notes WHERE type='link'`
**When to use:** LinksPage fetch on mount

```python
@app.get("/links")
def list_links():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT path, title, type, created_at, tags, body FROM notes"
        " WHERE type='link' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    links = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d.get("tags") or "[]")
        # Extract domain from body (url: field not in DB notes schema yet)
        # or read from frontmatter on disk — pragmatic: parse from body
        import re
        url_match = re.search(r'https?://([^/\s]+)', d.get("body", ""))
        d["domain"] = url_match.group(1) if url_match else ""
        d["snippet"] = d.get("body", "")[:120]
        links.append(d)
    return jsonify({"links": links})
```

**Alternative:** Add `url` column to `notes` table via migration (see Pitfall 1) — then domain extraction is trivial and indexed. Recommended if dedup or search-by-URL is anticipated.

### Pattern 4: LinksPage React Component
**What:** React component following MeetingsPage layout exactly
**Key differences from MeetingsPage:**
- "Visit Link" button in detail panel opens `window.open(url, '_blank')`
- `url` field displayed prominently
- Domain shown in list column instead of participant count
- Tag filter alongside title filter

```typescript
// frontend/src/types.ts additions
export interface LinkSummary {
  path: string
  title: string
  domain: string
  created_at: string
  tags: string[]
  snippet: string
}
```

```typescript
// frontend/src/contexts/UIContext.tsx — extend View union
type View = 'notes' | 'actions' | 'people' | 'meetings' | 'projects' | 'intelligence' | 'inbox' | 'links'
```

```typescript
// frontend/src/components/TabBar.tsx — add tab entry
const TABS = [
  // ... existing ...
  { id: 'links' as const, label: 'Links' },
]
```

```typescript
// frontend/src/App.tsx — import and render
import { LinksPage } from './components/LinksPage'
// in JSX: {currentView === 'links' && <LinksPage />}
```

### Anti-Patterns to Avoid
- **Bypassing capture_note() for write path:** The intelligence hooks (action extraction, connections) are wired in `capture_note()`. Calling `write_note_atomic()` directly bypasses them. The `url:` field injection must happen by setting `post["url"] = url` after `build_post()`, then calling `write_note_atomic()` directly — this is acceptable only because `capture_note()` doesn't accept extra frontmatter kwargs. Alternative: add `extra_fields: dict` param to `capture_note()` — cleaner but requires touching shared code.
- **Fetching full page HTML:** Only need the `<head>` section. Read max 65536 bytes and stop — prevents hanging on huge pages or streaming responses.
- **Blocking MCP tool on slow fetch:** The 10s timeout is already best-effort; no retry loop. Slow sites should time out quickly.
- **Opening URL in pywebview's WKWebView:** Use `window.open(url, '_blank')` in JS — pywebview passes this to the OS default browser, which is the correct behavior. Do NOT open in an iframe or in the pywebview window itself.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file write + DB index | Custom file write | `write_note_atomic()` | All integrity guarantees live there |
| Slug collision handling | Custom counter logic | Copy pattern from `capture_note()` | Already handles disk + DB collision check |
| URL domain extraction | Custom regex | `urllib.parse.urlparse(url).hostname` | Stdlib, handles edge cases |
| HTML meta parsing | Custom string split | `html.parser.HTMLParser` subclass | Handles encoding, entities, malformed HTML |
| Tag deserialization in API | Manual JSON parse | `json.loads(d.get("tags") or "[]")` | Established pattern, handles NULL |

---

## Common Pitfalls

### Pitfall 1: URL Not Stored as Queryable Column
**What goes wrong:** Storing `url:` only in frontmatter (file) but not as a dedicated column in the `notes` table makes URL dedup and search-by-URL expensive (requires LIKE scan or disk read).
**Why it happens:** `write_note_atomic()` only writes standard fields to DB; extra Post keys are ignored by the INSERT.
**How to avoid:** Add `url TEXT` column via `ALTER TABLE ADD COLUMN url TEXT DEFAULT NULL` migration in `db.py`, then extend `write_note_atomic()` to write it when present. The migration follows the same pattern as `migrate_add_people_column()`.
**Warning signs:** Dedup check doing full-table LIKE scan; `/links` endpoint having to read files from disk.

### Pitfall 2: Tasks 1+2 Must Be Committed Together (Frontend Build)
**What goes wrong:** App.tsx imports LinksPage — if App.tsx is committed without LinksPage.tsx existing, the Vite build fails.
**Why it happens:** All previous page additions (People, Meetings, Projects) had the same constraint — documented in STATE.md.
**How to avoid:** Commit App.tsx + LinksPage.tsx + TabBar.tsx + UIContext.tsx changes in a single plan. Do not split across plans unless the first plan adds a stub component.

### Pitfall 3: .secrets.baseline Hash Changes After Vite Build
**What goes wrong:** Vite produces a new hashed asset filename (e.g., `index-XYZabc.js`). detect-secrets picks up the new filename hash, failing the pre-commit hook.
**Why it happens:** Documented in STATE.md for every frontend build phase (27.4, 27.6, 27.8).
**How to avoid:** After `npm run build`, run `detect-secrets scan --update .secrets.baseline` before committing.

### Pitfall 4: fetch() to /links Returns Wrong url Field
**What goes wrong:** The `url:` frontmatter field is NOT stored in the `notes.body` DB column — body contains the user-visible description text. Relying on parsing `url:` from body fails.
**Why it happens:** `write_note_atomic()` writes `post.content` (body text) not the full frontmatter to DB.
**How to avoid:** Store `url:` in a dedicated DB column (see Pitfall 1). Fallback: read the file from disk in `GET /links/<path>` to extract url from frontmatter, same pattern as `GET /meetings/<path>` reads body from DB.

### Pitfall 5: pywebview window.open() Behavior
**What goes wrong:** `window.open(url, '_blank')` in pywebview WKWebView may open a new pywebview window rather than the OS browser.
**Why it happens:** pywebview intercepts navigation. This depends on pywebview version and platform.
**How to avoid:** Use `window.open(url, '_blank', 'noreferrer')` or test with Playwright first. Alternative: provide the URL as a plain `<a href target="_blank">` — pywebview typically passes these to the OS browser. Playwright test should verify `window.open` is called with the correct URL rather than asserting browser navigation.

### Pitfall 6: Metadata Fetcher Blocked by Bot Protection
**What goes wrong:** Sites like Twitter, LinkedIn, or Cloudflare-protected pages return 403/429 or empty content when fetched without a realistic User-Agent.
**Why it happens:** urllib sends a minimal UA by default.
**How to avoid:** Set `User-Agent: Mozilla/5.0 (second-brain link capture)` in the request headers (already shown in pattern above). If blocked, fall back to domain-as-title — this is explicitly the designed behavior.

---

## Code Examples

### DB Migration — url Column

```python
# engine/db.py — add alongside migrate_add_people_column pattern
def migrate_add_url_column(conn: sqlite3.Connection) -> None:
    """Add url column to notes table if absent. Safe to call repeatedly."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(notes)").fetchall()]
    if "url" not in cols:
        conn.execute("ALTER TABLE notes ADD COLUMN url TEXT DEFAULT NULL")
        conn.commit()
```

### write_note_atomic url Injection

```python
# In write_note_atomic(), extend the INSERT to include url column:
url_val = post.get("url")  # None if not a link note
conn.execute(
    f"{sql_verb} INTO notes (path, type, title, body, tags, people, created_at, updated_at, sensitivity, url)"
    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    (...existing args..., url_val),
)
```

### GET /links/<path> — Detail Endpoint

```python
@app.get("/links/<path:link_path>")
def get_link(link_path):
    try:
        p, _brain_root = _resolve_note_path(link_path)
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT path, title, body, url, tags, created_at FROM notes WHERE path=? AND type='link'",
        (str(p.resolve()),)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    d = dict(row)
    d["tags"] = json.loads(d.get("tags") or "[]")
    d["domain"] = urllib.parse.urlparse(d.get("url") or "").hostname or ""
    return jsonify(d)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No link type | Add `"link": "links"` to `TYPE_TO_DIR` | Phase 29 | Slug uses date-prefix pattern |
| No url frontmatter field | `url:` in YAML + `url` DB column | Phase 29 | Enables dedup, search-by-URL |
| 7 tabs (notes→inbox) | 8 tabs + links | Phase 29 | Add to `TABS` array + View union |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed) + pytest-playwright (installed) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_link_fetcher.py tests/test_links.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LINK-01 | `fetch_link_metadata()` returns title/description/domain | unit | `uv run pytest tests/test_link_fetcher.py -x` | Wave 0 |
| LINK-02 | `fetch_link_metadata()` returns domain fallback on network error | unit | `uv run pytest tests/test_link_fetcher.py -x` | Wave 0 |
| LINK-03 | `sb_capture_link` saves note with url: frontmatter field | unit | `uv run pytest tests/test_links.py::test_capture_link -x` | Wave 0 |
| LINK-04 | `GET /links` returns 200 with list including domain+snippet | unit | `uv run pytest tests/test_links.py::test_list_links -x` | Wave 0 |
| LINK-05 | `GET /links/<path>` returns 200 with url field | unit | `uv run pytest tests/test_links.py::test_link_detail -x` | Wave 0 |
| LINK-06 | LinksPage renders in tab bar; clicking tab shows page | e2e | `uv run pytest tests/test_gui.py::test_links_tab -x` | Wave 0 |
| LINK-07 | "Visit Link" button exists in detail panel | e2e | `uv run pytest tests/test_gui.py::test_links_visit_button -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_link_fetcher.py tests/test_links.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_link_fetcher.py` — covers LINK-01, LINK-02 (unit tests for fetcher with monkeypatched urllib)
- [ ] `tests/test_links.py` — already exists (empty); fill with LINK-03, LINK-04, LINK-05 stubs
- [ ] `tests/test_gui.py` additions — LINK-06, LINK-07 Playwright stubs seeded in gui_brain

---

## Open Questions

1. **url column vs. body LIKE scan for dedup**
   - What we know: `write_note_atomic()` only persists standard fields to DB
   - What's unclear: whether Phase 29 should add the `url` DB column migration now or defer to Phase 32 (Architecture Hardening)
   - Recommendation: Add the migration in Phase 29 — it's a simple `ALTER TABLE ADD COLUMN`; deferred in Phase 32 would require a retroactive migration anyway

2. **"Visit Link" button behavior in pywebview**
   - What we know: `window.open` in WKWebView may behave unexpectedly (see Pitfall 5)
   - What's unclear: exact pywebview 5.x behavior for `_blank` target
   - Recommendation: Use `<a href target="_blank" rel="noreferrer">` rendered as a Button-styled element; test with Playwright to confirm URL is correct

3. **Tag filter in LinksPage**
   - What we know: CONTEXT.md specifies "in-page search bar + tag filter (same pattern as Meetings/Notes pages)"
   - What's unclear: MeetingsPage only has title filter (no tag filter); which pattern to follow
   - Recommendation: Add both title filter and tag filter (chip-based) matching Notes page pattern; tag filter is explicitly in the spec

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `engine/capture.py`, `engine/mcp_server.py`, `engine/api.py`, `engine/db.py`
- Direct codebase inspection: `frontend/src/components/MeetingsPage.tsx`, `TabBar.tsx`, `UIContext.tsx`, `types.ts`
- `pyproject.toml` — confirmed no `requests` or `httpx` in dependencies
- `29-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- Python 3.13 stdlib docs: `urllib.request`, `html.parser` — stable APIs, no version concerns
- STATE.md decisions log — `Tasks 1+2 committed together` pattern verified across 6+ previous page phases

### Tertiary (LOW confidence)
- pywebview `window.open` behavior with `_blank` — not verified against pywebview 5.x docs; based on general WKWebView knowledge

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — confirmed from pyproject.toml; no new deps needed
- Architecture patterns: HIGH — direct code inspection of 4+ reference implementations
- Pitfalls: HIGH for build/secrets (STATE.md documented); MEDIUM for pywebview behavior

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable stack; pywebview behavior is the only uncertain item)
