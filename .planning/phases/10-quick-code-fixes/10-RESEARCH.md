# Phase 10: Quick Code Fixes - Research

**Researched:** 2026-03-15
**Domain:** Python docstring correctness; pathlib path canonicalization
**Confidence:** HIGH

## Summary

Phase 10 is pure tech-debt closure with two isolated, surgical changes identified in the v1.5 audit. No new requirements, no new dependencies.

**Fix 1 — Stale docstring in `engine/ai.py:126`:** The `update_memory()` docstring says "Always uses ClaudeAdapter regardless of sensitivity". That was the original design; Phase 8 changed implementation to route through `_router.get_adapter("public", config_path)` instead. The docstring is now factually wrong. The fix is a one-line docstring edit.

**Fix 2 — Missing `.resolve()` in `forget.py:forget_person()`:** The `brain_root` parameter is passed in as a raw `Path`. On macOS, `tmp_path` (and therefore real `~/SecondBrain` under some conditions) is a symlink (`/var/folders/...` → `/private/var/folders/...`). Every other module that stores or compares paths uses `.resolve()` to canonicalize. `forget_person()` constructs `person_path = str(brain_root / "people" / f"{slug}.md")` without resolving first. If the caller's `brain_root` is a symlink path but the DB row was written with a resolved path (as `capture.py` does via Phase 7 fix), the `DELETE FROM notes WHERE path IN (...)` will match zero rows — a silent GDPR failure. Adding `brain_root = brain_root.resolve()` as the first line of `forget_person()` closes this risk.

**Primary recommendation:** Apply both fixes atomically in a single plan (10-00-PLAN.md). No new tests needed — existing `test_forget_removes_row_stored_by_capture` already exercises the path-consistency contract; verify it stays green.

## Standard Stack

No new libraries. Both fixes are pure Python stdlib changes.

| Tool | Version | Purpose |
|------|---------|---------|
| `pathlib.Path.resolve()` | stdlib | Canonicalize path, follow symlinks |
| Python docstring | stdlib | Inline documentation |

## Architecture Patterns

### Fix 1: Docstring correction

**Current (stale):**
```python
def update_memory(note_type: str, summary: str, config_path: Path) -> None:
    """Update Claude memory with new context from a captured note (CAP-06).

    Always uses ClaudeAdapter regardless of sensitivity — summary is safe
    (no PII, just type + controlled summary).
    ...
    """
```

**Correct (post-Phase-8):**
```python
def update_memory(note_type: str, summary: str, config_path: Path) -> None:
    """Update Claude memory with new context from a captured note (CAP-06).

    Routes through ModelRouter with sensitivity='public' — config drives
    adapter selection (AI-05). Summary must not contain PII.
    ...
    """
```

### Fix 2: `.resolve()` at function entry

**Pattern used throughout the codebase (Phase 7 precedent):**
```python
# engine/capture.py, engine/rag.py — established pattern
brain_root = brain_root.resolve()
```

**Apply same pattern to forget_person():**
```python
def forget_person(slug: str, brain_root: Path, conn: sqlite3.Connection) -> dict:
    """..."""
    brain_root = brain_root.resolve()  # canonicalize — symlink-safe (Phase 7 pattern)
    import frontmatter
    ...
```

Place `brain_root = brain_root.resolve()` as the first executable line, before the deferred `import frontmatter`. This ensures all path constructions downstream (`person_file`, `meetings_dir`, `person_path`, `sole_ref_paths`, `brain_root.rglob(...)`) are canonical.

### Anti-Patterns to Avoid

- **Resolving only some paths:** Must resolve `brain_root` once at entry, not selectively on each use — partial resolution causes inconsistency.
- **Using `.absolute()` instead of `.resolve()`:** `.absolute()` does not follow symlinks. Phase 7 decision record is explicit: "Use `.resolve()` not `.absolute()`."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Symlink-safe canonical path | Custom symlink walker | `Path.resolve()` |

## Common Pitfalls

### Pitfall 1: `.absolute()` vs `.resolve()`
**What goes wrong:** Using `.absolute()` leaves macOS `/var/` → `/private/var/` symlink unresolved, causing path mismatch between DB rows (written with `.resolve()`) and forget operations.
**How to avoid:** Always `.resolve()`. This is a documented project decision from Phase 7.

### Pitfall 2: Resolving after path construction
**What goes wrong:** Applying `.resolve()` to `brain_root / "people" / slug` instead of `brain_root` itself — produces the same resolved leaf path but misses the `brain_root.rglob()` call which uses the unresolved root.
**How to avoid:** Resolve `brain_root` at the top of the function, before any path construction.

### Pitfall 3: Docstring drift from implementation
**What goes wrong:** Phase 8 changed routing logic but didn't update the docstring. Future readers trust the docstring and misunderstand the GDPR/routing contract.
**How to avoid:** When changing routing logic, always update the paired docstring in the same commit.

## Code Examples

### Existing passing test that validates the path contract (HIGH confidence)
```python
# tests/test_forget.py — test_forget_removes_row_stored_by_capture
brain_root = tmp_path.resolve() / "brain"
# ...
write_note_atomic(target, post, conn)   # capture stores resolved path
forget_person("carol-danvers", brain_root, conn)  # must delete that row
row = conn.execute("SELECT 1 FROM notes WHERE title = ?", ("Carol Danvers",)).fetchone()
assert row is None
```
This test passes today because `brain_root` is already resolved at the call site (`tmp_path.resolve()`). After the fix, `forget_person()` itself guarantees resolution internally — the test remains a valid regression guard.

### `.resolve()` precedent in codebase
From Phase 7 decision: "Tests use `tmp_path.resolve()` as `brain_root` — canonical macOS path contract."
The fix makes the function self-defending rather than relying on every call site to pre-resolve.

## State of the Art

| Old Approach | Current Approach | When Changed |
|--------------|------------------|--------------|
| `forget_person` trusts caller to resolve | `forget_person` resolves internally | Phase 10 (this phase) |
| `update_memory` docstring says ClaudeAdapter direct | Docstring reflects ModelRouter routing | Phase 10 (this phase) |

## Open Questions

None. Both fixes are unambiguous from the audit findings and existing codebase evidence.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via uv run --no-project --with pytest) |
| Config file | none (standard discovery) |
| Quick run command | `uv run --no-project --with pytest --with python-frontmatter tests/test_forget.py -x -q` |
| Full suite command | `uv run --no-project --with pytest --with python-frontmatter tests/ -x -q` |

### Phase Requirements → Test Map

Tech debt phase — no new requirement IDs. Existing tests cover both fixes:

| Behavior | Test | Type | Automated Command | File Exists? |
|----------|------|------|-------------------|-------------|
| forget_person deletes DB row by canonical path | `test_forget_removes_row_stored_by_capture` | integration | `uv run --no-project --with pytest --with python-frontmatter tests/test_forget.py::test_forget_removes_row_stored_by_capture -x` | Yes |
| All forget tests still pass after .resolve() added | full test_forget.py | unit | `uv run --no-project --with pytest --with python-frontmatter tests/test_forget.py -x -q` | Yes |
| update_memory docstring review (no automated test) | manual read | manual-only | n/a | n/a |

### Sampling Rate
- **Per task commit:** `uv run --no-project --with pytest --with python-frontmatter tests/test_forget.py -x -q`
- **Per wave merge:** `uv run --no-project --with pytest --with python-frontmatter tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

None — existing test infrastructure covers all phase requirements. No new test files needed.

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `engine/ai.py` lines 121–144 — confirmed stale docstring vs. implementation
- Direct code inspection: `engine/forget.py` lines 24–54 — confirmed missing `.resolve()` at entry
- Direct code inspection: `engine/paths.py` — `BRAIN_ROOT` is `Path.home() / "SecondBrain"` (not pre-resolved)
- Direct code inspection: `tests/test_forget.py` lines 219–247 — existing path-consistency regression test

### Secondary (MEDIUM confidence)
- STATE.md Phase 7 decision record: "Use `.resolve()` not `.absolute()` — macOS tmp_path is /var/... symlink to /private/var/...; only `.resolve()` gives canonical form"
- STATE.md Phase 8 decision record: "ClaudeAdapter import removed from engine/ai.py — all adapter calls now go through `_router.get_adapter` module ref"

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; pure stdlib
- Architecture: HIGH — fix pattern identical to Phase 7, documented precedent
- Pitfalls: HIGH — root cause verified by direct code inspection

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable codebase, no moving parts)
