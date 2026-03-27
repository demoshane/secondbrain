# Phase 40: UI Feature Completeness - Research

**Researched:** 2026-03-28
**Domain:** Flask API extension — new endpoints + DB migrations
**Confidence:** HIGH

## Summary

Phase 40 is pure backend work: five groups of new/extended API endpoints that support the Visily UI redesign coming in Phase 41. All decisions are locked in CONTEXT.md. The codebase is well-established — patterns for DB migration, AI generation, path validation, SSE broadcast, and pagination are all reusable directly.

The most structurally novel element is the `person_insights` table (a separate cache table, not a notes column). Every other capability either extends an existing endpoint (`GET /projects/<path>`, `GET /meetings/<path>`, `GET /projects`) or adds a sibling endpoint alongside an existing one (`GET /actions/grouped`, `GET /intelligence/synthesis`).

All five plans touch `engine/api.py` and `engine/db.py`. This is a shared-file situation — direct (single-agent, sequential) execution is required.

**Primary recommendation:** Implement plans sequentially, one per Claude session. All plans converge on `api.py` and `db.py`. Do not parallel-spawn.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**40-01: Per-person AI Brain Insight**
- D-01: New endpoint `GET /persons/<path>/insight`
- D-02: AI via Ollama — `_router.get_adapter('public')` adapter pattern
- D-03: Content: overview summary of the person + recent activity (meetings, notes, action items)
- D-04: Cache: 24h TTL in DB. New `person_insights` table (separate from notes schema)
- D-05: Always check cache age first; if < 24h return cached; else call Ollama and update cache

**40-02: Weekly Synthesis**
- D-06: New endpoint `GET /intelligence/synthesis`
- D-07: AI-generated weekly synthesis, similar to recap but weekly scope
- D-08: Use `_router.get_adapter('public')` — consistent with `generate_recap_on_demand`
- D-09: No caching — on-demand regenerated each call

**40-03: Project status field + stats**
- D-10: Add `status TEXT NOT NULL DEFAULT 'active'` to `notes` via idempotent migration
- D-11: Valid values: `'active'`, `'paused'`, `'completed'`
- D-12: `GET /projects` response adds `status` per row
- D-13: `GET /projects/<path>` adds `status`, `related_notes_count`, `linked_meetings_count`
- D-14: New `PUT /projects/<path>/status` — validates value, updates DB, broadcasts `notes_changed` SSE

**40-04: Linked meetings + participant objects**
- D-15: `GET /projects/<path>` adds `linked_meetings: [{path, title, meeting_date}]`
- D-16: `GET /meetings/<path>` changes `participants` from `["name"]` to `[{name, path}]` — path nullable
- D-17: `POST /projects/<path>/meetings` deferred to Phase 41

**40-05: Actions grouped-by-source + Links body**
- D-18: New endpoint `GET /actions/grouped` (separate, not a query param on `/actions`)
- D-19: Response: `{"groups": [{"note_title": "...", "note_path": "...", "actions": [...]}], "total": N}`
- D-20: Same filter support as `/actions` — `done`, `assignee` query params
- D-21: Links body already returns raw markdown — no backend change needed

### Claude's Discretion
- Cache storage for person insights: separate `person_insights` table (cleaner than polluting notes schema)
- SQL for `related_notes_count`: use relationships table, count rows where source or target matches project path

### Deferred Ideas (OUT OF SCOPE)
- `POST /projects/<path>/meetings` write endpoint — deferred to Phase 41
</user_constraints>

---

## Standard Stack

No new packages required. Phase 40 is entirely within the existing stack.

### Core (already installed)
| Component | Version | Purpose |
|-----------|---------|---------|
| Flask | existing | HTTP routing |
| SQLite / sqlite3 | stdlib | DB schema, migrations, queries |
| `engine.intelligence._router` | project | Ollama adapter dispatch |
| `engine.db.init_schema` | project | Migration orchestrator |

### Key Internal Helpers (reuse as-is)
| Helper | Location | Use in Phase 40 |
|--------|----------|-----------------|
| `_resolve_note_path(note_path)` | `api.py` | All new `/<path>` endpoints |
| `store_path(abs_path)` | `api.py` | Convert abs path → DB-relative |
| `_broadcast({"type": "notes_changed"})` | `api.py` | PUT status endpoint |
| `_int_param(name, default, min, max)` | `api.py` | Pagination on grouped endpoint |
| `list_actions(conn, done, assignee, note_path)` | `intelligence.py` | Base for grouped endpoint |
| `_router.get_adapter('public')` | `intelligence.py` | Ollama calls for insight + synthesis |
| Idempotent `ALTER TABLE ADD COLUMN` | `db.py` migrate functions | status column migration |

---

## Architecture Patterns

### DB Migration Pattern (established, use exactly)
```python
def migrate_add_status_column(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add 'status' TEXT column to notes if absent."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()}
    if "status" not in cols:
        conn.execute("ALTER TABLE notes ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
        conn.commit()
```
Register in `init_schema()` at the end, before `conn.commit()`.

### New Table Migration Pattern
```python
def migrate_create_person_insights(conn: sqlite3.Connection) -> None:
    """Idempotent: create person_insights cache table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS person_insights (
            person_path  TEXT PRIMARY KEY,
            insight      TEXT NOT NULL DEFAULT '',
            generated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    conn.commit()
```

### AI Endpoint Pattern (from `POST /intelligence/recap`)
```python
@app.get("/intelligence/synthesis")
def intelligence_synthesis():
    conn = get_connection()
    try:
        from engine.intelligence import generate_weekly_synthesis
        text = generate_weekly_synthesis(conn)
        return jsonify({"synthesis": text})
    except Exception as exc:
        return jsonify({"synthesis": f"Error: {exc}"}), 500
    finally:
        conn.close()
```

The heavy lifting goes in `intelligence.py` — keep API routes thin, logic in the intelligence module. This is consistent with how `generate_recap_on_demand` is structured: route calls into intelligence module, returns string.

### 24h Cache Check Pattern (for person insight)
```python
from datetime import datetime, timedelta, timezone

row = conn.execute(
    "SELECT insight, generated_at FROM person_insights WHERE person_path=?",
    (path_str,)
).fetchone()

if row:
    generated_at = datetime.fromisoformat(row["generated_at"].replace("Z", "+00:00"))
    age = datetime.now(timezone.utc) - generated_at
    if age < timedelta(hours=24):
        return jsonify({"insight": row["insight"]})

# Regenerate...
```

**Warning:** `datetime.utcnow()` is deprecated in Python 3.12+ (noted in STATE.md F-31). Use `datetime.now(timezone.utc)` instead.

### Participant Objects Pattern (meetings endpoint change)
Current: `participants = json.loads(row["people"] or "[]")` → returns `["Alice", "Bob"]`
New: resolve each name to a path via a person note lookup:
```python
def _resolve_participant(conn, name: str) -> dict:
    row = conn.execute(
        "SELECT path FROM notes WHERE type='person' AND title=?", (name,)
    ).fetchone()
    return {"name": name, "path": row["path"] if row else None}

participants = [_resolve_participant(conn, n) for n in json.loads(row["people"] or "[]")]
```
This is a best-effort lookup inside the already-open connection — no extra round trips to disk.

### Linked Meetings SQL (project detail)
```sql
SELECT n.path, n.title, substr(n.created_at,1,10) AS meeting_date
FROM notes n
JOIN relationships r ON (r.source_path=n.path OR r.target_path=n.path)
WHERE (r.source_path=? OR r.target_path=?)
  AND n.type='meeting'
```
Bind `(project_path, project_path)` — bidirectional relationship scan, consistent with how relationships are created (`POST /relationships` uses `source_path` + `target_path`).

### Related Notes Count SQL
```sql
SELECT COUNT(*) FROM relationships
WHERE source_path=? OR target_path=?
```
Bind `(project_path, project_path)`.

### Linked Meetings Count (for `GET /projects` list)
Add as a subquery in the existing `GET /projects` SQL:
```sql
(SELECT COUNT(*) FROM notes m
 JOIN relationships r ON r.source_path=m.path OR r.target_path=m.path
 WHERE (r.source_path=n.path OR r.target_path=n.path) AND m.type='meeting')
 AS linked_meetings_count
```

### Actions Grouped Endpoint Pattern
```python
@app.get("/actions/grouped")
def get_actions_grouped():
    done = request.args.get("done", "0") == "1"
    assignee = request.args.get("assignee") or None
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        actions = list_actions(conn, done=done, assignee=assignee)
    finally:
        conn.close()
    # Group in Python — simpler than GROUP BY with JSON aggregation
    from collections import defaultdict
    groups_map = defaultdict(list)
    note_titles = {}
    for a in actions:
        np = a["note_path"]
        groups_map[np].append(a)
        # Title lookup deferred to separate pass or embedded in list_actions
    groups = [
        {"note_path": np, "note_title": note_titles.get(np, np), "actions": items}
        for np, items in groups_map.items()
    ]
    return jsonify({"groups": groups, "total": len(actions)})
```

**Note:** `list_actions` doesn't return `note_title`. Two options: (a) join titles in a separate query after grouping, or (b) extend `list_actions` to accept a `with_title=True` kwarg that joins `notes.title`. Option (b) keeps it clean and reusable. Planner should specify.

### Status Validation Pattern
```python
VALID_STATUSES = {"active", "paused", "completed"}

@app.put("/projects/<path:note_path>/status")
def update_project_status(note_path):
    data = request.get_json(force=True) or {}
    status = data.get("status", "")
    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400
    # ... update + broadcast
```

### Anti-Patterns to Avoid
- **Building insight generation inline in the route handler** — put it in `intelligence.py`, route stays thin
- **Using `datetime.utcnow()`** — deprecated in Python 3.12; use `datetime.now(timezone.utc)`
- **Bidirectional relationship query with UNION** — single query with `OR` is cleaner and the relationships table is small
- **Grouping actions with SQL GROUP_CONCAT** — Python grouping with `defaultdict` is more readable and maintainable given Python pagination is already the project norm

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Idempotent DB migration | Custom column existence check | `PRAGMA table_info(notes)` column-set pattern (established) |
| AI routing | Direct Ollama call | `_router.get_adapter('public')` + `adapter.generate()` |
| Path validation | Custom security check | `_resolve_note_path()` — already handles traversal guard |
| SSE broadcast | New broadcast mechanism | `_broadcast({"type": "notes_changed"})` |
| Pagination | New pagination system | Python slice `actions[offset:offset+limit]` (project norm) |

---

## Common Pitfalls

### Pitfall 1: 24h Cache Comparison with Naive Datetimes
**What goes wrong:** `datetime.utcnow() - datetime.fromisoformat(stored)` raises TypeError if stored value has no timezone info, or gives wrong result if timezone is inconsistent.
**Why it happens:** SQLite stores datetimes as text; Python's `fromisoformat` behavior varies by format.
**How to avoid:** Store `generated_at` as ISO 8601 UTC (`strftime('%Y-%m-%dT%H:%M:%SZ', 'now')`) and parse with `.replace("Z", "+00:00")` before `fromisoformat`. Use `datetime.now(timezone.utc)` for the comparison side.
**Warning signs:** `TypeError: can't subtract offset-naive and offset-aware datetimes`

### Pitfall 2: Bidirectional Relationship Query Missing One Direction
**What goes wrong:** Linked meetings query only checks `source_path=project` — misses meetings where the project is the target.
**Why it happens:** Easy to overlook bidirectionality when writing SQL.
**How to avoid:** Always `WHERE (r.source_path=? OR r.target_path=?)` with the project path bound twice.

### Pitfall 3: status Migration Not Registered in init_schema
**What goes wrong:** `ALTER TABLE` never runs; `status` column absent at runtime → `OperationalError: no such column: status`.
**Why it happens:** New migration function written but not wired into `init_schema()`.
**How to avoid:** Always add new `migrate_*` calls to `init_schema()` before the final `conn.commit()`.

### Pitfall 4: Participant Lookup N+1 Inside Connection
**What goes wrong:** Opening a new connection per participant name inside the meeting endpoint.
**Why it happens:** Not noticing that `get_connection()` creates a new connection object.
**How to avoid:** Reuse the already-open connection for participant path lookups. Single `conn` for the whole request.

### Pitfall 5: Breaking Existing `/actions` Tests
**What goes wrong:** Modifying `list_actions` signature (e.g. adding `with_title` kwarg) breaks callers.
**Why it happens:** Shared helper used by tests and API.
**How to avoid:** Use `with_title=False` as default — backward compatible. Or keep `list_actions` unchanged and do a second titles query in the grouped endpoint.

### Pitfall 6: Person Type Check in Participant Lookup
**What goes wrong:** `WHERE type='person'` misses entries stored as `type='people'` (deprecated alias).
**Why it happens:** The codebase uses `PERSON_TYPES = ("person",)` after Phase 32 migration (`migrate_people_type_to_person`). However, a live DB that hasn't run that migration yet would have both.
**How to avoid:** Use `type IN ('person', 'people')` or reference `PERSON_TYPES` from `db.py`. In practice, `migrate_people_type_to_person` runs at startup so `type='person'` is safe.

---

## Code Examples

### Existing recap endpoint (model for synthesis)
```python
# Source: engine/api.py:1456
@app.post("/intelligence/recap")
def intelligence_recap():
    """On-demand recap generation. Always regenerates — no idempotency guard."""
    conn = get_connection()
    try:
        from engine.intelligence import generate_recap_on_demand
        text = generate_recap_on_demand(conn)
        return jsonify({"recap": text})
    except Exception as exc:
        return jsonify({"recap": f"Error: {exc}"}), 500
    finally:
        conn.close()
```

### Existing generate_recap_on_demand (model for generate_weekly_synthesis)
```python
# Source: engine/intelligence.py:554
def generate_recap_on_demand(conn, window_days: int | None = None) -> str:
    # ... reads config, queries notes within window_days, calls adapter.generate()
    adapter = _router.get_adapter("public", CONFIG_PATH)
    result = adapter.generate(user_content=text, system_prompt=RECAP_SYSTEM_PROMPT)
    return result
```
Weekly synthesis is the same shape — use a 7-day window, write a `SYNTHESIS_SYSTEM_PROMPT` constant, return string.

### Existing idempotent migration (model for status + person_insights)
```python
# Source: engine/db.py:153
def migrate_add_assignee_path(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add 'assignee_path' TEXT column to action_items if absent."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(action_items)").fetchall()}
    if "assignee_path" not in cols:
        conn.execute("ALTER TABLE action_items ADD COLUMN assignee_path TEXT NULL")
        conn.commit()
```

---

## Files Modified Per Plan

| Plan | Primary Files | Notes |
|------|--------------|-------|
| 40-01 | `engine/api.py`, `engine/db.py`, `engine/intelligence.py` | New endpoint + table + AI function |
| 40-02 | `engine/api.py`, `engine/intelligence.py` | New endpoint + AI function |
| 40-03 | `engine/api.py`, `engine/db.py` | Migration + extend 2 endpoints + new PUT |
| 40-04 | `engine/api.py` | Extend `GET /projects/<path>` + `GET /meetings/<path>` |
| 40-05 | `engine/api.py` | New sibling endpoint `GET /actions/grouped` |

**All 5 plans touch `engine/api.py`. Plans 40-01 and 40-03 both touch `engine/db.py`. Plans 40-01 and 40-02 both touch `engine/intelligence.py`.**

Execution strategy: direct (single-agent, sequential). Do NOT use `/gsd:execute-phase`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | none (uv run pytest) |
| Quick run command | `uv run pytest tests/test_projects.py tests/test_meetings.py tests/test_api.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Capability | Behavior | Test Type | File Target |
|------------|----------|-----------|-------------|
| 40-01 insight endpoint | GET returns cached insight if < 24h | unit | `tests/test_projects.py` or new `tests/test_people.py` |
| 40-01 insight endpoint | GET regenerates + stores when cache stale | unit | same |
| 40-01 DB migration | person_insights table created on init | unit | `tests/test_db.py` |
| 40-02 synthesis endpoint | GET returns string from adapter | unit | `tests/test_intelligence.py` |
| 40-03 status migration | status column added to notes | unit | `tests/test_db.py` |
| 40-03 status update | PUT /projects/<path>/status 200 + SSE | unit | `tests/test_projects.py` |
| 40-03 status validation | PUT with invalid value returns 400 | unit | `tests/test_projects.py` |
| 40-03 project detail | response includes status + counts | unit | `tests/test_projects.py` |
| 40-04 linked meetings | GET /projects/<path> includes linked_meetings | unit | `tests/test_projects.py` |
| 40-04 participant objects | GET /meetings/<path> participants are [{name, path}] | unit | `tests/test_meetings.py` |
| 40-05 grouped actions | GET /actions/grouped returns groups shape | unit | `tests/test_api.py` |
| 40-05 grouped filters | done/assignee params filter correctly | unit | `tests/test_api.py` |

### Sampling Rate
- Per task commit: `uv run pytest tests/test_projects.py tests/test_meetings.py -x -q`
- Per plan: `uv run pytest tests/ -q`
- Phase gate: full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_projects.py` — add tests for status field, linked meetings, status PUT endpoint (file exists, needs new test cases)
- [ ] `tests/test_meetings.py` — add test for participant objects shape (file exists if test_meetings.py exists — confirm)
- No new test files required; extend existing files

---

## Environment Availability

Step 2.6: SKIPPED — phase is code/API changes only, no external CLI tools or services beyond Ollama (already in use by existing intelligence features).

---

## Open Questions

1. **Note title in `GET /actions/grouped`**
   - What we know: `list_actions()` returns `note_path` but not `note_title`
   - What's unclear: whether to extend `list_actions(with_title=True)` or do a separate title lookup pass
   - Recommendation: Extend `list_actions` with `with_title: bool = False` kwarg. Cleaner and reusable. Backward-compatible default.

2. **Person insight system prompt**
   - What we know: D-03 specifies content (overview + meetings + notes + action items); format not locked
   - What's unclear: tone/structure of insight output
   - Recommendation: Model on `RECAP_ENTITY_SYSTEM_PROMPT` in intelligence.py; narrative + open action items. Define a `PERSON_INSIGHT_SYSTEM_PROMPT` constant in `intelligence.py`.

3. **`GET /projects` — should it include `linked_meetings_count` in the list response?**
   - CONTEXT.md D-13 specifies `linked_meetings_count` on the detail endpoint
   - CONTEXT.md Specifics section says: "`linked_meetings_count` in project list (`GET /projects`) can be a subquery COUNT for efficiency"
   - Recommendation: Include it in both list and detail for UI completeness. Subquery in list SQL.

---

## Sources

### Primary (HIGH confidence)
- Direct read of `engine/api.py` (lines 388–471, 752–770, 1456–1467, 1571–1588) — existing patterns
- Direct read of `engine/db.py` (full schema + all migration functions) — migration conventions
- Direct read of `engine/intelligence.py` (lines 1–620) — AI adapter pattern, `generate_recap_on_demand`
- Direct read of `.planning/phases/40-ui-feature-completeness/40-CONTEXT.md` — all decisions locked

### Secondary (MEDIUM confidence)
- `tests/test_projects.py` — confirms existing test patterns for extension
- `.planning/STATE.md` decisions log — confirmed `PERSON_TYPES` canonical values, Phase 32 path migration status

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all existing helpers
- Architecture patterns: HIGH — extracted directly from live codebase
- Pitfalls: HIGH — derived from actual code inspection and known project decisions in STATE.md
- Migration patterns: HIGH — exact same pattern used 10+ times in db.py

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable codebase, no fast-moving deps)
