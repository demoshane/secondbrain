# Performance Audit Findings

**Audited:** 2026-03-27
**Auditor:** gsd-executor agent (plan 39-03)
**Scope:** engine/api.py, engine/search.py, engine/ann_index.py, engine/embeddings.py,
  engine/intelligence.py, engine/brain_health.py, engine/reindex.py, engine/consolidate.py,
  engine/db.py, engine/health.py, engine/digest.py

**Scale target:** Phase 38 defines 100K notes as the target scale ceiling.

---

## Summary

| Severity | Count |
|----------|-------|
| High     | 3     |
| Medium   | 5     |
| Low      | 4     |

No Critical findings — no data loss or security-breach risk from performance issues.

---

## High

### PERF-01: N+1 query in note_meta backlink scan — full-table LIKE

- **Severity:** High
- **File:** engine/api.py:1040-1043
- **Description:** The `/notes/<path>/meta` endpoint scans the entire `notes` table using
  `WHERE LOWER(body) LIKE LOWER('%title%')` to find backlinks. There is no index on `body` and
  the LIKE pattern has a leading wildcard, so SQLite must scan every row. The FTS5 index exists
  for this purpose but is not used here. Called once per note view in the GUI.
- **Scale impact:** At 100K notes with average body size 500 chars, every note open triggers
  a 100K-row full scan with substring matching. Latency grows linearly — measured in seconds
  at scale.
- **Root cause:** Backlink detection was implemented as a LIKE scan rather than using the
  existing FTS5 index or a pre-computed backlink relationship table. The `relationships` table
  already tracks wiki-link backlinks (type='backlink') built during reindex — but this endpoint
  doesn't use it.
- **Recommended fix:** Replace the LIKE scan with a query on the `relationships` table:
  `SELECT source_path, title FROM relationships r JOIN notes n ON n.path=r.source_path
  WHERE r.target_path=? AND r.rel_type='backlink'`. This is O(1) with the existing index.
  If the relationships table isn't fully populated, run `sb-reindex` to rebuild. Alternatively,
  use FTS5: `SELECT path, title FROM notes_fts WHERE notes_fts MATCH '"{title}"'`.

---

### PERF-02: N+1 query pattern in search post-filter for tags

- **Severity:** High
- **File:** engine/api.py:220-230, 244-253
- **Description:** When filtering by multiple tags (POST /search with `tags` body param), the
  code loops through every candidate result and executes a separate DB query per note to fetch
  its tags from the `note_tags` junction table. For FTS5-matched results this can be 20-200
  individual `SELECT tag FROM note_tags WHERE note_path=?` queries per search request.
  At 100K notes with FTS5 returning 200 candidates, this is 200 sequential round-trips.
- **Scale impact:** Becomes noticeable at 1K+ notes when search is called frequently. At 100K
  notes with default FTS limit of 200, each filtered search issues 200+ queries.
- **Root cause:** Semgrep SQL injection scanner blocks dynamic IN-clause construction, so the
  original developer chose per-row lookups to avoid the scanner. However, a safe batch approach
  is possible via `GROUP_CONCAT` or by fetching all tags for matched paths in a single query.
- **Recommended fix:** After collecting candidate paths from FTS, fetch all their tags in one
  query: `SELECT note_path, tag FROM note_tags WHERE note_path IN (?, ?, ...)` — the IN-clause
  here uses parameterized placeholders (not string interpolation), which semgrep accepts. Or
  alternatively, use a JOIN in the initial FTS query itself.

---

### PERF-03: `rglob("*.md")` called twice in reindex_brain — double filesystem walk

- **Severity:** High
- **File:** engine/reindex.py:166-172
- **Description:** `reindex_brain()` calls `brain_root.rglob("*.md")` twice — once to build
  `disk_paths` (set, line 166) and a second time for the main indexing loop (line 172). Each
  rglob is a full directory tree walk. At 100K notes these are two separate O(n) filesystem
  walks. Additionally, `update_wiki_link_relationships()` at line 296 fetches all notes from
  DB (`SELECT path, body FROM notes`) and calls the update function per note — another O(n)
  loop with per-note DB writes.
- **Scale impact:** At 100K notes: two filesystem walks (~2-5s each on spinning disk), plus
  100K `update_wiki_link_relationships` calls — each potentially doing DB reads/writes. Full
  reindex time grows quadratically if wiki-link extraction triggers per-note relationship scans.
- **Root cause:** The two rglob walks were not consolidated. The per-note wiki-link update
  was added in a later phase without batching.
- **Recommended fix:** Consolidate into a single rglob pass by building `disk_paths` and
  collecting `md_paths` in the same loop (already available). For wiki-link extraction, batch
  the relationship writes rather than updating per-note; consider a two-pass approach
  (collect all links, then upsert in bulk).

---

## Medium

### PERF-04: `get_missing_file_notes` hardcoded LIMIT 500 — caps at wrong size

- **Severity:** Medium
- **File:** engine/brain_health.py:40-41
- **Description:** `get_missing_file_notes()` fetches at most 500 notes from the DB
  (`SELECT path, title FROM notes LIMIT 500`) and then calls `os.path.exists()` per row in
  Python. At 100K notes, only the first 500 are checked — orphan detection silently under-reports.
  The 500-row cap was intended as a performance guard but creates an incorrect result.
- **Scale impact:** At 100K notes, 99,500 notes are never checked. Health score and orphan
  count are unreliable at scale.
- **Root cause:** LIMIT 500 was likely added as a latency guard but creates silent correctness
  failure. `os.path.exists()` is fast (filesystem cache), so checking 10K rows would still be
  under 1s.
- **Recommended fix:** Remove or raise the LIMIT. If latency is a concern at extreme scale
  (1M notes), add a configurable cap with a warning when truncated:
  `... LIMIT ? LIMIT 10000` with a logged warning if count hits the cap.

---

### PERF-05: ANN cold-start cost — knn_query rebuilds index from DB on first call

- **Severity:** Medium
- **File:** engine/ann_index.py:111-153, engine/search.py:207-227
- **Description:** On the first call to `knn_query()` after process startup (when no cached
  singleton exists), `load_or_build_index()` may call `rebuild_index()` which fetches all
  embeddings from DB and builds a full hnswlib index in memory. At 100K notes this fetches
  100K * 768-float blobs (~300MB) and constructs the HNSW graph. This can take 10-30 seconds.
  The search endpoint calls this synchronously during a user request.
- **Scale impact:** First search after API restart takes 10-30s at 100K notes. Subsequent
  searches use the cached singleton (fast). Any API restart (deploy, crash recovery) resets
  the cold-start penalty.
- **Root cause:** Index is built lazily on first query. No warm-up on startup. Singleton cache
  is process-local (lost on restart).
- **Recommended fix:** Add an index warm-up call in `startup()` (api.py) — after DB init,
  call `load_or_build_index(conn)` in a background thread so the first user request doesn't
  block. Alternatively, persist the hnswlib index to disk (already done) and always load it
  rather than rebuilding from DB. The `load_or_build_index` function already loads from disk if
  the file exists — ensure the disk file is always kept up-to-date after reindex.

---

### PERF-06: `_enrich_with_excerpts` is O(n) per result — per-note chunk query in Python loop

- **Severity:** Medium
- **File:** engine/search.py:142-185
- **Description:** After every search (hybrid and semantic), `_enrich_with_excerpts()` is
  called. It loops over each result and executes a `SELECT chunk_text, embedding FROM note_chunks
  WHERE note_path=?` query per result. For a 20-result search, this is 20 sequential DB queries.
  It also calls `embed_texts([query])` — an LLM round-trip — at the start of every enrichment
  call. Both the per-note DB queries and the embedding call add latency to every search.
- **Scale impact:** 20-result search = 20 DB round-trips + 1 embedding call. At 100 results,
  100 round-trips. The embedding call cost (~50-200ms) is constant but the per-note queries
  scale with result count.
- **Root cause:** Excerpt enrichment was added without batching. Each result is processed
  independently.
- **Recommended fix:** Batch the chunk fetch: collect all result paths, then fetch all chunks
  in one query: `SELECT note_path, chunk_text, embedding FROM note_chunks WHERE note_path IN
  (?, ?, ...)`. Then match chunks to results in Python. This reduces N DB round-trips to 1.
  The embedding call cannot be batched but can be cached (same query string → same embedding).

---

### PERF-07: `get_duplicate_candidates` is O(n²) — full pair-scan over all embeddings

- **Severity:** Medium
- **File:** engine/brain_health.py:60-95
- **Description:** `get_duplicate_candidates()` iterates over every note that has an embedding
  (`SELECT note_path FROM note_embeddings`) and calls `find_similar()` per note. Each
  `find_similar()` call triggers a full sqlite-vec KNN scan over all embeddings. This is
  O(n²) at scale: 100K notes with embeddings = 100K KNN scans. This function is called in
  `take_health_snapshot()` (daily consolidation job) and in `get_brain_health_report()`
  (called by `/brain-health` endpoint).
- **Scale impact:** At 1K notes: ~1K queries, manageable. At 10K notes: ~10K queries, slow.
  At 100K notes: infeasible — would take hours. The daily consolidation job would block.
- **Root cause:** Duplicate detection was designed for small brain (< 1K notes). The hnswlib
  ANN index was added in Phase 38 specifically for scale, but `get_duplicate_candidates` still
  uses the sqlite-vec path via `find_similar()`.
- **Recommended fix:** Replace `get_duplicate_candidates` with an ANN-based approach: use
  `knn_query()` (hnswlib) for O(n log n) nearest-neighbour scan rather than O(n²) KNN.
  The `find_consolidation_candidates()` in consolidate.py already does this correctly — it's
  the template. Alternatively, add a row count guard: if note_embeddings > 10K rows,
  skip the full scan and return [] with a warning.

---

### PERF-08: `recap_entity` uses LIKE scan on `people` and `tags` JSON columns

- **Severity:** Medium
- **File:** engine/intelligence.py:437-443
- **Description:** `recap_entity()` queries notes with `WHERE people LIKE ? OR tags LIKE ?`
  using `%name%` pattern — a leading-wildcard LIKE on JSON text columns. This bypasses both
  the FTS5 index and the `note_people`/`note_tags` junction tables added in Phase 32.
  Called by `sb_recap` MCP tool (primary interface, 95% usage).
- **Scale impact:** At 100K notes, this is a 100K-row full scan per MCP tool call. Each recap
  of a person or project degrades proportionally to total note count.
- **Root cause:** `recap_entity` was not updated when Phase 32 added junction tables. It still
  uses the original JSON LIKE approach.
- **Recommended fix:** Replace the LIKE scan with a junction table query:
  `SELECT n.path, n.title, n.body, n.sensitivity FROM notes n
  JOIN note_people np ON np.note_path=n.path WHERE np.person LIKE ?
  UNION
  SELECT n.path, n.title, n.body, n.sensitivity FROM notes n
  JOIN note_tags nt ON nt.note_path=n.path WHERE nt.tag = ?`.
  The `note_people` and `note_tags` tables have indexes on `person` and `tag` columns
  respectively (created in `migrate_add_note_people_table` and `migrate_add_note_tags_table`).

---

## Low

### PERF-09: `list_people` fetches all records then paginates in Python

- **Severity:** Low
- **File:** engine/api.py:317-331
- **Description:** `list_people()` calls `list_people_with_metrics(conn)` which returns ALL
  person notes with metrics, then Python slices the result for pagination. At 1K+ person notes,
  this fetches all rows and computes metrics for all, returning only the requested page.
- **Scale impact:** Manageable for most use cases (people notes rarely exceed 1K), but
  inconsistent with how other list endpoints handle pagination. Noted by Phase 33 as acceptable
  for current scale.
- **Root cause:** Phase 33 documented: "list_people pagination applied in Python (slice after
  function call) to preserve filter support without dynamic SQL." This is a known trade-off.
- **Recommended fix:** Low priority. If people list grows beyond 1K, add DB-level LIMIT/OFFSET
  to `list_people_with_metrics`. Current implementation is correct for expected scale.

---

### PERF-10: `get_stale_notes` fetches 3× limit then filters in Python

- **Severity:** Low
- **File:** engine/intelligence.py:241-283
- **Description:** `get_stale_notes(conn, days=90, limit=5)` fetches `limit * 3` (15) rows
  from DB, then filters by snooze state, file existence, and evergreen flag — calling
  `frontmatter.load()` per candidate note (up to 15 disk reads). If many notes are snoozed,
  the function may return fewer than `limit` results without fetching more.
- **Scale impact:** 15 disk reads per stale-nudge check. Called during every search (via
  `check_stale_nudge`). Low impact but not free.
- **Root cause:** Intentional over-fetch to account for filtering. Acceptable for current scale.
- **Recommended fix:** Low priority. Store snooze state in DB instead of JSON file to avoid
  the 2-phase fetch. Not worth the complexity at current scale.

---

### PERF-11: `startup()` in api.py uses `glob.glob` for disk count

- **Severity:** Low
- **File:** engine/api.py:1731
- **Description:** `startup()` calls `glob.glob(f"{brain_root}/**/*.md", recursive=True)` to
  count markdown files on disk. At 100K files this is a full directory walk on every API startup.
  The result is only used for a warning message.
- **Scale impact:** Adds ~1-5 seconds to API startup time at 100K notes. Not a runtime issue,
  only affects cold start.
- **Root cause:** Convenience — glob is simpler than using the DB. A DB count would be faster
  and already available.
- **Recommended fix:** Replace glob with a DB count: `conn.execute("SELECT COUNT(*) FROM notes")`
  after init_schema. Already available in the same startup() function.

---

### PERF-12: `recap_main` issues two queries on closed connection

- **Severity:** Low
- **File:** engine/intelligence.py:810-820
- **Description:** In `recap_main()`, after calling `conn.close()` (line 809), the code
  continues on lines 813-814 with `conn.execute("SELECT summary FROM notes WHERE title = ?")`
  — querying a closed connection. This will raise `ProgrammingError: Cannot operate on a closed
  database.` on any code path that reaches line 783 (git context branch). The error is uncaught
  and will crash the CLI.
- **Scale impact:** Not a scale issue — this is a bug (correctness). Included here because it
  was found during the performance audit and matches the performance file scope (intelligence.py).
- **Root cause:** The `conn.close()` was inserted at line 809 inside a branch, but the recap
  loop on lines 811-824 still references `conn` without re-opening it. This is a latent bug
  that only manifests when `detect_git_context()` returns a non-None value AND notes exist for
  that context.
- **Recommended fix:** Move `conn.close()` to after the recap loop (after line 824), or use
  `try/finally` to ensure conn is closed at function exit. This is a Rule 1 (bug) finding.
  Recommend fixing in the remediation wave.

---

## Index Coverage Summary

**Existing indexes (db.py init_schema):**
- `idx_notes_type` on `notes(type)` — covers type-filter queries
- `idx_notes_url` on `notes(url)` — covers URL lookup
- `idx_note_tags_tag` on `note_tags(tag)` — covers tag filter
- `idx_note_tags_note_path` on `note_tags(note_path)` — covers note→tag lookup
- `idx_note_people_person` on `note_people(person)` — covers person filter
- `idx_note_people_note_path` on `note_people(note_path)` — covers note→person lookup
- `idx_note_chunks_path` on `note_chunks(note_path)` — covers chunk lookup by note
- `idx_audit_log_created_path` on `audit_log(created_at, note_path)` — covers audit pruning

**Missing indexes that would help:**
- `notes(created_at)` — used in ORDER BY for list_notes, fetch_recap_data, and digest queries
  without an index. Low impact (LIMIT keeps result set small) but adds value at 100K notes.
- `notes(updated_at)` — used in ORDER BY for stale_notes detection. Same as above.
- `notes(archived)` — used in WHERE archived=0 filter. Most queries filter on this column;
  without an index, SQLite must scan notes table for every paginated list.
- `action_items(note_path)` — heavily used in per-note action count subqueries in list_meetings
  and list_projects endpoints. Currently unindexed.

**Priority:** `notes(archived)` and `action_items(note_path)` are the most impactful additions.

---

## ANN Fallback Cost Assessment

**Verdict:** Bounded but has cold-start issue (PERF-05 above).

- hnswlib KNN query: O(log n) after index is warm. ef=50 means ~50 candidates explored.
- Index build from disk: ~100ms at 10K notes (loads pre-built index file). No rebuild needed.
- Index rebuild from DB: O(n) — only triggered when disk file is absent (first run or manual delete).
- Fallback to sqlite-vec: triggered on any exception from hnswlib. sqlite-vec KNN is O(n) —
  linear scan over all embeddings. At 100K notes with 768-dim vectors, this is ~300MB of data
  per query. Estimated latency: 10-60s at 100K scale.
- ANN fallback frequency: any exception triggers fallback, including dimension mismatch errors
  (CHUNK_THRESHOLD/CHUNK_SIZE handling), index corruption, or hnswlib not installed.

**Recommendation:** Log fallback events as warnings so operators can detect when the expensive
sqlite-vec path is being used. The current `logger.warning("ANN search failed, falling back...")`
is correct but the frequency is not tracked.

---

## Hybrid Search RRF Merge Complexity

**Verdict:** O(n log n) — acceptable.

- `_rrf_merge(bm25_results, vec_results, k=60, limit=20)` uses two O(n) loops to build score dict,
  then `sorted()` which is O(n log n). With typical n=40 (2× the default limit of 20), this is
  negligible.
- The 2× limit multiplier (search_hybrid calls both sub-searches with `limit=limit*2`) doubles
  the search cost but keeps the merge bounded.
- `_enrich_with_excerpts` is called once at merge point (not inside sub-search functions per
  Phase 38 decision) — correct, avoids double-enrichment.

---

## Scale Complexity Summary

| Operation | Current Complexity | At 100K | Acceptable |
|-----------|-------------------|---------|------------|
| FTS5 search | O(k) per query | Fast | Yes |
| Semantic search (ANN warm) | O(log n) | Fast | Yes |
| Semantic search (ANN cold) | O(n) rebuild | 10-30s | No (PERF-05) |
| Semantic search (sqlite-vec fallback) | O(n) | 10-60s | No |
| Excerpt enrichment | O(result_count) queries | 20 queries | Medium (PERF-06) |
| note_meta backlinks | O(n) LIKE scan | Full table scan | No (PERF-01) |
| Search post-filter (tags) | O(result_count) queries | 200 queries | Medium (PERF-02) |
| reindex_brain (filesystem) | 2× O(n) walks | Slow | Medium (PERF-03) |
| get_duplicate_candidates | O(n²) KNN scans | Infeasible | No (PERF-07) |
| recap_entity (LIKE scan) | O(n) | Full scan | No (PERF-08) |
| get_missing_file_notes | O(500) capped | Under-reports | Medium (PERF-04) |
| list_notes | O(limit) + COUNT | Fast | Yes |
| digest generation | O(7-day window) | Bounded | Yes |
| consolidation job (ANN) | O(n log n) | Manageable | Yes |

---

*Audit complete. All pre-identified items P-01 through P-04 from RESEARCH.md addressed below:*

- **P-01** (N+1 on note_meta): Confirmed and expanded → PERF-01 (backlink LIKE scan) + PERF-02 (tag filter N+1)
- **P-02** (rglob in capture): Confirmed as double-walk in reindex_brain → PERF-03
- **P-03** (FTS5 rebuild outside transaction): Verified correct — brain_health.py merge_notes and smart_merge_notes both rebuild FTS5 outside the transaction block (line 301 after `with conn:` exits). No finding needed.
- **P-04** (ANN fallback cost): Confirmed cold-start issue → PERF-05; confirmed fallback to sqlite-vec is unbounded at scale
