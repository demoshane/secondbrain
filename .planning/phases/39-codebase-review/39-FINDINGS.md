# Phase 39: Consolidated Findings

**Triage date:** 2026-03-27
**Total findings:** 31 (Critical: 0, High: 6, Medium: 11, Low: 14)
**Dimensions covered:** Security, Architecture, Performance, Coverage, Dead Code

---

## Critical

No critical findings. No data loss or security breach risk identified.

---

## High

### F-01: Unguarded int() calls in api.py — HTTP 500 on any bad query param
- **Dimension:** security
- **File(s):** engine/api.py:165-166, 321-322, 337-338, 406-407, 640-641, 738-739, 1108-1109, 1456 (8 locations)
- **Description:** Every `int(request.args.get("limit", ...))` and `int(request.args.get("offset", ...))` call is unguarded. Sending `limit=abc` or `offset=xyz` triggers `ValueError` and Flask returns HTTP 500. Any unauthenticated caller can force 500 responses on 8+ endpoints. Line 641 also accepts negative offsets (no `max(..., 0)` guard).
- **Root cause:** Endpoints added across 30+ phases without a shared query-param parsing helper. Pattern copy-pasted without error handling.
- **Fix:** Introduce `_int_param(name, default, min_val=None, max_val=None)` helper; replace all 8 `int(request.args.get(...))` callsites. Return HTTP 400 on bad input.
- **Blast radius:** Low — callers using valid params unaffected. Fix strictly improves 500→400.
- **User confirm required:** No

---

### F-02: templates.py is dead — zero engine callers
- **Dimension:** architecture, dead-code, coverage
- **File(s):** engine/templates.py (all 41 lines), tests/test_capture.py:83-88
- **Description:** `load_template()` and `render_template()` are defined but no engine module imports or calls them. The only reference is `tests/test_capture.py:84` — an isolated test of the dead module. Capture pipeline writes frontmatter directly; templates are unused in production.
- **Root cause:** Module built in an early phase; capture was later implemented differently. Module left in place.
- **Fix:** Delete `engine/templates.py`. Remove the isolation test at `tests/test_capture.py:83-88`. Verify first: `grep -rn "load_template\|render_template" engine/` must return 0 results.
- **Blast radius:** Low — no live feature path uses it. The test file must be updated simultaneously.
- **User confirm required:** No

---

### F-03: recap_entity uses LIKE scan on JSON columns — bypasses Phase 32 junction tables
- **Dimension:** performance
- **File(s):** engine/intelligence.py:437-443
- **Description:** `recap_entity()` queries notes with `WHERE people LIKE ? OR tags LIKE ?` using a leading-wildcard LIKE on JSON text columns. This bypasses both the FTS5 index and the `note_people`/`note_tags` junction tables added in Phase 32. Called by `sb_recap` — the primary MCP interface (95% of usage). At 100K notes this is a full-table scan per MCP call.
- **Root cause:** `recap_entity` was not updated when Phase 32 added junction tables. Known oversight per STATE.md decision PERF-08.
- **Fix:** Replace LIKE scan with junction table query: `SELECT n.* FROM notes n JOIN note_people np ON np.note_path=n.path WHERE np.person LIKE ? UNION SELECT n.* FROM notes n JOIN note_tags nt ON nt.note_path=n.path WHERE nt.tag = ?`. Indexes on `note_people(person)` and `note_tags(tag)` already exist.
- **Blast radius:** Low — pure query replacement. Return shape unchanged.
- **User confirm required:** No

---

### F-04: recap_main queries closed DB connection — latent crash
- **Dimension:** performance (correctness bug)
- **File(s):** engine/intelligence.py:810-820
- **Description:** `recap_main()` calls `conn.close()` at line 809, then continues at lines 813-814 with `conn.execute(...)` — querying a closed connection. Raises `ProgrammingError: Cannot operate on a closed database.` This path triggers when `detect_git_context()` returns a non-None value AND notes exist for that context. Bug is latent — only manifests in that specific branch.
- **Root cause:** `conn.close()` was inserted inside a conditional branch; the loop at lines 811-824 still references `conn` without re-opening.
- **Fix:** Move `conn.close()` to after the recap loop (line 824+), or use `try/finally` to ensure conn is closed at function exit.
- **Blast radius:** Low — only changes where close() happens. No schema or API changes.
- **User confirm required:** No

---

### F-05: N+1 query in note_meta backlinks — full-table LIKE scan on body
- **Dimension:** performance
- **File(s):** engine/api.py:1040-1043
- **Description:** The `/notes/<path>/meta` endpoint scans the entire `notes` table using `WHERE LOWER(body) LIKE LOWER('%title%')` to find backlinks. No index on body; leading wildcard means full scan. The `relationships` table already stores wiki-link backlinks (type='backlink') built during reindex — but this endpoint ignores it. Called every time a note is opened in the GUI.
- **Root cause:** Backlink detection implemented as LIKE scan rather than using the pre-computed `relationships` table. Known per STATE.md decision PERF-01.
- **Fix:** Replace LIKE scan with: `SELECT source_path, title FROM relationships r JOIN notes n ON n.path=r.source_path WHERE r.target_path=? AND r.rel_type='backlink'`. O(1) with existing index. Run `sb-reindex` if relationships table is not fully populated.
- **Blast radius:** Low — pure query replacement on a read endpoint. No write path changes.
- **User confirm required:** No

---

### F-06: sb_anonymize MCP tool has zero test coverage — GDPR safety operation untested
- **Dimension:** coverage
- **File(s):** tests/test_mcp.py (missing tests), engine/mcp_server.py (sb_anonymize handler)
- **Description:** `sb_anonymize` is a GDPR anonymization operation with a two-step confirm_token pattern. It has zero test coverage at the MCP layer. `sb_forget` (same pattern) has good token tests. The gap is inconsistent and means regressions in the token flow or scrub logic go undetected.
- **Root cause:** Tool was implemented but tests were not written.
- **Fix:** Add 3 tests to `tests/test_mcp.py`: (1) first call returns `confirm_token` with `status=pending`, (2) invalid token raises ValueError, (3) valid token executes and scrubs the note body.
- **Blast radius:** Test-only addition. No engine code changes.
- **User confirm required:** No

---

## Medium

### F-07: sb_files subfolder param allows path traversal outside files_dir
- **Dimension:** security
- **File(s):** engine/mcp_server.py:685
- **Description:** `sb_files` tool accepts a `subfolder` parameter concatenated directly into a path without validation: `search_root = files_dir / subfolder`. Passing `subfolder = "../../../etc"` escapes the files directory. The rglob then lists files outside the brain, returning absolute paths to the caller.
- **Root cause:** Subfolder parameter added without path validation.
- **Fix:** After constructing the path, assert it stays inside files_dir: `search_root = (files_dir / subfolder).resolve(); if not search_root.is_relative_to(files_dir.resolve()): raise ValueError("INVALID_SUBFOLDER")`.
- **Blast radius:** Low — affects only `sb_files`. Valid subfolder values unaffected.
- **User confirm required:** No

---

### F-08: Duplicate import at api.py:24-25 — line 24 is dead
- **Dimension:** security, architecture, dead-code (all three auditors flagged same location)
- **File(s):** engine/api.py:24-25
- **Description:** `from engine.paths import BRAIN_ROOT` appears on line 24. Line 25 immediately overwrites with `from engine.paths import BRAIN_ROOT, store_path`. Line 24 is a no-op.
- **Root cause:** Copy-paste when `store_path` was added; line 24 not removed.
- **Fix:** Delete line 24. Keep only line 25.
- **Blast radius:** Zero. Runtime effect identical.
- **User confirm required:** No

---

### F-09: No explicit CSP in Chrome extension manifest; innerHTML with single-quote gap
- **Dimension:** security
- **File(s):** chrome-extension/manifest.json:20-24, chrome-extension/popup.js:306-315
- **Description:** Two issues: (9a) manifest.json has no `content_security_policy` key — relies on Chrome MV3 default rather than explicit policy, silently accepting future weakening; (9b) `innerHTML` in popup.js:311 uses `escapeHtml()` which does not escape single quotes, creating a fragile pattern that future template changes could exploit.
- **Root cause:** CSP never explicitly configured; escapeHtml written for content context, not attribute context.
- **Fix:** (9a) Add `"content_security_policy": {"extension_pages": "script-src 'self'; object-src 'self'"}` to manifest.json. (9b) Use DOM API (`textContent`, `createElement`) instead of `innerHTML` for history list rendering.
- **Blast radius:** Low — 9a is additive; 9b is a functional equivalent change.
- **User confirm required:** No

---

### F-10: FK CASCADE missing on action_items and note_embeddings
- **Dimension:** architecture
- **File(s):** engine/db.py:68-75 (note_embeddings schema), engine/db.py:77-83 (action_items schema)
- **Description:** `note_tags` and `note_people` have `ON DELETE CASCADE` FK constraints. `action_items`, `note_embeddings`, `relationships` do NOT. They rely on application-level cascade in `forget.py`. If a note is deleted outside the `forget_person()` path (direct SQL, reindex cleanup, delete endpoint), child rows in these tables become orphans — a GDPR correctness gap.
- **Root cause:** Phase 32 added FK CASCADE only to the new junction tables. Original tables not migrated.
- **Fix:** Add `ON DELETE CASCADE` FK to `note_embeddings(note_path)`, `action_items(note_path)`, and `relationships` (both source and target). Do NOT cascade `audit_log` — audit entries must survive deletion for compliance. Schema migration required. `get_connection()` already enables `PRAGMA foreign_keys = ON`.
- **Blast radius:** Medium — schema migration needed. `forget.py` explicit deletes become belt-and-suspenders (correct).
- **User confirm required:** No

---

### F-11: Late BRAIN_ROOT re-imports inside api.py function bodies (3 locations)
- **Dimension:** architecture
- **File(s):** engine/api.py:1194, engine/api.py:1584, engine/api.py:1640
- **Description:** Three functions independently re-import `from engine.paths import BRAIN_ROOT` inside their function body despite module-level import at line 25. In production these are redundant. They exist to pick up monkeypatched values in tests — but this is unclear test design.
- **Root cause:** Test isolation workaround. Functions re-import inside body so pytest monkeypatching of `engine.paths.BRAIN_ROOT` is picked up.
- **Fix:** Verify whether tests for these endpoints actually monkeypatch `engine.paths.BRAIN_ROOT`. If yes, update tests to patch at module level or use `BRAIN_PATH` env var pattern. If tests pass without late imports, remove all three. Run `uv run pytest tests/ -q` after removal.
- **Blast radius:** Test failures if test fixtures rely on late import behavior. Verify before removing.
- **User confirm required:** No

---

### F-12: sb_capture_link has zero test coverage — Chrome extension primary save path
- **Dimension:** coverage
- **File(s):** tests/test_mcp.py (missing tests), engine/mcp_server.py (sb_capture_link), engine/link_capture.py
- **Description:** `sb_capture_link` is the Chrome extension's primary save path. Zero test coverage means any regression in URL parsing, note creation, or error handling goes undetected. No smoke test exists.
- **Root cause:** Tool implemented without tests.
- **Fix:** Add 2 tests to `tests/test_mcp.py`: (1) happy path with URL and title returns created status, (2) invalid/missing URL raises or returns error dict.
- **Blast radius:** Test-only addition.
- **User confirm required:** No

---

### F-13: sb_connections and sb_digest have zero test coverage
- **Dimension:** coverage
- **File(s):** tests/test_mcp.py (missing tests), engine/mcp_server.py
- **Description:** `sb_connections` (discovery feature) and `sb_digest` (weekly digest generation) have zero test coverage. A Python error in either would not be caught before reaching a user.
- **Root cause:** Tools implemented without tests.
- **Fix:** Add basic smoke tests: call each tool, assert returns expected shape (dict with connections/digest key).
- **Blast radius:** Test-only addition.
- **User confirm required:** No

---

### F-14: sb_actions_done has zero test coverage — action item lifecycle untested
- **Dimension:** coverage
- **File(s):** tests/test_mcp.py (missing tests), engine/mcp_server.py
- **Description:** Marking action items done is a core workflow. No test verifies the done flag is set in DB, or that calling again is a no-op. Complete action item lifecycle (capture → list → mark done) is untested.
- **Root cause:** Tool implemented without tests.
- **Fix:** Add 2 tests using isolated_action_db fixture: (1) mark action done → DB shows `done=1`, (2) calling again is a no-op.
- **Blast radius:** Test-only addition.
- **User confirm required:** No

---

### F-15: get_missing_file_notes hardcoded LIMIT 500 — silently under-reports at scale
- **Dimension:** performance
- **File(s):** engine/brain_health.py:40-41
- **Description:** `get_missing_file_notes()` fetches at most 500 notes from DB, then calls `os.path.exists()` per row. At 100K notes, 99,500 notes are never checked. Health score and orphan count are silently incorrect at scale.
- **Root cause:** LIMIT 500 added as a latency guard but creates a correctness failure.
- **Fix:** Remove or raise the LIMIT. Add a configurable cap (e.g., 10000) with a logged warning when truncated: `if len(rows) == cap: logger.warning("Orphan check truncated at %d rows", cap)`.
- **Blast radius:** Low — pure query and loop change on a health check function.
- **User confirm required:** No

---

### F-16: N+1 tag filter queries in search post-filter (200 queries per search at scale)
- **Dimension:** performance
- **File(s):** engine/api.py:220-230, 244-253
- **Description:** When filtering by multiple tags (POST /search with `tags` param), the code loops through every candidate result and executes a separate DB query per note to fetch tags from `note_tags`. At 200 FTS5 candidates, this is 200 sequential queries per search request.
- **Root cause:** Per-row tag lookups used to avoid semgrep SQL injection scanner blocking dynamic IN-clause. However, parameterized IN is safe.
- **Fix:** Batch the tag fetch: collect all candidate paths, then `SELECT note_path, tag FROM note_tags WHERE note_path IN (?, ?, ...)` — parameterized IN-clause satisfies semgrep. Match results in Python.
- **Blast radius:** Low — internal query optimization, same return shape.
- **User confirm required:** No

---

### F-17: No integration test for capture → search → read cycle at MCP layer
- **Dimension:** coverage
- **File(s):** tests/test_mcp.py (missing integration test)
- **Description:** Each step (capture, search, read) is unit-tested individually, but the composition across the full MCP workflow is untested. Subtle bugs in search result formatting or read path could exist undetected in the primary usage pattern (95% of actual use).
- **Root cause:** Integration tests not written for the MCP stack.
- **Fix:** Add 1 integration test to `test_mcp.py`: `sb_capture` a note → `sb_search` for it → assert found → `sb_read` it back → assert body matches.
- **Blast radius:** Test-only addition.
- **User confirm required:** No

---

## Low (STATE.md candidates)

- F-18: SEC-06 — CORS accepts any `chrome-extension://*` origin (accepted risk) — engine/api.py:64
- F-19: SEC-07 — Host header injection in `/ui` script injection (localhost-only, accepted risk) — engine/api.py:786-791
- F-20: SEC-08 — `/ui/prefs` PUT has no size/schema validation (localhost-only, low impact) — engine/api.py:783
- F-21: SEC-09 — Chrome extension `<all_urls>` permission scope (accepted risk, on-demand only) — manifest.json:21
- F-22: ARCH-06 — api.py at 1754 lines with no Flask Blueprint partitioning (defer to dedicated refactor plan) — engine/api.py
- F-23: ARCH-07 — consolidate.py lazy import comment says "circular import" but reason is actually load-time deferral — engine/consolidate.py:99-108
- F-24: PERF-09 — list_people fetches all records then paginates in Python (known trade-off from Phase 33) — engine/api.py:317-331
- F-25: PERF-10 — get_stale_notes fetches 3× limit then filters in Python (15 disk reads; acceptable at current scale) — engine/intelligence.py:241-283
- F-26: PERF-11 — startup() uses glob.glob for disk count instead of DB COUNT(*) — engine/api.py:1731
- F-27: DEAD-03 — Deprecated `/people` route aliases still live; `IntelligencePage.tsx:50` not yet migrated to `/persons` — engine/api.py:318,456,543,574
- F-28: DEAD-04 — `os.environ.get("BRAIN_PATH", ...)` repeated 13× in api.py instead of using imported `BRAIN_ROOT` — engine/api.py
- F-29: DEAD-05 — `json.loads(col or "[]")` pattern for tags/people repeated 13× across 5 files; no shared helper — multiple engine modules
- F-30: DEAD-07 — `ensure_person_profile()` in links.py writes to `person/` (singular) but brain uses `people/` (plural) — engine/links.py:46-60
- F-31: DEAD-08 — `datetime.utcnow()` used 33× across 13 files; deprecated in Python 3.12+ — multiple engine modules

---

## Remediation Grouping

### Group A: API Input Hardening (single plan, no user confirm)
- **F-01** — Unguarded int() → HTTP 500 (8 locations in api.py)
- **F-07** — sb_files subfolder path traversal (mcp_server.py:685)
- **F-08** — Duplicate import at api.py:24 (trivial, bundle with this plan)
- **F-09** — Chrome extension CSP + innerHTML (manifest.json, popup.js)

Shared fix pattern: input validation helpers. Group together in one plan (`39-07`). Estimated: 2 tasks, ~5 files.

---

### Group B: Missing DB Indexes + FK CASCADE (single plan, schema migration)
- **F-10** — FK CASCADE on action_items, note_embeddings, relationships

And high-priority index additions from the performance Index Coverage Summary (not elevated to numbered findings because they are additions, not bugs):
- `notes(archived)` index — used in nearly every paginated list query
- `action_items(note_path)` index — heavily used in per-note action count subqueries

Estimated: 1 task, 1 file (db.py migration only). Bundle index additions with FK CASCADE migration.

---

### Group C: Performance Query Fixes (single plan)
- **F-03** — recap_entity LIKE scan → junction table query (intelligence.py)
- **F-04** — recap_main closed connection bug (intelligence.py)
- **F-05** — note_meta backlink LIKE scan → relationships table (api.py)
- **F-16** — N+1 tag filter queries in search (api.py)

Shared characteristic: SQL query replacements, no schema changes, low blast radius. Single plan, ~4 tasks. Run full test suite after.

---

### Group D: Dead Code Removal (single plan)
- **F-02** — Delete templates.py + remove dead test (engine/templates.py, tests/test_capture.py)
- **F-11** — Late BRAIN_ROOT re-imports (api.py:1194, 1584, 1640) — verify tests first

Separate from Group A because deletion carries higher blast radius than import changes.

---

### Group E: Test Coverage Gaps (single plan)
- **F-06** — sb_anonymize tests (3 tests)
- **F-12** — sb_capture_link tests (2 tests)
- **F-13** — sb_connections + sb_digest smoke tests (2 tests)
- **F-14** — sb_actions_done lifecycle tests (2 tests)
- **F-17** — Capture → search → read integration test (1 test)

All test-only additions to `test_mcp.py`. Single plan, 1 task. Estimated ~10 new test functions.

---

### Group F: Medium Coverage Gaps — New Test Files (separate plan or bundle with Group E)
From COV-06 through COV-10 (Medium severity, new test files needed):
- `tests/test_attachments.py` — attachments.py has 90 lines, no tests
- `tests/test_merge_cli.py` — merge_cli.py has 37 lines, no tests
- `tests/test_config_loader.py` — config_loader.py has 34 lines, critical at startup
- `tests/test_ratelimit.py` — ratelimit.py has 30 lines, no tests
- MCP audit log entry test (1 test in test_mcp.py)

Could bundle with Group E if timeline allows, or defer to Phase 40.

---

### Findings Requiring User Confirmation Before Implementation
- **F-22** (ARCH-06) — api.py Blueprint refactor: structural change, defer to dedicated plan, user must decide priority
- **F-30** (DEAD-07) — `ensure_person_profile()` stale path: needs audit of Phase 30/32 interactions before changing; user review recommended
- **PERF-07** (not elevated, STATE.md) — get_duplicate_candidates O(n²): replacing with ANN approach is medium complexity; user should confirm approach

---

### Accepted Risks (No Remediation Planned)
- F-18, F-19, F-21 — CORS, host header injection, `<all_urls>`: localhost-only deployment; documented per SECURITY.md
- F-24, F-25 — Python-level pagination: known Phase 33 trade-offs; acceptable at current scale
- DEAD-06 (sharding.py unwired): Phase 38 scale architecture module; keep, add CLI entry point or document as maintenance-only

---

### PERF-05 and PERF-06 — Deferred (Medium complexity, Phase 38 scope)
- ANN cold-start (PERF-05): requires background thread warm-up at api startup. Medium blast radius. Defer to Phase 40 performance plan.
- Excerpt enrichment N+1 (PERF-06): batch chunk fetch is straightforward but touches search.py core. Defer to Phase 40.
- Double rglob in reindex (PERF-03): Medium complexity consolidation of two filesystem walks. Defer to Phase 40.
- get_duplicate_candidates O(n²) (PERF-07): ANN-based replacement. Defer to Phase 40.
