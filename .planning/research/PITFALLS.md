# Pitfalls Research

**Domain:** GUI overhaul + engine polish — pywebview/Flask/SQLite personal knowledge system (v3.0)
**Researched:** 2026-03-16
**Confidence:** HIGH — all findings grounded in direct code inspection of the existing engine and GUI layer

---

## Critical Pitfalls

### Pitfall 1: Live Refresh Race — DB Row Exists, File Does Not Yet

**What goes wrong:**
`write_note_atomic` commits the DB row first, then calls `os.replace(tmp, target)`. This is intentional: on failure, the DB is authoritative and the file is the thing that may be missing. However, it creates a transient window where the DB has the row and the markdown file does not yet exist on disk. If the GUI polls `/notes` and refreshes the sidebar in that window, the user sees the note listed. A click immediately triggers `GET /notes/<path>`, which calls `p.read_text()` on a file that does not yet exist — returns 404 — and the viewer renders "Error loading note." The note is real; the timing is the problem.

**Why it happens:**
The DB-first atomicity guarantee is correct for crash safety but creates a brief inconsistency observable to a polling GUI. The existing `app.js` has no handling for 404 on a freshly-listed note — it treats any non-OK response as an error.

**How to avoid:**
The GUI must distinguish "note not yet on disk" (transient 404 on a path that just appeared in `/notes`) from "note truly missing" (stale path in DB). When `GET /notes/<path>` returns 404, show a "Loading..." placeholder and retry after 500ms before rendering an error. The API layer should also add a `/notes/events` SSE endpoint that emits after `os.replace` completes (not after DB commit) so the GUI refresh is triggered at the right moment.

**Warning signs:**
- "Error loading note." appears immediately after dropping a file or creating a note via CLI.
- The note appears in the sidebar but errors on click only within the first 1-2 seconds of creation.

**Phase to address:** GUIX-01 (live refresh).

---

### Pitfall 2: Watcher Fires on GUI-Captured Files — Duplicate Notes

**What goes wrong:**
`sb-watch` monitors `~/SecondBrain/files/`. When GUI file upload (GUIF-01) writes a file into `files/`, the watcher's `on_created` fires and calls `capture_note` — creating a second note for the same file. The user ends up with two sidebar entries for one upload.

**Why it happens:**
The FSEvents history guard in `FilesDropHandler.on_created` (ctime vs. observer start time) only filters files that existed *before* the watcher started. Files written after startup — including those written by the GUI itself — pass the guard unconditionally. There is no mechanism to suppress events for files that were just intentionally captured.

**How to avoid:**
Maintain an in-process "recently captured" registry. When the GUI capture endpoint writes a file to `files/`, register the path with a 10-second TTL (a module-level dict `{path: expire_monotonic}` in `watcher.py` is sufficient). `FilesDropHandler.on_created` checks this registry before calling `on_new_file` and skips any path that is registered. Expire entries in `_fire_batch` before processing.

**Warning signs:**
- Uploading a file via GUI produces two sidebar entries with the same title.
- `SELECT COUNT(*) FROM notes WHERE title = ?` returns 2 for a freshly uploaded file.
- Both entries point to the same file path but have different `created_at` timestamps seconds apart.

**Phase to address:** GUIF-01 (file upload / capture from GUI).

---

### Pitfall 3: `marked.parse()` Without DOMPurify — Stored XSS

**What goes wrong:**
`app.js` renders note content with `viewer.innerHTML = marked.parse(md)`. `marked` does not sanitize HTML. A note body containing `<script>alert(1)</script>` or `<img src=x onerror="...">` executes in the pywebview WebView. For a strictly personal, never-imported brain this is low risk. The moment GUIF-01 enables file upload (importing external content), or git hook captures embed untrusted commit messages, the attack surface is real.

**Why it happens:**
`marked` v5 removed the built-in `sanitize` option (deprecated v4, removed v5). Developers assume a local single-user app is safe and skip sanitization. The vendored EasyMDE already bundles `marked` — checking which version is present requires opening the vendor file, which developers rarely do before shipping.

**How to avoid:**
Vendor `DOMPurify` alongside EasyMDE (already in `engine/gui/static/vendor/`) and wrap every innerHTML assignment:
```js
viewer.innerHTML = DOMPurify.sanitize(marked.parse(md));
```
This is one line. Verify the vendored `marked` version — if v4, the deprecated `sanitize: true` option is still available but DOMPurify is the correct forward path.

**Warning signs:**
- `grep -r "DOMPurify" engine/gui/static/` returns nothing.
- Pasting `<b>test</b>` into a note body and opening the note shows bold text — `marked` is active.
- Pasting `<script>document.title='xss'</script>` and opening changes the window title — sanitization is absent.

**Phase to address:** GUIX-03 (markdown rendering as formatted HTML).

---

### Pitfall 4: Note Deletion Cascade Misses `note_embeddings` and `relationships`

**What goes wrong:**
`forget.py` implements the full cascade for person erasure: notes, note_embeddings, relationships, audit_log, FTS5 rebuild. This logic is inline — there is no shared `delete_note()` utility. When GUIX-06 adds GUI deletion, a naive `DELETE /notes/<path>` endpoint that only calls `DELETE FROM notes WHERE path = ?` will leave orphan rows in `note_embeddings` and `relationships`. The FTS5 content table cleans itself via trigger on notes deletion, but the other two tables are not FK-constrained with `ON DELETE CASCADE` in the schema.

**Why it happens:**
The cascade pattern in `forget_person` is not discoverable as a shared utility — it is 100 lines of inline logic. A developer adding a new deletion surface reads the requirement "delete a note" and writes the obvious SQL without cross-referencing the GDPR erasure code.

**How to avoid:**
Extract a `delete_note(path: str, conn, brain_root: Path)` function from `forget_person`. It handles the cascade in order: (1) clean backlink lines from other notes, (2) `DELETE FROM note_embeddings WHERE note_path = ?`, (3) `DELETE FROM relationships WHERE source_path = ? OR target_path = ?`, (4) `DELETE FROM audit_log WHERE note_path = ?`, (5) `DELETE FROM notes WHERE path = ?`, (6) FTS5 rebuild, (7) `Path.unlink()`. Both `forget_person` and the new GUI deletion endpoint call this utility.

**Warning signs:**
- After GUI deletion, `SELECT COUNT(*) FROM note_embeddings WHERE note_path = '<deleted>'` > 0.
- `sb-check-links` reports orphan relationships pointing to a deleted file.
- Brain health score does not improve after deleting a note flagged as broken.

**Phase to address:** GUIX-06 (note deletion with cascade).

---

### Pitfall 5: Batch Capture Partial Failure Is Silent

**What goes wrong:**
`capture_note` is atomic per note (file + DB transaction). A batch loop that iterates over N items and calls `capture_note` for each will leave items 1-2 committed and items 4-10 not attempted if item 3 fails (AI timeout, duplicate slug, disk full). Because there is no batch transaction wrapper and error handling in a loop tends toward `except Exception: continue`, the user gets no indication of how many items succeeded or which failed.

**Why it happens:**
Per-note atomicity is correct and must not be replaced with a batch transaction (that would make one failure roll back all prior successes). The problem is the absence of a structured result. The existing `capture_note` returns the path on success and raises on failure — callers must accumulate results explicitly or they get implicit silent partial success.

**How to avoid:**
Batch capture must return a structured result dict matching the existing pattern in `forget_person`:
```python
{"succeeded": [path, ...], "failed": [{"item": ..., "reason": type(e).__name__}, ...]}
```
Never use `except Exception: pass` in a batch loop. Present the full result to the user before the operation is considered complete. Do not roll back successful captures on a later failure — per-note atomicity is correct; the result report is the recovery surface.

**Warning signs:**
- Batch of 10 items produces 7 notes with no output about the missing 3.
- Batch loop uses broad `except Exception: pass` or `except Exception: continue`.
- No return type annotation or test asserting the batch result structure.

**Phase to address:** ENGL-01 (batch capture).

---

### Pitfall 6: RRF Tuning Regresses Exact-Match (Precision) Queries

**What goes wrong:**
The current `_rrf_merge` uses `k=60` and equal weight (1.0 / (k + rank)) for both BM25 and vector lists. If tuning "improves relevance" by boosting vector weight (a common instinct when recall feels low), short exact-match queries regress: searching a person's name, a project slug, or a date returns semantically similar but lexically different notes at rank 1, displacing the exact match. The user notices but cannot articulate why search "feels worse."

**Why it happens:**
Vector search optimizes recall across paraphrases. BM25 optimizes precision for exact terms. Any weight increase for vector at the expense of BM25 trades precision for recall. Developers test recall-oriented queries ("what do I know about delegation?") and declare success, without running a precision-oriented regression ("alice-smith" → person profile at rank 1).

**How to avoid:**
Before touching any RRF parameter, establish a fixed regression suite: at minimum 5 precision queries (exact name, slug, date) and 5 recall queries (broad topic). Record the rank of the expected top result for each. Treat any precision query where the expected result drops below rank 3 as a regression that blocks the change. Keep `k=60` — it is the canonical default from the original RRF paper and is robust across most corpora. If tuning is needed, adjust the `limit` passed to each sub-ranker rather than `k`.

**Warning signs:**
- After tuning, `sb-search "alice-smith"` returns a meeting note before the person profile.
- Exact project code search returns thematically related but lexically different notes at rank 1.
- No regression test suite exists for search quality.

**Phase to address:** ENGL-02 (search hybrid ranking tuning).

---

### Pitfall 7: Brain Health False Positives After BRAIN_ROOT Path Change

**What goes wrong:**
The `notes` table stores absolute paths (e.g. `/Users/tuomas/SecondBrain/people/alice.md`). `check_links` in `links.py` checks `Path(source_str).exists()` against stored absolute paths. If `BRAIN_ROOT` changes — Mac migration, Drive remount at a different mount point, username change — every stored path fails `.exists()` and `check_links` reports hundreds of "source missing" orphans. The brain health dashboard shows a catastrophically unhealthy brain that is actually fine.

Additionally, `check_links` only validates the `relationships` table. When v3.0 adds GUI tag editing (GNAV-02) or batch capture that writes `[[wikilink]]` syntax in note bodies without inserting a `relationships` row, `check_links` will report 0 orphans even when broken wikilinks exist in note text.

**Why it happens:**
Absolute paths are fragile across machine migrations. The path was chosen for simplicity (no join needed to resolve full path) but breaks silently on any environment change. The wikilink scanning gap exists because `check_links` was purpose-built for the `relationships` table and was not designed to parse markdown syntax.

**How to avoid:**
Two independent mitigations:

1. **False positive on path change**: Before reporting orphans, detect whether stored paths share a common prefix that differs from the current `BRAIN_ROOT`. If the majority of stored paths have a stale prefix, emit a single warning ("BRAIN_ROOT may have changed — run sb-reindex before interpreting health results") rather than hundreds of individual orphan reports. Long-term fix: store paths relative to `BRAIN_ROOT` in the DB (schema migration required).

2. **Wikilink gap**: Add a separate `check_wikilinks(brain_root)` function to `links.py` that greps `[[...]]` patterns in all `.md` files and verifies the referenced slug exists as a file. Surface both checks in the ENGL-04 health dashboard, clearly labelled as distinct checks.

**Warning signs:**
- `sb-check-links` reports 50+ orphans immediately after `sb-reindex` (reindex should clear real orphans).
- All orphan source paths share the same stale path prefix.
- `SELECT DISTINCT substr(path, 1, 30) FROM notes LIMIT 3` shows an old home directory path.

**Phase to address:** ENGL-04 (brain health dashboard) and ENGL-05 (health score).

---

### Pitfall 8: Path Traversal via `/notes/<path>` API

**What goes wrong:**
`GET /notes/<path:note_path>` and `PUT /notes/<path:note_path>` in `api.py` resolve arbitrary absolute paths passed as the URL path component and read or write them directly. A request to `GET /notes//etc/passwd` (Flask's path converter passes the full string after the prefix) returns the contents of any world-readable file. `PUT /notes//Users/tuomas/.ssh/authorized_keys` with a crafted body overwrites SSH keys. The `_SlashNormMiddleware` already normalises double-slashes for the `notes` and `files` prefixes, which means `//etc/passwd` → `/etc/passwd` is reachable.

**Why it happens:**
The API was built for GUI-internal use where the caller is trusted (the pywebview JavaScript layer). No external-caller threat model was applied. As the system grows (MCP server, future REST clients), the assumption of a trusted caller weakens.

**How to avoid:**
Add a path validation guard at the top of every endpoint that accepts a file path:
```python
resolved = Path(note_path).resolve()
brain_root = Path(os.environ.get("BRAIN_PATH", "~/SecondBrain")).expanduser().resolve()
if not str(resolved).startswith(str(brain_root)):
    return jsonify({"error": "Forbidden"}), 403
```
This applies to `read_note`, `save_note`, and `note_meta`. Also remove `brain_path` from the `POST /notes` request body — the server must use `BRAIN_ROOT` from the environment, not from caller-supplied input.

**Warning signs:**
- `curl http://127.0.0.1:37491/notes/%2Fetc%2Fpasswd` returns file contents.
- `POST /notes` accepts any `brain_path` value without validation.
- No path prefix check in any endpoint that reads or writes files.

**Phase to address:** Any phase touching `api.py` — but GUIX-06 (deletion endpoint) is the latest it can be deferred to, since that phase adds another write endpoint.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Absolute paths in `notes` table | Simple lookups, no join needed | All paths break on BRAIN_ROOT rename or machine migration; health checks produce false positives | Acceptable until first migration event — plan relative-path migration for v4.0 |
| Cascade logic inline in `forget_person` (not a shared util) | Ships fast | Every new deletion surface re-implements or misses the cascade | Acceptable until GUIX-06 — extract `delete_note()` utility then |
| `marked.parse()` without DOMPurify | Renders markdown today | XSS from any imported or piped content once GUIF-01 ships | Never once file upload is added |
| `brainPath` derived by stripping 2 path components from first note path in JS | Zero config needed | Wrong for notes at top-level brain folder; fails on empty brain | Replace with pywebview API call that returns `BRAIN_ROOT` directly |
| Polling `/notes` on GUI open (no SSE/WebSocket) | No infrastructure needed | Live refresh requires interval polling; hammers Flask sidecar at short intervals | Acceptable at 5-second interval; SSE preferred for sub-second refresh |
| `search_notes` inserts an audit_log row on every call including internal calls from `note_meta` | Uniform audit coverage | `loadMeta` calls `search_notes` for related notes on every note open — generates audit noise | Acceptable until audit log analysis is added; add `audit=False` param then |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| pywebview + Flask | Calling `pywebview.api` before `pywebviewready` fires | Already handled for `open-editor-btn`; every new pywebview API call added in v3.0 must also gate on this event |
| watchdog + macOS FSEvents | Removing the ctime history guard thinking it is unnecessary | The guard is mandatory — FSEvents delivers historical events on observer start; removing it causes every pre-existing file to re-trigger on daemon restart |
| EasyMDE vendored offline | Assuming `marked` global is always available after an EasyMDE version bump | EasyMDE exposes `marked` as a global from its bundle; verify after any vendor update that `typeof marked !== 'undefined'` still holds before shipping |
| SQLite FTS5 + bulk delete | Assuming `DELETE FROM notes` cleans FTS5 | FTS5 content table triggers handle per-row deletes correctly, but after bulk deletes `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` is still needed to reclaim space and flush tombstones — already in `forget_person`, must be in new deletion utility too |
| Google Drive + SQLite | Drive syncing `brain.db` between machines | `brain.db` must be excluded from Drive sync — partially-written WAL from two machines is unrecoverable. Verify `.meta/` exclusion is in place whenever new DB tables are added |
| waitress + pywebview | Flask sidecar on a random port if 37491 is taken | Waitress binds to the specified port and raises on conflict — GUI will silently fail to load. Add a pre-start port check and clear error message |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `search_semantic` runs synchronously in Flask request thread | GUI search hangs 2-10s on Intel Mac (CPU-only sentence-transformers) | Use keyword mode as GUI default; add a loading spinner; consider offloading embedding to a background thread | Every semantic GUI search on this machine |
| `files_dir.rglob("*")` in `GET /files` with no depth limit | Slow sidebar load if `files/` has many subdirectories or nested content | Add `max_depth` parameter; cache listing with a short TTL | At 200+ files |
| `renderSidebar` rebuilds entire DOM on every search keystroke (300ms debounce) | Sidebar flicker; scroll position lost | Diff-based update or virtual list; at minimum preserve scroll position | At 500+ notes |
| `loadMeta` calls `search_notes` (which commits an audit row) on every note open | Audit log grows by 1 row per note view; `search_notes` opens and closes a DB connection per call | Pass `conn` through or cache; add `audit=False` path for internal calls | At 1,000+ note opens per day |
| Tag edit that writes frontmatter + triggers `sb-reindex` for the whole brain | Tag save causes multi-second delay | Re-index only the single edited note via targeted `UPDATE notes SET tags=? WHERE path=?` + FTS5 row update | Any edit on a brain with 100+ notes |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `GET /notes/<path>` reads any path without BRAIN_ROOT validation | Path traversal — any readable file on the machine is accessible | Validate resolved path starts with `BRAIN_ROOT` before reading; return 403 otherwise |
| `PUT /notes/<path>` writes any path without BRAIN_ROOT validation | Path traversal write — can overwrite any writable file | Same guard as read; applies to save_note endpoint |
| `POST /notes` accepts `brain_path` from request body | Caller can direct note writes outside the brain directory | Remove `brain_path` from request; use server-side `BRAIN_ROOT` env var only |
| `marked.parse(md)` assigned to `innerHTML` without sanitization | Stored XSS — any note with HTML/script content executes in pywebview | Add DOMPurify before innerHTML assignment (one line) |
| Flask sidecar on `127.0.0.1` with no auth | Any local process can call any API including `DELETE /notes/...` once deletion is added | Acceptable for now (single-user, no deletion endpoint yet); add a session token when destructive endpoints are added |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Note deletion with no confirmation dialog | Accidental permanent data loss; person profile erasure cascades silently to backlinks | Show confirmation dialog for all deletes; for person profiles specifically, name the cascade ("This will also clean backlinks in N other notes") |
| Tag editing that saves frontmatter without updating the FTS index | Tags visible in the UI but not searchable until restart | After tag save, update `notes.tags` in DB and re-run FTS5 for that row; do not require full reindex |
| Markdown rendering with YAML frontmatter block visible | Every note starts with raw `---\ntype: meeting\n---` | Strip frontmatter before passing body to `marked.parse` — `GET /notes/<path>` returns the full raw file; the GUI must strip it |
| Batch capture with no per-item progress | User has no feedback during a 10-item batch taking 15+ seconds | Show per-item status inline; do not block the UI thread; consider streaming results |
| Brain health "0 issues" when the `relationships` table is empty | User interprets this as "all links valid" when it actually means "no links tracked" | Distinguish "no issues found" from "nothing checked" in the health dashboard display |
| Live refresh that reloads the full note list on every file event | Current note selection lost; scroll position reset | Track selected path; restore selection and scroll after sidebar refresh |

---

## "Looks Done But Isn't" Checklist

- [ ] **Live refresh (GUIX-01):** Sidebar updates — verify the note is *clickable without error* (file on disk), not just *visible* (DB row exists). Test: drop a file via CLI, click sidebar entry within 500ms — no "Error loading note."
- [ ] **Markdown rendering (GUIX-03):** Bold/italic renders — verify YAML frontmatter block is stripped before rendering, and verify `<script>` in note body does NOT execute.
- [ ] **Note deletion (GUIX-06):** Note disappears from sidebar — verify `SELECT * FROM note_embeddings WHERE note_path = '<path>'` returns empty and `sb-check-links` reports no orphans for the deleted path.
- [ ] **Tag editing (GNAV-02):** Tags update in UI — verify `sb-search --keyword <new_tag>` returns the note (FTS index updated, not just frontmatter written).
- [ ] **File upload (GUIF-01):** File appears in sidebar once — verify it does not appear twice (watcher dedup check: `SELECT COUNT(*) FROM notes WHERE title = ?` = 1).
- [ ] **Batch capture (ENGL-01):** All items appear captured — verify the return value includes per-item success/failure, not just a final count. Simulate one item failing; verify the rest still succeed and are reported.
- [ ] **Search tuning (ENGL-02):** Hybrid results improved — verify exact-name search (`sb-search "alice smith"`) still returns the person profile at rank 1 after any RRF parameter change.
- [ ] **Brain health (ENGL-04):** Dashboard shows 0 orphans — verify this is not because `relationships` table is empty. Add a broken `[[nonexistent-note]]` wikilink manually; confirm it is flagged.
- [ ] **Path traversal guard:** `curl http://127.0.0.1:37491/notes/%2Fetc%2Fpasswd` returns 403, not file contents.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Orphan `note_embeddings` rows after delete | LOW | `DELETE FROM note_embeddings WHERE note_path NOT IN (SELECT path FROM notes)` |
| Orphan `relationships` rows after delete | LOW | `DELETE FROM relationships WHERE source_path NOT IN (SELECT path FROM notes) AND target_path NOT IN (SELECT path FROM notes)` |
| Health dashboard false positives after BRAIN_ROOT rename | LOW | Run `sb-reindex` — rebuilds `notes` table with current absolute paths; health check clears |
| Duplicate notes from watcher + GUI upload | LOW | `SELECT title, COUNT(*), GROUP_CONCAT(path) FROM notes GROUP BY title HAVING COUNT(*) > 1` to identify; delete the watcher-created duplicate via direct SQL + `Path.unlink()` |
| FTS5 out of sync after manual SQL operations | LOW | `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` — already used in `forget_person` |
| XSS payload stored in a note | LOW | Note is local-only; no remote exfiltration risk; delete the note and run `sb-reindex` |
| Partial batch capture (some items missing) | LOW | Re-run batch for failed items only — per-note atomicity means re-running a succeeded item will fail with duplicate key cleanly |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Live refresh race (DB row vs. file timing) | GUIX-01 | Drop file, click within 500ms — no 404 viewer error |
| Watcher fires on GUI-uploaded files (duplicate) | GUIF-01 | Upload via GUI; `SELECT COUNT(*) FROM notes WHERE title=?` = 1 |
| XSS via `marked.parse` without DOMPurify | GUIX-03 | Note with `<script>alert(1)</script>` body — no alert dialog fires |
| Cascade delete misses `note_embeddings`/`relationships` | GUIX-06 | Delete note; both tables clean; `sb-check-links` clear for that path |
| Batch capture partial failure silent | ENGL-01 | Simulate failure in item 3 of 5; verify structured result returned with 2 succeeded + 3 failed (or 2+3 depending on failure mode) |
| RRF tuning regresses exact-match search | ENGL-02 | Precision regression suite passes before and after any `_rrf_merge` change |
| Health false positives after path change | ENGL-04/05 | After `sb-reindex`, health reports 0 orphans on a clean brain |
| `check_links` misses wikilinks in note bodies | ENGL-04 | Broken `[[nonexistent]]` in note body flagged by health dashboard |
| Path traversal via `/notes/<path>` API | GUIX-06 (latest) | `GET /notes/%2Fetc%2Fpasswd` returns 403 |
| `brain_path` from POST body allows out-of-brain writes | Any phase touching `POST /notes` | Remove param; verify server uses env var only |

---

## Carried Forward from v2.0 (Still Relevant in v3.0)

| Pitfall | Why Still Relevant | Mitigation |
|---------|-------------------|------------|
| `sb-forget` cascade must include `note_embeddings` | Already implemented; new deletion utility (GUIX-06) must reuse same cascade | Extract `delete_note()` utility; both `forget_person` and GUI deletion call it |
| Prompt injection in intelligence prompts | On-demand recap button (GUIF-02) adds a new LLM call site | Apply XML-tag isolation pattern from v1.5 to all new AI calls |
| Drive sync must exclude `brain.db` | Adding new tables (`note_embeddings`) makes corruption worse | Verify `.meta/` Drive exclusion survives any `sb-init` changes in v3.0 |
| PII routing before any AI call | AI quality improvements (ENGL-03) add new AI call sites | Every new AI call goes through existing `router.py`; no direct model calls |

---

## Sources

- Direct code inspection: `engine/api.py`, `engine/watcher.py`, `engine/search.py`, `engine/forget.py`, `engine/health.py`, `engine/capture.py`, `engine/links.py`, `engine/gui/static/app.js` — all findings at HIGH confidence
- `marked` v5 sanitize removal: confirmed in marked changelog; DOMPurify is the canonical replacement — HIGH confidence
- RRF `k=60` default: Cormack & Clarke (2009) original paper; used as default in LangChain, LlamaIndex, Elasticsearch hybrid search — HIGH confidence
- watchdog FSEvents history events on macOS: documented watchdog behavior; ctime guard pattern is established mitigation — HIGH confidence
- pywebview `pywebviewready` event timing: confirmed in pywebview documentation — HIGH confidence
- Path traversal via Flask `path` converter: standard web security finding; `path:` converter in Flask passes the full remaining path including leading slashes after middleware normalisation — HIGH confidence

---
*Pitfalls research for: pywebview + Flask + SQLite personal knowledge system — v3.0 GUI overhaul and engine polish*
*Researched: 2026-03-16*
