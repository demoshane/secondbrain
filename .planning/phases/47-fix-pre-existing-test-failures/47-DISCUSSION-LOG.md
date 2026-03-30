# Phase 47: Fix Pre-existing Test Failures — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30

---

## Area 1: 308 fix approach (test_delete_endpoint_404)

**Question:** The test passes an absolute path as a URL segment, producing `//private/tmp/...` — Flask's URL normalisation returns a 308 redirect before the route handler runs. How should the fix be scoped?

**Options presented:**
- A — Fix test URL only (strip leading `/`)
- B — Fix route to add `p.exists()` → 404, AND fix test URL
- C — You decide

**User selected:** B

**Rationale captured:** Both the double-slash trigger (test URL) and the missing existence check (route) are real bugs. The route should always 404 on a ghost path — not silently succeed.

---

## Area 2: FK path mismatch fix level (3 xfailed tests)

**Question:** macOS `/tmp` → `/private/tmp` symlink causes FK constraint failures when relationship inserts use a different path representation than what was stored in `notes.path`. Fix at fixture level, production pipeline, or both?

**Options presented:**
- A — Fixture-level only
- B — Production code only
- C — Both

**User selected:** C

**Rationale captured:** Belt + suspenders. Fixture fix guarantees test isolation and removes macOS symlink ambiguity at the test boundary. Production pipeline fix ensures real-world captures (not just tests) don't silently drop relationships due to path inconsistency.

---

## Area 3: xfail markers

**Question:** After fixing, remove `@pytest.mark.xfail` markers or keep/update them?

**Options presented:**
- A — Remove all xfail markers after fix
- B — Keep markers, update reason strings
- C — Remove only the ones fully fixed

**User selected:** Claude chooses best approach → **A (remove entirely)**

**Rationale:** Markers document acknowledged debt. Once the debt is paid they are misleading. A failing test must be a real failure signal, not a silenced one. Removing alongside the fix (same commit) keeps the history clean.
