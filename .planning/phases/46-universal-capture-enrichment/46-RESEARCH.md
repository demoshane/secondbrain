# Phase 46: Universal Capture Enrichment — Research

**Researched:** 2026-03-30
**Domain:** Python async threading, capture pipeline, person stub creation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — Stub Creation Scope:**
Two-layer gate in `capture_note()` before calling Pass 5:
1. Skip if `note_type in {"coding", "link", "files"}`
2. Skip if `entities["people"]` is empty after entity extraction

Both conditions checked before entering the background thread stub logic. Zero overhead when neither passes.

**D-02 — Threading Model:**
Person stub creation runs async in the existing `_run_intelligence_hooks` background daemon thread in `capture_note()`. The thread already handles `check_connections` and `extract_action_items`. Stub creation is a third task added to that same thread.

**D-03 — Response Surface:**
No changes to `sb_capture` or `sb_capture_batch` response shapes. Stub creation is transparent to callers.

**D-04 — Context Detection:**
Context detection audit descoped. No changes to `extract_entities()`, `_PERSON_CONTEXT_SIGNALS`, or extraction thresholds.

### Claude's Discretion

- Whether stub creation in the background thread reuses `p5_assemble` module directly or calls `capture_note()` recursively for each stub (existing `sb_capture_smart` pattern)
- Error handling within the thread — stub creation failures must not surface or crash the thread (same silent-catch pattern as existing hooks)
- Whether `_run_intelligence_hooks` is refactored into named sub-functions or kept as a single closure

### Deferred Ideas (OUT OF SCOPE)

- Context detection audit (`extract_entities()` interface, source_type signal enrichment)
- Response surface enrichment (`person_stubs_created` in `sb_capture` responses)
</user_constraints>

---

## Summary

This phase extends the existing background intelligence hook in `capture_note()` to call Pass 5 person stub creation — the same logic already running in `sb_capture_smart`. The change is a single addition to the `_run_intelligence_hooks` closure: a third try/except block that calls `resolve_entities()` then `capture_note()` for each new stub, gated by note type and entity presence.

The architecture is already proven. `sb_capture_smart` does exactly this in `mcp_server.py` (~line 922). The task is to replicate that pattern inside the background thread in `capture.py`, not invent anything new. The main discretion question is whether to call `p5_assemble.assemble()` directly or to inline the `resolve_entities()` call — the latter is simpler given that `capture_note()` is already available in scope.

**Primary recommendation:** Add a single guarded try/except block to `_run_intelligence_hooks` in `capture_note()`. Gate on `note_type not in {"coding", "link", "files"}` before spawning the thread (or inside it). Reuse the same `capture_note()` recursive call pattern from `sb_capture_smart`.

---

## Standard Stack

This phase uses no new libraries. All dependencies are already present.

### Core (already in codebase)
| Module | Purpose | Location |
|--------|---------|----------|
| `engine/capture.py` | Write path; contains `_run_intelligence_hooks` to extend | Primary target |
| `engine/passes/p5_assemble.py` | `assemble()` — resolves entities to stubs or existing people | Called from background thread |
| `engine/segmenter.py` | `resolve_entities()` — FTS5 + fuzzy lookup, returns `new_stubs` list | Called by p5_assemble |
| `engine/entities.py` | `extract_entities()` — already runs synchronously in `capture_note()` | Result already available |
| `threading` (stdlib) | Background daemon thread — already wired | Reuse as-is |

**No new packages. No installation required.**

---

## Architecture Patterns

### Existing `_run_intelligence_hooks` Structure (capture.py ~line 586)

```python
_target_str = str(target)
_body = body
_sensitivity = content_sensitivity
_brain_root = brain_root

def _run_intelligence_hooks():
    try:
        # Task 1: check_connections (fast, short-lived conn)
        ...
    except Exception:
        pass
    try:
        # Task 2: extract_action_items (slow AI call, fresh conn)
        ...
    except Exception:
        pass

threading.Thread(target=_run_intelligence_hooks, daemon=True).start()
```

### Pattern to Add (Task 3 — Person Stubs)

Gate before thread spawn:

```python
_note_type = note_type
_entities = entities          # already computed synchronously above
_skip_stubs = note_type in {"coding", "link", "files"} or not entities.get("people")
```

Inside `_run_intelligence_hooks`, after the action items block:

```python
    if not _skip_stubs:
        try:
            from engine.db import get_connection as _get_conn
            from engine.segmenter import resolve_entities
            _conn3 = _get_conn()
            try:
                resolution = resolve_entities(_entities, _conn3, _brain_root)
                for stub in resolution.get("new_stubs", []):
                    try:
                        capture_note(
                            note_type=stub["type"],
                            title=stub["name"],
                            body="",
                            tags=[],
                            people=[],
                            content_sensitivity="public",
                            brain_root=_brain_root,
                            conn=_conn3,
                        )
                        _conn3.commit()
                    except Exception:
                        pass
            finally:
                _conn3.close()
        except Exception:
            pass
```

**Key implementation note:** The `resolve_entities()` call takes a fresh DB connection (same pattern as action items). Do NOT pass `_conn3` to the inner `capture_note()` recursive call — that would cause a reentrant lock on the same connection. Open and close one connection per stub or pass the same connection carefully.

**Discretion recommendation:** Pass the same `_conn3` to both `resolve_entities()` and `capture_note()` — they serialize naturally within the thread. Commit after each stub. This is the simplest path. `capture_note()` already handles slug collision detection so duplicate person notes are not created (checked via `notes WHERE path=?` query using the connection passed in).

### Alternative: Use p5_assemble directly

`p5_assemble.assemble()` requires a `list[DecomposedResult]`. That data structure is not available inside `capture_note()` (which is not called via the decomposer). Constructing a synthetic `DecomposedResult` just to call `assemble()` is unnecessary indirection. Call `resolve_entities()` directly.

### Anti-Patterns to Avoid

- **Opening the main capture connection inside the thread:** `capture_note()` receives `conn` from its caller. The thread MUST open its own fresh connections via `get_connection()`, same as the action items task. The caller's `conn` must not be used after the function returns.
- **Recursive `capture_note()` call without isolation:** Each recursive stub capture must use the thread's own connection, not the outer one. Reuse `_conn3` across stub creates within the thread (they are sequential, not concurrent).
- **Calling `p5_assemble.assemble()` with a synthetic segment list:** More code, no benefit. Use `resolve_entities()` directly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Stub deduplication | Custom "does this person exist?" check | `capture_note()` already handles slug collision — duplicate titles get `-2` suffix, but existing path check prevents double-writes |
| Person lookup | Custom name-to-path resolution | `resolve_entities()` in `segmenter.py` — FTS5 + difflib fuzzy match already implemented |
| Thread management | New threading primitives | Existing daemon thread pattern in `_run_intelligence_hooks` |

---

## Common Pitfalls

### Pitfall 1: Connection Reuse Across Thread Boundary
**What goes wrong:** Passing the caller's `conn` into the background thread causes "ProgrammingError: Cannot operate on a closed database" or silent corruption if the caller closes the connection after `capture_note()` returns.
**Why it happens:** SQLite connections are not thread-safe by default. The caller may close `conn` before the thread runs.
**How to avoid:** Thread opens its own fresh connection via `get_connection()` — exactly as the action items task does.
**Warning signs:** Intermittent test failures involving "closed database" or missing stubs.

### Pitfall 2: Recursive Stub Creation Loop
**What goes wrong:** Stub notes (empty body, `note_type='people'`) trigger another stub creation round, which tries to create stubs for the same people again.
**Why it happens:** `capture_note()` always runs `_run_intelligence_hooks`. If stubs call `capture_note()` with body="" and no entities, the background hook fires but `entities["people"]` will be empty, so the gate `not entities.get("people")` catches it.
**How to avoid:** The two-layer gate (D-01) prevents recursion because stub captures have `body=""`, so `extract_entities()` returns empty people. Verify this is true in tests.
**Warning signs:** Exponential stub proliferation in tests.

### Pitfall 3: Patching Only One DB_PATH in Tests
**What goes wrong:** Test calls `capture_note()` with a temp brain, but the stub creation thread opens `get_connection()` using the real `engine.paths.DB_PATH` and writes to `~/SecondBrain/.meta/brain.db`.
**Why it happens:** Background thread imports `engine.db.get_connection` at call time. If `engine.db.DB_PATH` was not patched (only `engine.paths.DB_PATH`), the thread uses the wrong DB.
**How to avoid:** Tests MUST patch both `engine.db.DB_PATH` and `engine.paths.DB_PATH` (LEARNINGS.md rule already documents this). Thread uses `engine.db.get_connection()` which reads from `engine.db.DB_PATH`.
**Warning signs:** `_guard_real_brain` session fixture fails with "ISOLATION FAILURE".

### Pitfall 4: Test Asserting Stubs Before Thread Completes
**What goes wrong:** Test calls `capture_note()`, immediately queries the DB for person notes, finds nothing, and fails — because the background thread hasn't run yet.
**Why it happens:** Daemon threads are not awaited. The main test thread races the background thread.
**How to avoid:** Tests for stub creation must either (a) mock the thread to run synchronously, or (b) wait with `time.sleep()` / `threading.Event`, or (c) assert on the stub-creation call being invoked (mock) rather than the DB state. Option (a) — mock `threading.Thread` to call `target()` synchronously — is cleanest.
**Warning signs:** Flaky tests that sometimes pass depending on scheduling.

---

## Code Examples

### Existing sb_capture_smart stub creation pattern (mcp_server.py ~line 922)
```python
# Source: engine/mcp_server.py
for stub in result.person_stubs:
    stub_name = stub["name"]
    if stub_name in stub_paths_created:
        resolved_links.append(stub_paths_created[stub_name])
        continue
    try:
        _stub_path = capture_note(
            note_type=stub["type"],
            title=stub_name,
            body="",
            tags=[],
            people=[],
            content_sensitivity="public",
            brain_root=BRAIN_ROOT,
            conn=conn,
        )
        stub_paths_created[stub_name] = str(_stub_path)
        resolved_links.append(str(_stub_path))
    except Exception:
        pass  # Non-fatal
```

### resolve_entities() return shape (segmenter.py)
```python
# Returns:
{
    "existing": [{"name": str, "path": str}, ...],
    "new_stubs": [{"name": str, "type": str}, ...],
}
```

### Current _run_intelligence_hooks end (capture.py ~line 609)
```python
        try:
            from engine.db import get_connection as _get_conn
            from engine.intelligence import extract_action_items
            _conn2 = _get_conn()
            try:
                extract_action_items(Path(_target_str), _body, _sensitivity, _conn2)
            finally:
                _conn2.close()
        except Exception:
            pass

threading.Thread(target=_run_intelligence_hooks, daemon=True).start()
```
The new stub-creation block is inserted **before** `threading.Thread(...)` call but **inside** the closure, after the action items block.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (uv run pytest) |
| Config file | pyproject.toml |
| Quick run command | `uv run pytest tests/test_capture.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements -> Test Map

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| `capture_note()` creates person stubs in background for meeting notes mentioning known people | unit | `uv run pytest tests/test_capture.py -k "stub" -x` | ❌ Wave 0 |
| Stub creation skipped for `note_type in {"coding", "link", "files"}` | unit | `uv run pytest tests/test_capture.py -k "stub_skip" -x` | ❌ Wave 0 |
| Stub creation skipped when `entities["people"]` is empty | unit | `uv run pytest tests/test_capture.py -k "stub_skip" -x` | ❌ Wave 0 |
| No recursive infinite loop when stub capture itself runs | unit | `uv run pytest tests/test_capture.py -k "stub_no_loop" -x` | ❌ Wave 0 |
| Thread errors in stub creation do not surface or crash | unit | `uv run pytest tests/test_capture.py -k "stub_error" -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_capture.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_capture.py` — add `TestPersonStubCreation` class with ~5 test methods covering: stub created, stub skipped by type, stub skipped by empty people, no loop on recursive stub, thread error is silent.
- [ ] Tests must mock `threading.Thread` to execute synchronously to avoid race conditions.
- [ ] Tests must patch both `engine.db.DB_PATH` and `engine.paths.DB_PATH` (existing LEARNINGS.md rule).

---

## Environment Availability

Step 2.6: SKIPPED — phase is code-only changes to `engine/capture.py`. No external tools, services, or runtimes beyond Python 3.13 and the existing project stack.

---

## Open Questions

1. **Connection reuse for multiple stubs in one call**
   - What we know: `resolve_entities()` may return multiple `new_stubs`
   - What's unclear: Should each stub get its own `get_connection()` call (safest, ~3ms overhead per stub) or share `_conn3`?
   - Recommendation: Share `_conn3` across all stubs in one thread invocation — they run sequentially, connection stays open for the thread's lifetime, commit after each. Same as how action items uses one connection.

2. **`stub_paths_created` dedup dict in `sb_capture_smart`**
   - What we know: `sb_capture_smart` tracks `stub_paths_created` to avoid calling `capture_note()` twice for the same name within one smart-capture run.
   - What's unclear: Is this needed in the background thread context?
   - Recommendation: Not needed. Each `capture_note()` invocation is independent. The slug collision check inside `capture_note()` provides dedup at the file/DB level. No in-memory dict needed.

---

## Sources

### Primary (HIGH confidence)
- `engine/capture.py` — direct read of `capture_note()`, `_run_intelligence_hooks`, entity extraction pattern
- `engine/passes/p5_assemble.py` — direct read of `assemble()` and its dependency on `resolve_entities()`
- `engine/passes/__init__.py` — direct read of `decompose()` and Pass 5 integration
- `engine/mcp_server.py` lines 920-942 — direct read of existing stub creation pattern in `sb_capture_smart`
- `engine/segmenter.py` lines 23-60 — direct read of `resolve_entities()` return shape
- `tests/test_capture.py` — direct read of existing test patterns and DB patching conventions
- `tests/conftest.py` — direct read of `stub_engine_embeddings`, `initialized_db`, `_guard_real_brain`
- `.claude/LEARNINGS.md` — DB_PATH patching rule, entity extraction ordering rule

### Secondary (MEDIUM confidence)
- `CONTEXT.md` decisions D-01 through D-04 — user decisions from discuss-phase
- `STATE.md` accumulated decisions — Phase 43 patterns, threading conventions

---

## Metadata

**Confidence breakdown:**
- Implementation pattern: HIGH — `sb_capture_smart` is a working reference; the task is replication not invention
- Threading pitfalls: HIGH — documented in LEARNINGS.md and visible in existing code patterns
- Test strategy: HIGH — existing test file and fixtures are well-understood

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable codebase; no external dependencies)
