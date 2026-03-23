# Phase 35: Brain Consolidation & Knowledge Hygiene — Research

**Researched:** 2026-03-23
**Domain:** SQLite data hygiene, note merging, launchd scheduling, MCP tool patterns
**Confidence:** HIGH — all findings verified against existing codebase; no external library unknowns

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**A — Merge Workflow (CONS-01)**
- D-01: Three access surfaces: MCP (`sb_merge_duplicates` + `sb_merge_confirm`), CLI (`sb-merge-duplicates`), GUI merge button in health panel
- D-02: Merge = copy body/tags/relationships from discard into keep (deduplicate), then `sb_forget` discard (cascade delete)
- D-03: Detection threshold stays at 0.92; no auto-merge

**B — Stub Enrichment (CONS-02)**
- D-04: Stub = body IS NULL, empty string, or < 50 words
- D-05: Merge-first: run stub through duplicate detection; if similar fuller note found → merge route; if no match → AI enrichment via `sb_capture_smart` pattern, user confirms before save
- D-06: `sb_find_stubs` MCP tool returns stubs with similarity matches

**C — Connection Graph Cleanup (CONS-03)**
- D-07: Dangling relationships auto-delete (source_path or target_path not in notes); bidirectional gaps flag for review (not auto-create)
- D-08: Cleanup in scheduled job + `sb_cleanup_connections` MCP tool for on-demand
- D-09: Return counts of deleted dangling rows and flagged bidirectional gaps

**D — Health Trend Tracking (CONS-04)**
- D-10: New `health_snapshots` table with: id, snapped_at, score, total_notes, orphan_count, broken_count, duplicate_count, stub_count
- D-11: Snapshot on scheduled job only — not on every `sb-health` call
- D-12: 90-day retention; cleanup in same scheduled job
- D-13: `sb_health_trend` MCP tool returns last-N-days time series

**E — Scheduled Consolidation (CONS-05)**
- D-14: New plist label: `com.secondbrain.consolidate`
- D-15: `StartCalendarInterval` daily at 03:00; launchd fires on next wake if missed
- D-16: Job order: archive old action items → delete dangling relationships → take health snapshot → clean old snapshots
- D-17: No auto-merge or auto-enrich — safe/idempotent ops only
- D-18: Installed via `scripts/install_native.py`

**Folded Todo**
- T-01: Tests for `brain_health.py` must ship with each plan that modifies it

### Claude's Discretion
- GUI health panel layout for merge buttons (extends existing health view)
- Bidirectional gap report format (table vs list vs grouped by note)
- Exact `sb_health_trend` response shape (array of snapshots vs delta-based)
- Similarity threshold for stub-to-merge routing (can start at 0.85, lower than duplicate threshold)

### Deferred Ideas (OUT OF SCOPE)
None surfaced.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONS-01 | Near-duplicate cluster detection + merge workflow | `get_duplicate_candidates()` exists; merge = content copy + `forget_person`-style cascade; confirm-token pattern in `_issue_token`/`_consume_token` |
| CONS-02 | Stub enrichment (merge-first, enrich-if-no-match) | `get_empty_notes()` returns empty notes; stub threshold is < 50 words (new logic); `find_similar` reusable for similarity check; `sb_capture_smart` AI pattern for enrichment |
| CONS-03 | Connection graph cleanup (dangling delete + bidirectional gap flag) | `relationships` table schema known; dangling = path not in notes; bidirectional gap is `A→B` without `B→A` |
| CONS-04 | Health trend tracking with `health_snapshots` table | Migration pattern well-established in `db.py`; schema defined in CONTEXT.md; 90-day retention matches `archive_old_action_items` pattern |
| CONS-05 | Scheduled consolidation launchd plist at 03:00 daily | `write_digest_plist` is the exact model; `StartCalendarInterval` pattern confirmed in `install_native.py` |
</phase_requirements>

---

## Summary

Phase 35 adds consolidation operations on top of a well-understood foundation. All five requirements build on code that already exists: `brain_health.py` has the detection queries, `intelligence.py` has `find_similar()`, `forget.py` provides cascade delete semantics, `db.py` has an established migration pattern, and `install_native.py` already installs two similar launchd plists. There are no unknown library dependencies.

The most architecturally significant work is the merge execution (CONS-01): it must be atomic, audit-logged, and reversible enough that a false-positive merge doesn't silently destroy data. The confirm-token pattern (`_issue_token`/`_consume_token`) already handles the safety gate; the implementation challenge is the content-merge logic (copy body/tags/relationships, deduplicate) before calling the cascade delete.

Stub enrichment (CONS-02) introduces a word-count check not in the existing `get_empty_notes()` (which only checks for NULL/empty string body). This is a small extension. The bigger integration risk is the AI enrichment path: it must follow `sb_capture_smart` semantics (user confirms before save) and handle the case where the AI adapter is unavailable gracefully.

**Primary recommendation:** Implement plans in order 35-01 → 35-02 → 35-03. Plan 35-01 (merge) is the most complex; plans 35-02 and 35-03 can proceed faster because their patterns are simpler extensions of existing code.

---

## Standard Stack

### Core (all already in pyproject.toml — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlite3 (stdlib) | Python 3.13 | DB operations, migrations, health_snapshots | All existing DB work uses it |
| fastmcp | current | New MCP tools | All 22 existing tools use it |
| plistlib (stdlib) | Python 3.13 | launchd plist generation | Used by `install_native.py` for all existing plists |
| Flask | current | REST endpoints for GUI merge/stub flows | All existing API routes use it |

### No New Dependencies Required

Phase 35 is entirely additive within the existing stack. The only new Python code touches modules already in the project. No `pip install` steps needed.

---

## Architecture Patterns

### Recommended Plan Structure

```
Plan 35-01: brain_health.py (merge logic) + mcp_server.py (sb_merge_*) + api.py (merge endpoint) + CLI entry point
Plan 35-02: brain_health.py (stub extension + connection cleanup) + mcp_server.py (sb_find_stubs, sb_cleanup_connections) + api.py + IntelligencePage.tsx
Plan 35-03: db.py (health_snapshots migration) + brain_health.py (snapshot + cleanup) + mcp_server.py (sb_health_trend) + install_native.py (consolidate plist) + new CLI entry point
```

### Pattern 1: Confirm-Token Two-Step for sb_merge_confirm

The existing pattern in `sb_forget` and `sb_anonymize` is the exact model:

```python
# Source: engine/mcp_server.py lines 686-707
@mcp.tool()
def sb_merge_confirm(pair_id: str, keep_path: str, discard_path: str, confirm_token: str = "") -> dict:
    if not confirm_token:
        tok = _issue_token()
        return {"status": "pending", "confirm_token": tok,
                "message": f"Call sb_merge_confirm again with confirm_token='{tok}' within 60s."}
    if not _consume_token(confirm_token):
        raise ValueError("TOKEN_EXPIRED: confirm_token invalid or expired.")
    # ... execute merge
```

### Pattern 2: DB Migration in init_schema

All migrations follow this pattern in `db.py`:

```python
# Source: engine/db.py — migrate_add_action_items_archive_table pattern
def migrate_add_health_snapshots_table(conn: sqlite3.Connection) -> None:
    """Idempotent migration: create health_snapshots table if absent."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS health_snapshots (
            id            INTEGER PRIMARY KEY,
            snapped_at    TEXT NOT NULL,
            score         INTEGER,
            total_notes   INTEGER,
            orphan_count  INTEGER,
            broken_count  INTEGER,
            duplicate_count INTEGER,
            stub_count    INTEGER
        )
    """)
    conn.commit()
# Then add call to init_schema() after existing migrations
```

### Pattern 3: launchd Plist for Scheduled Job

The `write_digest_plist` function is the exact model for the consolidation plist:

```python
# Source: scripts/install_native.py lines 108-130
plist = {
    "Label": "com.secondbrain.consolidate",
    "ProgramArguments": ["/usr/bin/env", "uv", "run", "--directory", str(repo_root), "sb-consolidate"],
    "WorkingDirectory": str(Path.home() / "SecondBrain"),
    "EnvironmentVariables": {"PATH": ..., "HOME": str(Path.home())},
    "StartCalendarInterval": {"Hour": 3, "Minute": 0},  # daily 03:00, fires on wake
    "StandardOutPath": str(log_dir / "second-brain-consolidate.log"),
    "StandardErrorPath": str(log_dir / "second-brain-consolidate-error.log"),
}
```

Note: digest plist uses `Weekday` key; consolidate plist omits it (daily = no Weekday key).

### Pattern 4: Merge Content Logic

The merge operation must be atomic and correct. Based on existing code in `forget.py` (cascade delete pattern) and `brain_health.py`:

1. Read keep note body/tags/relationships from DB
2. Read discard note body/tags/relationships from DB
3. In a single transaction:
   - Merge bodies (append discard body with separator if keep body is non-empty, else use discard body)
   - Merge tags (set union)
   - Merge relationships (INSERT OR IGNORE into relationships with keep_path as source/target)
   - UPDATE notes SET body=merged_body, tags=merged_tags, updated_at=now WHERE path=keep_path
   - DELETE FROM note_embeddings WHERE note_path=discard_path (stale embedding)
   - DELETE FROM relationships WHERE source_path=discard_path OR target_path=discard_path
   - DELETE FROM action_items WHERE note_path=discard_path
   - DELETE FROM notes WHERE path=discard_path
   - FTS5 rebuild
4. COMMIT
5. Delete discard file from disk
6. Audit log entry

**Key constraint:** `forget_person()` in `forget.py` handles person-specific cascade (meetings, people fields). For generic note merge, implement a simpler `merge_notes()` function directly in `brain_health.py` that handles the DB-level cascade without the GDPR-specific file walks.

### Pattern 5: get_empty_notes Extension for Stub Detection

Current `get_empty_notes()` only catches NULL/empty body. Stub definition adds word count < 50:

```python
# Extended query — body not null but too short
def get_stub_notes(conn) -> list[dict]:
    rows = conn.execute("""
        SELECT path, title, body FROM notes
        WHERE body IS NULL OR TRIM(body) = ''
           OR (LENGTH(TRIM(body)) - LENGTH(REPLACE(TRIM(body), ' ', '')) + 1) < 50
        LIMIT 50
    """).fetchall()
```

The word-count approximation using space-counting is fast but imprecise (doesn't handle multiple spaces, punctuation as word boundaries). For 50 words the approximation is good enough — a note with 47 words might have 46 spaces, which still classifies it correctly. The alternative is Python `len(body.split())` post-query — more accurate and simpler to reason about.

**Recommendation:** Fetch candidates with `LENGTH(body) < 400` (conservative proxy for 50 words) and filter with `len(body.split()) < 50` in Python. Avoids complex SQL and handles edge cases.

### Pattern 6: Bidirectional Gap Detection Query

```sql
SELECT r.source_path, r.target_path, r.rel_type
FROM relationships r
WHERE NOT EXISTS (
    SELECT 1 FROM relationships r2
    WHERE r2.source_path = r.target_path
      AND r2.target_path = r.source_path
)
AND r.source_path IN (SELECT path FROM notes)
AND r.target_path IN (SELECT path FROM notes)
ORDER BY r.source_path;
```

This returns all A→B pairs that have no B→A (regardless of rel_type). The context decision is to flag these, not auto-create the reverse. Return them as `{"source": ..., "target": ..., "rel_type": ...}`.

### Anti-Patterns to Avoid

- **Don't call `forget_person()` for discard step.** It's person-specific (walks meetings directory, cleans people JSON). Implement `merge_notes()` directly with targeted DELETE statements.
- **Don't call `get_brain_health_report()` from the scheduled job for the snapshot.** That function calls `archive_old_action_items()` as a side effect and triggers FTS rebuild; the consolidation job calls each step explicitly in defined order (D-16).
- **Don't add health_snapshots cleanup as a separate query in the scheduled job.** Fold it into the same transaction as the snapshot insert (DELETE WHERE snapped_at < datetime('now', '-90 days'), then INSERT) so they succeed or fail together.
- **Don't expose merge button directly (no confirm gate).** GUI merge button must call the API merge endpoint which internally uses the same confirm-token flow as the MCP tool, or use a two-step modal. The UI decision is discretionary but the backend must always require token confirmation.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cascade delete of discard note | Custom DELETE loop | Targeted DELETEs in one transaction (same as forget.py pattern) | FK cascade not guaranteed for all tables; explicit deletes are already audited |
| Similarity search | Custom cosine math | `find_similar()` in `intelligence.py` | Already handles sqlite-vec unavailability gracefully |
| launchd plist writing | Custom dict serialization | `plistlib.dump()` | Already in use for 3 plists; handles binary plist format correctly |
| Token confirmation | Custom nonce store | `_issue_token()` / `_consume_token()` in `mcp_server.py` | Thread-safe, 60s expiry, already tested implicitly by existing tools |
| Word count | SQL string functions only | Python `len(body.split()) < 50` post-filter | More readable, handles edge cases, negligible performance impact for <50 candidates |

---

## Common Pitfalls

### Pitfall 1: Migration Column Verify Rule

**What goes wrong:** Adding `health_snapshots` without verifying it's called from `init_schema()` — works on fresh DBs but existing brains never get the table.
**Why it happens:** Migration function exists but isn't wired into `init_schema()`.
**How to avoid:** Always append the migration call at the end of `init_schema()`, after existing migration calls. Run test with fresh AND pre-existing DB (monkeypatched `DB_PATH`).
**Warning signs:** `OperationalError: no such table: health_snapshots` on first scheduled job run.

### Pitfall 2: find_similar() With Absolute vs Relative Paths

**What goes wrong:** `find_similar(path, conn)` takes `note_path` as a string; the embeddings table may store relative paths (post-Phase 32 migration). Passing an absolute path gets zero matches.
**Why it happens:** Phase 32 migrated `note_embeddings.note_path` to relative. Code that constructs paths from BRAIN_ROOT will produce absolute paths.
**How to avoid:** Use `store_path()` from `engine.paths` to normalize paths before passing to `find_similar()`. Verify against actual DB content before assuming format.
**Warning signs:** `find_similar()` returns `[]` for notes that clearly have embeddings.

### Pitfall 3: FTS5 Must Be Rebuilt After Merge

**What goes wrong:** Merge deletes the discard note from `notes` but the FTS5 virtual table still has the stale row. Searches return ghost results.
**Why it happens:** The FTS5 AFTER DELETE trigger handles this for normal note deletion, but only if the DELETE goes through the trigger. If using `executemany` or raw DELETE, the trigger fires per row — should be fine. But if `reset=False` is used in `init_schema`, it must still fire.
**How to avoid:** Call `conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")` after the merge transaction commits. Matches the pattern in `forget_person()` (line 130).

### Pitfall 4: Duplicate Pairs Are Not Stable IDs

**What goes wrong:** `sb_merge_duplicates` returns pairs; `sb_merge_confirm` needs a `pair_id`. If the pair list is regenerated between the two calls, the index is unstable.
**Why it happens:** Pair list is computed dynamically from similarity scores; pairs may shift if embeddings are updated concurrently.
**How to avoid:** `pair_id` should be a stable hash of the sorted pair `(min(a,b), max(a,b))`. The caller passes `keep_path` and `discard_path` explicitly — `pair_id` is just for human/audit reference, not for re-lookup. The confirm step validates that both paths still exist before executing.

### Pitfall 5: get_empty_notes() vs get_stub_notes() Naming Conflict

**What goes wrong:** Adding `get_stub_notes()` that overlaps with the existing `get_empty_notes()` creates confusion about which function to call where.
**Why it happens:** Stub definition extends empty to include short-but-not-empty notes.
**How to avoid:** Either (a) rename/extend `get_empty_notes()` to include word-count check and update all callers including `get_brain_health_report()` and the GUI health endpoint, or (b) add `get_stub_notes()` as an additive function and keep `get_empty_notes()` for backward compat. Option (b) is safer because the existing GUI and tests reference `empty_notes` explicitly.

### Pitfall 6: Scheduled Job Must Be Idempotent

**What goes wrong:** Running `sb-consolidate` twice in quick succession (e.g., machine woke and job ran, then user manually runs it) takes two health snapshots within seconds — pollutes the trend with noise.
**Why it happens:** No dedup guard on snapshot insertion.
**How to avoid:** Before inserting a snapshot, check if one already exists for `date('now')`. If so, skip. A one-per-day guard is sufficient.

### Pitfall 7: Test Isolation — Patch Both DB_PATH Locations

**What goes wrong:** Tests that call `get_connection()` without explicit path get the real brain DB.
**Why it happens:** `engine.db.DB_PATH` and `engine.paths.DB_PATH` are separate module-level variables.
**How to avoid:** From LEARNINGS.md: always monkeypatch BOTH `engine.db.DB_PATH` and `engine.paths.DB_PATH` in test fixtures. Matches the pattern in `test_brain_health.py` `archive_conn` fixture.

---

## Code Examples

### sb_merge_duplicates Tool Shape

```python
# Pattern: matches sb_connections / sb_files response shape
@mcp.tool()
def sb_merge_duplicates(threshold: float = 0.92, limit: int = 20) -> dict:
    """Return near-duplicate note pairs above similarity threshold."""
    conn = get_connection()
    try:
        from engine.brain_health import get_duplicate_candidates
        pairs = get_duplicate_candidates(conn, threshold=threshold)[:limit]
        return {"pairs": pairs, "count": len(pairs)}
    finally:
        conn.close()
```

### health_snapshots Cleanup in Scheduled Job

```python
def cleanup_old_snapshots(conn, days: int = 90) -> int:
    """Delete health_snapshots older than `days` days. Returns deleted count."""
    result = conn.execute(
        "DELETE FROM health_snapshots WHERE snapped_at < datetime('now', ?)",
        (f"-{days} days",),
    )
    conn.commit()
    return result.rowcount
```

### Dangling Relationship Deletion

```python
def delete_dangling_relationships(conn) -> int:
    """Delete relationships where source or target path not in notes table."""
    result = conn.execute("""
        DELETE FROM relationships
        WHERE source_path NOT IN (SELECT path FROM notes)
           OR target_path NOT IN (SELECT path FROM notes)
    """)
    conn.commit()
    return result.rowcount
```

### Consolidation Job Entry Point Shape

```python
def consolidate_main() -> None:
    """Entry point for sb-consolidate launchd job."""
    conn = get_connection()
    init_schema(conn)
    results = {}
    results["archived_actions"] = archive_old_action_items(conn)
    results["deleted_dangling"] = delete_dangling_relationships(conn)
    results["snapshot"] = take_health_snapshot(conn)
    results["cleaned_old_snapshots"] = cleanup_old_snapshots(conn)
    conn.close()
    # Log to stdout — captured by launchd StandardOutPath
    import json, datetime
    print(json.dumps({"at": datetime.datetime.utcnow().isoformat(), **results}))
```

### IntelligencePage Merge Button Integration

The health panel duplicate section already renders `duplicate_candidates` as a list. Extend the list item with a "Merge" button that POSTs to a new `/brain-health/merge` endpoint:

```tsx
// Extends existing Section > ul > li pattern in IntelligencePage.tsx
{health.duplicate_candidates.map((dc, i) => (
  <li key={i} className="flex items-center justify-between text-xs text-muted-foreground">
    <span className="truncate">{dc.a} / {dc.b} ({Math.round(dc.similarity * 100)}%)</span>
    <Button size="sm" variant="ghost" onClick={() => handleMerge(dc)}>Merge</Button>
  </li>
))}
```

The `handleMerge` handler opens a confirmation modal (which note to keep) before calling the backend. This avoids needing a server-side confirm-token for the GUI flow — the GUI confirmation modal IS the confirmation step.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `get_empty_notes()` — NULL/empty only | `get_stub_notes()` — adds word count < 50 | Phase 35 | Catches thin notes, not just blank ones |
| Manual dedup via MCP search | `sb_merge_duplicates` workflow | Phase 35 | Actionable merge path, not just detection |
| No health history | `health_snapshots` trend table | Phase 35 | Can observe brain degradation/improvement over time |
| No scheduled cleanup | `sb-consolidate` launchd job (daily 03:00) | Phase 35 | Dangling rels cleaned, action items archived, snapshot taken automatically |

---

## Open Questions

1. **GUI confirmation for merge — modal or inline?**
   - What we know: Must select which note to keep (keep vs discard). Two notes have titles + similarity score to show.
   - What's unclear: Does a modal blocker (like `DeleteEntityModal`) fit, or is an inline "keep A / keep B" toggle sufficient?
   - Recommendation: Reuse `DeleteEntityModal` pattern from Phase 34 — it's already in the codebase and handles two-step confirm well. Planner decides.

2. **sb_health_trend response shape — snapshot array vs sparkline values?**
   - What we know: CONTEXT.md defers format to planner's discretion.
   - What's unclear: Does the GUI chart (if any) need a sparkline array `[{date, score}]` or full snapshot objects?
   - Recommendation: Return full snapshot objects `[{snapped_at, score, total_notes, ...}]` — GUI can extract what it needs; MCP callers get full detail.

3. **Word-count threshold for stub: 50 words boundary edge case**
   - What we know: A 50-word note with complex markdown (headers, code blocks) may have 50+ tokens but thin informational content.
   - What's unclear: Should word count apply to body minus frontmatter, or raw stored body (which has frontmatter stripped at capture time)?
   - Recommendation: Body in DB is already stripped of frontmatter (capture.py handles this). Count words in DB body directly.

---

## Environment Availability

Phase 35 is code/config-only changes with no new external dependencies. launchd is macOS system infrastructure (confirmed present on Intel Mac per CLAUDE.md).

Step 2.6: No new tools to audit — `launchd`, `plistlib`, `sqlite3`, `fastmcp` all confirmed present and in use by existing code.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (current version via uv) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/test_brain_health.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONS-01 | Merge copies content from discard into keep note | unit | `uv run pytest tests/test_brain_health.py::test_merge_copies_body_tags_relationships -x` | ❌ Wave 0 |
| CONS-01 | Cascade delete removes discard note and embeddings | unit | `uv run pytest tests/test_brain_health.py::test_merge_deletes_discard_note -x` | ❌ Wave 0 |
| CONS-01 | sb_merge_confirm requires confirm_token | unit | `uv run pytest tests/test_mcp.py::test_merge_confirm_requires_token -x` | ❌ Wave 0 |
| CONS-02 | get_stub_notes returns notes with < 50 words | unit | `uv run pytest tests/test_brain_health.py::test_get_stub_notes_word_count -x` | ❌ Wave 0 |
| CONS-02 | sb_find_stubs includes similarity matches if above threshold | unit | `uv run pytest tests/test_mcp.py::test_find_stubs_with_matches -x` | ❌ Wave 0 |
| CONS-03 | delete_dangling_relationships removes rows with unknown paths | unit | `uv run pytest tests/test_brain_health.py::test_delete_dangling_relationships -x` | ❌ Wave 0 |
| CONS-03 | get_bidirectional_gaps returns one-way relationships | unit | `uv run pytest tests/test_brain_health.py::test_bidirectional_gap_detection -x` | ❌ Wave 0 |
| CONS-04 | health_snapshots table created by migration | unit | `uv run pytest tests/test_brain_health.py::test_health_snapshots_migration -x` | ❌ Wave 0 |
| CONS-04 | Snapshot record inserted with correct field values | unit | `uv run pytest tests/test_brain_health.py::test_take_health_snapshot -x` | ❌ Wave 0 |
| CONS-04 | Snapshots older than 90 days are deleted | unit | `uv run pytest tests/test_brain_health.py::test_cleanup_old_snapshots -x` | ❌ Wave 0 |
| CONS-05 | consolidate_main runs all steps in order without error | unit | `uv run pytest tests/test_consolidate.py::test_consolidate_main_runs_clean -x` | ❌ Wave 0 |
| CONS-05 | write_consolidate_plist produces valid plist with StartCalendarInterval | unit | `uv run pytest tests/test_install.py::test_write_consolidate_plist -x` | ❌ Wave 0 |

### Sampling Rate

- Per task commit: `uv run pytest tests/test_brain_health.py -x -q`
- Per wave merge: `uv run pytest tests/ -q`
- Phase gate: Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_brain_health.py` — add Phase 35 test functions (CONS-01 through CONS-04); existing file is safe to extend
- [ ] `tests/test_mcp.py` — add `test_merge_confirm_requires_token` and `test_find_stubs_with_matches`; check if this file exists first
- [ ] `tests/test_consolidate.py` — new file for `consolidate_main` integration test
- [ ] `tests/test_install.py` — add `test_write_consolidate_plist` to existing install tests (if file exists)

---

## Sources

### Primary (HIGH confidence)

- `engine/brain_health.py` — all existing functions verified in full
- `engine/intelligence.py` — `find_similar()` signature and behavior verified
- `engine/forget.py` — cascade delete pattern for merge design
- `engine/db.py` — migration pattern, all table schemas, `init_schema()` call chain
- `engine/mcp_server.py` — confirm-token pattern, `_issue_token`/`_consume_token` implementation
- `engine/api.py` — `/brain-health` endpoint, `BrainHealth` response shape
- `scripts/install_native.py` — `write_digest_plist` as model for consolidate plist
- `frontend/src/components/IntelligencePage.tsx` — existing health panel DOM structure
- `frontend/src/types.ts` — `BrainHealth` interface, duplicate_candidates shape
- `tests/test_brain_health.py` — existing test patterns, fixture setup

### Secondary (MEDIUM confidence)

- macOS launchd `StartCalendarInterval` without `Weekday` key = daily — verified against `write_digest_plist` (weekly = has Weekday). Behavior on wake confirmed by CONTEXT.md (D-15 notes no extra logic needed).

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all patterns verified in codebase
- Architecture: HIGH — merge, stub, cleanup, snapshot, and launchd patterns all have direct analogues in existing code
- Pitfalls: HIGH — derived from LEARNINGS.md (verified project rules) and direct code inspection

**Research date:** 2026-03-23
**Valid until:** 2026-06-23 (stable codebase; no fast-moving external dependencies)
