# Phase 47: Fix Pre-existing Test Failures — Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix exactly 4 tests that have been failing (or xfailed) since before Phase 40:

1. `test_delete_endpoint_404` (tests/test_delete.py) — Flask returns 308 instead of 404
2. `test_bidirectional_relationships` (tests/test_smart_capture.py) — xfail: FK path mismatch
3. `TestSimilarRelationshipAutoLink::test_similar_relationship_inserted_on_confirm` (tests/test_smart_capture.py) — xfail: FK path mismatch
4. `test_smart_capture_golden_path` (tests/test_smart_capture.py) — xfail: FK path mismatch

No new features. No broader test audit. Scope is these 4 tests only.

</domain>

<decisions>
## Implementation Decisions

### D-01: 308 fix approach (test_delete_endpoint_404)

**Two-part fix:**

1. Fix the test URL — strip the leading `/` from the absolute path before passing to `client.delete()` so the URL doesn't produce a double-slash (`//private/tmp/...`) that triggers Flask's 308 redirect normalisation.

2. Add `p.exists()` check in `delete_note_endpoint` (engine/api.py) — if the resolved path does not exist on disk, return `jsonify({"error": "Not Found"}), 404` before calling `delete_note()`. This is the correct HTTP contract: deleting a ghost path should be a 404, not a silent 200.

Both parts are required. The test fix removes the 308 trigger; the route fix adds the correct 404 behaviour.

### D-02: FK path mismatch fix (3 xfailed tests)

**Dual fix: fixture-level + production pipeline.**

**Fixture level:**
- In `conftest.py`, ensure the `isolated_brain` fixture (or wherever `BRAIN_ROOT` is patched) uses `.resolve()` on the `tmp_path` value before patching. This prevents macOS `/tmp` → `/private/tmp` symlink mismatches at the fixture boundary.
- Patch `engine.db.DB_PATH` explicitly in tests that verify relationship rows via `get_connection(str(engine.db.DB_PATH))`. Without this, DB_PATH may drift from BRAIN_ROOT.

**Production pipeline:**
- Audit every place that inserts into the `relationships` table and ensure the `source_path` and `target_path` values are derived from `store_path()` (the canonical relative-path helper from Phase 32). Paths used as FK values must match what `notes.path` stores — no raw absolute paths, no unreolved symlinks.
- Focus areas: `engine/capture.py` (co-captured relationship insert), `engine/mcp_server.py` (similar relationship insert on confirm_token path).

### D-03: xfail markers

Remove `@pytest.mark.xfail` entirely from all 3 affected tests once the FK path mismatch is fixed. These markers exist only to document acknowledged debt — once the debt is paid they become misleading. A failing test must be a real signal.

Remove the markers as part of the same commit that fixes the underlying issue, not as a separate cleanup step.

### Claude's Discretion

- Exact location of `p.exists()` check in `delete_note_endpoint` (before vs after `_resolve_note_path` call — after is correct since we need `p` to be resolved first).
- Whether to add a helper or inline the check.
- Specific xfail `reason=` text to remove (all three have the same pattern, delete all).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Test files (failing tests live here)
- `tests/test_delete.py` — `test_delete_endpoint_404` at line 219
- `tests/test_smart_capture.py` — `test_bidirectional_relationships` at line 419, `TestSimilarRelationshipAutoLink::test_similar_relationship_inserted_on_confirm` at line 840, `test_smart_capture_golden_path` at line 981

### Production code to modify
- `engine/api.py` — `delete_note_endpoint` at line 1641, `_resolve_note_path` at line 296
- `engine/capture.py` — relationship insert logic (co-captured), `store_path()` usage
- `engine/mcp_server.py` — similar relationship insert on confirm_token path (around line 180)

### Test infrastructure
- `tests/conftest.py` — `isolated_brain` fixture (source of path resolution issue)

### Prior decisions (from STATE.md)
- [Phase 43]: Pre-existing FK path mismatch (macOS /var vs /private/var) causes silent co-captured/similar relationship failures — wrapped in try/except, test failures marked xfail, Phase 47 tracks root fix.
- [Phase 32]: `store_path()` is the canonical helper for relative-path storage — all DB inserts must use it.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `store_path(abs_path)` in `engine/paths.py` — converts absolute path to relative; already used throughout capture pipeline. This is the fix anchor for FK path consistency.
- `_resolve_note_path()` in `engine/api.py` — already handles absolute path reconstruction from URL; the `p.exists()` check slots in cleanly after it.

### Established Patterns
- 404 handling: other routes return `jsonify({"error": "Not Found"}), 404` — match this pattern.
- DB path isolation in tests: Phase 37 tests patch `engine.db.DB_PATH` and `engine.paths.BRAIN_ROOT` together — follow that pattern for the 3 xfailed tests.
- `tmp_path.resolve()` in fixtures: some conftest fixtures already use `.resolve()` — extend to `isolated_brain`.

### Integration Points
- `delete_note_endpoint` → `_resolve_note_path` → `delete_note` — the `p.exists()` check goes between resolution and `delete_note` call.
- `sb_capture_smart` → `capture_note` → relationship insert — the FK source/target paths must all go through `store_path()` before DB insert.

</code_context>

<specifics>
## Specific Ideas

No specific references beyond the test file line numbers above. The fix pattern is consistent with existing Phase 32/37 conventions already in the codebase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 47-fix-pre-existing-test-failures*
*Context gathered: 2026-03-30*
