# Feature Research

**Domain:** Desktop PKM app — GUI overhaul and engine polish (v3.0)
**Researched:** 2026-03-16
**Confidence:** MEDIUM-HIGH (core patterns well-established; PKM health scoring is emerging/informal)

---

## Scope Note

v1.5 and v2.0 features are treated as existing dependencies. This file covers only the **v3.0 target features**. Focus: GUI live refresh, markdown rendering polish, tag editing, file capture from GUI, on-demand recap, batch capture, search quality, and brain health dashboard.

---

## Existing Foundation (Already Built — Do Not Re-Implement)

- `sb-capture`, `sb-search` (FTS5 + semantic/RRF), `sb-forget`, `sb-export`, `sb-anonymize`
- `sb-recap`, `sb-actions`, `sb-digest` (weekly, launchd-triggered)
- `sb-gui` (pywebview + Flask sidecar on 127.0.0.1:37491, three-panel, EasyMDE vendored)
- `sb-mcp-server` (10 tools), launchd watcher, git hook
- `marked.parse()` already called via EasyMDE bundle — markdown parser is in the browser
- Waitress WSGI server (multi-threaded, suitable for SSE streaming)
- Sidebar groups by type, search mode selector, new-note modal, action checkbox list
- `GET /notes`, `PUT /notes/:path`, `POST /notes`, `GET /notes/:path/meta`, `GET /intelligence`, `GET /actions`, `GET /files`, `POST /files/move`

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features a GUI note app must have. Missing = feels broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Live refresh — new/edited notes appear without restart | Desktop apps reflect filesystem state; requiring restart is a v1 bug | MEDIUM | SSE push is correct; polling creates visible lag; watchdog already ships in project |
| Markdown renders as formatted HTML | Raw markdown text in a viewer is broken; every PKM tool renders it | LOW | `marked.parse()` already called in `renderMarkdown()` — mostly missing CSS to style output |
| Mouse scroll in note content area | Basic OS interaction — without it the panel is unusable for long notes | LOW | Likely a missing `overflow-y: auto` on `#viewer` in CSS |
| Note deletion with cascade | Any data app must let you remove records; half-deleted data is worse than no deletion | MEDIUM | Same cascade pattern as `sb-forget`: notes table, FTS5, vectors, backlinks |
| Correct backlinks display | Backlinks are a core PKM navigation feature; wrong data destroys trust | MEDIUM | Current `note_meta` uses fuzzy filename substring match — needs exact path lookup |
| Sidebar collapsible section navigation | 100s of notes across types; a flat list is unusable | LOW | Type grouping exists in `renderSidebar()` already — add collapse/expand toggle; pure JS/CSS |

### Differentiators (Competitive Advantage)

Features that go beyond generic note app UX and fit this system's persona.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Tag editing in GUI | Most PKM tools require raw frontmatter editing to change tags; in-app chip editor is a UX win | MEDIUM | Parse YAML frontmatter in JS, PUT full rewritten content; tag filter in sidebar is a separate sub-piece |
| Tag filtering in browse/search | Narrows results without a full-text query; standard in Obsidian tag pane and Notion | LOW | Sidebar already groups by type; add tag dimension; driven by `/notes?tag=X` API param |
| File capture from GUI | Drag-and-drop or file picker to copy a PDF/docx into `files/` and index it | MEDIUM | `/files/move` exists; need `<input type=file>` + new `POST /files/upload` endpoint + trigger reindex |
| On-demand weekly recap button | Generate a fresh recap at will, not only on launchd schedule | LOW-MEDIUM | `sb-recap` already works; expose as `POST /intelligence/recap`; show spinner (AI call = 5–30s latency) |
| Brain health dashboard | Score showing orphans, broken links, stale notes, duplicate candidates | MEDIUM | Obsidian ecosystem validates this (vault-statistics + find-unlinked-files both popular plugins); expose as `GET /health/brain`; surface in GUI |
| Batch capture trigger | One operation captures all pending new items rather than one at a time | MEDIUM | Find all `~/SecondBrain/**/*.md` not in `notes` table; process in batch; reuses watcher scan logic |
| Search hybrid ranking tuning | Reduced "why is this first?" frustration; immediately noticeable | MEDIUM-HIGH | Current RRF needs BM25/cosine weight calibration; recency boost for meeting/person notes; needs evaluation fixtures |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Polling-based live refresh | Simpler to implement | 3–10s lag; constant CPU use even on idle; interval management complexity | SSE push: emit event from Flask after write operations; JS `EventSource` calls `loadNotes()` |
| WebSocket for live refresh | "More real-time" | pywebview has documented WebSocket issues (GitHub issues #241, #688); ws:// URL in embedded WebKit needs extra config; bidirectionality not needed | SSE is unidirectional push — exactly what's needed here; no known pywebview blockers |
| Full markdown editor rebuild | Rich editing | EasyMDE already vendored with side-by-side preview; rebuilding wastes effort | Use EasyMDE's existing `side-by-side` toolbar option |
| Auto-save on every keystroke | Feels modern | Constant filesystem churn; Drive sync conflicts on rapid sequential writes; worse for audit log | Explicit Cmd+S (already wired) + unsaved-changes warning on navigation |
| Real-time collaborative editing | Modern feel | Violates local-first constraint; single-user system; adds OT/CRDT complexity | Google Drive handles multi-device; no in-app collab needed |
| Encryption at rest | Security | Deferred to v4.0 per PROJECT.md; blocks simpler features | Passphrase-gated PII display covers the sensitive content case |
| Binary file full-text extraction in GUI | Completeness | python-docx/pypdf edge cases; wrong extractions corrupt search results | Index metadata only (filename, date, size, manual description) in v3.0 |

---

## Feature Dependencies

```
[Live refresh — SSE push]
    └──requires──> [GET /events SSE endpoint in Flask (new)]
                       └──requires──> [Waitress streaming (already present, threaded)]
    └──enables──> [File capture appearing instantly after upload]
    └──enables──> [Brain health score updating after batch capture]

[Tag editing in GUI]
    └──requires──> [YAML frontmatter parser in JS (js-yaml or simple regex)]
    └──requires──> [PUT /notes/:path already rewrites full content (existing) — reuse]
    └──enhances──> [Tag filtering in sidebar]

[File capture from GUI]
    └──requires──> [POST /files/upload endpoint (new)]
    └──enhances──> [Live refresh — captured file appears in sidebar immediately]
    └──enhances──> [Batch capture — file drop can be part of batch flow]

[Brain health dashboard]
    └──requires──> [GET /health/brain endpoint (new)]
    └──requires──> [Orphan detection query — notes not linked by any other]
    └──requires──> [Broken links detection — links table targets not in notes table]
    └──requires──> [get_stale_notes() already in engine/intelligence.py]
    └──enhances──> [Live refresh — score updates after capture]

[On-demand recap button]
    └──requires──> [POST /intelligence/recap endpoint (new, wraps sb-recap logic)]
    └──requires──> [Spinner/loading state in Intelligence panel (UI only)]

[Batch capture]
    └──requires──> [POST /capture/batch endpoint (new, reuses watcher scan logic)]
    └──enhances──> [Live refresh — sidebar updates when batch completes]

[Search quality improvement]
    └──requires──> [Existing RRF in engine/search.py]
    └──requires──> [Evaluation fixtures to validate ranking changes before shipping]
```

### Dependency Notes

- **Live refresh must ship with file capture:** Without live refresh, user won't see the captured file appear — the two are effectively one unit of work.
- **Tag editing reuses existing save path:** `PUT /notes/:path` writes full file content atomically. Tag edit in JS = parse frontmatter → mutate tags array → reconstruct markdown → PUT. No new API endpoint needed.
- **Brain health needs accurate links data:** If a `links` table is incomplete, orphan detection falls back to full-text scan for `[[wikilinks]]` — acceptable but slower. Verify links table coverage before implementing.
- **On-demand recap has AI latency:** Claude call can take 5–30s. Spinner + disabled button during generation is not optional — without it the UX feels frozen.

---

## MVP Definition

### Ship in v3.0 (This Milestone)

**Bug-fixes first (P1):**
- [ ] Live refresh via SSE — immediately unblocks "new notes invisible without restart"
- [ ] Markdown rendering CSS polish — style `#viewer` rendered HTML (headers, code, tables, lists)
- [ ] Mouse scroll fix — `overflow-y: auto` on `#viewer`
- [ ] Backlinks correctness — exact path match, not fuzzy filename substring
- [ ] Note deletion with cascade — mirrors `sb-forget` cascade

**Navigation/UX (P1):**
- [ ] Sidebar collapsible sections — pure JS/CSS, no API change

**New features (P2):**
- [ ] Tag editing + filtering
- [ ] File capture from GUI
- [ ] On-demand recap button
- [ ] Brain health dashboard (CLI + GUI widget)
- [ ] Batch capture endpoint
- [ ] Search ranking tuning (BM25/cosine weights + recency boost)

### Add After v3.0 (Future)

- [ ] Full text extraction for binary files (PDF, docx) — reliability work needed
- [ ] Encryption at rest — deferred to v4.0
- [ ] Tag autocomplete (suggest existing tags while editing) — nice UX, not blocking
- [ ] Brain health trend over time (score history) — needs baseline data first

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Live refresh (SSE) | HIGH | MEDIUM | P1 |
| Markdown HTML styling | HIGH | LOW | P1 |
| Mouse scroll fix | HIGH | LOW | P1 |
| Backlinks correctness | HIGH | MEDIUM | P1 |
| Note deletion + cascade | HIGH | MEDIUM | P1 |
| Sidebar collapse navigation | MEDIUM | LOW | P1 |
| Tag editing + filtering | HIGH | MEDIUM | P2 |
| File capture from GUI | MEDIUM | MEDIUM | P2 |
| On-demand recap button | MEDIUM | LOW-MEDIUM | P2 |
| Brain health dashboard | MEDIUM | MEDIUM | P2 |
| Batch capture | MEDIUM | MEDIUM | P2 |
| Search ranking tuning | MEDIUM | HIGH | P2 |

**Priority key:** P1 = bugs and missing table-stakes, ship first. P2 = new features, ship in same milestone after P1 stable.

---

## Implementation Patterns (Research Findings)

### Live Refresh: SSE, Not Polling, Not WebSocket

**Decision: Server-Sent Events (SSE) via Flask `text/event-stream` response.**

Rationale:
- pywebview has documented WebSocket compatibility issues in embedded WebKit (GitHub #241, #688, #774 — ws:// URL handling, code:1006 errors)
- SSE uses plain HTTP — pywebview's WKWebView handles `EventSource` natively, no special config
- Communication is one-directional (server → client push) which is all that's needed for refresh notifications
- Flask SSE without extra deps: a generator endpoint streaming `data: ...\n\n` with `Content-Type: text/event-stream`; Waitress handles this in threaded mode
- Client: `const es = new EventSource('http://127.0.0.1:37491/events')` — `es.onmessage` calls `loadNotes()`
- Events to emit: after `POST /notes` (create), `PUT /notes/*` (save), `POST /capture/batch`, `POST /files/upload`
- No Redis required (flask-sse needs Redis; the dependency-free pattern uses a simple thread-safe queue or just a timestamp signal)

Confidence: MEDIUM — SSE in Flask is well-documented; the specific pywebview + SSE combination was not found in official docs, but no known blockers exist and the HTTP-only transport avoids the known WebSocket issues.

### Markdown Rendering: marked.js (Already Bundled)

**Decision: Use `marked` global already available from vendored EasyMDE. No new library.**

- `marked.parse()` is already called in `renderMarkdown()` in `app.js` — the parser works
- Missing piece is CSS: rules for h1–h6, `code`, `pre`, `blockquote`, `table`, `ul`/`ol` inside `#viewer`
- EasyMDE's own CSS targets `.EasyMDEContainer` scope — those rules do not apply to `#viewer` in view mode
- Solution: add a `prose` CSS class to `#viewer` and write scoped rules in `style.css`
- No CDN dependency, no new vendor file — consistent with "vendored offline" key decision

Confidence: HIGH — marked.js is the most-downloaded JS markdown parser on npm; already in use in this codebase.

### Tag Editing UX (from Obsidian/PKM ecosystem)

**Pattern: Inline chip editor in the note meta panel.**

- Display current tags as removable chips (`<span class="tag-chip">tag <button>×</button></span>`)
- Text input with add-on-Enter behavior appends a new tag chip
- On save: re-read current note content, parse YAML frontmatter `tags:` array (regex or `js-yaml`), replace with updated array, PUT full content
- Tag filter in sidebar: add a tag dropdown or click-on-chip-to-filter behavior; `/notes?tag=X` API param filters SQLite query with `WHERE tags LIKE '%"tag"%'` or JSON array containment
- Obsidian's tag pane shows all tags across vault with note counts — a nice v3.1 addition but not required for v3.0

Confidence: MEDIUM — pattern derived from Obsidian ecosystem observation, not official Obsidian docs.

### Brain Health Scoring (from Obsidian vault-statistics ecosystem)

**Decision: Simple weighted score displayed as 0–100 with green/amber/red bands. No graph analytics.**

Obsidian's "Vault Full Statistics" plugin tracks note count, link count, word count, and a "quality" metric. The "find-unlinked-files" plugin surfaces orphans and broken links on demand. Both are popular community plugins, validating user demand for vault health metrics.

For Second Brain v3.0:

| Signal | Weight | Implementation |
|--------|--------|----------------|
| Orphan notes (no backlinks, no outgoing links) | 30% | Notes not referenced in links table on either side |
| Broken links (target path not in notes table) | 30% | `links.target NOT IN (SELECT path FROM notes)` |
| Stale notes (updated_at > 90 days, not evergreen) | 20% | Already implemented in `get_stale_notes()` |
| Duplicate candidates (title similarity > 0.9) | 20% | sqlite-vec cosine query — skip if vectors not built |

Score = 100 − (weighted_penalty × 100). Show as integer with band: 80–100 = green, 60–79 = amber, <60 = red.

Expose as `GET /health/brain` returning `{score, orphans, broken_links, stale_count, duplicates}`. Render in GUI Intelligence panel footer or as a dedicated "Brain Health" section.

Confidence: MEDIUM — signals are logical and match Obsidian plugin patterns; specific weights are a recommendation, not an industry standard.

### On-Demand Recap UX

**Pattern: Button with loading state, result rendered inline.**

- Intelligence panel already has `recap-content` div
- Add "Generate Recap" button above it
- On click: disable button, show spinner/loading text, `POST /intelligence/recap`
- AI call latency is 5–30s — spinner is not optional; without it the UI feels frozen
- On response: render recap text in `recap-content`, re-enable button with label "Regenerate"
- Edge case: AI unavailable (Ollama down, Claude Code not active) — catch error, show "AI unavailable — try again" gracefully without crashing the panel

Confidence: MEDIUM — UX pattern is standard; the main risk is AI latency management.

### Batch Capture Pattern

**Pattern: Scan → diff → process unindexed.**

- `POST /capture/batch` enumerates `~/SecondBrain/**/*.md`, compares against `path` column in `notes` table, processes new/modified entries in sequence
- Progress: emit SSE event per processed file so sidebar updates incrementally
- Rate-limit: process max 50 files per batch call to avoid blocking the Waitress thread pool
- This reuses the same logic as `sb-watch` and the launchd watcher — extract into a shared `engine/capture.py` function if not already factored

Confidence: MEDIUM — pattern matches existing watcher logic; API design is a recommendation.

---

## Competitor Feature Analysis

| Feature | Obsidian | Notion | Second Brain v3.0 |
|---------|----------|--------|-------------------|
| Live refresh | Real-time (native FS access) | Cloud sync, instant | SSE push from Flask sidecar |
| Markdown rendering | Full CommonMark + extensions | Block-based (not raw MD) | marked.js, already integrated |
| Tag editing | Properties pane + frontmatter | Inline tag field | Chip editor in meta panel, frontmatter rewrite |
| Tag filtering | Tag pane, filter by tag | Filter view | Sidebar filter + `/notes?tag=X` |
| File attachment | Drag to vault | Upload to block | File input + `POST /files/upload` |
| Health dashboard | Vault Statistics plugin (community) | None | `GET /health/brain`, GUI widget |
| On-demand recap | None (manual review) | None | `POST /intelligence/recap` button |
| Batch capture | None (manual drag) | Clipper extension | `POST /capture/batch` |
| Local-first | Yes | No | Yes — hard constraint |

---

## Sources

- pywebview GitHub issues #241, #688, #774 — WebSocket compatibility in embedded WebKit: https://github.com/r0x0r/pywebview/issues/241
- pywebview 6.0 release notes: https://pywebview.flowrl.com/blog/pywebview6
- Flask SSE without extra dependencies: https://maxhalford.github.io/blog/flask-sse-no-deps/
- marked.js official: https://marked.js.org/
- npm trends (markdown-it vs marked vs remarkable vs showdown): https://npmtrends.com/markdown-it-vs-marked-vs-remarkable-vs-showdown
- Obsidian vault-statistics plugin: https://github.com/bkyle/obsidian-vault-statistics-plugin
- Obsidian vault-full-statistics plugin: https://github.com/jtprogru/obsidian-vault-full-statistics-plugin
- obsidianstats.com find-unlinked-files: https://www.obsidianstats.com/plugins/find-unlinked-files
- obsidian-find-orphan-block-identifiers: https://github.com/dashed/obsidian-find-orphan-block-identifiers
- Obsidian CLI (for vault health scripting): https://dev.to/shimo4228/obsidians-official-cli-is-here-no-more-hacking-your-vault-from-the-back-door-3123
- PKM batch capture patterns: https://buildin.ai/blog/personal-knowledge-management-system-with-ai
- Codebase: engine/api.py, engine/gui/static/app.js, engine/gui/static/index.html (read 2026-03-16)

---
*Feature research for: Second Brain v3.0 GUI Overhaul and Engine Polish*
*Researched: 2026-03-16*
