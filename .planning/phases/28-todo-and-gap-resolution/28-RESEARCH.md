# Phase 28: TODO & Gap Resolution - Research

**Researched:** 2026-03-19
**Domain:** Python/Flask backend (MCP tools, API), React/TypeScript frontend (Playwright fixes), SQLite
**Confidence:** HIGH

---

## Summary

Phase 28 is a gap-closure and feature-addition phase with two distinct halves:

**Half 1 — New MCP tools (plans 28-01 through 28-06):** The ROADMAP defines six new capabilities that were deferred from previous phases. These are net-new additions: title-only dedup fallback, `sb_capture_smart`, `sb_tag`, `sb_link`/`sb_unlink`, `sb_remind`, and `sb_person_context`. All use patterns already established in `engine/mcp_server.py` and `engine/api.py`.

**Half 2 — Playwright regression fixes (plan 28-07):** 9 Playwright GUI tests fail when the full test suite is run together (all pass in isolation). The failure mode is session-scoped fixture contamination — subsequent test files clobber `engine.db.DB_PATH` / `engine.paths.DB_PATH` after `gui_brain` sets them, so when `test_gui.py` runs last, the Flask server is no longer pointed at the test DB. The fix is improving test isolation in `conftest.py`.

**No TODO comments exist in `engine/` or `frontend/src/`** — codebase is comment-clean. All gaps are from the ROADMAP's explicit 28-xx plan list plus the known test failures.

**Primary recommendation:** Implement the 7 plans in ROADMAP order. Start with the Playwright fix (28-07) as a standalone plan since it unblocks CI confidence, then tackle MCP tools 28-01 through 28-06.

---

## Audit Results

### Open TODO Comments in Code

**None found.** Grep of `engine/*.py` and `frontend/src/*.tsx` for TODO/FIXME/HACK/XXX returned zero matches.

### Deferred Items from ROADMAP (explicit Phase 28 plan list)

| Plan | Item | Source |
|------|------|--------|
| 28-01 | Title-only dedup for large captures (fix MCP timeout on large bodies) | ROADMAP Phase 28 |
| 28-02 | `sb_capture_smart`: split raw freeform content into typed note suggestions | ROADMAP Phase 28 |
| 28-03 | `sb_tag`: add/remove tags with fuzzy matching + confirm-token for new tags | ROADMAP Phase 28 |
| 28-04 | `sb_link` / `sb_unlink`: explicit directional relationships (DB-only) | ROADMAP Phase 28 |
| 28-05 | `sb_remind`: set due date + snooze on action items; overdue in recap + GUI | ROADMAP Phase 28 |
| 28-06 | `sb_person_context`: one-call full context dump for a person | ROADMAP Phase 28 |
| 28-07 | Fix 9 Playwright GUI test failures (People/Meetings/Projects/right-panel) | ROADMAP Phase 28 + test run |

### Items From STATE.md Pending Todos

| Item | Status |
|------|--------|
| Tag management UI (global tag panel) | Listed in STATE.md TODOs; ROADMAP does not include it in Phase 28 — OUT OF SCOPE here |
| Audit and improve context detection on capture | Listed as general TODO; Phase 28-02 (sb_capture_smart) partially addresses it |

### Known Architectural Issues (tracked for Phase 32)

The following are **intentionally deferred to Phase 32** — do not fix in Phase 28:
- DB stores absolute paths (ARCH-01)
- No FK cascade (ARCH-02)
- Tags stored as JSON TEXT (ARCH-05)
- Entity extraction misses non-ASCII names (Phase 30)

### Deferred Gap from Phase 27.8

- **Digest section on IntelligencePage** — explicitly deferred in STATE.md: `[Phase 27.8-GAP]: Digest section omitted from IntelligencePage — backend unimplemented.` This is NOT in Phase 28 plan items. Do not address here.

---

## Standard Stack

### Core (existing — no new dependencies)
| Library | Version | Purpose | Where |
|---------|---------|---------|-------|
| FastMCP | existing | All `sb_*` MCP tools | `engine/mcp_server.py` |
| Flask | existing | REST endpoints called by MCP tools | `engine/api.py` |
| SQLite `engine/db.py` | existing | DB migrations, `get_connection()` | `engine/db.py` |
| `engine/capture.py` | existing | `check_capture_dedup()`, `capture_note()` | used by MCP tools |
| `engine/intelligence.py` | existing | `list_actions()`, action item queries | used by `sb_remind`, `sb_person_context` |
| `engine/search.py` | existing | Hybrid search for `sb_capture_smart` type routing | used by new tools |
| pytest + playwright-pytest | existing | Full test suite + Playwright GUI tests | `tests/` |

### No New Dependencies
All Phase 28 work uses the existing stack. Do not introduce new packages.

---

## Architecture Patterns

### Pattern 1: Adding a New MCP Tool
All tools follow the same structure in `engine/mcp_server.py`:

```python
# Source: engine/mcp_server.py — existing tools
@mcp.tool()
def sb_new_tool(param: str, confirm_token: str = "") -> dict:
    """Docstring used by sb_tools() for self-documentation."""
    conn = get_connection()
    try:
        # ... implementation ...
        conn.commit()
        return {"result": ...}
    except Exception as e:
        raise
    finally:
        conn.close()
```

Key rules (from STATE.md decisions):
- Destructive ops use two-step token pattern: first call returns `confirm_token`, second call with token executes
- Token expiry window is 60s (`sb_forget` pattern) or 300s (`sb_capture` pattern)
- `get_connection()` accepts optional `db_path` for test isolation
- Import `from engine.paths import BRAIN_ROOT as _BRAIN_ROOT` locally inside functions that write files (not at module level) — prevents test isolation failure

### Pattern 2: DB Migration
```python
# Source: engine/db.py — migrate_add_assignee_path pattern
def migrate_add_new_column(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add column if absent."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(action_items)")]
    if "new_column" not in cols:
        conn.execute("ALTER TABLE action_items ADD COLUMN new_column TEXT NULL")
        conn.commit()
```
Then call from `init_schema(conn)` at the bottom of that function.

### Pattern 3: Confirm-Token Gate (two-step destructive)
```python
# Source: engine/mcp_server.py sb_forget()
if not confirm_token:
    tok = _make_token()
    return {"confirm_token": tok, "message": "Call again with confirm_token='...' within 60s"}
if not _consume_token(confirm_token):
    raise ValueError("TOKEN_EXPIRED: confirm_token is invalid or has expired")
# ... execute destructive action ...
```

### Pattern 4: Test Fixture DB Isolation
Every test that calls `get_connection()` must patch both:
```python
monkeypatch.setattr(engine.db, "DB_PATH", tmp_db)
monkeypatch.setattr(engine.paths, "DB_PATH", tmp_db)
# If calling MCP capture functions also patch:
monkeypatch.setattr(engine.paths, "BRAIN_ROOT", tmp_path)
```

---

## Plan-by-Plan Technical Details

### 28-01: Title-Only Dedup (MCP Timeout Fix)

**Problem:** `check_capture_dedup()` in `capture.py` embeds `f"{title}\n{body}"`. For large notes (multi-KB body), `embed_texts()` can take > 8s, hitting the ThreadPoolExecutor timeout. On timeout it silently returns `[]` — but the delay still blocks `sb_capture`.

**Current code:** `engine/capture.py` line 63: `blobs = embed_texts([f"{title}\n{body}"])`

**Fix:** Add a `title_only` fast-path — when `len(body) > threshold` (e.g. 2000 chars), embed only the title. Title embedding is ~50 tokens vs potentially thousands for a large body. This keeps dedup meaningful for large captures without the timeout risk.

**Confidence:** HIGH — root cause confirmed in code; fix is a single-line change with an added param.

### 28-02: `sb_capture_smart`

**What it does:** Accept raw freeform text, classify it into 1-N typed note suggestions (person / meeting / project / idea / note) with inferred titles, types, and cross-links. Return suggestions; user confirms or edits before saving (does NOT save automatically on first call).

**Implementation approach:** This requires an AI classification step. Since the project has no direct Anthropic API key (uses Claude Code/MCP adapter pattern), this tool should use the existing `RouterAdapter` / model adapter pattern from `engine/adapters.py` or build a simple heuristic classifier (keyword-based) as the v1. A full AI adapter call is out of scope for this phase — use keyword/regex heuristics to segment content.

**Heuristic signals for type classification:**
- Contains "meeting", "discussed", "attendees", date patterns → `meeting`
- Contains a person name pattern + contextual words → `person`
- Contains "project", "milestone", "deadline" → `project`
- Default → `idea` or `note`

**Confidence:** MEDIUM — heuristic approach is straightforward; AI-based approach would need adapter wiring which adds complexity.

### 28-03: `sb_tag`

**What it does:** Add or remove tags on a note with fuzzy matching against existing tags (prevent "meeting" vs "meetings" proliferation). Confirm-token gate for creating a brand-new tag.

**Existing infrastructure:**
- `engine/api.py` `PUT /notes/<path>` with `tags_only=True` already saves tags via python-frontmatter + tempfile + `os.replace()` + targeted DB UPDATE
- Tags are stored as JSON TEXT in `notes.tags` column
- Fuzzy matching: use `difflib.get_close_matches()` (stdlib, no new dep)

**Token gate pattern:** If requested tag doesn't match any existing tag within `cutoff=0.8`, return `confirm_token` asking user to confirm creating new tag.

**Confidence:** HIGH — all infrastructure exists; this is primarily glue code.

### 28-04: `sb_link` / `sb_unlink`

**What it does:** Create or delete a directional relationship between two notes. DB-only — does NOT edit note body.

**Existing infrastructure:**
- `relationships` table: `(source_path TEXT, target_path TEXT, rel_type TEXT)` — confirmed in `engine/db.py`
- `rel_type` column (not `relationship_type`) — from STATE.md Phase 22 decision
- `INSERT OR IGNORE` pattern used in `engine/api.py` `create_relationship()` already drafted in Phase 27.9 RESEARCH

**Confidence:** HIGH — table exists, insert/delete pattern is trivial.

### 28-05: `sb_remind`

**What it does:** Set due date on an action item; surface overdue items in recap and GUI.

**Existing infrastructure:**
- `due_date TEXT` column already exists on `action_items` (Phase 27.2 migration `migrate_add_due_date`)
- `PUT /actions/<id>` already accepts `assignee_path` and `done` fields — extend to accept `due_date`
- `list_actions()` in `engine/intelligence.py` returns action items — extend to include `due_date` in output
- `sb_actions` MCP tool calls `list_actions()` — will auto-include `due_date` once `list_actions()` returns it
- Overdue surfacing in recap: add a check `WHERE due_date < datetime('now') AND done=0` to the recap generation

**Confidence:** HIGH — column exists; extension is additive.

### 28-06: `sb_person_context`

**What it does:** One-call full context dump for a person: person note body, all meetings they appear in, all action items assigned to or mentioning them, all notes that mention them by name.

**Existing infrastructure:**
- `GET /people/<path>` endpoint in `api.py` already returns person note with meetings, backlinks, and actions — this is the same logic
- `list_meetings()` + `get_meeting()` exist
- `note_meta()` endpoint does backlink + body-mention detection
- This MCP tool is essentially a wrapper that calls these existing functions and aggregates into one dict

**Distinction from Phase 30:** Phase 30 adds Unicode entity extraction and consolidates `people` column write-back. Phase 28's `sb_person_context` uses current infrastructure (body-mention detection fallback) and is explicitly listed in Phase 28 ROADMAP. Phase 30 improves the underlying data quality later.

**Confidence:** HIGH — all data already accessible via existing endpoints/functions.

### 28-07: Fix 9 Playwright GUI Test Failures

**Root cause identified:** The 9 tests all pass when `test_gui.py` is run alone. They fail when the full `tests/` suite runs. This is a session-scoped fixture contamination pattern:

1. `gui_brain` is session-scoped and sets `engine.db.DB_PATH` and `engine.paths.DB_PATH` to a tmp path
2. Other test files (e.g. `test_api.py`, `test_inbox.py`, `test_people.py`) have their own `client` fixtures that also patch `engine.db.DB_PATH` and `engine.paths.DB_PATH` via `monkeypatch` — but monkeypatch for session fixtures may not restore correctly between modules
3. When `test_gui.py` runs after those files in the same session, the Flask server (already started, session-scoped) may be using a different DB_PATH than the `gui_brain` fixture expects

**Evidence:** Exact same tests pass in isolation, fail with `[chromium]` parametrize suffix in full suite. The `[chromium]` suffix indicates these are the Playwright parametrized variants, not plain unit tests.

**Fix approach:** In `conftest.py`, the `live_server_url` fixture must ensure the Flask app's DB_PATH is re-anchored to `gui_brain` DB at server start time. Since Flask server is started once (session-scoped), the DB_PATH must be set permanently (not via monkeypatch which restores on teardown) for the session scope.

The current `gui_brain` fixture already sets `_paths.DB_PATH = tmp_db` and `_db.DB_PATH = tmp_db` directly (not via monkeypatch), so they should persist. The issue may be that other test fixtures using monkeypatch temporarily override and then restore to a wrong value, or that the Flask server was started before `gui_brain` ran.

**Fix options:**
1. Add an autouse session fixture that freezes DB_PATH after `gui_brain` sets it and prevents other test patches from affecting it
2. Move DB_PATH re-assignment into the Flask server thread startup (guaranteed to run after gui_brain)
3. Mark the 9 tests `xfail(strict=False)` with documented reason (minimal fix — acceptable if root cause is hard to isolate)

**Failing tests (confirmed from full suite run):**
1. `test_people_detail_opens[chromium]`
2. `test_people_detail_sections[chromium]`
3. `test_meetings_page_row_click[chromium]`
4. `test_projects_page_row_click[chromium]`
5. `test_people_tab_shows_real_content[chromium]`
6. `test_meetings_tab_shows_real_content[chromium]`
7. `test_projects_tab_shows_real_content[chromium]`
8. `test_right_panel_people_mention[chromium]`
9. `test_people_type_isolation[chromium]`

**Pattern:** All require seeded data from `gui_brain` fixture (person, meeting, project, or mention notes). The basic navigation tests that don't require seeded data pass fine.

**Confidence:** MEDIUM — root cause is clear (seeded data missing at test runtime); exact mechanism of contamination needs verification at plan execution time.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tag fuzzy matching | Custom edit-distance | `difflib.get_close_matches(tag, existing_tags, n=3, cutoff=0.8)` | stdlib, battle-tested |
| Relationship create/delete | Custom ORM | Direct `INSERT OR IGNORE` / `DELETE FROM relationships WHERE source_path=? AND target_path=?` | Table is simple; no ORM needed |
| MCP confirm-token | Custom UUID/expiry | `_make_token()` / `_consume_token()` already in `mcp_server.py` | Reuse existing helpers |
| Tag save to frontmatter | Custom frontmatter editor | `python-frontmatter` + `tempfile` + `os.replace()` pattern (api.py tags_only PUT) | Already handles atomic write + encoding |
| Person context aggregation | Multiple sequential MCP calls | Single `sb_person_context()` that calls internal functions directly | Faster, no network overhead |

---

## Common Pitfalls

### Pitfall 1: MCP Tool BRAIN_ROOT Import
**What goes wrong:** Writing `from engine.paths import BRAIN_ROOT` at module level in `mcp_server.py` means test patches to `engine.paths.BRAIN_ROOT` are ignored — the module-level import captured the original value.
**How to avoid:** Import `BRAIN_ROOT` locally inside functions that use it: `from engine.paths import BRAIN_ROOT as _BRAIN_ROOT` inside the function body.
**Source:** LEARNINGS.md + STATE.md [Phase 27.1]

### Pitfall 2: Playwright Tests Fail Only in Full Suite
**What goes wrong:** Tests pass in isolation, fail when `pytest tests/` runs everything. Session-scoped fixtures are patched then restored by other test files' monkeypatches.
**How to avoid:** Use direct attribute assignment (`engine.db.DB_PATH = tmp_db`) not `monkeypatch.setattr()` for session-scoped fixtures that must survive the full session. Monkeypatch restores on teardown, which may happen mid-session.
**Source:** Current Phase 28 audit.

### Pitfall 3: `sb_capture_smart` Auto-Saving
**What goes wrong:** Developer implements `sb_capture_smart` to save notes immediately on first call, bypassing user review.
**How to avoid:** First call returns suggestions only (no save). User must call `sb_capture_batch` with confirmed notes to save. The confirm-token or a separate "save" call is the gate.
**Source:** ROADMAP Phase 28 description: "user confirms or edits before saving."

### Pitfall 4: `due_date` Column Already Exists
**What goes wrong:** Plan adds a `migrate_add_due_date` migration that already exists in `engine/db.py` — results in duplicate migration or test failure.
**How to avoid:** `due_date` column was added in Phase 27.2. Do NOT add another migration. The column exists; just expose it in `list_actions()` output and `PUT /actions/<id>`.
**Source:** `engine/db.py` lines 147-151 confirmed.

### Pitfall 5: `relationships` rel_type Column Name
**What goes wrong:** Using `relationship_type` instead of `rel_type` in INSERT statement.
**How to avoid:** Column is `rel_type` — from STATE.md [Phase 22] decision: "relationships table uses rel_type column (not relationship_type)."
**Source:** STATE.md.

### Pitfall 6: Tags Column is JSON TEXT
**What goes wrong:** Treating `notes.tags` as a comma-separated string or Python list.
**How to avoid:** Tags stored as JSON TEXT (e.g. `'["meeting", "work"]'`). Always use `json.loads(tags or "[]")` to read and `json.dumps(tag_list)` to write.
**Source:** CLAUDE.md known architectural issues.

---

## Code Examples

### `sb_link` skeleton
```python
# Source: engine/mcp_server.py pattern + relationships table schema
@mcp.tool()
def sb_link(source_path: str, target_path: str, rel_type: str = "link") -> dict:
    """Create a directional relationship between two notes. DB-only — does not edit note bodies."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
            (source_path, target_path, rel_type),
        )
        conn.commit()
        return {"linked": True, "source": source_path, "target": target_path}
    finally:
        conn.close()
```

### `sb_remind` — set due date on action item
```python
# Source: engine/api.py PUT /actions/<id> pattern + due_date column (Phase 27.2)
@mcp.tool()
def sb_remind(action_id: int, due_date: str) -> dict:
    """Set a due date on an action item. Format: YYYY-MM-DD."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE action_items SET due_date=? WHERE id=?",
            (due_date, action_id),
        )
        conn.commit()
        return {"updated": True, "action_id": action_id, "due_date": due_date}
    finally:
        conn.close()
```

### Title-only dedup fast-path
```python
# Source: engine/capture.py check_capture_dedup() — proposed change
def check_capture_dedup(title, body, conn, threshold=0.92, max_body_len=2000):
    text_to_embed = title if len(body) > max_body_len else f"{title}\n{body}"
    # ... rest unchanged ...
```

### Tag fuzzy matching
```python
# stdlib — no new dep
import difflib
existing_tags = json.loads(conn.execute("SELECT DISTINCT value FROM ...").fetchall())
# Or query from notes.tags JSON:
matches = difflib.get_close_matches(new_tag, existing_tags, n=3, cutoff=0.8)
if not matches and not confirm_token:
    tok = _make_token()
    return {"confirm_token": tok, "message": f"'{new_tag}' is a new tag. Pass confirm_token to create."}
```

### Conftest session isolation fix (28-07)
```python
# engine/db.DB_PATH and engine.paths.DB_PATH set via direct assignment (not monkeypatch)
# so they persist for the whole session and are not restored by other test teardowns.
# In gui_brain fixture (already done correctly):
_paths.DB_PATH = tmp_db   # direct assignment, NOT monkeypatch.setattr
_db.DB_PATH = tmp_db      # direct assignment, NOT monkeypatch.setattr
# Problem: other test files' fixtures use monkeypatch which may transiently reset these.
# Fix: add a session-autouse fixture AFTER gui_brain runs that re-anchors these values.
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact for Phase 28 |
|--------------|------------------|--------------|---------------------|
| Vanilla JS frontend | React + TypeScript + shadcn/ui | Phase 27.3 | No frontend changes needed for MCP tools |
| No confirm-token for tags | sb_tag uses confirm-token gate | Phase 28 (new) | Must implement to prevent tag sprawl |
| Body+title embedding for dedup | Title-only fallback for large bodies | Phase 28 (new) | Fixes MCP timeout on large captures |
| No explicit link tool | sb_link/sb_unlink | Phase 28 (new) | Relationships were implicit (backlinks only) |

---

## Open Questions

1. **`sb_capture_smart` — heuristic vs AI classifier**
   - What we know: project has no direct API key; uses Claude Code/MCP adapter pattern
   - What's unclear: whether heuristic-only v1 is sufficient or if the adapter should be invoked
   - Recommendation: implement heuristic v1 (keyword/regex classification); document as "v1 — upgrade to AI-assisted in Phase 31"

2. **Playwright full-suite failure root cause — exact contamination mechanism**
   - What we know: tests pass in isolation, fail in full suite; gui_brain uses direct assignment not monkeypatch
   - What's unclear: which test file causes the contamination and in what order tests run
   - Recommendation: add `print(engine.db.DB_PATH)` at test start in failing tests to confirm the value at runtime; fix fixture ordering in conftest if needed

3. **`sb_capture_smart` — return format**
   - What we know: ROADMAP says "returns N typed note suggestions"; user confirms before saving
   - What's unclear: exact dict structure for suggestions
   - Recommendation: `{"suggestions": [{"title": str, "type": str, "body": str, "links": [str]}, ...], "confirm_token": str}`

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + playwright-pytest |
| Config file | `pyproject.toml` (existing) |
| Quick run command | `uv run pytest tests/test_mcp.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |
| GUI tests command | `uv run pytest tests/test_gui.py -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| 28-01 | Title-only dedup used for large bodies | unit | `uv run pytest tests/test_capture.py::test_dedup_title_only_large_body -x` | ❌ Wave 0 |
| 28-02 | sb_capture_smart returns typed suggestions | unit | `uv run pytest tests/test_mcp.py::test_sb_capture_smart_returns_suggestions -x` | ❌ Wave 0 |
| 28-03 | sb_tag adds tag + fuzzy match + confirm-token gate | unit | `uv run pytest tests/test_mcp.py::test_sb_tag_adds -x` | ❌ Wave 0 |
| 28-04 | sb_link creates relationship; sb_unlink removes it | unit | `uv run pytest tests/test_mcp.py::test_sb_link_unlink -x` | ❌ Wave 0 |
| 28-05 | sb_remind sets due_date on action item | unit | `uv run pytest tests/test_mcp.py::test_sb_remind_sets_due_date -x` | ❌ Wave 0 |
| 28-06 | sb_person_context returns note + meetings + actions + mentions | unit | `uv run pytest tests/test_mcp.py::test_sb_person_context -x` | ❌ Wave 0 |
| 28-07 | 9 failing Playwright tests pass in full suite | e2e | `uv run pytest tests/test_gui.py -q` | ✅ (tests exist, need fix) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_mcp.py tests/test_capture.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green (including `tests/test_gui.py`) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_mcp.py` — add xfail stubs for 28-02 through 28-06 (new MCP tools)
- [ ] `tests/test_capture.py` — add xfail stub for 28-01 (title-only dedup)
- [ ] Wave 0 stubs use `xfail(strict=False)` per project convention — auto-promote to PASS once Wave 1 ships

---

## Sources

### Primary (HIGH confidence)
- `engine/mcp_server.py` — all existing MCP tool patterns, `_make_token`, `_consume_token`, `check_capture_dedup`
- `engine/capture.py` — `check_capture_dedup()` implementation (lines 40-84)
- `engine/db.py` — migration pattern, confirmed `due_date` and `assignee_path` columns exist
- `engine/api.py` — `list_meetings()`, `list_projects()`, `list_people()`, `note_meta()`, tags_only PUT pattern
- `tests/conftest.py` — `gui_brain` fixture seeding; `live_server_url` startup pattern
- `tests/test_gui.py` — 9 failing test functions identified (lines 252-481)
- `/tmp/pytest-phase28.txt` — full suite run output confirming 9 FAILED tests
- `.planning/ROADMAP.md` Phase 28 section — 7 explicit plan items
- `.planning/STATE.md` — accumulated decisions, pending todos, deferred items

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` Decisions section — `rel_type` column name, tag JSON format, monkeypatch isolation rules
- `.claude/LEARNINGS.md` — BRAIN_ROOT import rule, deploy pipeline, test isolation rules

---

## Metadata

**Confidence breakdown:**
- MCP tool implementations (28-01, 28-03, 28-04, 28-05, 28-06): HIGH — all infrastructure exists
- `sb_capture_smart` (28-02): MEDIUM — heuristic approach clear; AI approach needs adapter wiring
- Playwright fix (28-07): MEDIUM — root cause identified (session contamination); exact fix needs runtime verification

**Research date:** 2026-03-19
**Valid until:** 2026-04-18 (stable codebase)
