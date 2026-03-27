# Phase 39: Remediation Scope

**Approved:** 2026-03-27
**Decision:** fix-all — all High + Medium findings approved for remediation

---

## Approved Fixes

| Finding | Severity | Title | Files | Risky |
|---------|----------|-------|-------|-------|
| F-01 | High | Unguarded int() → HTTP 500 on 8 endpoints | engine/api.py (8 locations) | No |
| F-02 | High | templates.py dead module — delete it | engine/templates.py, tests/test_capture.py | No |
| F-03 | High | recap_entity LIKE scan bypasses Phase 32 junction tables | engine/intelligence.py:437-443 | No |
| F-04 | High | recap_main queries closed DB connection — latent crash | engine/intelligence.py:810-820 | No |
| F-05 | High | note_meta backlink uses full-table LIKE scan | engine/api.py:1040-1043 | No |
| F-06 | High | sb_anonymize zero tests — GDPR op untested | tests/test_mcp.py | No |
| F-07 | Medium | sb_files subfolder path traversal outside files_dir | engine/mcp_server.py:685 | No |
| F-08 | Medium | Duplicate import at api.py:24 | engine/api.py:24 | No |
| F-09 | Medium | Chrome ext: no CSP + innerHTML single-quote gap | chrome-extension/manifest.json, popup.js | No |
| F-10 | Medium | FK CASCADE missing on action_items, note_embeddings | engine/db.py | Yes (schema migration) |
| F-11 | Medium | Late BRAIN_ROOT re-imports in api.py (verify tests first) | engine/api.py:1194,1584,1640 | No |
| F-12 | Medium | sb_capture_link zero tests — Chrome ext primary path | tests/test_mcp.py | No |
| F-13 | Medium | sb_connections + sb_digest zero tests | tests/test_mcp.py | No |
| F-14 | Medium | sb_actions_done lifecycle untested | tests/test_mcp.py | No |
| F-15 | Medium | Orphan check truncated at 500 rows — silently wrong at scale | engine/brain_health.py:40-41 | No |
| F-16 | Medium | N+1 tag filter queries in search (200 queries/search) | engine/api.py:220-253 | No |
| F-17 | Medium | No capture→search→read integration test at MCP layer | tests/test_mcp.py | No |

**Also approved (bundled with Group B):**
- Add `notes(archived)` index — used in nearly every paginated list query
- Add `action_items(note_path)` index — used in per-note action count subqueries

---

## Deferred

| Finding | Severity | Reason |
|---------|----------|--------|
| PERF-03 | Medium | Double rglob in reindex — medium complexity, defer to Phase 40 |
| PERF-05 | Medium | ANN cold-start warm-up — background thread, defer to Phase 40 |
| PERF-06 | Medium | Excerpt enrichment N+1 in search.py — defer to Phase 40 |
| PERF-07 | Medium | get_duplicate_candidates O(n²) → ANN replacement — defer to Phase 40 |

---

## Skipped / Accepted Risk

| Finding | Severity | Reason |
|---------|----------|--------|
| F-18 (SEC-06) | Low | CORS chrome-extension://* — localhost-only, accepted risk per SECURITY.md |
| F-19 (SEC-07) | Low | Host header injection /ui — localhost-only, accepted risk |
| F-20 (SEC-08) | Low | /ui/prefs no schema validation — localhost-only, low impact |
| F-21 (SEC-09) | Low | <all_urls> permission — accepted risk, on-demand only |
| F-22 (ARCH-06) | Low | api.py Blueprint refactor — defer to dedicated refactor plan |
| F-23–F-31 | Low | Various low-severity items — added to STATE.md Pending Todos |
| DEAD-06 | Info | sharding.py unwired — keep, document as maintenance-only |

---

## Execution Plan

### Group A: API Input Hardening (plan 39-A)
**Findings:** F-01, F-07, F-08, F-09
**Files:** engine/api.py, engine/mcp_server.py, chrome-extension/manifest.json, chrome-extension/popup.js
**Tasks:**
1. Add `_int_param()` helper to api.py; replace all 8 `int(request.args.get(...))` callsites → HTTP 400 on bad input
2. Add `resolve()+is_relative_to()` guard to sb_files subfolder param in mcp_server.py
3. Delete duplicate import at api.py:24
4. Add explicit CSP to chrome-extension/manifest.json; replace innerHTML with DOM API in popup.js

---

### Group B: DB Schema Migration (plan 39-B)
**Findings:** F-10 + index additions
**Files:** engine/db.py
**Tasks:**
1. Add `ON DELETE CASCADE` FK to `note_embeddings(note_path)`, `action_items(note_path)`, `relationships` (source+target, no cascade on audit_log)
2. Add `CREATE INDEX IF NOT EXISTS` for `notes(archived)` and `action_items(note_path)`

---

### Group C: Performance Query Fixes (plan 39-C)
**Findings:** F-03, F-04, F-05, F-15, F-16
**Files:** engine/intelligence.py, engine/api.py, engine/brain_health.py
**Tasks:**
1. Replace recap_entity LIKE scan with junction table query (intelligence.py:437-443)
2. Move conn.close() after recap loop in recap_main (intelligence.py:810-820)
3. Replace note_meta backlink LIKE scan with relationships table query (api.py:1040-1043)
4. Batch N+1 tag filter with parameterized IN-clause (api.py:220-253)
5. Remove/raise LIMIT 500 in get_missing_file_notes with logged warning (brain_health.py:40-41)

---

### Group D: Dead Code Removal (plan 39-D)
**Findings:** F-02, F-11
**Files:** engine/templates.py, tests/test_capture.py, engine/api.py
**Tasks:**
1. Verify `grep -rn "load_template\|render_template" engine/` returns 0 results, then delete engine/templates.py and remove test_capture.py:83-88
2. Verify whether api.py:1194,1584,1640 late re-imports are needed by tests; remove if tests pass without them

---

### Group E: MCP Test Coverage (plan 39-E)
**Findings:** F-06, F-12, F-13, F-14, F-17
**Files:** tests/test_mcp.py
**Tasks:**
1. Add 3 tests for sb_anonymize: confirm_token returned, invalid token raises, valid token scrubs note
2. Add 2 tests for sb_capture_link: happy path + invalid URL error
3. Add 2 smoke tests for sb_connections and sb_digest: call each, assert expected shape
4. Add 2 tests for sb_actions_done lifecycle: mark done → DB shows done=1; calling again is no-op
5. Add 1 integration test: sb_capture → sb_search → assert found → sb_read → assert body matches

---

### Group F: New Test Files for Untested Modules (plan 39-F)
**Source:** COV-06 through COV-10
**Files (new):** tests/test_attachments.py, tests/test_merge_cli.py, tests/test_config_loader.py, tests/test_ratelimit.py
**Tasks:**
1. Write tests/test_attachments.py covering attachments.py (90 lines, no tests)
2. Write tests/test_merge_cli.py covering merge_cli.py (37 lines, no tests)
3. Write tests/test_config_loader.py covering config_loader.py (34 lines, critical at startup)
4. Write tests/test_ratelimit.py covering ratelimit.py (30 lines, no tests)
5. Add MCP audit log entry test to test_mcp.py: capture → verify audit_log row exists
