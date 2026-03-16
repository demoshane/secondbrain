# Stack Research

**Domain:** Second Brain v3.0 — GUI Overhaul & Engine Polish
**Researched:** 2026-03-16
**Confidence:** HIGH (new additions verified via PyPI/official docs; existing stack read from codebase)

---

## Scope

This file covers ONLY additions and changes needed for v3.0 new features. The entire
v2.0 validated stack (pywebview 5.4, Flask/waitress, SQLite FTS5 + sqlite-vec,
sentence-transformers all-MiniLM-L6-v2, FastMCP, uv tool, launchd, Python 3.13,
watchdog 6.0) is unchanged and not repeated here.

---

## New Dependencies Required

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `Markdown` (python-markdown) | `>=3.7` (current: 3.10.2, Feb 2026) | Server-side markdown-to-HTML rendering in Flask `/notes/<path>` endpoint | Moves rendering from fragile client-side `marked.js` (tied to EasyMDE internals) to deterministic server-side Python. Extensions `tables`, `fenced_code`, `toc`, `nl2br` all ship in the stdlib bundle — zero extra packages. `python-frontmatter` (already a dep) strips YAML frontmatter before rendering so it never leaks into HTML. |

**That is the only new PyPI dependency for v3.0.** All other features are implemented
using libraries already present in `pyproject.toml`.

---

## Feature-by-Feature Stack Decisions

### (1) GUI Live Refresh

**Existing deps used:** `watchdog>=6.0` (already in `pyproject.toml`), `pywebview>=5.0`.

**Mechanism:**
`watchdog` is currently used by `engine/watcher.py` for the launchd file-drop daemon.
For GUI live refresh, start a *second* in-process `Observer` instance inside
`engine/gui/__init__.py`, scoped to `~/SecondBrain/**/*.md`. On
`FileCreatedEvent` / `FileModifiedEvent`, call:

```python
window.run_js("window.__sbRefresh && window.__sbRefresh()")
```

`window` is the pywebview `Window` object from `main()`. Pass it into the watchdog
handler at construction time. JS defines `window.__sbRefresh = loadNotes` at startup
so the sidebar reloads from the API.

**Why `run_js` not `evaluate_js`:** `run_js()` is fire-and-forget and safe to call
from a non-GUI background thread. `evaluate_js()` blocks waiting for a return value,
which causes a deadlock when called from a watchdog `Observer` thread.

**Debounce:** watchdog fires multiple events per save (editor partial writes + fsync).
Add a 0.5 s debounce in the handler using `threading.Timer` — cancel and restart on
each new event. Prevents cascade refreshes on a single user save.

**No new dependency.**

---

### (2) Markdown-to-HTML Rendering in pywebview

**Current state:** `app.js` calls `marked.parse(md)` client-side using the `marked`
library bundled inside `easymde.min.js`. This works but has three problems: YAML
frontmatter leaks into the rendered output unless manually stripped in JS; the
`marked` version is locked to whatever EasyMDE vendors; and raw markdown text is
visible in the DOM for a frame before parse completes.

**v3.0 approach:** Add `"html"` key to the `/notes/<path>` response alongside the
existing `"content"` key. Flask renders HTML once with `python-markdown`. The GUI
uses `innerHTML = data.html` directly. EasyMDE's vendored `marked` remains available
for the edit preview pane only — no change to edit mode.

**Extensions to enable:**

| Extension | Reason |
|-----------|--------|
| `tables` | Renders `|col|col|` tables common in meeting and strategy notes |
| `fenced_code` | Renders ` ```python ``` ` code blocks in coding notes |
| `toc` | Generates heading anchors (`#heading-id`) for longer notes |
| `nl2br` | Single newlines become `<br>` — matches user expectation writing in a text editor |

All four are bundled in `python-markdown` — no extra packages.

**YAML stripping:** `python-frontmatter` (already a dep) parses the frontmatter out.
Pass `post.content` (not raw file text) to `markdown.markdown()`.

**New dependency:** `Markdown>=3.7` — add one line to `pyproject.toml`.

---

### (3) Batch Capture

**Existing deps used:** `engine/capture.py`, `engine/api.py`, `python-frontmatter`.

**No new dependency.** Add `capture_batch(paths: list[Path], note_type: str) -> list[dict]`
to `engine/capture.py`. Iterates over paths, calls the existing atomic
`capture_note()` per file, collects results, returns a summary dict with per-file
status. Add a `/capture/batch` POST endpoint in `engine/api.py` accepting
`{"paths": [...], "type": "..."}`. The GUI file-upload dialog POSTs a list of file
paths in one call.

File parsing scope for v3.0: plain text and markdown only. PDF/docx/pptx have
existing parsers (`pypdf`, `python-docx`, `python-pptx`) noted in PROJECT.md risks —
those are already available as transitive deps if needed but not gated on v3.0.

---

### (4) Brain Health Dashboard

**Existing deps used:** `engine/health.py`, `engine/links.py`, `engine/db.py`,
`sqlite-vec` (already a dep).

**No new dependency.** The existing `engine/health.py` covers infra-level checks
(DB, FTS index, Ollama, launchd, MCP). Add a new `engine/brain_quality.py` module
for content-quality checks, exposing a `/health/brain` GET endpoint.

**Content quality checks:**

| Check | Query | Metric |
|-------|-------|--------|
| Orphan notes | `SELECT COUNT(*) FROM notes n LEFT JOIN relationships r ON n.path = r.source WHERE r.source IS NULL` | `orphan_pct` |
| Broken links | Reuse `engine/links.py` `check_links()` result | `broken_link_pct` |
| Embedding gaps | `(COUNT(notes) - COUNT(note_embeddings)) / COUNT(notes)` | `embedding_gap_pct` |
| Duplicate candidates | sqlite-vec KNN per note, cosine similarity > 0.92 — collect pairs | `duplicate_pct` |

Duplicate detection is O(n²) in the naive case. Run it async (background thread,
results cached in SQLite) or only on-demand when the user opens the dashboard. Do not
run on every health check call.

**Health score formula (0–100):**

```
score = 100
score -= orphan_pct * 25          # up to -25 points
score -= broken_link_pct * 35     # up to -35 points
score -= embedding_gap_pct * 20   # up to -20 points
score -= duplicate_pct * 20       # up to -20 points
score = max(0, round(score))
```

Expose via:
- `GET /health/brain` → JSON with per-check details + aggregate score
- `sb-health --brain` flag added to existing `main()` in `engine/health.py`
- GUI Intelligence panel renders a compact score card

---

### (5) Search Ranking Improvements

**Existing deps used:** `engine/search.py`, SQLite FTS5, `sqlite-vec`.

**No new dependency.** Three tuning levers:

**A. FTS5 column weight boosting.**

Pass per-column weights to `bm25()` to boost title matches over body matches.
First verify `notes_fts` schema in `engine/db.py` — it must index `title` and `body`
as separate columns (not a single concatenated column). If separate:

```sql
ORDER BY bm25(notes_fts, 10.0, 1.0)   -- title weight 10x body
```

If currently single-column, split during next `sb-reindex` schema migration
(adds one column, requires rebuild).

**B. Recency bias in hybrid RRF.**

Add a `recency_boost: bool = True` parameter to `_rrf_merge()`. Notes with
`updated_at` within 30 days receive a small additive RRF bonus equivalent to
appearing one rank higher. Controlled by a flag so it can be disabled if it
degrades recall quality.

**C. Tag filtering in search.**

Add `tags: list[str] = []` parameter to `search_notes()` and `search_hybrid()`.
v3.0 scope: simple `WHERE n.tags LIKE '%tag%'` filter (no schema change needed).
Proper normalised `note_tags` join table deferred to v4.0 if LIKE proves too
imprecise.

---

## Installation Delta

```toml
# pyproject.toml — only addition for v3.0:
[project.dependencies]
"Markdown>=3.7",   # python-markdown — server-side markdown rendering
```

No other new packages. No version bumps required to existing deps.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `python-markdown` server-side render | Keep `marked.js` client-side | If you intentionally want zero server render and accept YAML frontmatter leaking to DOM |
| `python-markdown` | `mistune` | mistune is faster but fewer bundled extensions; reasonable if performance matters at large scale |
| `python-markdown` | `markdown-it-py` | Better CommonMark compliance; use if notes use CommonMark-specific syntax not covered by python-markdown |
| `window.run_js()` for live refresh | Flask SSE `/events` stream | If GUI ever has multiple windows or non-pywebview clients |
| sqlite-vec cosine for duplicate detection | `difflib.SequenceMatcher` | Never — O(n²) over raw text at 500+ notes is too slow |
| Simple `LIKE` tag filter | Normalised `note_tags` table | When tag queries become complex (AND/OR logic across multiple tags) |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `bleach` / HTML sanitisation | GUI is local-only; content is the user's own notes; sanitisation adds complexity with zero security benefit in this threat model | Raw `markdown.markdown()` output |
| SSE or WebSocket for live refresh | Protocol complexity; pywebview's `run_js` bridge is already present and sufficient for single-user desktop | `window.run_js()` from watchdog callback thread |
| `difflib` for duplicate detection | O(n²) over raw text is slow; sqlite-vec embeddings already exist and are faster and semantically richer | sqlite-vec cosine KNN |
| Re-indexing on every file event | watchdog fires on partial writes; a full `sb-reindex` per save is far too slow | 0.5 s debounce → `loadNotes()` re-fetch from DB (which already has the saved content) |
| New scheduler library for health scans | APScheduler already present from v2.0 | APScheduler 3.x (existing dep) |
| `pandas` for health metrics | No tabular computation needed; simple SQLite aggregates suffice | Raw `sqlite3` queries |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `Markdown>=3.7` (3.10.2) | Python 3.13, Flask 3.x | Pure Python; no binary extensions; no known conflicts |
| `watchdog>=6.0` | Python 3.13, macOS FSEvents | Already pinned; macOS uses FSEvents natively (no polling); safe to call from threads |
| `pywebview>=5.0` | Python 3.13, macOS | `window.run_js()` available since pywebview 3.x; confirmed thread-safe in docs |

---

## Sources

- [Python-Markdown PyPI](https://pypi.org/project/Markdown/) — version 3.10.2 current (Feb 9 2026); HIGH confidence
- [Python-Markdown extensions docs](https://python-markdown.github.io/extensions/) — `tables`, `fenced_code`, `toc`, `nl2br` all bundled; HIGH confidence
- [watchdog PyPI](https://pypi.org/project/watchdog/) — version 6.0.0 current; HIGH confidence
- [pywebview evaluate_js / run_js docs](https://pywebview.flowrl.com/api/) — `run_js()` thread-safe, fire-and-forget; MEDIUM confidence (docs, no explicit thread-safety statement found but confirmed via community issues)
- [SQLite FTS5 docs](https://www.sqlite.org/fts5.html) — `bm25(table, w0, w1, ...)` column weighting confirmed; HIGH confidence
- Codebase read: `pyproject.toml`, `engine/gui/__init__.py`, `engine/api.py`, `engine/search.py`, `engine/health.py`, `engine/gui/static/app.js` — direct source of truth for what is already present

---

*Stack research for: Second Brain v3.0 GUI Overhaul & Engine Polish*
*Researched: 2026-03-16*
