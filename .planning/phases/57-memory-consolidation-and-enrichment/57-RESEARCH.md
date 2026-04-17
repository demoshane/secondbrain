# Phase 57: Memory Consolidation & Enrichment - Research

**Researched:** 2026-04-17
**Domain:** SQLite schema migration, AI-assisted content merge, capture pipeline extension, MCP tool authoring
**Confidence:** HIGH — all findings derived from direct source code inspection

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**AI provider split:**
- Interactive MCP calls: use `_router.get_adapter("public", CONFIG_PATH)` (ModelRouter, routes to configured provider)
- Nightly cron (`consolidate_main`): local Ollama only, same `_router.get_adapter("public")` path Phase 54 uses; if Ollama unavailable, queue candidates instead of failing

**`enrich_note()` signature:**
```python
def enrich_note(existing_path: str, new_content: str, conn, adapter=None) -> dict:
    """Returns: {"path": str, "before_length": int, "after_length": int, "enriched": bool}"""
```
Behavior: read existing body+frontmatter, AI-merge, atomic write back (DB + disk), re-embed, rebuild FTS5, write audit log. Fallback: structured append (heading + new content), NOT raw `---` concatenation.

**Capture-time similarity detection approach:** Capture-then-suggest, not block-and-ask.
1. `capture_note()` writes note unchanged
2. After write: `find_similar(new_path, threshold=0.80, limit=3)`
3. Return `{"similar": [...]}` in result dict if matches found
4. MCP layer surfaces as hint: "Similar note found: {title}. Use sb_enrich to combine."
5. No blocking, no auto-merge.

**`consolidation_queue` schema (verbatim):**
```sql
CREATE TABLE IF NOT EXISTS consolidation_queue (
    id INTEGER PRIMARY KEY,
    action TEXT NOT NULL,          -- 'merge', 'enrich', 'review', 'stale'
    source_paths TEXT NOT NULL,    -- JSON array
    target_path TEXT,
    reason TEXT,
    similarity REAL,
    detected_at TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- 'pending', 'accepted', 'dismissed'
    resolved_at TEXT
);
```

**Nightly consolidation additions to `consolidate_main()`:**
1. `enrichment_sweep()` — pairs 0.80–0.92 similarity, queue as 'enrich', skip dismissed
2. `stale_review()` — 90+ days + access_count < 3, queue as 'stale'
3. `backlink_repair()` — scan `[[path]]` refs for dead targets, fix if merge found in audit_log

**`merge_notes()` upgrades:**
1. Frontmatter merge: union people/tags lists; scalar fields keep target; `created_at` earliest; `updated_at` now
2. Body: call `enrich_note()` if adapter available, else fall back to current `---` separator
3. Backlink repair: scan all note bodies for `[[discard_path]]`, replace with `[[keep_path]]`; same for `source_notes` in synthesis frontmatter

**New MCP tools:**
- `sb_enrich(target_path, new_content)` — non-destructive, no two-step token needed
- `sb_consolidation_review(action="all", limit=10)` — returns pending queue items

**Module placement:**
- `enrich_note()` → `engine/intelligence.py`
- `merge_notes()` upgrades → `engine/brain_health.py`
- New nightly steps → `engine/consolidate.py`
- Similarity hint → `engine/capture.py`
- MCP tools → `engine/mcp_server.py`
- DB migration → `engine/db.py`
- Tests → `tests/test_consolidation.py`, `tests/test_enrich.py`

### Claude's Discretion

None stated explicitly — all major design choices are locked.

### Deferred Ideas (OUT OF SCOPE)

- Auto-enrich on capture for >0.95 similarity (risky)
- Weekly consolidation review notification via CronCreate
- GUI consolidation dashboard with visual merge preview
- Cross-note fact extraction / structured knowledge graph
- Confidence scoring for enrichment count
- Undo enrichment (revert to pre-enrich snapshot)
</user_constraints>

---

## Summary

Phase 57 adds a memory consolidation lifecycle: capture-time similarity hints, AI-assisted in-place note enrichment, a `consolidation_queue` staging table, extended nightly hygiene, and two new MCP tools. The work is additive — every new function plugs into existing infrastructure without changing call signatures of functions external consumers depend on.

The codebase pattern is well established. The atomic write path (`write_note_atomic`), migration idiom (`ALTER TABLE ... ADD COLUMN` wrapped in try/except), AI adapter access (`_router.get_adapter("public", CONFIG_PATH)`), FTS5 rebuild (`INSERT INTO notes_fts(notes_fts) VALUES('rebuild')`), and background thread spawn (`_spawn_background`) are all in production and tested. Every new function follows these exact patterns.

The main technical risk is embedding latency at capture time (~200ms KNN lookup). The CONTEXT.md explicitly accepts this. The second risk is the backlink repair scan — iterating all note bodies in Python is O(N) and could be slow on large brains; the implementation must cap or batch this.

**Primary recommendation:** Implement plans 57-01 through 57-05 strictly in order — the DB migration (01) is a hard prerequisite for all later plans, and `enrich_note()` (01) is consumed by both the upgraded `merge_notes()` (02) and the nightly sweep (04).

---

## Standard Stack

### Core (already in-tree, no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `python-frontmatter` | in `pyproject.toml` | Read/write YAML frontmatter | Used by every write path in `capture.py`, `brain_health.py` |
| `sqlite-vec` | in `pyproject.toml` | KNN cosine similarity in SQLite | Used by `find_similar()` and `check_capture_dedup()` |
| `sentence-transformers` / Ollama | configured in `config.toml` | Text embeddings | Used by `engine/embeddings.py` |

**No new packages required.** All dependencies already installed.

---

## Architecture Patterns

### Pattern 1: Atomic Note Update (existing, reuse for `enrich_note()`)

The `update_note()` function in `capture.py` is the exact pattern to follow for `enrich_note()`: read existing frontmatter with `frontmatter.load()`, modify `.content`, write to tempfile in same directory, UPDATE DB, commit, then `os.replace(tmp, target)`. The only addition is a DB + disk re-embed step after commit.

```python
# engine/capture.py — update_note() template (lines 303-394)
post = frontmatter.load(str(target))
post["updated_at"] = _now_utc()
post.content = new_body  # AI-merged body

tmp_fd, tmp_name = tempfile.mkstemp(dir=target.parent)
with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
    fh.write(frontmatter.dumps(post))
conn.execute("UPDATE notes SET body=?, updated_at=? WHERE path=?", (new_body, now, db_path))
log_audit(conn, "update", db_path)
conn.commit()
os.replace(tmp_name, target)
```

**After the atomic write, re-embed and rebuild FTS5:**
```python
# Re-embed (pattern from engine/embeddings.py via search.py)
from engine.embeddings import embed_texts
blobs = embed_texts([new_body])
if blobs:
    conn.execute(
        "INSERT OR REPLACE INTO note_embeddings (note_path, embedding) VALUES (?, ?)",
        (db_path, blobs[0])
    )
conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")
conn.commit()
```

**Audit log for enrichment:**
```python
conn.execute(
    "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?, ?, ?, datetime('now'))",
    ("enriched", db_path, f"before:{before_len},after:{after_len}")
)
```

### Pattern 2: DB Migration (existing idiom, reuse for `consolidation_queue`)

Every migration in `engine/db.py` follows this pattern:
```python
def migrate_add_consolidation_queue(conn: sqlite3.Connection) -> None:
    """Idempotent migration: create consolidation_queue table if absent."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS consolidation_queue (
            ...
        )
    """)
    conn.commit()
```

Then add one line to `init_schema()` at the end of the migration chain (currently ends with `migrate_add_capture_session(conn)` and `_migrate_junction_triggers(conn)`).

### Pattern 3: Similarity-based candidate detection (enrich sweep)

`get_duplicate_candidates()` in `brain_health.py` is the template for `enrichment_sweep()`. The key differences:
- Threshold range: 0.80–0.92 (not 0.92+)
- Output: insert into `consolidation_queue` instead of returning pairs
- Dismissed tracking: use `consolidation_queue.status = 'dismissed'` instead of `dismissed_inbox_items`

```python
# Pseudo-pattern for enrichment_sweep()
paths = conn.execute("SELECT note_path FROM note_embeddings ORDER BY rowid DESC LIMIT ?", (cap,)).fetchall()
for path in paths:
    matches = find_similar(path, conn, threshold=0.80, limit=5)
    for m in matches:
        if m["similarity"] >= 0.92:
            continue  # above dup threshold — skip (handled by existing dup detection)
        key = tuple(sorted([path, m["note_path"]]))
        if _already_queued_or_dismissed(conn, key):
            continue
        conn.execute(
            "INSERT INTO consolidation_queue (action, source_paths, similarity, reason, detected_at) VALUES (?,?,?,?,datetime('now'))",
            ("enrich", json.dumps(list(key)), m["similarity"], "embedding_similarity")
        )
```

### Pattern 4: Nightly step wrapper (safe, isolated)

Each new step in `consolidate_main()` follows the existing try/except wrapper:
```python
try:
    results["enrichment_sweep"] = enrichment_sweep(conn)
except Exception as exc:
    logger.warning("Enrichment sweep failed: %s", exc)
    results["enrichment_sweep"] = {"error": str(exc)}
```

### Pattern 5: Capture-time hint injection

The background thread `_run_intelligence_hooks()` in `capture_note()` is the hook point for the similarity scan. However, the CONTEXT.md spec says to return similarity hints in the `capture_note()` return value itself (not in a background thread), since the MCP tool needs to surface them synchronously. This means the similarity scan runs **synchronously** post-write, before returning, using `find_similar()` with a dedicated DB connection (same pattern as other post-write hooks but synchronous).

Specifically: after `write_note_atomic()` and `conn.commit()`, before returning `target`:
```python
# Similarity hint — synchronous, best-effort, ~200ms
similar_hint: list[dict] = []
try:
    from engine.intelligence import find_similar
    from engine.paths import store_path as _sp
    _new_rel = _sp(target.resolve())
    similar_hint = find_similar(_new_rel, conn, threshold=0.80, limit=3)
except Exception:
    pass
# Return dict instead of just Path — MCP caller unwraps
```

**Important:** `capture_note()` currently returns `Path`. Changing the return type breaks existing callers. The hint should be returned via a separate mechanism — either a thread-local side channel, or change `capture_note()` to return `(Path, dict)`. The MCP layer (`sb_capture`) would need to unpack the second element. Check all `capture_note()` call sites before changing the signature.

**Alternative (lower risk):** Add `find_similar` call directly in `sb_capture` MCP tool after the `capture_note()` call, using the returned path. This avoids touching `capture_note()` signature.

### Pattern 6: Frontmatter merge for `merge_notes()`

Current `merge_notes()` reads `tags` from the notes table (JSON column). For frontmatter merge, load the disk file with `frontmatter.load()` to access all YAML fields. The merge logic:

```python
import frontmatter as _fm
keep_post = _fm.load(str(keep_file))
discard_post = _fm.load(str(discard_file))

# List fields: union
for field in ("people", "tags"):
    keep_val = keep_post.get(field, []) or []
    discard_val = discard_post.get(field, []) or []
    keep_post[field] = sorted(set(keep_val + discard_val))

# created_at: take earlier
if discard_post.get("created_at") and discard_post["created_at"] < keep_post.get("created_at", "9999"):
    keep_post["created_at"] = discard_post["created_at"]

keep_post["updated_at"] = _now_utc()
```

### Pattern 7: Backlink repair

`repair_person_backlinks()` in `brain_health.py` already implements the general pattern: SQL query to find backlink relationships where target doesn't exist, then file text replacement. The new `backlink_repair()` needs a broader version that operates on wiki-link body text patterns (`[[path]]`), not just person-file backlink lines.

The pattern for body-text wiki-link repair:
```python
# Find notes with wiki-links to moved/merged paths (from audit_log)
merged_pairs = conn.execute(
    "SELECT note_path, detail FROM audit_log WHERE event_type='merge'",
).fetchall()
# detail format: "merged:{discard_path}"
for kept_path, detail in merged_pairs:
    discard_path = detail.replace("merged:", "")
    # Find notes whose body contains [[discard_path]]
    body_rows = conn.execute(
        "SELECT path, body FROM notes WHERE body LIKE ?", (f"%[[{discard_path}]]%",)
    ).fetchall()
    for note_path, body in body_rows:
        new_body = body.replace(f"[[{discard_path}]]", f"[[{kept_path}]]")
        # atomic write back
```

**Performance note:** `LIKE '%string%'` does a full table scan. For large brains, cap this or limit to notes updated since last consolidation run. An index on `body` is not useful for LIKE with leading wildcard.

### Pattern 8: MCP tool structure

```python
@mcp.tool()
def sb_enrich(target_path: str, new_content: str) -> dict:
    """Enrich an existing note by AI-merging new_content into it."""
    _ensure_ready()
    conn = get_connection()
    try:
        from engine.intelligence import enrich_note
        result = enrich_note(target_path, new_content, conn)
        _log_mcp_audit("mcp_enrich", target_path)
        return {"status": "enriched", **result}
    finally:
        conn.close()

@mcp.tool()
def sb_consolidation_review(action: str = "all", limit: int = 10) -> dict:
    """Return pending consolidation candidates."""
    _ensure_ready()
    conn = get_connection()
    try:
        where = "" if action == "all" else f"AND action = '{action}'"  # parameterize this
        rows = conn.execute(
            f"SELECT id, action, source_paths, target_path, reason, similarity, detected_at "
            f"FROM consolidation_queue WHERE status = 'pending' {where} ORDER BY detected_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        items = [...]
        return {"items": items, "count": len(items)}
    finally:
        conn.close()
```

**Note:** Use parameterized query for `action` filter — don't interpolate into SQL string.

### Anti-Patterns to Avoid

- **Changing `capture_note()` return type without auditing all call sites.** There are at least 5 internal call sites (CLI `main()`, `sb_capture`, `sb_capture_batch`, `sb_capture_smart`, person stub creation in background thread). Changing to `(Path, dict)` breaks all of them. Prefer adding hint logic in the MCP layer instead.
- **Blocking capture with similarity scan.** The scan must be non-blocking or have a timeout (same 8s timeout pattern as `check_capture_dedup()`). If embedding is unavailable, return empty similar list silently.
- **O(N²) backlink scan without a cap.** The audit_log approach limits scope to recently merged notes. Don't scan all bodies against all wiki-links unconditionally.
- **Forgetting to update FTS5 after enrich.** `UPDATE notes SET body=...` does NOT auto-trigger FTS5 update — the FTS5 `notes_fts` table uses content-tracking triggers defined in `_migrate_junction_triggers()`. Verify if FTS5 content triggers exist or if manual rebuild is needed. Current `merge_notes()` does manual `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` after the transaction — follow this pattern.
- **Skipping `note_embeddings` update after body change.** After any body update (enrich or merge), re-embed and upsert into `note_embeddings`. If the embedding is stale, `find_similar()` returns wrong results next time.
- **Using `sensitivity` frontmatter key inconsistently.** The DB column is `sensitivity`, but `build_post()` sets `content_sensitivity`. The `write_note_atomic()` reads `post.get("content_sensitivity", "public")`. When loading existing notes via `frontmatter.load()`, the field may be stored as either key depending on when it was written. Read both and prefer `content_sensitivity`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file write | Custom temp+rename | `tempfile.mkstemp()` + `os.replace()` | Already in `write_note_atomic()` and `update_note()` |
| Frontmatter parse | Custom YAML parser | `python-frontmatter` | Handles edge cases, round-trips cleanly |
| Cosine similarity | Custom vector math | `sqlite-vec` via `find_similar()` | Already optimized, handles extension loading |
| AI text generation | Custom LLM client | `_router.get_adapter().generate()` | Routes Ollama/Groq/Claude, has fallback logic |
| DB migration guard | Custom column check | `ALTER TABLE ... ADD COLUMN` in try/except | Established pattern in all 20+ existing migrations |
| FTS5 sync | Manual FTS row management | `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` | Proven pattern; triggers may not cover all UPDATE paths |

---

## Common Pitfalls

### Pitfall 1: FTS5 Out of Sync After Body Update

**What goes wrong:** After `UPDATE notes SET body=...`, FTS5 index (`notes_fts`) does not reflect the new content. Searches return stale results or miss the note.

**Why it happens:** FTS5 content-row tables use triggers defined in `_migrate_junction_triggers()`, but those triggers handle `note_tags` and `note_people` junction tables, NOT FTS5. FTS5 has its own content-row tracking, but the current code uses explicit `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` calls after modifications rather than relying on automatic triggers.

**How to avoid:** After any body update, call `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')` outside the transaction (same as `merge_notes()` at line 355), then commit.

**Warning signs:** `sb_search` returns stale titles or misses newly enriched notes.

### Pitfall 2: Stale Embedding After Enrichment

**What goes wrong:** `find_similar()` uses the pre-enrichment embedding, so enriched notes are found similar to notes they've diverged from, or not found similar to newly relevant notes.

**Why it happens:** `note_embeddings` is only updated by the capture pipeline. Manual body updates bypass this.

**How to avoid:** After every `enrich_note()` call, call `embed_texts([new_body])` and upsert the result into `note_embeddings WHERE note_path = ?`. Best-effort — if Ollama is down, skip silently and log.

### Pitfall 3: `capture_note()` Return Type Change Breaks Callers

**What goes wrong:** Adding a similarity hint to `capture_note()` by changing return from `Path` to `(Path, dict)` silently breaks all call sites that do `path = capture_note(...)` — they receive a tuple, and downstream `str(path)` gives the wrong value.

**Why it happens:** Python doesn't enforce return types. Errors appear at runtime, not import time.

**How to avoid:** Do NOT change `capture_note()` signature. Add similarity detection logic in `sb_capture` (MCP layer) after `capture_note()` returns, using the returned path directly.

### Pitfall 4: `consolidation_queue` Dismissed Check Must Use Source Path Pair

**What goes wrong:** If dismissed check uses only `target_path`, the same pair gets re-queued whenever either note is processed.

**Why it happens:** The dedup key must be a canonical pair (sorted tuple), not a single path.

**How to avoid:** Store the pair in `source_paths` as JSON `["path_a", "path_b"]` (sorted). When checking for dismissed items, deserialize and compare sorted tuples.

### Pitfall 5: Backlink Repair Corrupting Synthesis Frontmatter

**What goes wrong:** Synthesis notes store `source_notes` as a YAML list in frontmatter. A naive string replacement of `[[discard_path]]` in the body doesn't update the `source_notes` frontmatter list.

**Why it happens:** Frontmatter and body are separate. `body.replace()` only touches the content section.

**How to avoid:** Load the synthesis note with `frontmatter.load()`, update `post["source_notes"]` list explicitly, AND update `post.content` body. Write back atomically.

### Pitfall 6: Ollama Unavailability in Nightly Job

**What goes wrong:** `enrich_note()` and `enrichment_sweep()` try to call Ollama at 03:00. If Ollama isn't running, the entire nightly consolidation fails.

**Why it happens:** Launchd doesn't guarantee Ollama is running when the consolidation job fires.

**How to avoid:** Wrap every AI call in try/except. On failure: queue candidates with `status='pending'` (for enrichment sweep), or fall back to structured append (for enrich_note). Never raise from nightly steps. Use the existing pattern: `try: result = consolidation_step(conn); except Exception as exc: results[step] = {"error": str(exc)}`.

### Pitfall 7: DB Path Monkeypatching in Tests

**What goes wrong:** Tests that call `get_connection()` without patching `engine.db.DB_PATH` AND `engine.paths.DB_PATH` open the real brain database.

**Why it happens:** `get_connection()` reads from `engine.db.DB_PATH`, but some code paths re-import from `engine.paths.DB_PATH`. Both must be patched.

**How to avoid:** Use the established fixture pattern from `test_consolidate.py`:
```python
@pytest.fixture
def cons_conn(tmp_path):
    import engine.db as _db, engine.paths as _paths
    db_path = tmp_path / "test.db"
    _db.DB_PATH = db_path
    _paths.DB_PATH = db_path
    conn = sqlite3.connect(str(db_path))
    init_schema(conn)
    yield conn
    conn.close()
```
Also patch `engine.paths.BRAIN_ROOT` for any test that writes files.

---

## Code Examples

### `enrich_note()` skeleton — engine/intelligence.py

```python
ENRICH_SYSTEM_PROMPT = (
    "You are a knowledge management assistant. "
    "Update the existing note by integrating new information. "
    "Preserve all existing facts. Add new information naturally. "
    "Don't duplicate content. Maintain the note's style and structure. "
    "Output only the updated note body — no preamble."
)

def enrich_note(existing_path: str, new_content: str, conn, adapter=None) -> dict:
    """Integrate new_content into an existing note using AI-assisted merge.
    Returns: {"path": str, "before_length": int, "after_length": int, "enriched": bool}
    """
    from engine.paths import BRAIN_ROOT, CONFIG_PATH
    import frontmatter as _fm

    # Resolve path
    p = Path(existing_path)
    if not p.is_absolute():
        p = BRAIN_ROOT / existing_path
    if not p.exists():
        raise ValueError(f"Note not found: {existing_path!r}")

    post = _fm.load(str(p))
    existing_body = post.content or ""
    before_len = len(existing_body)

    enriched = False
    if adapter is None:
        try:
            adapter = _router.get_adapter("public", CONFIG_PATH)
        except Exception:
            adapter = None

    if adapter and existing_body:
        try:
            merged_body = adapter.generate(
                user_content=f"EXISTING NOTE:\n{existing_body}\n\nNEW INFORMATION:\n{new_content}",
                system_prompt=ENRICH_SYSTEM_PROMPT,
            )
            enriched = True
        except Exception:
            merged_body = None
    else:
        merged_body = None

    if not merged_body:
        # Structured fallback: append with heading
        today = datetime.date.today().isoformat()
        merged_body = existing_body + f"\n\n## Update {today}\n\n{new_content}"

    post.content = merged_body
    post["updated_at"] = _now_utc()
    after_len = len(merged_body)

    # Atomic write back
    try:
        db_path = _store_path(p.resolve())
    except ValueError:
        db_path = existing_path
    tmp_fd, tmp_name = tempfile.mkstemp(dir=p.parent)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(_fm.dumps(post))
        tmp_fd = None
        conn.execute("UPDATE notes SET body=?, updated_at=? WHERE path=?", (merged_body, post["updated_at"], db_path))
        conn.execute(
            "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?,?,?,datetime('now'))",
            ("enriched", db_path, f"before:{before_len},after:{after_len}")
        )
        conn.commit()
        os.replace(tmp_name, p)
    except Exception:
        if tmp_fd is not None:
            try: os.close(tmp_fd)
            except OSError: pass
        Path(tmp_name).unlink(missing_ok=True)
        raise

    # Re-embed (best-effort)
    try:
        from engine.embeddings import embed_texts
        blobs = embed_texts([merged_body[:4000]])
        if blobs:
            conn.execute(
                "INSERT OR REPLACE INTO note_embeddings (note_path, embedding) VALUES (?,?)",
                (db_path, blobs[0])
            )
    except Exception:
        pass

    # Rebuild FTS5
    conn.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild')")
    conn.commit()

    return {"path": existing_path, "before_length": before_len, "after_length": after_len, "enriched": enriched}
```

### Migration addition — engine/db.py

```python
def migrate_add_consolidation_queue(conn: sqlite3.Connection) -> None:
    """Idempotent: create consolidation_queue table if absent."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS consolidation_queue (
            id INTEGER PRIMARY KEY,
            action TEXT NOT NULL,
            source_paths TEXT NOT NULL,
            target_path TEXT,
            reason TEXT,
            similarity REAL,
            detected_at TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            resolved_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cq_status ON consolidation_queue(status, action)")
    conn.commit()
```

Add at end of `init_schema()` before `conn.commit()`.

---

## Runtime State Inventory

> Not a rename/refactor phase — this section is not applicable.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Ollama (`nomic-embed-text`) | `enrich_note()`, embedding re-index | Configured (known gotcha: macOS 26 no torch wheel) | nomic-embed-text via Ollama | Skip re-embed, log warning |
| `sqlite-vec` | `find_similar()` for similarity hints | In pyproject.toml, already used in prod | Current | Return `[]` silently (existing pattern) |
| `python-frontmatter` | `enrich_note()`, `merge_notes()` upgrade | In pyproject.toml | Current | N/A — required |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:**
- Ollama unavailable at nightly run: queue candidates for later review, do not fail.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/test_consolidation.py tests/test_enrich.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Plan | Behavior | Test Type | Automated Command | File Exists? |
|------|----------|-----------|-------------------|-------------|
| 57-01 | `consolidation_queue` table created by `init_schema` | unit | `uv run pytest tests/test_db.py -k consolidation_queue -x` | ❌ Wave 0 |
| 57-01 | `enrich_note()` AI path updates body, re-embeds, logs audit | unit | `uv run pytest tests/test_enrich.py -k test_enrich_ai -x` | ❌ Wave 0 |
| 57-01 | `enrich_note()` fallback on Ollama unavailable uses structured append | unit | `uv run pytest tests/test_enrich.py -k test_enrich_fallback -x` | ❌ Wave 0 |
| 57-02 | `merge_notes()` preserves discard frontmatter people + tags | unit | `uv run pytest tests/test_brain_health.py -k test_merge_frontmatter -x` | ❌ Wave 0 |
| 57-02 | `merge_notes()` repairs `[[discard_path]]` wiki-links in other notes | unit | `uv run pytest tests/test_brain_health.py -k test_merge_backlink -x` | ❌ Wave 0 |
| 57-02 | `merge_notes()` updates synthesis `source_notes` frontmatter | unit | `uv run pytest tests/test_brain_health.py -k test_merge_synthesis_refs -x` | ❌ Wave 0 |
| 57-03 | `sb_capture` returns `similar` hint when match >= 0.80 | unit | `uv run pytest tests/test_capture_nudges.py -k test_similar_hint -x` | ❌ Wave 0 |
| 57-03 | Capture with no matches returns no `similar` key | unit | `uv run pytest tests/test_capture_nudges.py -k test_no_similar_hint -x` | ❌ Wave 0 |
| 57-04 | `enrichment_sweep()` queues pairs 0.80-0.92, skips dismissed | unit | `uv run pytest tests/test_consolidation.py -k test_enrichment_sweep -x` | ❌ Wave 0 |
| 57-04 | `stale_review()` queues notes 90+ days old with low access | unit | `uv run pytest tests/test_consolidation.py -k test_stale_review -x` | ❌ Wave 0 |
| 57-04 | `backlink_repair()` replaces dead wiki-links using audit_log | unit | `uv run pytest tests/test_consolidation.py -k test_backlink_repair -x` | ❌ Wave 0 |
| 57-04 | `consolidate_main()` includes all 3 new steps in output | integration | `uv run pytest tests/test_consolidation.py -k test_consolidate_main_full -x` | ❌ Wave 0 |
| 57-05 | `sb_enrich` updates note body in DB and on disk | integration | `uv run pytest tests/test_mcp.py -k test_sb_enrich -x` | ❌ Wave 0 |
| 57-05 | `sb_consolidation_review` returns pending queue items | integration | `uv run pytest tests/test_mcp.py -k test_sb_consolidation_review -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_enrich.py tests/test_consolidation.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_enrich.py` — unit + integration tests for `enrich_note()`
- [ ] `tests/test_consolidation.py` — extend with: `test_enrichment_sweep`, `test_stale_review`, `test_backlink_repair`, `test_consolidate_main_full` (existing file has 4 tests only)
- [ ] `tests/test_brain_health.py` — add: `test_merge_frontmatter`, `test_merge_backlink`, `test_merge_synthesis_refs`
- [ ] `tests/test_capture_nudges.py` — add: `test_similar_hint`, `test_no_similar_hint` (file likely exists, check for test gaps)
- [ ] `tests/test_mcp.py` — add: `test_sb_enrich`, `test_sb_consolidation_review`

---

## Open Questions

1. **`capture_note()` return type for similarity hints**
   - What we know: function returns `Path`; 5+ internal callers depend on this
   - What's unclear: whether to change signature to `(Path, dict)` or put hint logic in MCP layer only
   - Recommendation: put hint logic in `sb_capture` MCP tool after `capture_note()` returns — zero signature breakage risk

2. **FTS5 trigger coverage**
   - What we know: `merge_notes()` does manual `INSERT INTO notes_fts(notes_fts) VALUES('rebuild')`; `_migrate_junction_triggers()` handles `note_tags`/`note_people` but not FTS5
   - What's unclear: whether any FTS5 triggers exist that auto-update on `UPDATE notes SET body=...`
   - Recommendation: always call manual rebuild in `enrich_note()` and upgraded `merge_notes()` — safe to call redundantly

3. **Backlink repair scope in nightly job**
   - What we know: O(N) body scan for `LIKE '%[[path]]%'` is full table scan
   - What's unclear: size of real brain at execution time; whether capping to recently-merged notes is sufficient
   - Recommendation: limit `backlink_repair()` to merges in audit_log from the last 7 days; add a cap parameter

4. **`access_count` availability for stale detection**
   - What we know: `migrate_add_access_tracking()` is in `init_schema()` (line 767 in db.py); column exists
   - What's unclear: what percentage of existing notes have `access_count > 0` (may be 0 for all old notes)
   - Recommendation: `stale_review()` should treat `access_count IS NULL OR access_count < 3` as low-access; do not require > 0

---

## Sources

### Primary (HIGH confidence)

All findings from direct source inspection (no external research required — this is a greenfield addition to an established codebase):

- `/Users/tuomasleppanen/second-brain/engine/brain_health.py` — `merge_notes()`, `smart_merge_notes()`, `get_duplicate_candidates()`, `repair_person_backlinks()`
- `/Users/tuomasleppanen/second-brain/engine/consolidate.py` — `consolidate_main()`, `synthesize_clusters()`
- `/Users/tuomasleppanen/second-brain/engine/intelligence.py` — `find_similar()`, `cluster_recent_notes()`, `check_stale_nudge()`, `_router` pattern
- `/Users/tuomasleppanen/second-brain/engine/capture.py` — `capture_note()`, `write_note_atomic()`, `update_note()`, `_spawn_background()`
- `/Users/tuomasleppanen/second-brain/engine/mcp_server.py` — `sb_capture()`, `sb_merge_confirm()`, `sb_find_stubs()`
- `/Users/tuomasleppanen/second-brain/engine/db.py` — all migration functions, `init_schema()`, `migrate_add_access_tracking()`
- `/Users/tuomasleppanen/second-brain/tests/test_consolidate.py` — fixture patterns, test structure
- `/Users/tuomasleppanen/second-brain/.planning/phases/57-memory-consolidation-and-enrichment/57-CONTEXT.md` — all locked decisions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, all existing dependencies confirmed in pyproject.toml
- Architecture patterns: HIGH — derived directly from production source code
- Pitfalls: HIGH — identified from existing code structure and LEARNINGS.md; FTS5 and embedding staleness risks confirmed by reading `merge_notes()` code

**Research date:** 2026-04-17
**Valid until:** 2026-05-17 (stable codebase, internal research — not time-sensitive)
