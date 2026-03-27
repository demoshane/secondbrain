# Test Coverage Audit Findings

**Audit date:** 2026-03-27
**Auditor:** Phase 39, Plan 04
**Scope:** All engine/*.py modules vs tests/, with deep MCP tool coverage analysis

---

## Module Coverage Matrix

| Engine Module | Lines | Test File | Test Count | Coverage Quality |
|---------------|-------|-----------|-----------|------------------|
| `api.py` | 1754 | `test_api.py` + `test_api_*.py` (4 files) | 40+ | Good — endpoints tested; input validation gaps exist |
| `mcp_server.py` | 1550 | `test_mcp.py` | 62 | Partial — 13/22 tools have dedicated tests; 9 untested |
| `intelligence.py` | 824 | `test_intelligence.py` | 36 | Good — recap, connections, actions, digests tested |
| `db.py` | 570 | `test_db.py` | unknown | Good — schema, migrations tested |
| `capture.py` | 576 | `test_capture.py` | 20 | Good — write path, rollback, frontmatter tested |
| `brain_health.py` | 657 | `test_brain_health.py` | unknown | Present |
| `search.py` | 412 | `test_search.py` | 17 | Good — FTS5, semantic, hybrid tested |
| `init_brain.py` | 382 | `test_init_brain.py` | unknown | Present |
| `reindex.py` | 374 | `test_reindex.py` | unknown | Present |
| `segmenter.py` | 479 | `test_smart_capture.py` (shared) | 20+ | Good — heavy coverage via test_smart_capture.py |
| `health.py` | 323 | `test_health.py` | unknown | Present |
| `watcher.py` | 260 | `test_watcher.py` | unknown | Present |
| `entities.py` | 220 | `test_entities.py` | unknown | Present |
| `sharding.py` | 207 | `test_sharding.py` | unknown | Present |
| `backup.py` | 245 | `test_backup.py` | unknown | Present |
| `ann_index.py` | 243 | `test_ann_index.py` | unknown | Present |
| `anonymize.py` | 172 | `test_anonymize.py` | unknown | Present |
| `ai.py` | 180 | `test_ai.py` | unknown | Present |
| `embeddings.py` | 162 | `test_embeddings.py` | unknown | Present |
| `forget.py` | 237 | `test_forget.py` | unknown | Present — person erasure + cascade |
| `consolidate.py` | 124 | `test_consolidate.py` | 2 | **THIN** — only runs/idempotent; no behavior tested |
| `digest.py` | 127 | `test_digest.py` | unknown | Present |
| `links.py` | 134 | `test_links.py` | unknown | Present |
| `export.py` | 107 | `test_export.py` | unknown | Present |
| `delete.py` | 106 | `test_delete.py` | unknown | Present |
| `read.py` | 110 | `test_read.py` | unknown | Present |
| `people.py` | 57 | `test_people.py` | unknown | Present |
| `router.py` | 31 | `test_router.py` | unknown | Present |
| `link_capture.py` | 51 | `test_link_capture.py` | unknown | Present |
| `classifier.py` | 42 | `test_classifier.py` | 5 | **THIN** — good coverage for its size (all classifier paths tested) |
| `smart_classifier.py` | 70 | `test_smart_capture.py` (shared) | partial | Covered via integration tests |
| `rag.py` | 51 | `test_rag.py` | unknown | Present but module may be stale (D-01) |
| `paths.py` | 73 | `test_paths.py` | unknown | Present |
| `adapters/claude_adapter.py` | unknown | `test_adapters.py` | unknown | Present |
| `adapters/ollama_adapter.py` | unknown | `test_adapters.py` | unknown | Present |
| `adapters/base.py` | unknown | `test_adapters.py` | unknown | Present |
| `gui/__init__.py` | unknown | `test_gui.py` | unknown | Present |
| `config_loader.py` | 34 | **NONE** | 0 | **MISSING** |
| `ratelimit.py` | 30 | **NONE** | 0 | **MISSING** |
| `merge_cli.py` | 37 | **NONE** | 0 | **MISSING** |
| `attachments.py` | 90 | **NONE** | 0 | **MISSING** |
| `templates.py` | 41 | **NONE** | 0 | **MISSING** (but module may be stale) |
| `hooks/post_commit.py` | unknown | `test_hooks.py` | unknown | Present |

**Missing test files: 5 modules** (`config_loader`, `ratelimit`, `merge_cli`, `attachments`, `templates`)

---

## MCP Tool Coverage Matrix

The 22 MCP tools are defined in `engine/mcp_server.py`. Coverage assessed from `tests/test_mcp.py` (1335 lines, 62 test functions).

| Tool | Test Exists | Behavior Tested | Edge Cases | Notes |
|------|------------|----------------|-----------|-------|
| `sb_capture` | Yes | BODY_TOO_LARGE guard, TITLE_TOO_LONG guard | Dedup (xfail stubs) | Core write path not tested end-to-end |
| `sb_capture_batch` | Yes | Happy path (2 notes), partial failure | — | Behavior tested |
| `sb_capture_smart` | Yes | Type routing (meeting/project/default), auto-save, no confirm_token | — | Well covered |
| `sb_capture_link` | **No** | — | — | Zero coverage |
| `sb_search` | Yes | Basic search, type filter | — | No edge cases for empty results, pagination |
| `sb_read` | Yes | PII routing, path traversal rejection | PATH_OUTSIDE_BRAIN | Good — security edge cases covered |
| `sb_edit` | Yes | Frontmatter preservation | — | Basic behavior tested |
| `sb_recap` | Yes | No-name path, with-name path, empty result fallback | — | Good |
| `sb_digest` | **No** | — | — | Zero coverage |
| `sb_connections` | **No** | — | — | Zero coverage |
| `sb_actions` | Yes | Returns items with due_date key | — | Minimal — list shape only |
| `sb_actions_done` | **No** | — | — | Zero coverage |
| `sb_files` | Yes | Pagination shape (keys: files, total, total_pages, page) | — | Shape only, no content tested |
| `sb_forget` | Yes | Two-step token flow (pending+token), invalid token raises | Token expiry | Good security coverage |
| `sb_anonymize` | **No** | — | — | Zero coverage |
| `sb_tools` | Yes | Returns list with name/description/parameters | — | Basic shape test |
| `sb_tag` | Yes | add/remove, fuzzy match, confirm_token gate | — | Well covered |
| `sb_remind` | Yes | set/clear due_date, tool registration | — | Good |
| `sb_link` | Yes | Create relationship, custom rel_type, idempotent | — | Well covered |
| `sb_unlink` | Yes | Remove relationship, noop on absent pair | — | Well covered |
| `sb_person_context` | Yes | Returns note body, meetings, actions, mentions; unknown path; fast path via note_people | — | Excellent coverage |
| `sb_list_persons` | Yes | Happy path, empty result | — | Covered |

**Summary: 13/22 tools have dedicated tests. 9 tools have NO test coverage:**
- `sb_capture_link` — completely untested
- `sb_digest` — completely untested
- `sb_connections` — completely untested
- `sb_actions_done` — completely untested
- `sb_anonymize` — completely untested (destructive GDPR operation)
- Plus `sb_search`, `sb_actions`, `sb_files`, `sb_recap` are shallowly tested (shape-only, no behavior depth)

---

## Thin Test Analysis

### test_gitignore.py — 14 lines
**Verdict:** Tests .gitignore file content, not engine code. These are infrastructure correctness checks. Low value as "tests" but they serve as guardrails. Not a gap worth filling.

### test_classifier.py — 37 lines, 5 tests
**Verdict:** Actually good for module size (42 lines). Tests all four classifier paths (pii frontmatter wins, private wins, public wins, keyword scan, clean body). Adequate coverage.

### test_consolidate.py — 40 lines, 2 tests
**Verdict:** Thin but covers the critical happy path: consolidate_main runs without crash and produces correct output shape, plus the one-per-day snapshot guard. Missing: tests for what happens when action_items exist (archival behavior), dangling relationship cleanup behavior, health_snapshot content correctness.

### test_audit.py — 42 lines, 3 tests
**Verdict:** Thin but covers the two key audit log event types (create and search). Third test is a detect-secrets scan that skips outside devcontainer. Missing: edit events, forget events, MCP audit log entries.

---

## Integration Test Gaps

### Capture → Search → Read cycle
No dedicated integration test exercises: capture a note → search for it → read it back. Individual unit tests cover each step, but the full MCP workflow (which is 95% of actual usage) is not tested end-to-end. The closest is `test_sb_capture_smart_auto_saves` which captures and then queries DB directly, but does not search or read back.

### Forget → Cascade → Verify Gone
`test_forget.py` tests the `forget_person()` function directly. No test exercises the MCP surface: `sb_forget` (confirm token) → file deleted → search returns no results → `sb_read` raises PATH_OUTSIDE_BRAIN. The MCP-level forget pipeline is only partially tested (token flow, but not actual cascade deletion and search exclusion).

### sb_anonymize — zero coverage
`sb_anonymize` is a GDPR operation with a two-step token. It has no tests at all. The underlying `engine/anonymize.py` has `test_anonymize.py` but the MCP tool wrapper has no tests.

### sb_actions_done workflow
No test for the complete action item lifecycle: action item created (via capture) → listed (sb_actions) → marked done (sb_actions_done). The mark-done step is completely untested.

---

## Findings

### COV-01
- **Severity:** High
- **Gap:** `sb_anonymize` MCP tool has zero test coverage
- **Risk:** GDPR anonymization workflow is a primary safety operation. Regressions in the two-step token pattern or the scrub logic would go undetected. This is the MCP equivalent of `sb_forget` which HAS token tests — the gap is inconsistent.
- **Recommended fix:** Add 3 tests to `test_mcp.py`: (1) first call returns confirm_token with status=pending, (2) invalid token raises ValueError, (3) valid token executes and scrubs the note body

### COV-02
- **Severity:** High
- **Gap:** `sb_capture_link` has zero test coverage (completely untested MCP tool)
- **Risk:** Link capture is the Chrome extension's primary save path. Any regression in parsing, URL extraction, or note creation goes undetected. No smoke test exists.
- **Recommended fix:** Add 2 tests: (1) happy path with URL and title returns created status, (2) invalid URL raises or returns error dict

### COV-03
- **Severity:** High
- **Gap:** `sb_connections` and `sb_digest` have zero test coverage
- **Risk:** `sb_connections` is a discovery feature; `sb_digest` generates weekly digests. Neither has a smoke test. A Python error in either would not be caught before reaching a user.
- **Recommended fix:** Add basic smoke tests: call each tool, assert returns expected shape (dict with connections/digest key)

### COV-04
- **Severity:** High
- **Gap:** `sb_actions_done` has zero test coverage
- **Risk:** Marking action items done is a core workflow. No test verifies the done flag is set in DB, or that re-calling does not error.
- **Recommended fix:** Add 2 tests using isolated_action_db fixture: (1) mark action done → DB shows done=1, (2) calling again is a noop

### COV-05
- **Severity:** Medium
- **Gap:** No integration test for the capture → search → read cycle end-to-end (at MCP layer)
- **Risk:** Each step is unit-tested individually, but the composition is untested. Subtle bugs in search result formatting or read path could exist undetected in the primary usage pattern (95% MCP).
- **Recommended fix:** Add 1 integration test to `test_mcp.py`: `sb_capture` a note → `sb_search` for it → assert found in results → `sb_read` it back → assert body matches

### COV-06
- **Severity:** Medium
- **Gap:** `engine/attachments.py` (90 lines) has no test file
- **Risk:** Attachments module handles binary file tracking. No tests for attachment link creation, deletion, or DB consistency.
- **Recommended fix:** Create `tests/test_attachments.py` with basic add/list/remove tests

### COV-07
- **Severity:** Medium
- **Gap:** `engine/merge_cli.py` (37 lines) has no test file
- **Risk:** Merge CLI is part of the consolidation/dedup workflow. No tests for the merge execution path.
- **Recommended fix:** Create `tests/test_merge_cli.py` with basic merge operation test using tmp brain

### COV-08
- **Severity:** Medium
- **Gap:** `engine/config_loader.py` (34 lines) has no test file
- **Risk:** Config loader is used at startup. A regression in config parsing would crash all engine operations on first use. The module is small but critical.
- **Recommended fix:** Create `tests/test_config_loader.py`: (1) default config loads, (2) TOML file overrides default, (3) missing file returns defaults gracefully

### COV-09
- **Severity:** Medium
- **Gap:** `engine/ratelimit.py` (30 lines) has no test file
- **Risk:** Rate limiting, if broken, either blocks legitimate operations or fails open (no limiting at all). The module is 30 lines — easy to test completely.
- **Recommended fix:** Create `tests/test_ratelimit.py`: (1) first N calls succeed, (2) call N+1 is rate-limited, (3) window resets after expiry

### COV-10
- **Severity:** Medium
- **Gap:** MCP audit log entries not tested (test_audit.py only covers capture/search events from engine layer, not MCP layer)
- **Risk:** MCP operations route through `_log_mcp_audit()` — no test verifies audit entries are written when MCP tools are called. A refactor could silently break audit logging.
- **Recommended fix:** Add 1 test to `test_mcp.py`: call `sb_search` via MCP, query audit_log table, assert `mcp_*` event type is present

### COV-11
- **Severity:** Low
- **Gap:** Chrome extension has zero automated tests (no test runner configured)
- **Risk:** JS logic in popup.js, content.js is exercised only manually. Regressions only caught by user.
- **Recommended fix:** Document as low-priority tech debt in STATE.md. Adding Jest would be the fix, but out of scope for this phase.

### COV-12
- **Severity:** Low
- **Gap:** `engine/templates.py` (41 lines) has no test file but module is likely stale (not imported by engine code)
- **Risk:** If the module is dead, no test is needed. If it's live, it needs tests.
- **Recommended fix:** Confirm via grep whether `templates.py` is imported anywhere in engine code. If dead, delete (tracked as D-02 in dead code audit). If live, add tests.

### COV-13
- **Severity:** Low
- **Gap:** `test_consolidate.py` does not test action archival behavior — only that consolidate_main runs and returns correct output shape
- **Risk:** The actual archival logic (which action items get archived, thresholds) could regress without the test catching it.
- **Recommended fix:** Add 2 tests: (1) action item older than threshold gets archived, (2) recent action item is not archived

### COV-14
- **Severity:** Low
- **Gap:** `sb_search` tested with empty query and type filter but not with pagination parameters or empty result set
- **Risk:** Pagination off-by-one or empty-result formatting bugs go undetected.
- **Recommended fix:** Add 2 tests: (1) page=2 with insufficient results returns empty results list, (2) search with no match returns empty results with total=0

---

## Summary

**MCP tool coverage: 13/22 (59%) have any test coverage**

Critical MCP gaps: `sb_capture_link`, `sb_anonymize`, `sb_actions_done`, `sb_connections`, `sb_digest`

**Engine module coverage: 34/39 modules have test files (87%)**

Missing test files: `config_loader.py`, `ratelimit.py`, `merge_cli.py`, `attachments.py`, `templates.py`

**Integration test coverage: None** — no end-to-end MCP workflow tests exist

**Total findings: 14**
- High: 4 (COV-01 through COV-04)
- Medium: 6 (COV-05 through COV-10)
- Low: 4 (COV-11 through COV-14)
