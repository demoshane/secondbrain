# Phase 15: Intelligence Layer - Research

**Researched:** 2026-03-15
**Domain:** Proactive intelligence features — session recap, action item tracking, stale nudges, connection suggestions
**Confidence:** HIGH

## Summary

Phase 15 adds four proactive intelligence features to the second brain CLI. All features share a single daily notification budget gated by `~/.meta/intelligence_state.json`. The implementation is entirely intra-codebase: no new external dependencies are required. The primary deliverable is a new `engine/intelligence.py` module that exposes four subsystems (recap, action items, connections, stale nudge) and two new CLI entry points (`sb-recap`, `sb-actions`).

The existing codebase is well-prepared: `engine/ai.py` has the LLM adapter pattern; `engine/capture.py` is the primary integration hook; `engine/search.py` is the secondary integration hook; `engine/db.py` needs one new table (`action_items`) via an idempotent migration following the `migrate_add_people_column` pattern; `engine/embeddings.py` provides embedding BLOBs and needs a new `find_similar()` function for KNN cosine similarity. No external library additions are needed beyond what is already installed.

The main implementation risk is the `sqlite-vec` KNN query API — the exact SQL for cosine similarity against a BLOB column must be verified against the installed version. The budget logic and state file are straightforward JSON read/write, and the action item DDL and stale nudge query are purely SQLite.

**Primary recommendation:** Implement `engine/intelligence.py` as a single new module with clear subsystem functions, integrated into `capture.py` and `search.py` as best-effort post-processing calls (same pattern as `add_backlinks`).

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Session context detection**
- Auto-detect context from current git repo name (`git rev-parse --show-toplevel` + basename)
- Outside a git repo: `sb-recap` requires an explicit name argument (`sb-recap "Alice"`, `sb-recap "Acme project"`)
- Proactive INTL-01 session offer (once-per-day) lives in `~/.claude/CLAUDE.md` — existing file, follows established pattern
- `sb-recap` without args in a non-git dir prints: `"No context detected — try sb-recap <name>"`
- Recap summarizes notes tagged or linked to the detected context name

**Action item extraction**
- LLM extraction via existing AI adapter at capture time — handles natural language commitments
- PII note extraction routes through Ollama automatically (existing ModelRouter applies)
- Extract from all note types (not just meetings — any note can contain commitments)
- Store in a new `action_items` table in `brain.db`
  - Schema: `id INTEGER PK, note_path TEXT, text TEXT, done BOOL DEFAULT 0, created_at TEXT`
- `sb-actions` default output: all open items, newest first — columns: ID | text | source note | date
- `sb-actions --done <id>` marks an item complete

**Notification budget mechanics**
- "Session" = calendar day; budget resets at midnight
- State persisted in `~/.meta/intelligence_state.json` (already decided in roadmap)
- Vault gate: 20 notes minimum before any proactive offer fires
- Priority order when multiple features compete for the daily slot: **Recap > connection suggestion > stale nudge**
- Proactive offers only fire from `sb-capture` and `sb-search` — not from maintenance commands
- Explicit commands (`sb-recap`, `sb-actions`) always work on-demand — budget only gates **unsolicited** inline offers

**Connection suggestions**
- After `sb-capture`: run KNN query against `note_embeddings` for cosine similarity > 0.8
- Show top 3 matching notes as notification lines before prompt returns
- Auto-append `Related: [[note-title]]` to the **new note only** (one-directional)
- If embeddings table is empty or missing: silently skip — no error, no hint
- Connection suggestion consumes the daily proactive slot (second priority after recap)

**Stale nudge behavior**
- Notes not accessed/updated in 90 days surface as nudges (max 5 per session per INTL-06)
- Notes with `evergreen: true` frontmatter are exempt
- Stale nudge rechecks at 180 days if not acted on (INTL-08)
- Fires from `sb-search` and `sb-capture` — lowest priority in budget

### Claude's Discretion
- Exact LLM prompt for action item extraction
- `intelligence_state.json` schema (fields, versioning)
- How `sb-recap` generates the summary (prompt structure, note count limit)
- Exact output formatting for `sb-actions` list (spacing, truncation)
- Stale note selection algorithm (oldest first, random sample, or by category)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INTL-01 | User sees a once-per-session recap offer in Claude Code when working in a known context | CLAUDE.md hook pattern; budget check in `intelligence_state.json` |
| INTL-02 | User can run `sb-recap` to get a summary of recent activity in the detected context | git context detection + FTS search + LLM adapter summarization |
| INTL-03 | Action items are extracted from meeting notes at capture time | LLM adapter call in `capture_note()` post-write; `action_items` DDL |
| INTL-04 | User can list open action items via `sb-actions` | `SELECT ... WHERE done=0 ORDER BY created_at DESC` |
| INTL-05 | User can mark action items complete via `sb-actions --done <id>` | `UPDATE action_items SET done=1 WHERE id=?` |
| INTL-06 | User is nudged about notes not accessed/updated in 90 days (max 5 per session) | SQLite date comparison on `updated_at`; frontmatter `evergreen` check |
| INTL-07 | Notes with `evergreen: true` frontmatter are exempt from stale nudges | Frontmatter read via `python-frontmatter`; filter before nudge list |
| INTL-08 | Stale nudge rechecks at 180 days if not acted on | `last_stale_check` persisted per-note in `intelligence_state.json` or separate field |
| INTL-09 | User sees a connection suggestion after capturing a note that closely matches an existing note | `find_similar()` KNN on `note_embeddings`; cosine similarity > 0.8; top 3 shown |
| INTL-10 | All proactive features share a single notification budget — one unsolicited offer per session | `intelligence_state.json` `last_offer_date` vs `date.today().isoformat()` |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlite3 (stdlib) | built-in | `action_items` table, stale query, budget state | All existing DB work uses it |
| python-frontmatter | >=1.0 | Read `evergreen` frontmatter field | Already installed; used throughout engine |
| engine.ai (local) | current | LLM adapter for recap and action item extraction | Established adapter with PII routing |
| engine.embeddings (local) | current | KNN query for connection suggestions | Phase 14 deliverable |
| json (stdlib) | built-in | `intelligence_state.json` read/write | Established pattern in codebase |
| subprocess (stdlib) | built-in | `git rev-parse --show-toplevel` for context detection | Used in engine/ai.py already |
| pathlib.Path (stdlib) | built-in | All path handling | Project convention |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite-vec | >=0.1 | Cosine similarity KNN on embedding BLOBs | Connection suggestions only |
| datetime (stdlib) | built-in | Budget date comparison, stale age calculation | Throughout intelligence module |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSON state file | New DB table | JSON is simpler; only 2-3 scalar fields; no query complexity needed |
| sqlite-vec KNN | Manual cosine in Python | sqlite-vec KNN is already installed; manual approach would be slower on large vaults |
| `subprocess git` for context | `gitpython` library | No new dependency; git is always present on dev machines |

**Installation:** No new dependencies required. All libraries are already declared in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

New files this phase:
```
engine/
├── intelligence.py      # All four intelligence subsystems
tests/
├── test_intelligence.py # Unit tests for all INTL-* requirements
```

Modifications:
```
engine/
├── db.py                # migrate_add_action_items_table()
├── capture.py           # Call check_connections() + extract_action_items() post-write
├── search.py            # Call check_stale_nudge() post-search
pyproject.toml           # Add sb-recap + sb-actions entry points
~/.claude/CLAUDE.md      # Add one-line session hook for INTL-01
```

### Pattern 1: Budget Gate

All unsolicited offers run through a single budget check before firing. The budget is one offer per calendar day per vault.

```python
# engine/intelligence.py
import json
import datetime
from pathlib import Path

STATE_PATH = Path.home() / ".meta" / "intelligence_state.json"
VAULT_GATE = 20  # minimum notes before any offer fires


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def budget_available(conn) -> bool:
    """Return True if no unsolicited offer has been made today and vault has 20+ notes."""
    note_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    if note_count < VAULT_GATE:
        return False
    state = _load_state()
    today = datetime.date.today().isoformat()
    return state.get("last_offer_date") != today


def consume_budget() -> None:
    """Record that today's offer has been used."""
    state = _load_state()
    state["last_offer_date"] = datetime.date.today().isoformat()
    _save_state(state)
```

### Pattern 2: Post-Write Hook (same as `add_backlinks`)

Connection suggestions and action item extraction fire after `capture_note()` returns, as best-effort calls that never raise to the caller.

```python
# engine/capture.py — after return target line in capture_note()
def capture_note(...) -> Path:
    ...
    write_note_atomic(target, post, conn)
    if people:
        from engine.links import add_backlinks
        add_backlinks(target, people, brain_root, conn)

    # Phase 15: best-effort intelligence hooks
    try:
        from engine.intelligence import check_connections, extract_action_items
        check_connections(target, conn, brain_root)
        extract_action_items(target, post.content, content_sensitivity, conn)
    except Exception:
        pass  # Never block capture

    return target
```

### Pattern 3: Idempotent Migration (follow `migrate_add_people_column`)

```python
# engine/db.py
def migrate_add_action_items_table(conn: sqlite3.Connection) -> None:
    """Idempotent migration: create action_items table if absent."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS action_items (
            id         INTEGER PRIMARY KEY,
            note_path  TEXT NOT NULL,
            text       TEXT NOT NULL,
            done       BOOL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)
    conn.commit()
```

Call this from `init_schema()` and from the CLI entry points that need it.

### Pattern 4: KNN Similarity Query

`sqlite-vec` is already installed (see `pyproject.toml`). The cosine similarity query pattern for the installed version:

```python
# engine/intelligence.py
def find_similar(note_path: str, conn, threshold: float = 0.8, limit: int = 3) -> list[dict]:
    """Return up to `limit` notes with cosine similarity > threshold to note_path."""
    row = conn.execute(
        "SELECT embedding FROM note_embeddings WHERE note_path = ?", (note_path,)
    ).fetchone()
    if not row or not row[0]:
        return []
    query_blob = row[0]

    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except Exception:
        return []  # sqlite-vec not available — silently skip

    rows = conn.execute(
        """
        SELECT ne.note_path,
               vec_distance_cosine(ne.embedding, ?) AS dist
        FROM note_embeddings ne
        WHERE ne.note_path != ?
          AND (1.0 - dist) >= ?
        ORDER BY dist
        LIMIT ?
        """,
        (query_blob, note_path, threshold, limit),
    ).fetchall()
    return [{"note_path": r[0], "similarity": 1.0 - r[1]} for r in rows]
```

**NOTE (MEDIUM confidence):** `vec_distance_cosine` is the sqlite-vec function name as of v0.1.x. Verify against installed version with `sqlite_vec.__version__` before implementing. The function returns a distance (0=identical, 1=orthogonal), so similarity = 1 - distance.

### Pattern 5: Git Context Detection

```python
# engine/intelligence.py
import subprocess

def detect_git_context() -> str | None:
    """Return current git repo basename, or None if not in a git repo."""
    try:
        result = subprocess.run(
            ["/usr/bin/git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return Path(result.stdout.strip()).name
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None
```

Note: use `/usr/bin/git` not bare `git` — scm_breeze shell plugin on this machine breaks bare `git` (per project CLAUDE.md).

### Pattern 6: LLM Action Item Extraction

Action item extraction uses the same `_router.get_adapter()` pattern as `ask_followup_questions`. The system prompt is STATIC; note body is passed as `user_content` only (AI-10 constraint).

```python
ACTION_ITEM_SYSTEM_PROMPT = (
    "You are an assistant that extracts action items from notes. "
    "Output ONLY a newline-separated list of action items — one per line. "
    "Each line must be a concrete, specific commitment or to-do. "
    "If there are no action items, output exactly: NONE"
)

def extract_action_items(note_path: Path, body: str, sensitivity: str, conn) -> None:
    """Extract and store action items from note body. Best-effort — never raises."""
    from engine.paths import CONFIG_PATH
    try:
        adapter = _router.get_adapter(sensitivity, CONFIG_PATH)
        raw = adapter.generate(user_content=body, system_prompt=ACTION_ITEM_SYSTEM_PROMPT)
        lines = [l.strip() for l in raw.splitlines() if l.strip() and l.strip() != "NONE"]
        for line in lines:
            conn.execute(
                "INSERT INTO action_items (note_path, text) VALUES (?, ?)",
                (str(note_path.resolve()), line),
            )
        conn.commit()
    except Exception:
        pass  # Best-effort
```

### Pattern 7: Stale Note Query

```python
def get_stale_notes(conn, days: int = 90, limit: int = 5) -> list[dict]:
    """Return up to limit notes not updated in `days` days, excluding evergreen."""
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    rows = conn.execute(
        """
        SELECT path, title, updated_at FROM notes
        WHERE updated_at < ?
        ORDER BY updated_at ASC
        LIMIT ?
        """,
        (cutoff + "T00:00:00Z", limit * 3),  # fetch more, then filter evergreen
    ).fetchall()

    results = []
    for path, title, updated_at in rows:
        if len(results) >= limit:
            break
        # Check evergreen frontmatter
        p = Path(path)
        if p.exists():
            try:
                import frontmatter
                meta = frontmatter.load(str(p))
                if meta.get("evergreen"):
                    continue
            except Exception:
                pass
        results.append({"path": path, "title": title, "updated_at": updated_at})
    return results
```

### Pattern 8: intelligence_state.json Schema (Claude's Discretion)

Recommended minimal schema with versioning:

```json
{
  "version": 1,
  "last_offer_date": "2026-03-15",
  "stale_snoozed": {
    "/abs/path/to/note.md": "2026-06-12"
  }
}
```

- `last_offer_date`: ISO date string, gates the daily budget
- `stale_snoozed`: maps absolute note path to date when it should recheck (180-day snooze for INTL-08)

### Pattern 9: sb-recap Summary (Claude's Discretion)

Recommended prompt structure — fetch up to 10 most recent notes matching context name (tags or title contains name), concatenate titles + first 200 chars of body, summarize via LLM:

```python
RECAP_SYSTEM_PROMPT = (
    "You are a personal assistant. Given a list of recent notes about a context, "
    "write a 3-5 sentence summary of recent activity, key themes, and open threads. "
    "Be concise. Output plain text, no bullet points."
)
```

Note count limit: 10 notes per recap (avoids LLM context overflow for typical note sizes).

### Anti-Patterns to Avoid

- **Never block capture or search on intelligence failures.** All hooks in `capture.py` and `search.py` must be wrapped in `try/except Exception: pass`.
- **Never include note body content in error messages.** Follow the GDPR-safe error pattern from `write_note_atomic`.
- **Never fire proactive offers from maintenance commands.** `sb-reindex`, `sb-forget`, `sb-export`, `sb-anonymize` must not trigger intelligence checks.
- **Never modify existing notes during connection suggestions.** Only append `Related: [[stem]]` to the newly captured note; never touch the matched notes.
- **Do not use bare `git`.** Always use `/usr/bin/git` — scm_breeze breaks bare git on this machine.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cosine similarity search | Manual vector loop in Python | `sqlite-vec vec_distance_cosine` | Already installed; handles BLOB format correctly; faster |
| LLM inference | Direct HTTP to Ollama/Claude | `engine.router.get_adapter()` | PII routing, config-driven adapter selection, already tested |
| Frontmatter parsing | Manual YAML string parsing | `python-frontmatter` | Edge cases with multiline strings, special chars |
| Atomic file writes | `open(path, 'w')` | `write_note_atomic()` + temp file pattern | Crash safety; already battle-tested in this codebase |
| DB migration | Drop/recreate tables | `CREATE TABLE IF NOT EXISTS` idempotent pattern | Preserves existing data |

---

## Common Pitfalls

### Pitfall 1: sqlite-vec Extension Loading
**What goes wrong:** `conn.enable_load_extension(True)` must be called before `sqlite_vec.load(conn)`. If called on a connection that already loaded the extension, it silently no-ops but doesn't error. If sqlite-vec is not installed or the extension path is wrong, it raises.
**Why it happens:** sqlite-vec is a loadable extension, not a built-in; the load must happen per-connection.
**How to avoid:** Wrap the load in `try/except Exception: return []` in `find_similar()`. Silently skip on any failure — embeddings table empty check already handles the "no embeddings" case.
**Warning signs:** `OperationalError: no such function: vec_distance_cosine` means the extension was not loaded on this connection.

### Pitfall 2: Budget State File Race
**What goes wrong:** `budget_available()` reads the state, then `consume_budget()` writes it. If two CLI commands run concurrently (unlikely but possible), both could see `available=True`.
**Why it happens:** No file locking.
**How to avoid:** Acceptable at this scale (single-user CLI). Document it as a known limitation. The consequence is at most two offers on the same day — not a data integrity issue.

### Pitfall 3: Stale Query Matches System/Meta Notes
**What goes wrong:** `.meta/` directory files (config, templates, state) are not in the `notes` table (they're not captured notes), but if they ever were indexed, they'd appear as stale immediately.
**Why it happens:** `notes` table contains whatever was indexed by `sb-reindex` or `sb-capture`.
**How to avoid:** The stale query already filters by `updated_at < cutoff`. The `.meta/` path can be excluded with `AND path NOT LIKE '%/.meta/%'` if needed.

### Pitfall 4: Action Item Extraction on PII Notes Leaks to Claude
**What goes wrong:** If sensitivity="pii" but ModelRouter is misconfigured (e.g., config.toml missing `pii_model`), the adapter could fall back to Claude and send PII data over the network.
**Why it happens:** Config error.
**How to avoid:** `get_adapter("pii", config_path)` uses the existing ModelRouter which enforces pii→Ollama routing. No additional bypass needed. Extraction is best-effort — if Ollama is down, the try/except swallows the error and no items are extracted.

### Pitfall 5: Git Context Detection Timeout
**What goes wrong:** `git rev-parse` blocks if run inside a network mount or slow filesystem.
**Why it happens:** git may check remote ref state on some configurations.
**How to avoid:** Set `timeout=5` on `subprocess.run`. Return `None` on `TimeoutExpired`.

### Pitfall 6: `Related:` Backlink Appended to Encrypted Notes
**What goes wrong:** If a new note has `content_sensitivity: pii` and is Fernet-encrypted (future Phase 17+), appending `Related:` via plain-text write corrupts the file.
**Why it happens:** Encryption is not yet implemented (Phase 17+), but the append pattern needs to be safe.
**How to avoid:** Check `content_sensitivity` before appending. If `pii`, skip the backlink append. Add comment in code flagging this for Phase 17 revisit.

---

## Code Examples

### Append Related Backlink to New Note
```python
# engine/intelligence.py
# Source: existing backlink pattern in engine/links.py (add_backlinks)
def _append_related_link(note_path: Path, matched_stem: str) -> None:
    """Append Related: [[stem]] to new note — one-directional, best-effort."""
    try:
        existing = note_path.read_text(encoding="utf-8")
        link_line = f"\nRelated: [[{matched_stem}]]"
        if link_line.strip() not in existing:
            note_path.write_text(existing + link_line, encoding="utf-8")
    except OSError:
        pass
```

### sb-actions CLI Entry Point Pattern
```python
# engine/intelligence.py
def actions_main(argv=None) -> None:
    import argparse
    from engine.db import get_connection, init_schema
    from engine.intelligence import migrate_add_action_items_table

    parser = argparse.ArgumentParser(prog="sb-actions", description="Manage action items")
    parser.add_argument("--done", type=int, metavar="ID", help="Mark item complete")
    args = parser.parse_args(argv)

    conn = get_connection()
    init_schema(conn)
    migrate_add_action_items_table(conn)

    if args.done is not None:
        conn.execute("UPDATE action_items SET done=1 WHERE id=?", (args.done,))
        conn.commit()
        print(f"Marked item {args.done} complete.")
        conn.close()
        return

    rows = conn.execute(
        "SELECT id, text, note_path, created_at FROM action_items WHERE done=0 ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    if not rows:
        print("No open action items.")
        return

    # Header
    print(f"{'ID':<4}  {'Action Item':<50}  {'Source':<30}  {'Date'}")
    print("-" * 100)
    for row_id, text, path, created_at in rows:
        short_path = Path(path).name if path else ""
        truncated = text[:48] + ".." if len(text) > 50 else text
        print(f"{row_id:<4}  {truncated:<50}  {short_path:<30}  {created_at[:10]}")
```

### INTL-01 CLAUDE.md Hook Line
```
**Second Brain:** When starting work in a project, offer: "I noticed you're in `{repo}` — run `sb-recap` to see recent activity?"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Polling for changes | Event-driven hooks at capture/search time | Phase 15 design | No background process needed; zero-overhead when not capturing |
| Global notification spam | Single daily budget with vault gate | Phase 15 design | Proactive features never become noise |
| Manual connection discovery | Automatic KNN at capture time | Phase 15 (Phase 14 prerequisite) | Connection suggestions require embeddings from Phase 14 |

---

## Open Questions

1. **sqlite-vec `vec_distance_cosine` exact API for installed version**
   - What we know: sqlite-vec v0.1.x is installed (`pyproject.toml`); `vec_distance_cosine` is the documented function name
   - What's unclear: exact SQL syntax for comparing a query vector against stored BLOBs; whether `enable_load_extension` works without a special SQLite build
   - Recommendation: Wave 0 of implementation should include a smoke test that loads sqlite-vec on an in-memory connection and runs a trivial `vec_distance_cosine` call. If it fails, fall back to Python-side cosine (import numpy, deserialize BLOBs, compute manually).

2. **INTL-08 stale recheck tracking granularity**
   - What we know: notes snoozed at 90 days should recheck at 180 days
   - What's unclear: whether to track snooze per-note in `intelligence_state.json` (simple dict of path→recheck_date) or add a `last_nudged_at` column to the `notes` table
   - Recommendation: use `intelligence_state.json` `stale_snoozed` dict (path→ISO date) to avoid another DB migration. The planner should make the final call.

3. **`sb-recap` note matching strategy**
   - What we know: search notes where tags or `people`/project fields contain the context name
   - What's unclear: whether FTS5 phrase search on tags JSON is reliable (tags stored as JSON array string `["tag1","tag2"]`) — searching for "acme" in `["acme-project","client"]` requires LIKE or JSON functions, not FTS5
   - Recommendation: use `SELECT ... FROM notes WHERE tags LIKE '%' || ? || '%' OR people LIKE '%' || ? || '%' OR title LIKE '%' || ? || '%'` with the context name. Simple and correct for typical tag values.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/test_intelligence.py -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTL-01 | CLAUDE.md contains session hook text | unit (file content check) | `pytest tests/test_intelligence.py::TestClaudeMdHook -x` | ❌ Wave 0 |
| INTL-02 | `sb-recap` with git context returns summary | unit (mock LLM + mock git) | `pytest tests/test_intelligence.py::TestRecap -x` | ❌ Wave 0 |
| INTL-02 | `sb-recap` without args outside git prints error | unit | `pytest tests/test_intelligence.py::TestRecapNoContext -x` | ❌ Wave 0 |
| INTL-03 | Action items extracted and stored at capture time | unit (mock adapter) | `pytest tests/test_intelligence.py::TestExtractActionItems -x` | ❌ Wave 0 |
| INTL-04 | `sb-actions` lists open items newest-first | unit (in-memory DB) | `pytest tests/test_intelligence.py::TestActionsList -x` | ❌ Wave 0 |
| INTL-05 | `sb-actions --done <id>` marks item done | unit (in-memory DB) | `pytest tests/test_intelligence.py::TestActionsDone -x` | ❌ Wave 0 |
| INTL-06 | Stale notes >90 days surface (max 5) | unit (in-memory DB with old dates) | `pytest tests/test_intelligence.py::TestStaleNudge -x` | ❌ Wave 0 |
| INTL-07 | `evergreen: true` notes excluded from stale | unit (tmp note file with frontmatter) | `pytest tests/test_intelligence.py::TestEvergreenExempt -x` | ❌ Wave 0 |
| INTL-08 | Snoozed stale note not re-nudged until 180 days | unit (mock state file) | `pytest tests/test_intelligence.py::TestStaleSnooze -x` | ❌ Wave 0 |
| INTL-09 | Connection suggestion fires when similarity > 0.8 | unit (mock find_similar) | `pytest tests/test_intelligence.py::TestConnectionSuggestion -x` | ❌ Wave 0 |
| INTL-09 | Connection suggestion silently skips empty embeddings table | unit | `pytest tests/test_intelligence.py::TestConnectionSuggestionEmpty -x` | ❌ Wave 0 |
| INTL-10 | Second proactive offer on same day is suppressed | unit (mock state file with today's date) | `pytest tests/test_intelligence.py::TestBudgetGate -x` | ❌ Wave 0 |
| INTL-10 | Budget does not gate explicit `sb-recap` / `sb-actions` | unit | `pytest tests/test_intelligence.py::TestExplicitCommandsAlwaysWork -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_intelligence.py -q`
- **Per wave merge:** `python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_intelligence.py` — covers all INTL-01 through INTL-10
- [ ] `engine/intelligence.py` — new module (stub with `pass` bodies for RED phase)
- [ ] `engine/db.py` migration function `migrate_add_action_items_table()` — covers INTL-03/04/05
- [ ] `action_items` DDL addition to `SCHEMA_SQL` constant in `engine/db.py`

---

## Sources

### Primary (HIGH confidence)
- Codebase: `engine/capture.py` — integration hook pattern (add_backlinks post-write)
- Codebase: `engine/ai.py` — LLM adapter pattern, AI-10 system prompt isolation
- Codebase: `engine/db.py` — idempotent migration pattern, existing schema
- Codebase: `engine/embeddings.py` — BLOB serialization format, provider dispatch
- Codebase: `engine/router.py` — PII routing enforcement
- Codebase: `engine/paths.py` — `META_DIR`, `DB_PATH`, `CONFIG_PATH` constants
- Codebase: `tests/conftest.py` — test fixture patterns, stub_engine_embeddings autouse fixture
- `pyproject.toml` — installed dependencies; sqlite-vec confirmed present

### Secondary (MEDIUM confidence)
- sqlite-vec v0.1.x docs (known at training time): `vec_distance_cosine(a, b)` returns cosine distance; `enable_load_extension` required per connection
- CONTEXT.md `<specifics>` section — budget check pattern, backlink format, recap strategy

### Tertiary (LOW confidence)
- sqlite-vec exact SQL syntax for BLOB-vs-BLOB KNN query — verify against installed version before implementing

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in pyproject.toml and existing engine files
- Architecture: HIGH — patterns directly derived from existing codebase conventions
- Pitfalls: HIGH — derived from reading actual code; sqlite-vec API caveat is MEDIUM
- Test map: HIGH — follows established test class pattern from test_embeddings.py

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable domain; sqlite-vec API is the only fast-moving surface)
