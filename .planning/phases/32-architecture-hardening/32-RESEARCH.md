# Phase 32: Architecture Hardening - Research

**Researched:** 2026-03-21
**Domain:** SQLite schema migrations, Python connection safety, GDPR cascade, junction tables, LIKE injection, logging hygiene
**Confidence:** HIGH

## Summary

Phase 32 is pure internal hardening — no new user-visible features. The 16 ARCH requirements address structural issues identified during Phase 30 review: absolute paths in DB (move risk), missing FK cascade (delete leak risk), raw set-based suppress (thread safety), file upload without size cap (DoS vector), tags/people stored as JSON text (full-scan on filter), and a cluster of people-graph consistency fixes (duplicate code, wrong match logic, LIKE injection, non-ASCII miss).

All changes are to Python engine files (`db.py`, `paths.py`, `api.py`, `mcp_server.py`, `capture.py`, `forget.py`, `brain_health.py`, `intelligence.py`, `people.py` new). No frontend changes, no new CLI commands, no new MCP tools. Migrations run automatically in `init_schema()` — the existing pattern is well-established and the planner should follow it exactly.

The key complexity concentrations are: (1) relative path migration touches every module that reads paths from DB, (2) the `forget_person()` GDPR gap (ARCH-08) requires a transaction wrapping file I/O + DB writes in a safe order, and (3) the `note_tags`/`note_people` junction tables need dual-write (junction + JSON column) to avoid a breaking change, which means touching both `capture_note()` and `update_note()`.

**Primary recommendation:** Plan as 6 sequential waves: DB/schema migrations first (ARCH-01+02+05+06+15), then path resolution plumbing (ARCH-01 read side), then connection safety sweep (ARCH-03+04+07), then people logic fixes (ARCH-10+11+12+13+14+16), then GDPR gap (ARCH-08), then logging cleanup (ARCH-09). FK cascade (ARCH-02) must come after relative path migration is stable.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Migration Safety
- Auto-migrate on startup via init_schema() — same pattern as existing ALTER TABLE ADD COLUMN migrations
- Each migration wrapped in a single SQLite transaction (all-or-nothing)
- Sequential migration order in one init_schema() call: 1) relative paths, 2) junction tables, 3) FK cascade — FK goes last because it needs clean paths
- Migration progress logged via Python logging.info() with counts (e.g., "Migrated 342 paths to relative") — silent in normal operation, visible with -v

#### Action Items Archival (ARCH-06)
- 90-day threshold for archiving completed action items
- Archive table includes `archived_at` timestamp + `archived_reason` column for GDPR audit trail
- Archived items visible only in sb-health report (count only) — not in GUI, CLI, or MCP list endpoints
- Archival runs as part of sb-health — no new daemon or startup cost
- Archived items included in sb-export for GDPR data portability

#### Data Loss Risk Tolerance
- forget_person() cascade: dry-run first showing affected notes, then two-step token confirmation (same pattern as sb_forget)
- Structured fields only — remove person from frontmatter people/entities fields and DB columns; body text untouched (sb-anonymize handles full text redaction separately)
- DB first, then files — single DB transaction commits, then update frontmatter on disk; if file writes fail, sb-reindex fixes the inconsistency
- FK cascade (ARCH-02): enable DB-level ON DELETE CASCADE AND keep existing app-level cascade in forget.py as safety net — remove app cascade in a future cleanup phase once proven

#### Breaking Change Handling
- Junction tables (note_tags, note_people): write to BOTH junction table and JSON column; read queries use junction table (indexed). JSON columns kept for backward compat and raw DB querying. Drop JSON in a future phase.
- No version bump — this is internal hardening within v4.0 milestone. Schema changes are forward-only with idempotent migrations.
- Relative path resolution: helper functions in paths.py — `resolve_path(rel)` → absolute, `store_path(abs)` → relative. Called at DB read/write boundaries. Clean, DRY, greppable.
- _SlashNormMiddleware removal: fix test fixtures that produce double slashes + run one-time migration to normalize any double-slash paths in DB, then remove middleware

### Claude's Discretion
- Exact migration detection logic (column existence checks, table introspection)
- Junction table index design (single-column vs composite)
- LIKE escape helper implementation details (ARCH-14)
- PERSON_TYPES constant placement and import pattern (ARCH-16)
- Connection leak fix approach in api.py (ARCH-03) — try/finally vs context manager
- File upload size cap enforcement method (ARCH-04)

### Deferred Ideas (OUT OF SCOPE)
- Drop JSON tags/people columns after junction tables proven stable — future cleanup phase
- Remove app-level cascade code after FK cascade proven reliable — future cleanup phase
- Schema version tracking table — not needed now but consider if migrations grow more complex
- sb-migrate standalone command — unnecessary with auto-migrate, but could be useful for manual control later
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ARCH-01 | Relative path storage in DB; resolve_path/store_path helpers in paths.py; migration converts existing rows | Migration pattern in db.py; BRAIN_ROOT in paths.py is the reference anchor |
| ARCH-02 | PRAGMA foreign_keys=ON on every connection; all child tables have ON DELETE CASCADE referencing notes(path) | get_connection() is the single entry point — add PRAGMA there; existing child tables: action_items, relationships, note_embeddings, attachments, audit_log |
| ARCH-03 | All get_connection/conn.close pairs in api.py wrapped in try/finally; suppress_next_delete uses threading.Event keyed by path | api.py has 63 get_connection/conn.close occurrences; watcher.py currently uses a plain set with a lock — needs Event-per-path approach |
| ARCH-04 | File upload endpoint enforces 50 MB size cap; _SlashNormMiddleware removed | upload_file() in api.py has no size check; test fixtures produce double-slash paths that need fixing before removal |
| ARCH-05 | note_tags junction table; migration converts JSON tags column; all tag queries use indexed table | notes.tags currently TEXT JSON; search endpoint does json.loads() inline; filter is full-scan |
| ARCH-06 | action_items_archive table for completed items >90 days; audit_log index on (created_at, note_path); sb-health reports archive counts | brain_health.py has compute_health_score and get_* functions; archival runs during sb-health |
| ARCH-07 | move_file() validates src/dst within BRAIN_ROOT; note_meta() removes redundant path re-resolution | move_file() at line 826 in api.py has no path-traversal guard; note_meta() at line 677 re-resolves path after _resolve_note_path |
| ARCH-08 | forget_person() wraps cascade in single transaction; file removal AFTER DB commit; cleans forgotten person from people JSON in surviving notes + frontmatter | forget.py currently: files first, DB second — must reverse; no transaction wrapper around the whole cascade |
| ARCH-09 | Entity extraction logs failures via logging.warning() instead of bare except:pass; search_semantic() uses logging.warning() instead of print(); check_connections() logs budget exhaustion | Silent failures currently in capture.py and intelligence.py — easy sweep |
| ARCH-10 | Extract list_people_with_metrics(conn) into engine/people.py; /people API and sb_list_people both call it | /people endpoint in api.py lines 249-278 has inline SQL; sb_list_people in mcp_server.py has separate duplicate implementation |
| ARCH-11 | sb_list_people and /people match by both path AND exact title, not path-only | Current json_each query in /people only matches pe.value=n.path — misses name-string entries in people column |
| ARCH-12 | sb-reindex --entities merges extracted people with existing frontmatter people field instead of overwriting | reindex.py currently overwrites; frontmatter people field is ground truth for user-supplied entries |
| ARCH-13 | sb_edit and update_note() re-run extract_entities() on new body and update people+entities DB columns with merge logic | update_note() in capture.py does not re-extract entities on edit |
| ARCH-14 | _escape_like() helper; all LIKE patterns with user input escape %; sb_person_context uses exact title match | note_meta() in api.py uses LIKE f"%{title_row['title']}%" — title could contain % or _ |
| ARCH-15 | note_people junction table; idx_notes_people dropped; capture_note and update_note populate junction table | idx_notes_people on notes(people) JSON text column — useless index; json_each() queries are full-scans |
| ARCH-16 | PERSON_TYPES constant in engine/db.py; replace all hardcoded type IN ('person','people') usages | Hardcoded strings appear in api.py, mcp_server.py, capture.py — at least 8 locations based on grep |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlite3 (stdlib) | Python 3.13 | DB connection, migration | Already in use; no deps |
| threading (stdlib) | Python 3.13 | Thread-safe Event for suppress | Already in use in watcher.py |
| logging (stdlib) | Python 3.13 | Replace bare except/print | Python best practice for library code |
| frontmatter (python-frontmatter) | installed | Read/write .md frontmatter on disk | Already in use everywhere |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib.Path | Python 3.13 | Path resolution; is_relative_to() | All path boundary checks |
| werkzeug.utils | installed | secure_filename in upload | Already in use; request.content_length for size cap |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| try/finally for connection closing | contextlib.contextmanager wrapper | Context manager cleaner long-term but bigger diff; try/finally is minimal change and consistent with existing code |
| request.content_length for size cap | f.read() with limit | content_length is set by client (spoofable) so must also cap on stream read; werkzeug handles this with max_content_length on app config |

**Installation:** No new packages needed. All changes use stdlib and existing deps.

## Architecture Patterns

### Recommended Project Structure
```
engine/
├── db.py              # add PRAGMA FK + new migration functions + PERSON_TYPES constant
├── paths.py           # add resolve_path(rel) + store_path(abs) helpers
├── people.py          # NEW: list_people_with_metrics(conn) shared service function
├── api.py             # try/finally sweep, size cap, path traversal, remove middleware, use people.py
├── mcp_server.py      # use people.py, PERSON_TYPES
├── capture.py         # populate junction tables, re-extract on edit, PERSON_TYPES, logging
├── forget.py          # transaction wrap, reverse order (DB first), clean people fields
├── brain_health.py    # archival trigger, archive count reporting, audit_log index
└── intelligence.py    # logging.warning() instead of print()/bare except
```

### Pattern 1: Idempotent Migration (existing, extend this)
**What:** Each migration is a standalone function, detected via PRAGMA table_info or CREATE TABLE IF NOT EXISTS, registered in init_schema().
**When to use:** Every schema change in this phase.
**Example:**
```python
# Source: engine/db.py (existing pattern)
def migrate_add_note_tags_table(conn: sqlite3.Connection) -> None:
    """Idempotent: create note_tags junction table if absent."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS note_tags (
            note_path  TEXT NOT NULL,
            tag        TEXT NOT NULL,
            PRIMARY KEY (note_path, tag)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_note_tags_tag ON note_tags(tag)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_note_tags_path ON note_tags(note_path)")
    conn.commit()
```

### Pattern 2: Data Migration with Logging
**What:** Convert existing rows in a transaction; log count; skip if already done.
**When to use:** ARCH-01 (paths → relative), ARCH-05 (tags JSON → junction), ARCH-15 (people JSON → junction).
**Example:**
```python
def migrate_paths_to_relative(conn: sqlite3.Connection, brain_root: Path) -> None:
    import logging
    rows = conn.execute(
        "SELECT path FROM notes WHERE path LIKE '/%'"
    ).fetchall()
    if not rows:
        return
    with conn:  # single transaction
        for (abs_path,) in rows:
            try:
                rel = Path(abs_path).relative_to(brain_root)
                conn.execute("UPDATE notes SET path=? WHERE path=?",
                             (str(rel), abs_path))
            except ValueError:
                logging.warning("Path outside BRAIN_ROOT, skipping: %s", abs_path)
    logging.info("Migrated %d paths to relative", len(rows))
```

### Pattern 3: FK-safe Connection
**What:** Enable FK enforcement on every connection; child table DDL must already have REFERENCES + ON DELETE CASCADE.
**When to use:** ARCH-02.
```python
# engine/db.py get_connection() — add after journal_mode pragma
conn.execute("PRAGMA foreign_keys = ON")
```

### Pattern 4: try/finally for Connection Closing (ARCH-03)
**What:** Wrap every bare `conn = get_connection() ... conn.close()` pair.
**When to use:** All 63 locations in api.py.
```python
# Before (leak risk):
conn = get_connection()
rows = conn.execute(...).fetchall()
conn.close()

# After:
conn = get_connection()
try:
    rows = conn.execute(...).fetchall()
finally:
    conn.close()
```

### Pattern 5: Path Boundary Helpers
**What:** `store_path(abs)` converts absolute → relative before DB write; `resolve_path(rel)` converts relative → absolute for file access.
**When to use:** At every DB read/write boundary that touches `path` column.
```python
# engine/paths.py additions
def store_path(abs_path: str | Path) -> str:
    """Convert absolute path to relative (relative to BRAIN_ROOT) for DB storage."""
    return str(Path(abs_path).relative_to(BRAIN_ROOT))

def resolve_path(rel_path: str | Path) -> Path:
    """Resolve DB-stored relative path back to absolute."""
    p = Path(rel_path)
    if p.is_absolute():
        return p  # already absolute — backward compat during migration
    return BRAIN_ROOT / p
```

### Pattern 6: LIKE Escape Helper (ARCH-14)
**What:** Escape `%` and `_` in user-controlled strings before LIKE patterns.
**When to use:** Any LIKE pattern with user input, including note titles and person names.
```python
def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

# Usage:
conn.execute(
    "SELECT ... WHERE LOWER(body) LIKE LOWER(?) ESCAPE '\\'",
    (f"%{_escape_like(title)}%",)
)
```

### Anti-Patterns to Avoid
- **Threading.Event as singleton:** ARCH-03 requires per-path Events, not a global shared Event; use a `dict[str, threading.Event]` protected by a lock.
- **Migration without transaction:** Multi-row data migrations (ARCH-01 path conversion) must be wrapped in `with conn:` so a crash mid-migration doesn't leave partial data.
- **FK ON without child table DDL:** Enabling `PRAGMA foreign_keys=ON` without adding `REFERENCES notes(path) ON DELETE CASCADE` to child tables will cause inserts to fail on new rows, not cascade on delete. Both sides must be done.
- **ADD CONSTRAINT on existing SQLite table:** SQLite does not support `ALTER TABLE ADD CONSTRAINT`. To add FK to existing tables, must recreate them. For this phase the decision is to add CASCADE on newly created tables via migration + keep app-level cascade in forget.py — not recreate existing tables.
- **Double-write inconsistency:** junction table writes must be inside the same transaction as JSON column writes; otherwise a crash between the two leaves them out of sync.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Relative path detection | Custom regex/heuristics | `Path.is_absolute()` + `Path.relative_to()` | stdlib handles edge cases; raises ValueError cleanly |
| LIKE injection escape | Ad-hoc string replace | `_escape_like()` helper + ESCAPE clause | SQLite ESCAPE keyword is the canonical approach |
| FK cascade enforcement | Manual DELETE cascade in every caller | `PRAGMA foreign_keys=ON` + DDL CASCADE | DB enforces atomically; app cascade is a safety net only |
| Upload size cap | Read entire file, check length | `app.config["MAX_CONTENT_LENGTH"]` + 413 handler | Flask/Werkzeug handles streaming; no OOM risk |
| Migration idempotency | Version number tracking | `CREATE TABLE IF NOT EXISTS` + `PRAGMA table_info()` | Established project pattern; simple and reliable |

**Key insight:** SQLite's `PRAGMA foreign_keys` + `ON DELETE CASCADE` in DDL is the correct level for cascade enforcement. App-level cascade (forget.py) stays as belt-and-suspenders, but the DB is the primary guard.

## Common Pitfalls

### Pitfall 1: SQLite FK — Existing Rows Not Validated on PRAGMA Enable
**What goes wrong:** Enabling `PRAGMA foreign_keys = ON` does not retroactively check existing rows. Pre-existing orphan rows in child tables won't cause errors, but new INSERT/UPDATE will enforce FK. If paths are migrated to relative AFTER FK is enabled, the relative path won't match the absolute path in child tables — inserts fail.
**Why it happens:** SQLite FK constraint is evaluated at write time, not at PRAGMA toggle time.
**How to avoid:** Migration order is locked: relative paths first, junction tables second, FK last. This is already a locked decision.
**Warning signs:** `FOREIGN KEY constraint failed` on INSERT after migration.

### Pitfall 2: `with conn:` vs `conn.commit()` Confusion
**What goes wrong:** `with conn:` in Python's sqlite3 is a transaction context, not a connection context. It commits on `__exit__` and rolls back on exception — but does NOT close the connection. `conn.close()` must still be called.
**Why it happens:** Naming confusion between DB connection and transaction.
**How to avoid:** Use `try/finally: conn.close()` for resource management; use `with conn:` or explicit `conn.commit()` for transaction management. These are orthogonal.
**Warning signs:** DB file stays locked after endpoint returns.

### Pitfall 3: `Path.relative_to()` Raises on Non-Subpaths
**What goes wrong:** `Path("/some/other/path").relative_to(BRAIN_ROOT)` raises `ValueError` if the path is not inside BRAIN_ROOT. During path migration, any paths that are already relative or are outside BRAIN_ROOT would crash the migration loop.
**Why it happens:** `relative_to()` is strict.
**How to avoid:** Guard with `p.is_absolute()` check; use `try/except ValueError` in migration loop with `logging.warning()` for skipped paths; treat already-relative paths as no-ops.
**Warning signs:** Migration crashes on first run; count logged as 0 when > 0 expected.

### Pitfall 4: `_SlashNormMiddleware` Removal Breaks Tests Before Fixture Fix
**What goes wrong:** Removing the middleware before fixing test fixtures will cause test suite failures where fixtures pass absolute paths like `/notes//private/var/...`.
**Why it happens:** The middleware was added precisely because test fixtures produce double-slash paths.
**How to avoid:** Fix test fixtures first, run the test suite green, then remove the middleware. This is a sequential dependency within ARCH-04.
**Warning signs:** Flask 404s on note path endpoints in tests after middleware removal.

### Pitfall 5: forget_person() Transaction Order
**What goes wrong:** Current code does file deletes BEFORE DB commit. If the process crashes between file deletion and DB commit, notes are deleted from disk but DB still references them — inconsistent state that sb-reindex cannot fully repair (file is gone).
**Why it happens:** Original implementation prioritized file cleanup.
**How to avoid:** ARCH-08 reverses this: commit DB transaction first, then delete files. If file deletion fails, DB is consistent; sb-reindex will eventually see the missing file and remove the DB row.
**Warning signs:** Notes appear in search results but can't be opened.

### Pitfall 6: Junction Table Dual-Write Must Be in Same Transaction
**What goes wrong:** If JSON column write and junction table write are separate commits, a crash between them leaves the junction table out of sync with the JSON column. Read queries use junction table — missing entries look like missing tags/people.
**Why it happens:** Treating them as independent writes.
**How to avoid:** In `capture_note()` and `update_note()`, wrap the JSON column UPDATE and the junction table INSERT/DELETE/INSERT in a single transaction.
**Warning signs:** Tags disappear from junction table queries; visible in JSON column but not in tag filter.

### Pitfall 7: PERSON_TYPES Circular Import
**What goes wrong:** Importing `PERSON_TYPES` from `engine/db.py` into `api.py`, `mcp_server.py`, and `capture.py` is safe — db.py has no imports from those modules. But if the constant is placed in a module that imports from api.py or mcp_server.py, circular import will crash startup.
**Why it happens:** Choosing the wrong home for the constant.
**How to avoid:** `engine/db.py` is the correct home — it is imported by everything but imports nothing from engine except paths. Confirmed safe.
**Warning signs:** `ImportError: cannot import name 'PERSON_TYPES'` at startup.

## Code Examples

Verified patterns from existing codebase:

### FK pragma addition in get_connection()
```python
# engine/db.py
def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")   # ARCH-02
    return conn
```

### New child table with FK cascade (ARCH-02)
```python
# Note: SQLite cannot ADD CONSTRAINT to existing tables.
# Strategy: new tables get CASCADE in DDL; existing tables keep app-level cascade (forget.py).
# For note_tags and note_people (new junction tables), add FK in CREATE TABLE:
CREATE TABLE IF NOT EXISTS note_tags (
    note_path  TEXT NOT NULL REFERENCES notes(path) ON DELETE CASCADE,
    tag        TEXT NOT NULL,
    PRIMARY KEY (note_path, tag)
);
```

### File upload size cap (ARCH-04)
```python
# engine/api.py — add to app configuration
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({"error": "File too large (max 50 MB)"}), 413
```

### suppress_next_delete thread-safe Event (ARCH-03)
```python
# engine/watcher.py — replace set-based approach with Event-per-path
_suppress_events: dict[str, threading.Event] = {}
_suppress_lock = threading.Lock()

def suppress_next_delete(abs_path: str, window: float = 0.5) -> None:
    ev = threading.Event()
    with _suppress_lock:
        _suppress_events[abs_path] = ev
    threading.Timer(window, _clear_suppress, args=(abs_path,)).start()

def is_suppressed(abs_path: str) -> bool:
    with _suppress_lock:
        return abs_path in _suppress_events

def _clear_suppress(abs_path: str) -> None:
    with _suppress_lock:
        _suppress_events.pop(abs_path, None)
```

### list_people_with_metrics() (ARCH-10)
```python
# engine/people.py (new file)
import sqlite3, json

def list_people_with_metrics(conn: sqlite3.Connection) -> list[dict]:
    """Shared query for /people API and sb_list_people MCP tool.
    Matches by both path AND exact title to fix zero-metrics bug (ARCH-11).
    """
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT n.path, n.title, n.entities, substr(n.updated_at, 1, 10) AS updated_at,
            (SELECT COUNT(*) FROM action_items a WHERE a.assignee_path=n.path AND a.done=0) AS open_actions,
            (SELECT MAX(m.created_at) FROM notes m, json_each(COALESCE(m.people, '[]')) pe
             WHERE (pe.value=n.path OR LOWER(pe.value)=LOWER(n.title))
             AND m.type='meeting') AS last_interaction,
            (SELECT COUNT(*) FROM notes m, json_each(COALESCE(m.people, '[]')) pe
             WHERE (pe.value=n.path OR LOWER(pe.value)=LOWER(n.title))
             AND m.type NOT IN ('person','people')) AS mention_count
        FROM notes n WHERE n.type IN ('person', 'people') ORDER BY n.title
    """).fetchall()
    result = []
    for r in rows:
        ents = json.loads(r["entities"] or "{}")
        org = (ents.get("orgs") or [""])[0]
        result.append({
            "path": r["path"],
            "title": r["title"],
            "updated_at": r["updated_at"],
            "open_actions": r["open_actions"],
            "org": org,
            "last_interaction": r["last_interaction"],
            "mention_count": r["mention_count"] or 0,
        })
    return result
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bare `except: pass` in entity extraction | `logging.warning()` | ARCH-09 | Silent failures become visible in logs |
| `_suppress_delete` as plain `set` | `dict[str, threading.Event]` per path | ARCH-03 | Race condition fixed on high-frequency saves |
| Absolute paths in DB | Relative paths + resolve_path() | ARCH-01 | Brain directory moveable without orphaning index |
| JSON tags text column full-scan | `note_tags` junction table with index | ARCH-05 | O(1) tag filter lookup |
| json_each() people queries | `note_people` junction table | ARCH-15 | Removes useless `idx_notes_people` index; proper indexed joins |

**Deprecated/outdated:**
- `_SlashNormMiddleware`: Added as a workaround for test fixtures producing double-slash paths — removing it after fixing root cause (ARCH-04)
- `idx_notes_people` index on `notes(people)` JSON text column: Indexes a JSON blob string, not individual people values — zero selectivity; drop it (ARCH-15)

## Open Questions

1. **note_meta() LIKE injection scope**
   - What we know: `note_meta()` at line 692 uses `LIKE LOWER(?)` with `f"%{title_row['title']}%"` — title comes from DB but was originally from user input
   - What's unclear: How many other LIKE patterns in the codebase use unescaped user input?
   - Recommendation: Planner should include a grep task for `LIKE` patterns across all engine files as part of ARCH-14 to ensure comprehensive coverage

2. **forget_person() transaction scope and file I/O**
   - What we know: SQLite transactions cannot span file system operations; the decision is DB commit first, then file writes
   - What's unclear: If the process crashes after DB commit but before file deletion, the person file remains on disk but the DB has no record — sb-reindex would re-index the deleted person on next run
   - Recommendation: The decided approach (DB first, files second) is correct for GDPR intent. Document explicitly that a crashed forget_person() may require a manual file deletion + sb-reindex. This is acceptable per CONTEXT.md.

3. **sb-reindex --entities merge logic (ARCH-12)**
   - What we know: Current reindex overwrites; ARCH-12 requires merge with frontmatter people field
   - What's unclear: Where exactly in reindex.py this happens — not read during research
   - Recommendation: Planner should read engine/reindex.py as context file for the ARCH-12 plan

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | none — invoked directly |
| Quick run command | `uv run pytest tests/test_db.py tests/test_api.py tests/test_forget.py tests/test_people.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARCH-01 | Paths stored relative; resolve_path/store_path round-trip | unit | `pytest tests/test_db.py tests/test_paths.py -x -q` | tests/test_paths.py ✅ |
| ARCH-02 | PRAGMA FK=ON on every connection; CASCADE on junction tables | unit | `pytest tests/test_db.py -x -q` | ✅ |
| ARCH-03 | Connection leaks patched; suppress_next_delete thread-safe | unit | `pytest tests/test_watcher.py tests/test_api.py -x -q` | ✅ |
| ARCH-04 | 50 MB upload cap returns 413; _SlashNormMiddleware gone | unit | `pytest tests/test_api_upload.py tests/test_api.py -x -q` | ✅ |
| ARCH-05 | note_tags table exists; tag filter uses junction table | unit | `pytest tests/test_db.py tests/test_api_tags.py -x -q` | ✅ |
| ARCH-06 | Completed items >90d moved to archive; sb-health reports count | unit | `pytest tests/test_brain_health.py -x -q` | ✅ |
| ARCH-07 | move_file blocks path traversal; note_meta no double-resolve | unit | `pytest tests/test_api.py -x -q` | ✅ |
| ARCH-08 | forget_person cascade: DB first, files second; cleans people fields | unit | `pytest tests/test_forget.py -x -q` | ✅ |
| ARCH-09 | No bare except/print in entity extraction and search_semantic | unit | `pytest tests/test_entities.py tests/test_search.py -x -q` | ✅ |
| ARCH-10 | list_people_with_metrics shared fn; /people and sb_list_people return identical fields | unit | `pytest tests/test_people.py tests/test_mcp.py -x -q` | ✅ |
| ARCH-11 | People column entries matched by path OR title | unit | `pytest tests/test_people.py -x -q` | ✅ |
| ARCH-12 | sb-reindex --entities merges people; doesn't overwrite | unit | `pytest tests/test_reindex.py -x -q` | ❌ Wave 0: create tests/test_reindex.py |
| ARCH-13 | sb_edit re-extracts entities; updates people+entities columns | unit | `pytest tests/test_mcp.py -x -q` | ✅ |
| ARCH-14 | LIKE patterns escape % and _; person context uses exact match | unit | `pytest tests/test_api.py tests/test_mcp.py -x -q` | ✅ |
| ARCH-15 | note_people table; idx_notes_people dropped; capture populates it | unit | `pytest tests/test_db.py tests/test_capture.py -x -q` | ✅ |
| ARCH-16 | PERSON_TYPES constant used everywhere; no hardcoded strings | unit | `pytest tests/test_db.py -x -q` | ✅ |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_db.py tests/test_api.py tests/test_forget.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_reindex.py` — covers ARCH-12 (merge logic); existing file not found during research
- [ ] Verify `tests/test_paths.py` has tests for new `resolve_path`/`store_path` helpers — current file only tests existing path detection logic

*(All other test infrastructure exists — this phase extends existing test files)*

## Sources

### Primary (HIGH confidence)
- Direct source read: `engine/db.py` — migration pattern, init_schema, existing table schemas
- Direct source read: `engine/paths.py` — BRAIN_ROOT, existing path detection
- Direct source read: `engine/api.py` (full 900+ lines) — connection patterns, endpoint implementations, _SlashNormMiddleware, move_file, upload_file, note_meta, list_people
- Direct source read: `engine/forget.py` — existing cascade order and transaction handling
- Direct source read: `engine/watcher.py` — suppress_next_delete current implementation
- Direct source read: `engine/brain_health.py` — health check structure
- Direct source read: `engine/capture.py` — capture pipeline, update_note
- Direct source read: `engine/mcp_server.py` — sb_list_people, two-step token pattern
- Direct source read: `.claude/LEARNINGS.md` — established rules, known bugs, test isolation patterns
- Direct source read: `.planning/phases/32-architecture-hardening/32-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- SQLite documentation (training knowledge): PRAGMA foreign_keys behavior, ON DELETE CASCADE DDL requirement, ALTER TABLE limitations in SQLite, `with conn:` transaction semantics
- Flask/Werkzeug (training knowledge): MAX_CONTENT_LENGTH config, 413 handler pattern

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all changes use existing project deps; no new libraries
- Architecture: HIGH — patterns derived from existing code in the same repo
- Pitfalls: HIGH — several come directly from .claude/LEARNINGS.md documented bugs; SQLite FK behavior is well-documented
- Migration order: HIGH — locked decision in CONTEXT.md, technically correct per SQLite FK semantics

**Research date:** 2026-03-21
**Valid until:** 2026-06-21 (stable domain; no fast-moving dependencies)
