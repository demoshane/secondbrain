# Architecture Audit Findings

**Audit date:** 2026-03-27
**Auditor:** 39-02 executor agent
**Scope:** Backend module structure, coupling, dead code, dual-write consistency, api.py structure
**Total findings:** 13 (Critical: 0, High: 2, Medium: 5, Low: 6)

---

## Summary

Architecture is generally sound. Phase 32 hardening landed the key structural improvements (relative paths, FK cascade on junction tables, junction table dual-write). No circular imports found. Dead code is minimal and mostly confirmed-live via pyproject.toml or lazy-import callers. Main concerns: duplicate import in api.py (cosmetic but signals residue), three late BRAIN_ROOT re-imports inside api.py functions, and api.py at 1754 lines without blueprint partitioning. Dual-write paths are consistent across all write surfaces.

---

## ARCH-01: Duplicate module-level import in api.py

- **Severity:** Low
- **File:** `engine/api.py:24-25`
- **Description:** Two back-to-back imports: `from engine.paths import BRAIN_ROOT` (line 24) then `from engine.paths import BRAIN_ROOT, store_path` (line 25). Line 24 is dead — it is immediately shadowed by line 25.
- **Root cause:** Copy-paste when `store_path` was added to the import. Line 24 was not removed.
- **Recommended fix:** Delete line 24. Single import: `from engine.paths import BRAIN_ROOT, store_path`
- **Blast radius:** Zero — no behavior change. Pure cosmetic.
- **Evidence:** Direct read of api.py lines 24-25.

---

## ARCH-02: Late BRAIN_ROOT re-imports inside api.py function bodies (3 locations)

- **Severity:** Medium
- **File:** `engine/api.py:1194`, `engine/api.py:1584`, `engine/api.py:1640`
- **Description:** Three functions independently re-import `from engine.paths import BRAIN_ROOT` inside their function body, despite BRAIN_ROOT already being imported at module level (line 25). These are redundant in production.
- **Root cause:** These were originally added as workarounds for test isolation — when tests monkeypatch `engine.paths.BRAIN_ROOT`, a module-level import already binds the name and is not affected by monkeypatching. A late in-function import re-reads from the module, picking up the patched value. However, production code has no monkeypatching, so these are unnecessary overhead that also signals unclear test design.
- **Recommended fix:** Per RESEARCH.md Pitfall 5 — verify test isolation before removing. If tests for these endpoints monkeypatch `engine.paths.BRAIN_ROOT` specifically, the late imports must stay OR the tests need to be updated to use the module-level import correctly. If tests are correct without them, remove all three.
- **Blast radius:** Test failures if test fixtures rely on late import behavior. Verify with `uv run pytest tests/ -q` after removing.
- **Evidence:** `grep -n "from engine.paths import BRAIN_ROOT" engine/api.py` returns lines 24, 25, 1194, 1584, 1640.

---

## ARCH-03: Dual-write consistency — tags (VERIFIED CONSISTENT)

- **Severity:** N/A (informational)
- **File:** `engine/capture.py:226-238`, `engine/capture.py:325-335`, `engine/api.py:901-904`, `engine/reindex.py:283-287`
- **Description:** Tags are written to both `notes.tags` (JSON column) and `note_tags` junction table. All four write surfaces maintain dual-write:
  1. `write_note_atomic()` — capture.py:226-238 — dual-writes both in same transaction
  2. `update_note()` — capture.py:325-335 — dual-writes both in same transaction
  3. Direct note people update in api.py edit endpoint — lines 901-904 — handles note_people correctly
  4. `reindex_brain()` — reindex.py:283-287 — maintains note_people during reindex
- **Read path:** Search uses `note_tags` junction table via `_apply_filters()` in search.py. The `GET /tags` endpoint in api.py uses `note_tags` first with fallback to JSON column if empty.
- **Root cause:** Intentional Phase 32 decision: keep JSON columns for backward compat while reads use junction tables.
- **Recommended fix:** No action needed. Dual-write is consistent. Future: drop JSON columns once all installs are migrated (not in this phase).
- **Blast radius:** N/A

---

## ARCH-04: Dual-write consistency — people (VERIFIED CONSISTENT)

- **Severity:** N/A (informational)
- **File:** `engine/capture.py:239-249`, `engine/capture.py:351-358`, `engine/reindex.py:283-287`
- **Description:** People are written to both `notes.people` (JSON column) and `note_people` junction table. All write surfaces maintain dual-write. `update_note()` re-extracts entities and refreshes `note_people` in the same transaction.
- **Root cause:** Same intentional Phase 32 decision as tags.
- **Recommended fix:** No action needed. Consistent.
- **Blast radius:** N/A

---

## ARCH-05: FK CASCADE gap — action_items, note_embeddings, audit_log, relationships

- **Severity:** Medium
- **File:** `engine/db.py:77-83` (action_items SCHEMA_SQL), `engine/db.py:68-75` (note_embeddings SCHEMA_SQL)
- **Description:** `note_tags` and `note_people` have `ON DELETE CASCADE` FK constraints. However, `action_items`, `note_embeddings`, `audit_log`, and `relationships` do NOT have FK CASCADE — they rely on application-level cascade in `forget.py`. This is a GDPR correctness gap: if `DELETE FROM notes` is called outside the `forget_person()` path (e.g., via direct SQL, sb-reindex cleanup, delete endpoint), child rows in these tables become orphans.
- **Root cause:** Phase 32 added FK CASCADE only to the new junction tables. The original tables were not migrated.
- **Recommended fix:** Add `ON DELETE CASCADE` FK to `note_embeddings(note_path)`, `action_items(note_path)`. For `audit_log` and `relationships`: GDPR requirement is that audit log entries survive deletion for compliance trail — do NOT cascade here. `relationships` should cascade (no orphan links needed). The `forget_person()` explicit deletes provide belt-and-suspenders for GDPR erasure, which is correct.
- **Blast radius:** Medium — adding FK CASCADE to `note_embeddings` and `action_items` requires schema migration. If `PRAGMA foreign_keys = ON` is not active at connection time, cascade won't fire — verify `get_connection()` always enables it. Currently: yes, `get_connection()` runs `PRAGMA foreign_keys = ON` at line 104.
- **Evidence:** `grep -n "ON DELETE CASCADE" engine/db.py` returns only note_tags and note_people entries.

---

## ARCH-06: api.py at 1754 lines — no Blueprint partitioning

- **Severity:** Medium
- **File:** `engine/api.py` (all 1754 lines)
- **Description:** All 55 Flask route handlers live in a single file with no blueprint structure. Natural domain boundaries are visible:
  - **Notes** (lines ~163–991): CRUD for notes, search, meta, impact
  - **People/Meetings/Projects** (lines ~317–636): entity management
  - **Files/Attachments** (lines ~1106–1268): file operations
  - **Actions** (lines ~733–1420): action item management
  - **Intelligence/Inbox** (lines ~1422–1571): recap, connections, inbox
  - **Relationships/Smart-capture/Brain-health** (lines ~1553–1754): misc
- **Root cause:** Organic growth across 38 phases. Flask blueprints were not introduced.
- **Recommended fix:** Register Flask Blueprints per domain. Reduces file size per unit to ~150-300 lines each. This is a refactor, not a critical fix — no behavior change, no DB change.
- **Blast radius:** Low-medium if done carefully (pure internal restructuring, same endpoints, same URL paths). Import paths change. Test imports need updating.
- **User confirm required:** Yes — this is a structural refactor. Defer to a dedicated plan if the team wants to proceed.

---

## ARCH-07: consolidate.py lazy imports — still justified

- **Severity:** Low (informational)
- **File:** `engine/consolidate.py:99-108`
- **Description:** `consolidate_main()` imports `engine.db`, `engine.brain_health` lazily inside the function body. The module itself has NO top-level engine imports (only stdlib: `datetime`, `json`, `logging`). The lazy imports are not about circular imports — there is no circular dependency here. They are about deferring import cost for a CLI entry point that rarely runs.
- **Root cause:** Defensive design from Phase 35. Comment says "avoids circular import" but that's not accurate — there is no circular import. The real benefit is load-time speed for the `sb-consolidate` CLI.
- **Recommended fix:** The lazy imports cause no correctness issues. Add a clarifying comment that the reason is load-time deferral, not circular import prevention. Low priority.
- **Blast radius:** Zero.
- **Evidence:** `grep "^import\|^from" engine/consolidate.py` returns only stdlib imports.

---

## ARCH-08: D-01 — engine/rag.py — LIVE, not dead

- **Severity:** Low (informational — pre-identified as candidate, confirmed live)
- **File:** `engine/rag.py` (51 lines)
- **Description:** `rag.py` is imported lazily by `engine/ai.py` at line 91: `from engine.rag import augment_prompt`. `ai.py` is called by `capture.py` CLI path for follow-up questions and memory updates. `ai.py` also has a registered CLI entry point (`sb-update-memory = "engine.ai:main"`). The RAG path is reachable in production via `sb-capture` CLI.
- **Root cause:** Research pre-identified this as "potentially stale" — confirmed still live.
- **Recommended fix:** No action. Module is live.
- **Blast radius:** N/A

---

## ARCH-09: D-02 — engine/templates.py — DEAD (not imported by any engine code)

- **Severity:** High
- **File:** `engine/templates.py` (41 lines)
- **Description:** `templates.py` is imported by NO engine module. Only one reference exists in the entire codebase: `tests/test_capture.py:84` — `from engine.templates import load_template, render_template`. The templates module is NOT imported by `capture.py` or any other production code path. The actual note writing in `capture.py` does not use template rendering — it writes frontmatter directly via python-frontmatter.
- **Root cause:** The templates system was built in an early phase but capture was later implemented differently. The module was left in place but is unreachable from any production path. The test file tests a dead module.
- **Recommended fix:** Delete `engine/templates.py`. Update `tests/test_capture.py` to remove the dead import test (lines 83-88). The templates themselves (`.meta/templates/*.md`) may still be used by CLI capture for body scaffolding — check `capture.py` main() to see if templates are loaded there. If templates are used in CLI, they need a live import path.
- **Blast radius:** High if templates are actually used somewhere not found by static analysis. Dynamic/runtime import possible but not visible here. Before deleting, search for `load_template` and `render_template` in ALL Python files.
- **Evidence:** `grep -rn "from engine.templates import\|import engine.templates" engine/` → no results. `grep -rn "from engine.templates" tests/` → `tests/test_capture.py:84`.

---

## ARCH-10: D-03 — engine/ai.py — LIVE (CLI entry point)

- **Severity:** Low (informational)
- **File:** `engine/ai.py` (180 lines)
- **Description:** `ai.py` is confirmed live. `ask_followup_questions()` is called lazily from `capture.py:406` and `update_memory()` from `capture.py:441`. `sb-update-memory` is registered as CLI entry point in pyproject.toml. Module is also tested in `tests/test_ai.py`.
- **Root cause:** Pre-identified as "partial use" — confirmed fully live.
- **Recommended fix:** No action.
- **Blast radius:** N/A

---

## ARCH-11: D-04 — engine/ratelimit.py — LIVE (imported by watcher.py)

- **Severity:** Low (informational — pre-identified as candidate, confirmed live)
- **File:** `engine/ratelimit.py` (30 lines)
- **Description:** `ratelimit.py` is imported at module level by `engine/watcher.py:11` — `from engine.ratelimit import RateLimiter`. `watcher.py` is the active file-watch daemon, a registered CLI entry point (`sb-watch = "engine.watcher:main"`). The RateLimiter is used in production by the watcher to prevent runaway API calls.
- **Root cause:** Research pre-identified this as "not found imported by engine modules" — that grep was incorrect. `watcher.py` is an engine module and does import it.
- **Recommended fix:** No action. Module is live.
- **Blast radius:** N/A

---

## ARCH-12: D-05 — Duplicate import at api.py line 24 (same as ARCH-01)

(See ARCH-01 — duplicate finding consolidated there.)

---

## ARCH-13: D-06 — Late BRAIN_ROOT imports in api.py function bodies (same as ARCH-02)

(See ARCH-02 — duplicate finding consolidated there.)

---

## ARCH-14: D-07 — NoteEditor.tsx — NOT dead (imported by NoteViewer.tsx)

- **Severity:** Low (informational — pre-identified as dead, confirmed live)
- **File:** `frontend/src/components/NoteEditor.tsx`
- **Description:** `NoteEditor.tsx` IS imported and used. `NoteViewer.tsx:8` — `import { NoteEditor } from './NoteEditor'` — and rendered at `NoteViewer.tsx:113`. Not dead.
- **Root cause:** Research pre-identified this incorrectly. The component is not directly in App.tsx but is used as a sub-component of NoteViewer.
- **Recommended fix:** No action.
- **Blast radius:** N/A

---

## ARCH-15: A-02 — FK CASCADE is NOT on action_items or note_embeddings (same as ARCH-05)

(See ARCH-05 — this is the canonical finding.)

---

## Summary Table

| ID | Severity | Finding | Action |
|----|----------|---------|--------|
| ARCH-01 | Low | Duplicate import line 24 in api.py | Delete line 24 |
| ARCH-02 | Medium | 3 late BRAIN_ROOT re-imports inside api.py functions | Verify tests then remove |
| ARCH-03 | N/A | Dual-write tags: CONSISTENT | No action |
| ARCH-04 | N/A | Dual-write people: CONSISTENT | No action |
| ARCH-05 | Medium | FK CASCADE missing on action_items, note_embeddings | Add CASCADE migration |
| ARCH-06 | Medium | api.py 1754 lines, no blueprints | Refactor (user confirm) |
| ARCH-07 | Low | consolidate.py lazy import comment inaccurate | Update comment |
| ARCH-08 | Low | rag.py confirmed live | No action |
| ARCH-09 | High | templates.py dead — zero engine imports | Investigate then delete |
| ARCH-10 | Low | ai.py confirmed live | No action |
| ARCH-11 | Low | ratelimit.py confirmed live | No action |
| ARCH-14 | Low | NoteEditor.tsx confirmed live (NoteViewer uses it) | No action |

**Actionable findings requiring work:** ARCH-01 (Low), ARCH-02 (Medium), ARCH-05 (Medium), ARCH-06 (Medium/defer), ARCH-09 (High)
