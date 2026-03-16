---
phase: 16-semantic-search-and-digest
verified: 2026-03-15T00:00:00Z
status: passed
score: 4/4 success criteria verified
re_verification: false
human_verification:
  - test: "Confirm launchd plist fires sb-digest on Monday 08:00"
    expected: "Digest file written to BRAIN_ROOT/.meta/digests/ on Monday morning"
    why_human: "Requires waiting for real calendar trigger or manual launchctl start"
---

# Phase 16: Semantic Search and Digest — Verification Report

**Phase Goal:** Users can find notes by meaning (not just keywords) and receive a weekly digest of brain activity, themes, and open actions
**Verified:** 2026-03-15
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `sb-search --semantic <query>` returns semantically relevant notes even when query shares no keywords with content | VERIFIED | `search_semantic()` in `engine/search.py` L105–178: loads sqlite-vec, embeds query via `embed_texts`, runs `vec_distance_cosine` KNN against `note_embeddings`, returns list with `score = 1.0 - dist` |
| 2 | Hybrid search combines BM25 and vector via RRF; `sb-search` (no flag) uses merged ranking | VERIFIED | `_rrf_merge()` L80–102, `search_hybrid()` L181–204; `main()` L224–229 defaults to `search_hybrid(conn, args.query, limit=args.limit)` when no flags; mutually exclusive `--semantic`/`--keyword` group in argparse |
| 3 | `sb-recap <name>` returns cross-context synthesis for person or project; PII notes route through Ollama | VERIFIED | `recap_entity()` in `engine/intelligence.py` L291–398: fetches via `search_hybrid` + `people LIKE` query, splits by `sensitivity == "pii"`, calls `_router.get_adapter("pii", CONFIG_PATH)` for PII rows and `_router.get_adapter("public", CONFIG_PATH)` for others; `recap_main()` L405–458 routes explicit args to `recap_entity()` |
| 4 | Weekly digest written to `.meta/digests/` automatically; readable via `sb-read --digest latest`; four sections; PII summaries via Ollama | VERIFIED | `generate_digest()` in `engine/digest.py` L27–114: idempotent week-file check, four-section `_render_digest_body()`, PII routing via `_router.get_adapter("pii", CONFIG_PATH)`; `_resolve_digest()` + `--digest` flag in `engine/read.py` L76–103; `write_digest_plist()` in `scripts/install_native.py` L82–109 with `StartCalendarInterval Weekday=1 Hour=8` |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/search.py` | `search_semantic()`, `search_hybrid()`, `_rrf_merge()`, updated `main()` | VERIFIED | All three functions present and substantive; `main()` has `--semantic`/`--keyword` argparse flags; default mode calls `search_hybrid()` |
| `engine/intelligence.py` | `recap_entity(name, conn)`; updated `recap_main()` | VERIFIED | `recap_entity()` at L291; `recap_main()` routes `args.context` to `recap_entity()` at L416; backward-compat session recap preserved |
| `engine/digest.py` | `generate_digest()`, `digest_main()`, `_week_filename()`, `_render_digest_body()` | VERIFIED | All four functions present and fully implemented; no `NotImplementedError` stubs remain |
| `engine/read.py` | Updated `main()` with `--digest` flag; `_resolve_digest()` | VERIFIED | `_resolve_digest()` at L76; `--digest` argparse arg at L91; branch at L94–103 handles `latest` and specific selectors |
| `scripts/install_native.py` | `write_digest_plist()` called from `main()` | VERIFIED | `write_digest_plist()` at L82; called from `main()` at L179 inside `--launchd`/`run_all` branch with try/except warning |
| `pyproject.toml` | `sb-digest` entry point registered | VERIFIED | `sb-digest = "engine.digest:digest_main"` present |
| `tests/test_search.py` | 5 new test classes (SRCH-01/02) | VERIFIED | `TestSemanticSearch`, `TestSemanticFallback`, `TestHybridSearch`, `TestKeywordFlag`, `TestHybridFallback` all present |
| `tests/test_intelligence.py` | 3 new test classes (SRCH-03/04) | VERIFIED | `TestRecapEntity`, `TestRecapEntityEmpty`, `TestRecapEntityPIIRouting` present; `seeded_db` fixture seeds alice PII notes |
| `tests/test_digest.py` | 4 test classes (DIAG-01/02/04) | VERIFIED | `TestDigestWrite`, `TestDigestIdempotent`, `TestDigestSections`, `TestDigestPIIRouting` — all substantive with real assertions |
| `tests/test_read.py` | 2 test classes (DIAG-03) | VERIFIED (with warning) | `TestDigestFlag`, `TestDigestFlagEmpty` present; tests pass but were never upgraded from Wave 0 stubs — see anti-patterns |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `engine/search.py main()` | `search_hybrid()` | default mode (no flags) | WIRED | L229: `results = search_hybrid(conn, args.query, limit=args.limit)` |
| `engine/search.py main()` | `search_semantic()` | `--semantic` flag | WIRED | L225: `if args.semantic: results = search_semantic(...)` |
| `search_hybrid()` | `_rrf_merge()` | RRF fusion of bm25 + vec_results | WIRED | L204: `return _rrf_merge(bm25, vec_results, k=60, limit=limit)` |
| `search_semantic()` | `note_embeddings` table | `vec_distance_cosine()` query | WIRED | L152–167: SQL uses `vec_distance_cosine(ne.embedding, ?)` |
| `recap_main()` | `recap_entity()` | explicit context arg | WIRED | L416: `if args.context: recap_entity(args.context, conn)` |
| `recap_entity()` | `_router.get_adapter()` | per-note sensitivity routing | WIRED | L374: `_router.get_adapter("pii", CONFIG_PATH)`; L386: `_router.get_adapter("public", CONFIG_PATH)` |
| `recap_entity()` | `search_hybrid()` | semantic+FTS note discovery | WIRED | L301–304: lazy import of `search_hybrid`, called with `limit=20` |
| `engine/digest.py generate_digest()` | `.meta/digests/` | `BRAIN_ROOT / ".meta" / "digests"` | WIRED | `digest_main()` L124: `digests_dir = BRAIN_ROOT / ".meta" / "digests"` |
| `engine/digest.py generate_digest()` | `_router.get_adapter()` | PII routing for Key Themes | WIRED | L90: `_router.get_adapter("pii", CONFIG_PATH)`; L96: `_router.get_adapter("public", CONFIG_PATH)` |
| `engine/read.py main()` | `_resolve_digest()` | `--digest` flag path resolution | WIRED | L97: `digest_path = _resolve_digest(digests_dir, args.digest)` |
| `scripts/install_native.py` | `com.secondbrain.digest` plist | `plistlib.dump()` with `StartCalendarInterval` | WIRED | L98–103: `StartCalendarInterval: {"Weekday": 1, "Hour": 8, "Minute": 0}` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SRCH-01 | 16-01, 16-02 | User can run `sb-search --semantic` for vector-enhanced search | SATISFIED | `search_semantic()` implemented; `--semantic` flag in `main()`; `TestSemanticSearch` exists |
| SRCH-02 | 16-01, 16-02 | Hybrid search merges BM25 and vector results via RRF | SATISFIED | `_rrf_merge()` + `search_hybrid()` implemented; default `main()` uses hybrid; `TestHybridSearch`, `TestKeywordFlag`, `TestHybridFallback` exist |
| SRCH-03 | 16-01, 16-03 | User can run `sb-recap <name>` for cross-context synthesis | SATISFIED | `recap_entity()` implemented; `recap_main()` routes to it; `TestRecapEntity`, `TestRecapEntityEmpty` exist |
| SRCH-04 | 16-01, 16-03 | Cross-context synthesis routes PII notes through Ollama only | SATISFIED | `recap_entity()` splits by `sensitivity == "pii"` and calls `_router.get_adapter("pii", ...)` for PII rows; `TestRecapEntityPIIRouting` confirms routing |
| DIAG-01 | 16-01, 16-04 | Weekly digest generated automatically and saved to `.meta/digests/` | SATISFIED | `generate_digest()` writes `YYYY-WNN.md`; `digest_main()` uses `BRAIN_ROOT / ".meta" / "digests"`; launchd plist fires Monday 08:00 |
| DIAG-02 | 16-01, 16-04 | Digest includes: notes captured this week, key themes, open actions, stale items | SATISFIED | `_render_digest_body()` produces exactly four sections; `TestDigestSections` asserts all four headers present |
| DIAG-03 | 16-01, 16-04 | User can read latest digest via `sb-read --digest latest` | SATISFIED | `_resolve_digest()` + `--digest` flag in `read.py`; `sys.exit(0)` after printing; `TestDigestFlag` and `TestDigestFlagEmpty` pass |
| DIAG-04 | 16-01, 16-04 | Digest generation routes PII note summaries through Ollama | SATISFIED | `generate_digest()` splits by `sensitivity == "pii"` before calling `_router.get_adapter()`; `TestDigestPIIRouting` asserts `"pii"` call |

**All 8 requirements: SATISFIED. No orphaned requirements.**

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_read.py` | 154–171 | `TestDigestFlag` and `TestDigestFlagEmpty` use `pytest.raises(SystemExit)` — Wave 0 RED stubs never upgraded | Warning | Tests pass for the wrong reason: `sys.exit(0)` in the implementation satisfies `pytest.raises(SystemExit)`, but no assertion on printed content is made. DIAG-03 behavior is correct in production code; test coverage is weaker than intended. |
| `tests/test_search.py` | 56–67 | `TestSemanticFallback` patches `search_semantic` to raise then calls it again — the test body logic is confused (patch context exits before the real call) | Warning | The test happens to pass because the bare `search_semantic(seeded_db, "test query")` call returns `[]` (no embeddings match) and the "sb-reindex" string check has an `or len(results) >= 0` fallback that is always true. Coverage of the >50-missing-embeddings warning path is incomplete. |
| `.planning/phases/16-semantic-search-and-digest/16-VALIDATION.md` | 2–8 | `nyquist_compliant: false`, `wave_0_complete: false`, all tasks still `pending` | Info | VALIDATION.md was never updated after implementation. Not a code defect, but the phase tracking artifact is stale. |

---

### Human Verification Required

#### 1. launchd Weekly Digest Trigger

**Test:** Run `launchctl list | grep secondbrain.digest` after running `python scripts/install_native.py --launchd`. Then either wait for Monday 08:00 or run `launchctl start com.secondbrain.digest` immediately.
**Expected:** A digest file appears in `~/SecondBrain/.meta/digests/` with the current week's filename (`YYYY-WNN.md`) containing all four sections.
**Why human:** Requires the `sb-digest` binary to be installed via `uv tool install .`, a real brain directory at `~/SecondBrain`, and either a live Ollama instance or a patched adapter. Cannot be verified by static analysis.

---

### Gaps Summary

No gaps. All four success criteria are achieved by substantive, wired implementations. The two test quality warnings (TestDigestFlag and TestSemanticFallback) do not block the phase goal — the production behaviors they cover are correctly implemented and verified by other means.

---

_Verified: 2026-03-15_
_Verifier: Claude (gsd-verifier)_
