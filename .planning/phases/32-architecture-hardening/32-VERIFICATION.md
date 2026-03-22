---
phase: 32-architecture-hardening
verified: 2026-03-22T00:00:00Z
status: gaps_found
score: 15/16 requirements verified
re_verification: false
gaps:
  - truth: "Entity extraction logs failures via logging.warning(), not bare except:pass"
    status: failed
    reason: "check_connections() in intelligence.py still uses `except Exception: pass` at line 390 — swallows connection errors silently. ARCH-09 specified this as a target for replacement with logging.warning(). Also capture.py lines 555/567 use bare except:pass for best-effort background tasks, but those are intentional defensive guards, not logging gaps."
    artifacts:
      - path: "engine/intelligence.py"
        issue: "check_connections() line 390: `except Exception: pass` swallows errors silently instead of logging.warning()"
    missing:
      - "Replace `except Exception: pass` in check_connections() with `logging.warning('check_connections failed: %s', type(e).__name__, exc_info=True)` or similar"
human_verification:
  - test: "Verify archived items not visible in GUI action items page"
    expected: "Items completed >90 days ago do not appear in the GUI action items list"
    why_human: "Requires populated test data with old timestamps and GUI inspection"
  - test: "Verify 50 MB upload cap triggers 413 in browser"
    expected: "Uploading a file >50 MB shows an error, not a silent hang"
    why_human: "Requires actual large file upload via GUI or curl"
---

# Phase 32: Architecture Hardening — Verification Report

**Phase Goal:** Fix structural issues that will cause data loss or pain as the brain grows — relative path storage, FK cascade, connection leak safety, tags as indexed structure, action item lifecycle, security/consistency fixes
**Verified:** 2026-03-22
**Status:** gaps_found (1 gap)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | All new notes stored with relative paths in DB | VERIFIED | `store_path()` imported and used in capture.py lines 12, 198, 306, 493, 532 |
| 2 | Existing absolute paths migrated on init_schema() | VERIFIED | `migrate_paths_to_relative()` registered in init_schema() db.py line 428 |
| 3 | resolve_path/store_path helpers exist in paths.py | VERIFIED | engine/paths.py lines 31-73 — both functions implemented with correct edge case handling |
| 4 | PRAGMA foreign_keys=ON on every connection | VERIFIED | db.py line 103: `conn.execute("PRAGMA foreign_keys = ON")` |
| 5 | All api.py connections wrapped in try/finally | VERIFIED | 30 conn.close() calls, 32 finally: blocks in api.py — wiring confirmed |
| 6 | suppress_next_delete is thread-safe with per-path Events | VERIFIED | watcher.py lines 84-104: `_suppress_events: dict[str, threading.Event]` with `_suppress_lock` |
| 7 | File uploads larger than 50 MB return 413 | VERIFIED | api.py line 43: MAX_CONTENT_LENGTH, lines 47-49: 413 handler |
| 8 | _SlashNormMiddleware removed | VERIFIED | No `_SlashNorm` string found in api.py |
| 9 | note_tags and note_people junction tables with indexed tag/person columns | VERIFIED | db.py lines 218-302: both tables with FK CASCADE and indexes; init_schema lines 430-431 |
| 10 | capture_note and update_note dual-write to junction + JSON | VERIFIED | capture.py lines 226-249 (capture), 325-358 (update) |
| 11 | Tag filter queries use junction table not JSON parsing | VERIFIED | api.py lines 165-208: `note_tags` JOIN used for tag filtering |
| 12 | action_items_archive table + 90-day archival | VERIFIED | db.py lines 198-215, brain_health.py lines 116-151 |
| 13 | archive_old_action_items called from health report | VERIFIED | brain_health.py line 164, response includes `archived_action_items` key |
| 14 | audit_log index on (created_at, note_path) | VERIFIED | db.py line 435: `CREATE INDEX IF NOT EXISTS idx_audit_log_created_path` |
| 15 | move_file() validates src and dst within BRAIN_ROOT | VERIFIED | api.py line 846: `not src_p.is_relative_to(BRAIN_ROOT) or not dst_p.is_relative_to(BRAIN_ROOT)` |
| 16 | forget_person() DB-first: commits before file deletion | VERIFIED | forget.py line 130: `conn.commit()` before file deletion at lines 135-150 |
| 17 | forget_person() cleans people JSON in surviving notes + frontmatter | VERIFIED | forget.py lines 106-124 (DB), lines 153-176 (frontmatter on disk) |
| 18 | Entity extraction logs failures via logging.warning() | FAILED | check_connections() in intelligence.py line 390 still has bare `except Exception: pass` |
| 19 | search_semantic() uses logging.warning() not print() | VERIFIED | search.py lines 163-174: `logger.warning()` used for empty index and missing embeddings warnings |
| 20 | PERSON_TYPES constant in db.py, imported everywhere | VERIFIED | db.py line 10, imported in api.py line 23 and mcp_server.py line 17 |
| 21 | _escape_like() helper in db.py, applied to LIKE patterns | VERIFIED | db.py lines 13-15, imported in api.py line 23 |
| 22 | sb_person_context uses exact title match | VERIFIED | mcp_server.py line 306: `WHERE LOWER(title) = LOWER(?) LIMIT 1` |
| 23 | engine/people.py with list_people_with_metrics shared service | VERIFIED | engine/people.py lines 8-57, imported by api.py line 257 and mcp_server.py line 1257 |
| 24 | People matched by path AND exact title (ARCH-11 fix) | VERIFIED | people.py lines 25-33: `np.person = n.path OR LOWER(np.person) = LOWER(n.title)` |
| 25 | sb-reindex --entities merges people, not overwrites | VERIFIED | reindex.py lines 180-197: merge via `dict.fromkeys(frontmatter_people + extracted)` |
| 26 | update_note re-extracts entities and merges into people+entities | VERIFIED | capture.py lines 336-358 |
| 27 | sb-export includes archived action items | VERIFIED | export.py includes query `FROM action_items_archive` |

**Score:** 26/27 truths verified (1 gap)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/paths.py` | resolve_path() and store_path() helpers | VERIFIED | Both functions implemented, 74 lines |
| `engine/db.py` | migrate_paths_to_relative() in init_schema() | VERIFIED | Function at line 305, registered at line 428 |
| `engine/db.py` | PERSON_TYPES constant, _escape_like() helper | VERIFIED | Lines 10, 13-15 |
| `engine/db.py` | note_tags and note_people table DDL + migrations | VERIFIED | Lines 218-302 |
| `engine/db.py` | action_items_archive table DDL | VERIFIED | Lines 198-215 |
| `engine/capture.py` | store_path() used at DB write boundary | VERIFIED | Line 12 import, lines 198/306/493/532 usage |
| `engine/capture.py` | Dual-write to junction tables on capture and update | VERIFIED | Lines 226-249, 325-358 |
| `engine/api.py` | PRAGMA FK enforcement via get_connection() | VERIFIED | db.py line 103 |
| `engine/api.py` | try/finally wrapping, 50MB cap, no middleware | VERIFIED | Lines 43, 47-49; 30 finally blocks |
| `engine/api.py` | move_file() path traversal guard | VERIFIED | Line 846 |
| `engine/watcher.py` | Thread-safe suppress_next_delete with dict[str, Event] | VERIFIED | Lines 84-104 |
| `engine/brain_health.py` | archive_old_action_items() + archive count in report | VERIFIED | Lines 116-181 |
| `engine/forget.py` | DB-first cascade, people field cleanup | VERIFIED | Lines 66-188 |
| `engine/people.py` | list_people_with_metrics() shared service | VERIFIED | Entire file, 58 lines |
| `tests/test_paths.py` | Path helper tests | VERIFIED | File exists |
| `tests/test_people.py` | People service tests | VERIFIED | File exists |
| `tests/test_reindex.py` | Reindex entity merge tests | VERIFIED | File exists |
| `tests/test_brain_health.py` | Archive function tests | VERIFIED | File exists |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| engine/db.py | engine/paths.py | `from engine.paths import BRAIN_ROOT` | VERIFIED | Dynamic import in migrate_paths_to_relative() |
| engine/capture.py | engine/paths.py | `from engine.paths import store_path as _store_path` | VERIFIED | Line 12 |
| engine/api.py | engine/db.py | `from engine.db import PERSON_TYPES, _escape_like` | VERIFIED | Line 23 |
| engine/api.py | engine/people.py | `from engine.people import list_people_with_metrics` | VERIFIED | Line 257 |
| engine/mcp_server.py | engine/people.py | `from engine.people import list_people_with_metrics` | VERIFIED | Line 1257 |
| engine/mcp_server.py | engine/db.py | `from engine.db import PERSON_TYPES, _escape_like` | VERIFIED | Line 17 |
| engine/forget.py | notes table | conn.commit() before file deletion | VERIFIED | Line 130 before line 135 |
| engine/brain_health.py | action_items_archive | INSERT INTO archive, DELETE FROM action_items | VERIFIED | Lines 137-147 |

---

## Requirements Coverage

Note: ARCH-01 through ARCH-16 are **not defined in REQUIREMENTS.md** — they are v4.0 requirements defined only in `32-RESEARCH.md` and `32-CONTEXT.md`. REQUIREMENTS.md covers v3.0 only. This is expected for this phase (v4.0 work in progress) but the requirements should be added to REQUIREMENTS.md for traceability.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| ARCH-01 | 32-01 | Relative path storage; resolve_path/store_path; migration | SATISFIED | paths.py, db.py, capture.py all verified |
| ARCH-02 | 32-02 | PRAGMA foreign_keys=ON on every connection | SATISFIED | db.py get_connection() |
| ARCH-03 | 32-02 | try/finally + thread-safe suppress_next_delete | SATISFIED | api.py 30 finally blocks; watcher.py Event dict |
| ARCH-04 | 32-02 | 50MB upload cap; _SlashNormMiddleware removed | SATISFIED | api.py MAX_CONTENT_LENGTH + 413 handler |
| ARCH-05 | 32-03 | note_tags junction table; indexed; tag queries use it | SATISFIED | db.py + api.py + capture.py |
| ARCH-06 | 32-04 | action_items_archive; 90-day archival; audit_log index | SATISFIED | db.py + brain_health.py |
| ARCH-07 | 32-05 | move_file() path traversal guard; note_meta cleanup | SATISFIED | api.py line 846 |
| ARCH-08 | 32-05 | forget_person DB-first; people JSON cleaned | SATISFIED | forget.py |
| ARCH-09 | 32-05 | Logging: replace bare except:pass with logging.warning | BLOCKED | check_connections() in intelligence.py line 390 still bare except:pass |
| ARCH-10 | 32-06 | list_people_with_metrics in engine/people.py | SATISFIED | engine/people.py |
| ARCH-11 | 32-06 | Path+title matching for people lookup | SATISFIED | people.py OR query |
| ARCH-12 | 32-06 | reindex --entities merges people not overwrites | SATISFIED | reindex.py |
| ARCH-13 | 32-06 | update_note re-extracts entities and merges | SATISFIED | capture.py |
| ARCH-14 | 32-05 | _escape_like() applied to LIKE with user input | SATISFIED | db.py + api.py |
| ARCH-15 | 32-03 | note_people junction table; indexed; FK CASCADE | SATISFIED | db.py |
| ARCH-16 | 32-05 | PERSON_TYPES constant replaces hardcoded strings | SATISFIED | db.py + api.py + mcp_server.py |

**Satisfied:** 15/16 (ARCH-09 partially satisfied — search.py logging done, intelligence.py check_connections missed)

**Orphaned requirements:** ARCH-01 through ARCH-16 are not in REQUIREMENTS.md. This is expected (v4.0 phase) but should be documented in REQUIREMENTS.md.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| engine/intelligence.py | 390 | `except Exception: pass` in check_connections() | Warning | Silently swallows connection errors — connection suggestions fail invisibly |
| engine/capture.py | 237, 248 | `except Exception: pass` for junction table writes | Info | Intentional: guards against old schemas without junction tables. Comment explains. |
| engine/capture.py | 555, 567 | `except Exception: pass` for background tasks | Info | Intentional: best-effort post-capture tasks (check_connections, action item extraction). Connection error after successful capture should not fail capture. |
| engine/intelligence.py | 383-386 | `print()` in check_connections() | Warning | CLI-only context (ok), but inconsistent with logging hygiene goal of ARCH-09 |
| engine/watcher.py | 212 | `print()` in sb-watch main() | Info | CLI daemon entry point — print() is appropriate here |

---

## Human Verification Required

### 1. Archived items hidden from GUI

**Test:** Open GUI action items page. Mark a test action item as done. Manually update its `done_at` in the DB to a date >90 days ago. Run `sb-health`. Reload the GUI action items page.
**Expected:** The archived item no longer appears in GUI; sb-health report shows `archived_action_items: 1`
**Why human:** Requires time-travel test data and GUI inspection

### 2. 50 MB upload cap via browser

**Test:** Attempt to upload a file >50 MB via the GUI file upload feature
**Expected:** Server returns 413 response; GUI shows an error message
**Why human:** Requires actual large file and browser network inspection

### 3. Relative path portability

**Test:** Run `sb-health` to confirm the DB has no absolute paths after startup migration. Check: `sqlite3 ~/SecondBrain/.meta/brain.db "SELECT COUNT(*) FROM notes WHERE path LIKE '/%'"`
**Expected:** Count = 0 (all paths relative)
**Why human:** Requires running on a live brain with pre-existing notes to confirm migration ran

---

## Gaps Summary

One gap blocks full ARCH-09 compliance: `check_connections()` in `engine/intelligence.py` (line 390) uses a bare `except Exception: pass` that was listed as a target in the ARCH-09 logging cleanup sweep. The function also contains `print()` calls (lines 383-386) which ARCH-09 targeted for replacement with `logging`.

This is a minor hygiene gap — the function is best-effort by design and failures don't affect correctness. However, the PLAN's done condition was "no bare except:pass or print() in engine code" and this specific location was called out in the spec.

All other 15 ARCH requirements are implemented and wired correctly. The architecture hardening goals — relative path portability, FK enforcement, connection safety, indexed tag/people lookups, action item lifecycle, and security fixes — are all delivered.

---

_Verified: 2026-03-22_
_Verifier: Claude (gsd-verifier)_
