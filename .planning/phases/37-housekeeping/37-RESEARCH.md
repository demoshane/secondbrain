# Phase 37: Housekeeping — Research

**Researched:** 2026-03-25
**Domain:** Python/Flask engine fixes, React/TypeScript frontend UX, Playwright test debugging, SQLite cascade cleanup, macOS Drive sync detection
**Confidence:** HIGH — all findings come from direct source code inspection

## Summary

Phase 37 is eight targeted fixes across engine, frontend, and test infrastructure — no net-new architecture. Every item has a clear existing pattern to extend or a specific gap to close. The biggest implementation risk is the Playwright test trio (37-06): these are live E2E tests that depend on timing, SSE propagation, and DOM structure. The embedding reindex tests (37-07) have a well-defined fix (synchronous mode) but need care to not break the conftest stub machinery. The people-chips feature (37-03) is the largest frontend change and requires a new API endpoint branch in `PUT /notes/<path>`.

The cascade delete improvements (37-04) touch `delete.py` and `forget.py`, which have no FK safety net for the `action_items.assignee_path` column — that NULL-out must be done in application code. Drive sync detection (37-08) is purely additive: new bash block in `setup.sh` and a new dict key in `get_brain_health_report()`.

**Primary recommendation:** Plan each of the eight items as its own PLAN.md. The plans share files (`api.py`, `mcp_server.py`, `intelligence.py`) carefully, so execute sequentially not in parallel.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**37-01: sb_recap weekly view fix**
- `sb_recap` MCP tool currently calls `recap_entity()` when `name=None`, returning "No recap available"
- Fix: when `name=None`, call `generate_recap_on_demand()` instead — already exists in `intelligence.py`
- No MCP signature change needed

**37-02: Action item creation from person note view**
- ActionItemList component already renders in PeoplePage detail view
- Add a create button/inline form consistent with the existing ActionItemList creation pattern (Phase 34)

**37-03: People chips in NoteViewer**
- Location: NoteViewer (middle panel) — same location as tag chips/TagAutocomplete
- Pattern: People chips alongside tag chips. `+` opens autocomplete dropdown sourced from `/persons` endpoint. `x` removes the link.
- Writes to: `note_people` junction table + `people` JSON column on the note
- Read from: `note_people` junction table (already populated by entity extraction on capture)
- Same visual and interaction pattern as existing tag editing — no new UI paradigm

**37-04: Cascade delete — impact preview + orphan cleanup**
- Pre-delete impact summary: Before executing any delete, query and return counts: `{ action_items: N, relationships: N, appears_in_people_of: N_notes }`. Show in GUI delete confirmation modal AND in `sb_forget` pre-confirmation step.
- `delete_note()` gaps to fix:
  - Add `DELETE FROM note_people WHERE person = ?` when deleting a person note (other notes' people links become orphaned)
  - Add `UPDATE/NULL action_items WHERE assignee_path = ?` when deleting a person note (assignee references orphaned)
- `forget_person()` gap to fix:
  - Add `UPDATE/NULL action_items WHERE assignee_path IN (person_paths)` — currently missing
- All other cascade targets already handled
- Impact preview is informational, not a hard blocker

**37-07: Embedding reindex test fix**
- Tests fail due to race condition: embeddings run in a background thread, test asserts immediately after
- Fix: Add `synchronous=True` parameter to the embed pass function (or reindex call) — runs embedding inline, no thread, blocks until done
- `synchronous=True` used in tests only; production keeps non-blocking behavior
- Ollama IS running with `nomic-embed-text:latest` — no mock needed, tests should hit real embeddings

**37-08: Drive sync setup**
- User has added `~/SecondBrain` to Google Drive Desktop mirror sync (done 2026-03-25)
- Drive Desktop skips hidden folders (`.meta/`) automatically — SQLite DB and embeddings stay local-only
- `setup.sh` guidance: Detect if `/Applications/Google Drive.app` exists. If not installed, print step-by-step instructions. If installed, print reminder to confirm `~/SecondBrain` is added in Drive Preferences → My Computer.
- `sb-health` Drive check (3-tier):
  - Drive installed + process running + DriveFS account DB present
  - Drive installed but process not running — warn
  - Drive not installed — warn with setup instructions
  - Always append: "Confirm ~/SecondBrain is added in Drive preferences"
- Detection: `pgrep -x "Google Drive"`, `/Applications/Google Drive.app`, glob for `mirror_sqlite.db` in `~/Library/Application Support/Google/DriveFS/{account_id}/`
- Drive check is a warning, not a hard error

### Claude's Discretion
- Action item creation UX in person view (inline vs modal) — follow whatever pattern ActionItemList already uses for creation
- Exact wording of Drive setup instructions in setup.sh
- Whether assignee_path is NULLed or the action item is deleted when a person is removed (NULL preferred — preserve the action item)
- Playwright test fixes (37-06) — pure debugging, no design decisions

### Deferred Ideas (OUT OF SCOPE)
- None raised — discussion stayed within phase scope
</user_constraints>

---

## Standard Stack

### Core (all existing — no new dependencies)
| Component | Version | Purpose |
|-----------|---------|---------|
| Python / FastMCP | project version | MCP tool fixes (37-01) |
| Flask | project version | API endpoint additions (37-03, 37-04) |
| SQLite3 | built-in | Cascade query additions |
| React / TypeScript | project version | Frontend people chips (37-03) |
| pytest | project version | New tests (37-05, 37-07) |
| Playwright | project version | E2E test debugging (37-06) |

No new packages needed for any plan in this phase.

---

## Architecture Patterns

### 37-01: sb_recap — wiring generate_recap_on_demand

**Current flow (broken):**
```python
# mcp_server.py line ~573-594
def sb_recap(name: str | None = None) -> str:
    if name is None and _detect_git_context is not None:
        name = _detect_git_context()
    if name is None:
        return "No recap available for this context."  # <-- falls through, never calls generate_recap_on_demand
    recap = recap_entity(name, conn)
```

**Fixed flow:**
```python
from engine.intelligence import find_dormant_related, find_similar, get_overdue_actions, list_actions, recap_entity, generate_recap_on_demand

def sb_recap(name: str | None = None, days: int | None = None) -> str:
    if name is None and _detect_git_context is not None:
        name = _detect_git_context()
    if name is None:
        # No entity name — run weekly session recap
        conn = get_connection()
        try:
            result = generate_recap_on_demand(conn, window_days=days)
            return result or "No recent notes to recap."
        finally:
            conn.close()
    # Entity recap path (unchanged)
    ...
```

The import at line 22 of `mcp_server.py` must add `generate_recap_on_demand` to the import list.

### 37-03: People chips in NoteViewer

The tag chip pattern in NoteViewer (lines 111-181) is the exact template. People chips need:

1. New state: `localPeople`, `addingPerson`, `newPerson`
2. `savepeople` function that PUTs `{ people: [...] }` to `/notes/<path>`
3. `PUT /notes/<path>` in `api.py` needs a new "people-only branch" (lines ~850-870 are the tags-only branch template) that:
   - Writes `people` JSON to frontmatter
   - Updates `notes.people` column
   - Replaces `note_people` rows: DELETE + INSERT OR IGNORE
4. New `PersonAutocomplete` component (clone of `TagAutocomplete`, fetch from `/persons` instead of `/tags`, display person title not slug)

**API endpoint addition (people-only branch):**
```python
people_val = body.get("people")
if people_val is not None and "content" not in body and "tags" not in body and "title" not in body:
    # Write frontmatter + DB + note_people junction
    raw = p.read_text(encoding="utf-8")
    post = _fm.loads(raw)
    post.metadata["people"] = people_val
    # ... atomic write ...
    conn.execute("UPDATE notes SET people=?, updated_at=? WHERE path=?",
                 (json.dumps(people_val), now, path_str))
    conn.execute("DELETE FROM note_people WHERE note_path=?", (path_str,))
    for person in people_val:
        conn.execute("INSERT OR IGNORE INTO note_people (note_path, person) VALUES (?, ?)",
                     (path_str, person))
    conn.commit()
```

**PersonAutocomplete** sources from `/persons` which returns `{ people: [{ path, name, ... }] }`. Display `name` in dropdown, store `name` (not path) in the people array to match the existing convention (entity extraction stores names, not paths).

### 37-04: Cascade gaps in delete_note() and forget_person()

**delete_note() additions** (after existing step 6, before step 7):

```python
# 6a. If deleting a person note — NULL assignee_path in action_items
note_row = conn.execute("SELECT type FROM notes WHERE path=?", (path_str,)).fetchone()
if note_row and note_row[0] in ("person",):
    conn.execute("UPDATE action_items SET assignee_path=NULL WHERE assignee_path=?", (path_str,))
    conn.execute("DELETE FROM note_people WHERE person=?", (path_str,))
```

**forget_person() addition** (after step 2d, before step 2e):

```python
# 2d-bis. NULL assignee_path in action_items for all person paths being erased
if all_delete_paths:
    for pth in all_delete_paths:
        conn.execute("UPDATE action_items SET assignee_path=NULL WHERE assignee_path=?", (pth,))
```

**Impact preview query** (for both MCP sb_forget first-step and GUI DeleteNoteModal):

```python
def get_delete_impact(path_str: str, conn) -> dict:
    action_items = conn.execute(
        "SELECT COUNT(*) FROM action_items WHERE note_path=?", (path_str,)
    ).fetchone()[0]
    relationships = conn.execute(
        "SELECT COUNT(*) FROM relationships WHERE source_path=? OR target_path=?",
        (path_str, path_str)
    ).fetchone()[0]
    appears_in = conn.execute(
        "SELECT COUNT(*) FROM note_people WHERE person=?", (path_str,)
    ).fetchone()[0]
    return {"action_items": action_items, "relationships": relationships, "appears_in_people_of": appears_in}
```

### 37-07: Synchronous embedding in reindex

`reindex_brain()` calls `embed_pass_async()` at line 263. The fix adds a `synchronous` param:

```python
def reindex_brain(brain_root, conn=None, full=False, entities=False, synchronous=False):
    ...
    if synchronous:
        result = embed_pass(conn_for_embed, provider=provider, batch_size=batch_size, force=full)
    else:
        future = embed_pass_async(get_connection, provider=provider, batch_size=batch_size, force=full)
        result = future.result()
```

Tests call `reindex_brain(brain_root, db_conn, synchronous=True)` — same connection, no thread. This also solves the SQLite "database is locked" issue that occurs when the background thread opens a second connection to an in-memory DB that the test owns.

The conftest `stub_engine_embeddings` already excludes `TestReindexGeneratesEmbeddings` from the autouse stub — so these tests still inject their own fake module. `synchronous=True` just controls threading, not the embeddings module.

### 37-06: Playwright test debugging

The three failing tests:

**test_title_sync (SC-4):** The test does PUT → POST /notes/refresh → waits for SSE to update sidebar. Likely failure: `POST /notes/refresh` endpoint does not exist or SSE event isn't broadcast with the right type. Verify `/notes/refresh` is registered in `api.py`, and the SSE event name matches what the frontend listens for. Also check: the test waits for `has_text="Updated Title"` in `note-item` — if the sidebar doesn't re-render, it times out.

**test_delete_flow (SC-6):** Opens a note, clicks `[data-testid="delete-btn"]`, expects `[data-testid="delete-note-modal"]`. If the delete button no longer renders in `NoteViewer` (it may have been moved to `RightPanel`), the test fails. Check `NoteViewer.tsx` for `data-testid="delete-btn"` and `DeleteNoteModal.tsx` for `data-testid="delete-note-modal"`.

**test_right_panel_people_mention (QA-02):** Opens "Test Mention Note" (a `gui_brain` fixture note that mentions "Test Person" in body), expects `data-testid="people-badge"`. This depends on `/notes/<path>/meta` returning person mentions from body scan, and RightPanel rendering `people-badge` elements. Check `conftest.py` `gui_brain` fixture to confirm "Test Mention Note" and "Test Person" notes are seeded correctly.

### 37-08: Drive sync check architecture

`get_brain_health_report()` returns a dict. Add a new `drive_sync` key:

```python
def check_drive_sync() -> dict:
    """3-tier Drive sync health check. Returns dict with status and message."""
    import glob as _glob
    app_path = Path("/Applications/Google Drive.app")
    driveFS_base = Path.home() / "Library" / "Application Support" / "Google" / "DriveFS"

    if not app_path.exists():
        return {"status": "not_installed", "message": "Google Drive not installed. ..."}

    import subprocess
    proc = subprocess.run(["pgrep", "-x", "Google Drive"], capture_output=True)
    if proc.returncode != 0:
        return {"status": "not_running", "message": "Google Drive installed but not running. Brain won't sync."}

    # Check for DriveFS account DB
    db_matches = list(driveFS_base.glob("*/mirror_sqlite.db"))
    if db_matches:
        return {"status": "ok", "message": "Drive running. Confirm ~/SecondBrain is added in Drive Preferences → My Computer."}
    else:
        return {"status": "not_configured", "message": "Drive running but no DriveFS account DB found. Open Drive preferences."}
```

`setup.sh` Drive block inserts between step 7 (reindex) and step 8 (health check):

```bash
step "Checking Google Drive sync"
if [[ -d "/Applications/Google Drive.app" ]]; then
  ok "Google Drive installed"
  echo "  Reminder: open Google Drive Preferences → My Computer → confirm ~/SecondBrain is added"
else
  printf "  \033[33m!\033[0m Google Drive not installed.\n"
  echo "  For brain sync: https://www.google.com/drive/download/"
  echo "  After install: Preferences → My Computer → Add folder → ~/SecondBrain"
fi
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| People autocomplete UI | Custom input + fetch | Clone `TagAutocomplete`, swap `/tags` → `/persons` |
| Cascade impact count | Complex JOIN | Three separate `COUNT(*)` queries — simple and readable |
| Drive process check | Parse `ps aux` | `pgrep -x "Google Drive"` — the correct POSIX tool |
| Synchronous test embedding | Thread join hacks | `synchronous=True` param, call `embed_pass()` directly |

---

## Common Pitfalls

### Pitfall 1: note_people.person stores names, not paths
**What goes wrong:** People chips write person paths (`~/SecondBrain/person/alice-smith.md`) when they should write person names (`"Alice Smith"`) — same format as entity extraction. PUT handler and autocomplete dropdown must agree on what value to store.

**How to avoid:** Check what entity extraction writes to `note_people.person` (it stores display names/slugs from frontmatter, not absolute paths). The autocomplete should return the `name` field from `/persons`, not `path`.

### Pitfall 2: embed_pass_async opens its own connection
**What goes wrong:** `embed_pass_async` creates a new `get_connection()` inside the thread. In tests using an in-memory `:memory:` DB, this second connection sees an empty database. The `synchronous=True` path must pass the test's own `conn` directly to `embed_pass()`.

**How to avoid:** When `synchronous=True`, call `embed_pass(conn, ...)` with the caller's connection, bypassing `embed_pass_async` entirely.

### Pitfall 3: conftest stub_engine_embeddings exclusion
**What goes wrong:** The autouse `stub_engine_embeddings` fixture in `conftest.py` specifically skips `TestReindexGeneratesEmbeddings` (line 138). Tests in that class inject their own fake module per-test. If the `synchronous=True` fix changes the module lookup path, the injected fake might not be found.

**How to avoid:** The fake module injection in `TestReindexGeneratesEmbeddings` uses `sys.modules["engine.embeddings"]` directly. The fix in `reindex.py` must preserve the `sys.modules` lookup path (current code already does this at lines 33-36).

### Pitfall 4: DELETE /persons already NULLs assignee_path (don't double-implement)
**What goes wrong:** `api.py` line 577 already does `UPDATE action_items SET assignee_path = NULL WHERE assignee_path = ?` in the DELETE /persons endpoint. The `delete_note()` fix must not assume this is missing everywhere — it IS missing in the direct note delete path (NoteViewer's delete button), but it exists in the PeoplePage delete flow.

**How to avoid:** Add the NULL-out inside `delete_note()` function itself (so it applies regardless of how the delete is triggered), but note that the API endpoint path already does it redundantly — that's fine.

### Pitfall 5: Playwright test_delete_flow — delete-btn location
**What goes wrong:** If `data-testid="delete-btn"` was moved out of `NoteViewer` (e.g. into `RightPanel`) during Phase 34 UX work, the test can't find it and times out.

**How to avoid:** Before writing the fix, grep the frontend source for `delete-btn` and `delete-note-modal` to confirm their current location. The fix may need to click a different element sequence.

---

## Code Examples

### Recap MCP fix (minimal)
```python
# Source: engine/mcp_server.py ~line 569
@mcp.tool()
def sb_recap(name: str | None = None, days: int | None = None) -> str:
    """Get session recap or cross-context synthesis for a person/project name."""
    import engine.mcp_server as _self
    if name is None and _detect_git_context is not None:
        name = _detect_git_context()
    if name is None:
        # Weekly session recap
        conn = get_connection()
        try:
            from engine.intelligence import generate_recap_on_demand
            result = generate_recap_on_demand(conn, window_days=days)
            return result or "No recent activity to recap."
        finally:
            conn.close()
    # Entity recap (existing path unchanged)
    ...
```

### Tags-only branch pattern (template for people-only branch)
```python
# Source: engine/api.py ~line 851 — copy this pattern for people
tags_val = body.get("tags")
if tags_val is not None and "content" not in body:
    raw = p.read_text(encoding="utf-8")
    post = _fm.loads(raw)
    post.metadata["tags"] = tags_val
    updated_text = _fm.dumps(post)
    with tempfile.NamedTemporaryFile(...) as f:
        f.write(updated_text)
        tmp = f.name
    suppress_next_delete(str(p))
    os.replace(tmp, p)
    conn.execute("UPDATE notes SET tags=?, updated_at=? WHERE path=?", ...)
    conn.commit()
    return jsonify({"saved": True, "path": str(p)})
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (with playwright plugin) |
| Config file | `pytest.ini` / `pyproject.toml` |
| Quick run command | `uv run pytest tests/test_embeddings.py tests/test_mcp.py tests/test_intelligence.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map
| Plan | Behavior | Test Type | Automated Command |
|------|----------|-----------|-------------------|
| 37-01 | sb_recap with no name calls generate_recap_on_demand | unit | `uv run pytest tests/test_mcp.py -k recap -x` |
| 37-02 | ActionItemList create in PeoplePage | Playwright E2E | `uv run pytest tests/test_gui.py -k people -x` |
| 37-03 | People chips render, add, remove via PUT | unit + Playwright | `uv run pytest tests/test_api.py -k people -x` |
| 37-04 | delete_note NULLs assignee_path, impact counts returned | unit | `uv run pytest tests/test_delete.py tests/test_forget.py -x` |
| 37-05 | install_subagent copies file, idempotent | unit | `uv run pytest tests/test_subagent.py -x` |
| 37-06 | 3 Playwright tests green | Playwright E2E | `uv run pytest tests/test_gui.py::test_title_sync tests/test_gui.py::test_delete_flow tests/test_gui.py::test_right_panel_people_mention -v` |
| 37-07 | TestReindexGeneratesEmbeddings all 4 tests green | unit | `uv run pytest tests/test_embeddings.py::TestReindexGeneratesEmbeddings -v` |
| 37-08 | check_drive_sync returns correct tier | unit | `uv run pytest tests/test_brain_health.py -k drive -x` |

### Wave 0 Gaps
- [ ] `tests/test_brain_health.py` needs `test_drive_sync_*` tests (37-08)
- [ ] No existing test file covers `scripts/install_subagent.py` — `tests/test_subagent.py` already exists, check if it covers the script or needs additions

*(Existing test infrastructure covers all other plans)*

---

## Runtime State Inventory

> Phase is not a rename/refactor — skip full inventory. Only noting relevant runtime state.

| Category | Items | Action Required |
|----------|-------|-----------------|
| Stored data | `note_people` junction: existing rows use name format (not path) for `person` column | People chips must write names to stay consistent |
| Live service config | Drive sync already configured by user (2026-03-25) | Verify `~/SecondBrain` shows in Drive Preferences |
| OS-registered state | None affected | — |
| Secrets/env vars | None affected | — |
| Build artifacts | Frontend rebuild needed for 37-02, 37-03, 37-06 (React changes) | `make dev` on host after frontend changes |

---

## Environment Availability

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| Ollama (nomic-embed-text) | 37-07 embedding tests | Yes | CONTEXT.md: "Ollama IS running with nomic-embed-text:latest" |
| Google Drive Desktop | 37-08 health check | Yes | User confirmed installed and sync configured 2026-03-25 |
| Playwright | 37-06 test fixes | Yes | Already in test suite |

---

## Open Questions

1. **test_title_sync failure root cause** — needs a test run to see actual error. Most likely: `/notes/refresh` endpoint exists but SSE propagation timing. Check `api.py` for the endpoint and the frontend SSE listener event type.

2. **test_right_panel_people_mention — gui_brain fixture** — does the fixture seed "Test Mention Note" with a person mention and a corresponding "Test Person" `type=person` note? Read `conftest.py` `gui_brain` fixture fully before fixing.

3. **ActionItemList creation pattern in PeoplePage** — the CONTEXT.md says "follow whatever pattern ActionItemList already uses for creation." Read `ActionItemList.tsx` to confirm the create affordance exists and what props it needs before writing 37-02.

---

## Sources

### Primary (HIGH confidence)
- Direct source inspection: `engine/mcp_server.py`, `engine/intelligence.py`, `engine/delete.py`, `engine/forget.py`, `engine/reindex.py`, `engine/embeddings.py`, `engine/db.py`, `engine/brain_health.py`
- Direct source inspection: `frontend/src/components/NoteViewer.tsx`, `frontend/src/components/TagAutocomplete.tsx`, `frontend/src/components/PeoplePage.tsx`
- Direct source inspection: `tests/test_embeddings.py`, `tests/test_gui.py`, `tests/conftest.py`
- Direct source inspection: `setup.sh`, `scripts/install_subagent.py`
- Project context: `CONTEXT.md` (37-housekeeping), `CLAUDE.md`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all existing code inspected
- Architecture patterns: HIGH — code patterns taken directly from source
- Pitfalls: HIGH — identified from actual code gaps (lines cited)
- Test map: HIGH — existing test files verified, gaps identified

**Research date:** 2026-03-25
**Valid until:** 60 days (stable Python/React codebase, no fast-moving deps)
