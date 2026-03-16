# Project Research Summary

**Project:** Second Brain v3.0 — GUI Overhaul and Engine Polish
**Domain:** Local-first desktop personal knowledge management (pywebview + Flask + SQLite)
**Researched:** 2026-03-16
**Confidence:** HIGH (grounded in direct code inspection; all recommendations reference the actual codebase)

## Executive Summary

Second Brain v3.0 is a polishing milestone on an already-working system. The v2.0 stack (pywebview, Flask/waitress, SQLite FTS5 + sqlite-vec, sentence-transformers, FastMCP, launchd) is validated and unchanged. The v3.0 work falls into two categories: fixing broken-feeling table-stakes behavior in the GUI (live refresh, scroll, markdown rendering, backlinks accuracy, note deletion), and layering on targeted new features (tag editing, file capture, on-demand recap, brain health dashboard, batch capture, search tuning). The recommended approach is to fix the bugs first — the P1 list is short, low-risk, and has high user impact — then ship new features in a coherent second sweep. Only one new PyPI dependency is required across the entire milestone (`Markdown>=3.7`), and even that is optional depending on the markdown rendering decision described in the gaps section.

The architecture is fully understood through direct code inspection. Every feature has a clear landing zone: new Flask routes in `engine/api.py`, logic in existing engine modules (`capture.py`, `health.py`, `intelligence.py`, `search.py`), and JS/CSS additions in `engine/gui/static/`. No new top-level files or directories are needed. The GUI-to-engine boundary is hard — the JS layer calls Flask endpoints only, never imports Python — so every new capability requires a corresponding new or extended route. The SSE live-refresh infrastructure (`GET /events`, `_notify()` helper) is the single most important piece to land early because it unblocks every subsequent write operation from a UX standpoint.

The key risks are not technical unknowns — they are known implementation shortcuts that must be addressed in v3.0 before they become costly. Path traversal in the notes API, XSS from unsanitized `marked.parse()` output, and duplicate note creation from the GUI-upload/watcher race are all preventable with targeted one-to-five line fixes. The cascade delete pattern already exists in `forget.py` but must be extracted into a shared `delete_note()` utility before GUI deletion is added, or the pattern will be repeated incorrectly on the new endpoint.

---

## Key Findings

### Recommended Stack

The v2.0 stack requires no version changes. Add `Markdown>=3.7` to `pyproject.toml` only if choosing the server-side rendering path (see Gap 1). The watchdog, pywebview, SQLite, and Flask versions already in `pyproject.toml` cover all new feature requirements without upgrade.

**Core technologies for v3.0 additions:**
- `watchdog>=6.0` (already present): second Observer instance for GUI live-refresh — use `window.run_js()` (fire-and-forget, thread-safe) not `evaluate_js()` (blocks, causes deadlock from watchdog thread)
- `queue.SimpleQueue` (stdlib): in-process SSE event bus — zero new dependencies, replaces the need for Redis or flask-sse
- `marked.js` (already vendored in EasyMDE): client-side markdown rendering — strip YAML frontmatter with a one-line regex before `marked.parse()`; vendor DOMPurify alongside it
- `werkzeug.utils.secure_filename` (already present): path-safe file upload handling
- SQLite FTS5 `bm25()` column weights (already present): title-boosted search ranking without schema change

See `.planning/research/STACK.md` for full details and alternatives considered.

### Expected Features

**Must have — P1 bugs (table stakes the GUI currently lacks):**
- Live refresh via SSE — new/edited notes invisible without restart is a critical bug
- Markdown CSS polish — `#viewer` renders raw markdown text; scoped `prose` CSS class rules fix this
- Mouse scroll fix — `overflow-y: auto` on `#viewer`; currently unusable for long notes
- Backlinks correctness — fuzzy `LIKE` filename match replaced with exact `relationships` table query
- Note deletion with full cascade — mirrors `sb-forget` pattern; must use shared `delete_note()` utility
- Sidebar collapsible sections — type grouping already in `renderSidebar()`; needs toggle UI

**Should have — P2 new features (competitive differentiators):**
- Tag editing in GUI — inline chip editor; `PATCH /notes/<path>/tags` endpoint; no full-body roundtrip
- Tag filtering in sidebar/search — `tag` param on `/search`; `WHERE tags LIKE '%tag%'` initially
- File capture from GUI — `POST /files/upload` (multipart); hidden `<input type="file">`; watcher dedup guard required
- On-demand recap button — `POST /recap/trigger`; spinner mandatory (5-30s AI latency)
- Brain health dashboard — `GET /health/brain`; `BRAIN_CHECKS` group in `engine/health.py`; 0-100 score
- Batch capture endpoint — `POST /batch-capture`; structured per-item success/failure result required
- Search ranking tuning — BM25 column weights + recency boost; regression suite required before shipping

**Defer to v4.0+:**
- Binary file full-text extraction (PDF/docx reliability work needed)
- Encryption at rest
- Tag autocomplete
- Brain health trend over time (needs baseline data first)
- Relative paths in DB (schema migration; absolute paths acceptable until first migration event)

See `.planning/research/FEATURES.md` for full prioritization matrix and competitor analysis.

### Architecture Approach

The system is a single-user local desktop app with a hard boundary between the GUI layer (pywebview WebView running vanilla JS) and the engine layer (Flask/waitress sidecar on `127.0.0.1:37491`). All changes land in existing files — no new modules needed. The SSE event bus (`queue.SimpleQueue` in `api.py`) is the backbone: once `GET /events` and `_notify()` are in place, every write endpoint gains live-refresh for free by calling `_notify()` at the end. The `sb-watch` daemon bridges to SSE via `POST /internal/notify` over loopback.

**Major components and their v3.0 responsibilities:**
1. `engine/api.py` — adds 8 new routes: `/events`, `/internal/notify`, `DELETE /notes/<path>`, `PATCH /notes/<path>/tags`, `POST /files/upload`, `POST /recap/trigger`, `GET /health/brain`, `POST /batch-capture`
2. `engine/gui/static/app.js` — adds: EventSource subscriber, tag chip editor, file upload handler, health panel renderer, sidebar collapse, frontmatter strip before `marked.parse()`
3. `engine/health.py` — adds: `BRAIN_CHECKS` list and `compute_brain_score()`
4. `engine/capture.py` — adds: `batch_capture(items)` wrapping existing `capture_note()` in a single transaction
5. `engine/search.py` — modifies: `tag_filter` param; optional BM25 column weight tuning in `_rrf_merge()`
6. `engine/intelligence.py` — modifies: expose `generate_recap()` as a callable for the on-demand endpoint

Build order from architecture research: markdown/scroll fixes (pure frontend) → backlink/title-sync fixes → SSE infrastructure (unlocks all subsequent features) → delete + security hardening → sidebar collapse → tags → file upload → recap → health dashboard → batch capture → search tuning last (needs regression fixtures).

See `.planning/research/ARCHITECTURE.md` for full component mapping, data flow diagrams, and anti-patterns.

### Critical Pitfalls

1. **Path traversal in `/notes/<path>` API** — `GET` and `PUT` accept arbitrary paths with no `BRAIN_ROOT` validation. Add a resolved-path prefix check returning 403 before any file read/write. Must be in place before `DELETE /notes/<path>` ships. Also remove `brain_path` from the `POST /notes` request body.

2. **XSS via `marked.parse()` without DOMPurify** — becomes exploitable as soon as file upload enables external content import. One-line fix: `viewer.innerHTML = DOMPurify.sanitize(marked.parse(stripFrontmatter(md)))`. Vendor DOMPurify alongside EasyMDE. Never acceptable to defer once file upload ships.

3. **Cascade delete missing `note_embeddings` and `relationships`** — the full cascade exists in `forget.py` but is inline. Extract `delete_note(path, conn, brain_root)` utility; both `forget_person` and `DELETE /notes/<path>` must call it. A naive delete endpoint that only hits the `notes` table leaves orphan rows that corrupt brain health scores.

4. **Watcher fires on GUI-uploaded files — duplicate notes** — `sb-watch` monitors `files/`; GUI upload writes there and triggers a second `capture_note`, producing two sidebar entries. Fix: module-level `{path: expire_monotonic}` "recently captured" registry in `watcher.py`; GUI upload registers the path for 10 seconds; watcher skips registered paths.

5. **Batch capture partial failure is silent** — per-note atomicity is correct; do not wrap all items in one transaction. The problem is the absence of a structured result. Must return `{"succeeded": [...], "failed": [{"item": ..., "reason": ...}]}`. Never use `except Exception: pass` in the batch loop.

6. **RRF tuning regresses exact-match precision** — boosting vector weight improves recall but degrades precision (exact name/slug queries drop from rank 1). Establish a fixed regression suite (5 precision + 5 recall queries) before touching any `_rrf_merge` parameter. Keep `k=60`.

7. **Brain health false positives after BRAIN_ROOT path change** — all paths stored as absolute; if `BRAIN_ROOT` moves, every stored path fails `.exists()`. Detect stale-prefix pattern; emit a single "run sb-reindex" warning instead of hundreds of individual orphan alerts.

See `.planning/research/PITFALLS.md` for full pitfall descriptions, warning signs, and the "looks done but isn't" verification checklist.

---

## Implications for Roadmap

Based on combined research, the dependency graph from ARCHITECTURE.md drives a natural phase structure. The SSE infrastructure is the central dependency — everything after it benefits from live refresh. Security hardening must not slip past the deletion phase.

### Phase 1: Frontend Bug Fixes
**Rationale:** Zero backend dependencies; pure JS/CSS changes; delivers immediate user-visible quality improvement; unblocks accurate testing of all subsequent phases.
**Delivers:** Usable viewer (scroll, rendered markdown, no YAML frontmatter bleed), accurate backlinks, title sync after save.
**Addresses:** GUIX-02 (title sync), GUIX-03 (markdown rendering), GUIX-04 (scroll fix), GUIX-05 (backlinks correctness).
**Avoids:** Frontmatter-in-viewer UX pitfall; sets up DOMPurify addition before file upload arrives.
**Research flag:** Standard patterns — skip research-phase.

### Phase 2: Live Refresh Infrastructure (SSE)
**Rationale:** SSE event bus is the backbone; once `_notify()` exists, every write in phases 3-6 gets live refresh for free. Must ship before note deletion, file upload, tags, or batch capture.
**Delivers:** Notes appear in sidebar the moment they are created or edited anywhere (GUI, CLI, watcher daemon).
**Addresses:** GUIX-01 (live refresh).
**Uses:** `queue.SimpleQueue` (stdlib), watchdog `run_js()` bridge, `POST /internal/notify` for watcher process.
**Avoids:** DB-row-before-file-on-disk race — GUI must retry on transient 404 before showing an error.
**Research flag:** Validate SSE + pywebview `EventSource` compatibility with a minimal proof-of-concept before building the full infrastructure. Otherwise standard patterns.

### Phase 3: Note Deletion + Security Hardening
**Rationale:** Deletion adds a destructive write endpoint — path traversal guard must be in place first. Extract `delete_note()` cascade utility here so it is reused correctly by all future deletion surfaces.
**Delivers:** Users can delete notes from GUI; no orphan DB rows; path traversal blocked on all endpoints; confirmation dialog prevents accidental data loss.
**Addresses:** GUIX-06 (note deletion); path traversal guard (Pitfall 8).
**Avoids:** Cascade-miss pitfall (Pitfall 4); path traversal pitfall (Pitfall 8); accidental person-profile erasure without warning.
**Research flag:** Standard patterns — cascade pattern already in `forget.py`; path traversal guard is a standard web security pattern.

### Phase 4: Navigation Polish (Sidebar Collapse + Tags)
**Rationale:** Sidebar collapse and tag editing/filtering are pure navigation improvements with no inter-phase dependencies beyond SSE. Grouped together because both improve browse ergonomics and neither affects data integrity.
**Delivers:** Collapsible sidebar type-groups; tag chip editor in viewer; tag filter dropdown in sidebar.
**Addresses:** GNAV-01 (sidebar collapse), GNAV-02 (tag editing), GNAV-03 (tag filter).
**Avoids:** Tag-save-without-FTS-update pitfall — tags must update both frontmatter and `notes.tags` DB column + FTS row (targeted update, not full reindex).
**Research flag:** Standard patterns — skip research-phase. Confirm `tags` column existence in `engine/db.py` schema at phase start (Gap 3).

### Phase 5: File Capture + Batch Capture
**Rationale:** File upload and batch capture both write to the filesystem and both need the watcher dedup guard. Group them so the dedup registry is implemented once. DOMPurify must be vendored before this phase ships — file upload introduces external content.
**Delivers:** Drag-or-pick file upload from GUI; batch capture of all unindexed markdown files; no duplicate notes from watcher race; structured per-item batch result.
**Addresses:** GUIF-01 (file upload), ENGL-01 (batch capture).
**Avoids:** Watcher-duplicate pitfall (Pitfall 2); XSS pitfall (Pitfall 3 — DOMPurify required before this phase ships); batch partial-failure silence (Pitfall 5).
**Research flag:** Standard patterns — skip research-phase.

### Phase 6: Intelligence Features (Recap + Brain Health)
**Rationale:** On-demand recap and brain health dashboard are independent additive features. Both depend on SSE (Phase 2) for UI feedback. Low risk to ship together as "intelligence additions."
**Delivers:** "Generate Recap" button with spinner in Intelligence panel; brain health score widget with orphan/broken-link/duplicate checks; `sb-health --brain` CLI flag.
**Addresses:** GUIF-02 (on-demand recap), ENGL-04 (brain health data), ENGL-05 (health score).
**Avoids:** Brain health false positive on path change (Pitfall 7); "0 orphans = healthy" when relationships table is empty (UX: distinguish "no issues found" from "nothing checked").
**Research flag:** Standard patterns — skip research-phase. All check patterns already established in `engine/health.py`.

### Phase 7: Search Quality Tuning
**Rationale:** Comes last because it requires evaluation fixtures that can only be built once real notes are flowing through the system. No user-facing feature is blocked on it.
**Delivers:** BM25 column weight boosting for title matches; optional recency boost for recent notes; tag filter in search results.
**Addresses:** ENGL-02 (search hybrid ranking tuning), ENGL-03 (AI quality — prompt improvements).
**Avoids:** RRF precision-regression pitfall (Pitfall 6 — regression suite required and gated before any parameter change).
**Research flag:** Needs `/gsd:research-phase` — RRF weight calibration is empirical and requires evaluation fixtures built against the actual note corpus. Do not begin implementation without a regression suite in place.

### Phase Ordering Rationale

- Frontend fixes first (Phase 1): zero-risk pure-frontend changes that make all subsequent testing meaningful.
- SSE second (Phase 2): backbone infrastructure — phases 3-6 all call `_notify()` for free once it exists.
- Deletion + security third (Phase 3): a destructive endpoint (DELETE) must not ship without the path traversal guard; cascade utility extracted here reused later.
- Navigation fourth (Phase 4): self-contained quality-of-life improvement before the more complex capture work.
- Capture fifth (Phase 5): file upload introduces external content (XSS risk, watcher dedup risk); DOMPurify and the dedup registry must be in place first.
- Intelligence sixth (Phase 6): additive features that do not affect data integrity; low risk to ship after the core UX is solid.
- Search tuning last (Phase 7): empirical and iterative; cannot be done correctly without a regression fixture set.

### Research Flags

Phases needing deeper research during planning:
- **Phase 7 (Search Quality):** RRF weight calibration is empirical — build evaluation fixtures against the actual note corpus before touching any `_rrf_merge` parameters.
- **Phase 2 (SSE):** Validate `EventSource` + pywebview WebKit compatibility with a minimal proof-of-concept at phase start before committing to the full SSE architecture.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Pure CSS/JS changes; all patterns identified in code inspection.
- **Phase 3:** Cascade pattern already in `forget.py`; path traversal guard is a standard web security one-liner.
- **Phase 4:** All patterns derived from existing `renderSidebar()` and `PUT /notes/<path>` code paths.
- **Phase 5:** `capture_note()` already exists; dedup registry is a simple dict; werkzeug `secure_filename` is documented.
- **Phase 6:** `engine/health.py` check pattern already established; `generate_recap()` already callable from CLI.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | One new dep (`Markdown>=3.7`) verified on PyPI; all others read directly from `pyproject.toml`; version compatibility confirmed |
| Features | MEDIUM-HIGH | P1 bugs confirmed via code inspection (HIGH); P2 feature patterns derived from Obsidian ecosystem observation (MEDIUM) |
| Architecture | HIGH | All component boundaries, data flows, and implementation sketches derived from direct code inspection of the actual source files |
| Pitfalls | HIGH | All critical pitfalls grounded in direct code reading; security findings (path traversal, XSS) are standard web security patterns with HIGH confidence |

**Overall confidence:** HIGH

### Gaps to Address

- **Gap 1 — Server-side vs. client-side markdown rendering:** STACK.md recommends adding `python-markdown` for server-side rendering; ARCHITECTURE.md recommends staying with the already-vendored `marked.js` (client-side, no new dep). These contradict each other. ARCHITECTURE.md is more grounded (direct code inspection). Recommended resolution at Phase 1 planning: use client-side `marked.js` with frontmatter strip — no new dependency, consistent with existing design. Only choose server-side if rendered HTML needs to be consumed by MCP or API clients.

- **Gap 2 — SSE in pywebview WebKit not explicitly confirmed:** FEATURES.md notes that SSE + pywebview was inferred from the absence of known blockers, not confirmed from official docs. Validate with a two-line proof-of-concept (`EventSource` hitting a test `/events` endpoint) at the start of Phase 2 before building the full SSE infrastructure.

- **Gap 3 — `tags` column existence in `notes` table schema:** ARCHITECTURE.md notes the `tags` column needs confirmation against `engine/db.py init_schema`. Confirm at Phase 4 planning start; if absent, add via non-breaking `ALTER TABLE ADD COLUMN tags TEXT DEFAULT ''`.

- **Gap 4 — Search regression fixtures:** Phase 7 cannot be planned or executed without a fixed evaluation set drawn from the actual note corpus. Assemble during Phase 6 when brain health provides visibility into note structure.

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `engine/api.py`, `engine/gui/static/app.js`, `engine/gui/static/index.html`, `engine/search.py`, `engine/health.py`, `engine/capture.py`, `engine/watcher.py`, `engine/forget.py`, `engine/links.py`, `pyproject.toml` — 2026-03-16
- Flask streaming responses (SSE): https://flask.palletsprojects.com/en/3.1.x/patterns/streaming/
- MDN EventSource API: https://developer.mozilla.org/en-US/docs/Web/API/EventSource
- SQLite FTS5 `bm25()` column weighting: https://www.sqlite.org/fts5.html
- Python-Markdown PyPI (v3.10.2 current, Feb 2026): https://pypi.org/project/Markdown/
- werkzeug `secure_filename`: https://werkzeug.palletsprojects.com/en/3.1.x/utils/#werkzeug.utils.secure_filename
- waitress threading model: https://docs.pylonsproject.org/projects/waitress/en/stable/runner.html
- RRF `k=60` default: Cormack & Clarke (2009); confirmed as default in LangChain, LlamaIndex, Elasticsearch hybrid search
- `marked` v5 sanitize removal + DOMPurify as replacement: marked changelog (HIGH confidence)

### Secondary (MEDIUM confidence)
- pywebview WebSocket issues (#241, #688, #774): https://github.com/r0x0r/pywebview/issues/241 — confirms SSE preferred over WebSocket in embedded WebKit
- pywebview `run_js()` thread safety: https://pywebview.flowrl.com/api/ — fire-and-forget confirmed; explicit thread-safety statement not found but community-confirmed
- Flask SSE without extra dependencies: https://maxhalford.github.io/blog/flask-sse-no-deps/
- Obsidian vault-statistics plugin (brain health UX validation): https://github.com/bkyle/obsidian-vault-statistics-plugin
- obsidianstats.com find-unlinked-files (orphan detection validation): https://www.obsidianstats.com/plugins/find-unlinked-files
- Tag chip editor UX pattern: derived from Obsidian ecosystem observation

---
*Research completed: 2026-03-16*
*Ready for roadmap: yes*
