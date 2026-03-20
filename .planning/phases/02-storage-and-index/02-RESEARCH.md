# Phase 2: Storage and Index - Research

**Researched:** 2026-03-14
**Domain:** Python CLI capture, atomic file writes, YAML frontmatter, SQLite FTS5 search, audit log, secret hygiene
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CAP-01 | `/sb-capture` CLI prompts for content type, title, body, optional tags; writes atomic markdown note with YAML frontmatter | argparse + `input()` or typer prompts; atomic write via `tempfile` + `os.replace`; `frontmatter.dumps()` for serialisation |
| CAP-02 | YAML frontmatter includes: `type`, `title`, `date`, `tags`, `people`, `created_at`, `updated_at`, `content_sensitivity` | python-frontmatter Post object; all fields already in `notes` schema; `people` is new field — needs DB column or JSON store |
| CAP-03 | Capture is atomic: write file then index; if indexing fails, file write is rolled back | Two-phase pattern: write temp → index → rename; on index exception, delete temp file and re-raise |
| CAP-07 | Notes use consistent Markdown templates per content type (defined in `.meta/templates/`) | Template files in `TEMPLATES_DIR`; `string.Template` or f-string substitution; one `.md` template per content type |
| SEARCH-01 | `/sb-search <query>` performs FTS5 full-text search across all notes with BM25 ranking | FTS5 `MATCH` + `ORDER BY bm25(notes_fts)` ASC (scores are negative; most-negative = best match) |
| SEARCH-02 | `/sb-search --type <type> <query>` scopes search to single content type | JOIN `notes_fts` with `notes` table; add `WHERE n.type = ?` filter |
| GDPR-03 | Every note creation, access, and modification recorded in `audit_log` with timestamp and operation type | `audit_log` table already in schema; insert row with `event_type`, `note_path`, ISO 8601 `created_at` after each operation |
| GDPR-05 | `.env.host` secrets never logged, never in error messages, never written to any file except `.env.host` | No secret interpolation in f-strings or log calls; `detect-secrets` scan already enforced via pre-commit |
| GDPR-06 | Engine passes `detect-secrets` scan (zero baseline violations) — enforced in CI | Already passing from Phase 1; Phase 2 must not introduce new violations; run `detect-secrets scan --baseline .secrets.baseline` in CI |
</phase_requirements>

---

## Summary

Phase 2 builds on the Phase 1 foundation (SQLite schema, FTS5 triggers, `engine/db.py`, `engine/paths.py`) to deliver the first user-visible features: capturing a note and searching for it. The schema already has everything needed — `notes`, `notes_fts`, `audit_log`, `relationships` tables with WAL mode and BM25 triggers. No schema changes are required.

The two highest-risk items are atomicity (CAP-03) and the `people` frontmatter field (CAP-02). Atomicity requires a two-phase write: write the markdown to a temp file in the same directory, attempt SQLite index insert, then `os.replace()` to commit — all inside a `try/except` that deletes the temp file on failure. The `people` field is not in the current `notes` table; the cleanest approach is to store it as JSON text (same pattern as `tags`) rather than adding a schema migration at this stage.

The FTS5 BM25 search (SEARCH-01/02) is straightforward: scores are *negative* (more negative = more relevant), so `ORDER BY bm25(notes_fts)` ascending gives best-first. The `--type` filter requires a JOIN from `notes_fts` back to `notes`. The 2-second SLA on 1000 notes is easily met by SQLite FTS5 with no tuning needed.

**Primary recommendation:** Implement `engine/capture.py` (note creation + atomic write + audit), `engine/search.py` (FTS5 query + type filter), and CLI entry points `sb-capture` / `sb-search` using argparse (consistent with Phase 1 tooling — no new CLI framework dependency). Templates live in `.meta/templates/` as plain markdown files.

---

## Standard Stack

### Core

| Library/Tool | Version | Purpose | Why Standard |
|---|---|---|---|
| python-frontmatter | 1.x (already in pyproject.toml) | Parse and write YAML frontmatter to/from markdown | Already a dependency; provides `Post`, `dumps()`, `loads()` |
| sqlite3 | stdlib | DB access, FTS5 queries, audit log writes | Already used in `engine/db.py`; no new dep |
| argparse | stdlib | CLI argument parsing for `sb-capture` and `sb-search` | Already used in `engine/init_brain.py` and `engine/reindex.py` — keep consistent |
| tempfile | stdlib | Safe temp-file creation for atomic writes | No dep; `NamedTemporaryFile(delete=False, dir=same_dir)` + `os.replace()` is the canonical stdlib pattern |
| os.replace | stdlib | Atomic rename on POSIX (same filesystem required) | POSIX rename is atomic; Windows: `os.replace` also atomic via MoveFileEx |
| datetime | stdlib | ISO 8601 timestamps for `created_at`, `updated_at`, `date` | `datetime.utcnow().isoformat() + "Z"` — consistent with existing `reindex.py` |

### Supporting

| Library/Tool | Version | Purpose | When to Use |
|---|---|---|---|
| json | stdlib | Serialise `tags` and `people` lists to text for DB column | Already used in `reindex.py` for `tags` |
| pathlib.Path | stdlib | All path handling (mandated FOUND-12) | Already enforced |
| string.Template | stdlib | Fill per-type markdown templates with capture values | Simple variable substitution; no new dep |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| argparse | typer / click | typer gives nicer prompts and `--help` auto-generation but adds a dependency; argparse is zero-dep and already used in the codebase — switch at Phase 3 if UX becomes a concern |
| `os.replace` pattern | `python-atomicwrites` library | `python-atomicwrites` is actively maintained but adds a dep; the stdlib pattern (`tempfile` + `os.replace`) is identical functionality and zero-dep |
| JSON text for `people` | Separate `note_people` join table | Join table is more queryable but requires schema migration; JSON text matches `tags` pattern and is sufficient for Phase 2 |

**No new packages needed.** All Phase 2 work uses existing dependencies.

---

## Architecture Patterns

### Files to Create in Phase 2

```
engine/
├── capture.py        # Note creation, atomic write, audit log insert
├── search.py         # FTS5 query, BM25 ranking, type filter
└── templates.py      # Load and render per-type templates from .meta/templates/

scripts/
└── (new console_scripts: sb-capture, sb-search registered in pyproject.toml)

brain/.meta/templates/   (created by sb-init or on first capture)
├── note.md
├── meeting.md
├── people.md
├── coding.md
├── strategy.md
└── idea.md

tests/
├── test_capture.py   # Atomic write, frontmatter fields, rollback behaviour
└── test_search.py    # FTS5 search results, BM25 order, type scoping
```

### Pattern 1: Atomic Two-Phase Write (CAP-03)

**What:** Write markdown to a temp file in the same directory as the target, insert into SQLite inside a transaction, then `os.replace()` the temp over the target. If the SQLite insert fails, delete the temp file and re-raise.

**Why same directory:** `os.replace()` is only atomic when source and destination are on the same filesystem. A temp file in `/tmp` and a note in `/workspace/brain/` may cross filesystem boundaries inside Docker; always use `dir=target_path.parent`.

```python
# engine/capture.py
import os
import tempfile
from pathlib import Path
import frontmatter

def write_note_atomic(target: Path, post: frontmatter.Post, conn) -> None:
    """Write a markdown note atomically.

    1. Write to temp file in same directory.
    2. Insert into SQLite (inside transaction).
    3. Rename temp → target (atomic on POSIX).
    Rolls back file write if indexing fails.
    """
    tmp_path = None
    try:
        # Step 1: write to temp file in same directory
        fd, tmp_str = tempfile.mkstemp(
            dir=str(target.parent),
            prefix=".sb-tmp-",
            suffix=".md"
        )
        tmp_path = Path(tmp_str)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(frontmatter.dumps(post))

        # Step 2: index in SQLite (raises on failure)
        _index_note(target, post, conn)

        # Step 3: atomic rename — only reaches here if indexing succeeded
        os.replace(str(tmp_path), str(target))
        tmp_path = None  # ownership transferred

    except Exception:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
        raise
```

### Pattern 2: YAML Frontmatter Schema (CAP-02)

**What:** Use `python-frontmatter.Post` to hold metadata and body; serialise with `frontmatter.dumps()`.

**All required fields for every note:**

```python
import datetime
import frontmatter

def build_post(
    note_type: str,
    title: str,
    body: str,
    tags: list[str],
    people: list[str],
    content_sensitivity: str = "public",
) -> frontmatter.Post:
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.date.today().isoformat()
    metadata = {
        "type": note_type,
        "title": title,
        "date": today,
        "tags": tags,
        "people": people,          # list of relative paths e.g. ["people/alice.md"]
        "created_at": now,
        "updated_at": now,
        "content_sensitivity": content_sensitivity,
    }
    return frontmatter.Post(body, **metadata)
```

`frontmatter.dumps(post)` produces:
```
---
type: meeting
title: Q1 Planning
date: 2026-03-14
tags: [planning, okr]
people: [people/alice.md]
created_at: 2026-03-14T12:00:00Z
updated_at: 2026-03-14T12:00:00Z
content_sensitivity: public
---

Body text here.
```

### Pattern 3: FTS5 BM25 Search (SEARCH-01 / SEARCH-02)

**Critical: BM25 scores in FTS5 are negative.** More negative = more relevant. `ORDER BY bm25(notes_fts)` ASC gives best-first. Never use DESC.

```python
# engine/search.py

def search_notes(conn, query: str, note_type: str = None, limit: int = 20) -> list[dict]:
    """Full-text search with BM25 ranking.

    Returns rows ordered best-match first.
    Optional note_type scopes to a single content folder.
    """
    if note_type:
        sql = """
            SELECT n.path, n.type, n.title, n.created_at,
                   bm25(notes_fts) AS score
            FROM notes_fts
            JOIN notes n ON notes_fts.rowid = n.id
            WHERE notes_fts MATCH ?
              AND n.type = ?
            ORDER BY bm25(notes_fts)
            LIMIT ?
        """
        rows = conn.execute(sql, (query, note_type, limit)).fetchall()
    else:
        sql = """
            SELECT n.path, n.type, n.title, n.created_at,
                   bm25(notes_fts) AS score
            FROM notes_fts
            JOIN notes n ON notes_fts.rowid = n.id
            WHERE notes_fts MATCH ?
            ORDER BY bm25(notes_fts)
            LIMIT ?
        """
        rows = conn.execute(sql, (query, limit)).fetchall()

    return [
        {"path": r[0], "type": r[1], "title": r[2], "created_at": r[3], "score": r[4]}
        for r in rows
    ]
```

**2-second SLA verification:** On a 1000-note index, FTS5 with BM25 runs in < 50ms. The SLA is not a concern but should be confirmed in a test with a fixture of 1000 synthetic notes.

### Pattern 4: Audit Log Insert (GDPR-03)

**What:** Every create/read/update gets a row in `audit_log`. This must happen inside the same DB transaction as the notes insert so it's atomic.

```python
# engine/capture.py (partial)
import datetime

def log_audit(conn, event_type: str, note_path: str) -> None:
    """Insert one row into audit_log. Call inside same transaction as note insert."""
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT INTO audit_log (event_type, note_path, created_at) VALUES (?, ?, ?)",
        (event_type, note_path, now),
    )
    # Caller calls conn.commit()
```

Audit `event_type` values: `"create"`, `"read"`, `"update"` (matches GDPR-03 requirement for operation type).

### Pattern 5: Per-Type Markdown Templates (CAP-07)

**What:** Plain markdown files in `.meta/templates/` with `${variable}` placeholders. Loaded at capture time, rendered with `string.Template.safe_substitute()`.

```
# .meta/templates/meeting.md
---
type: meeting
title: ${title}
date: ${date}
tags: ${tags}
people: ${people}
created_at: ${created_at}
updated_at: ${updated_at}
content_sensitivity: ${content_sensitivity}
---

## Attendees

${people}

## Agenda

## Notes

## Action Items
```

`capture.py` uses `build_post()` to produce the frontmatter and renders the body section from the template. Templates provide structure for the body; frontmatter is always generated programmatically (not from the template file) to ensure all required fields are present.

### Pattern 6: `people` Field — JSON-text Storage

The current `notes` table has no `people` column. Add it as a TEXT column (JSON array, same pattern as `tags`). This requires a schema migration in `db.py`.

```sql
-- Add to SCHEMA_SQL (idempotent via ALTER TABLE … IF NOT EXISTS not available in SQLite;
-- use a migration function instead)
ALTER TABLE notes ADD COLUMN people TEXT NOT NULL DEFAULT '[]';
```

**Migration pattern for SQLite (no ALTER TABLE ADD COLUMN IF NOT EXISTS):**

```python
def migrate_add_people_column(conn: sqlite3.Connection) -> None:
    """Idempotent: adds people column if absent."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(notes)").fetchall()}
    if "people" not in cols:
        conn.execute("ALTER TABLE notes ADD COLUMN people TEXT NOT NULL DEFAULT '[]'")
        conn.commit()
```

Call `migrate_add_people_column(conn)` from `get_connection()` or `init_schema()` so it runs automatically.

### Anti-Patterns to Avoid

- **Temp file in `/tmp/` or default `tempfile.gettempdir()`**: On Linux inside Docker, `/tmp` may be `tmpfs` (different filesystem from `/workspace/brain`). `os.replace()` across filesystems raises `OSError: Invalid cross-device link`. Always pass `dir=target.parent`.
- **Writing the note to final path before indexing**: If indexing fails, you have a file on disk with no index entry — violates CAP-03. Always temp-first.
- **`conn.execute()` without `conn.commit()`**: SQLite in Python defaults to implicit transactions; you must call `conn.commit()` or use a context manager `with conn:` to commit. Forgetting `commit()` means audit log and note index are silently not persisted.
- **Logging user-provided note content in error messages**: Note body may contain PII (GDPR-05). Error messages should log path and exception type, never the note body or metadata values.
- **`ORDER BY bm25(notes_fts) DESC`**: Returns *worst* matches first. Use ASC (or just `ORDER BY bm25(notes_fts)` — ASC is the default).
- **Storing `people` as a comma-separated string**: Breaks parsing when names contain commas. Use JSON array consistently with `tags`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| YAML frontmatter serialisation | Custom `---\n` string assembly | `frontmatter.dumps(post)` | Handles escaping, multi-line values, special chars in titles/tags |
| Atomic file write | Custom write + rename without temp | `tempfile.mkstemp(dir=same_dir)` + `os.replace()` | stdlib pattern; handles cleanup on exception; same-filesystem guarantee |
| FTS5 BM25 full-text search | Custom inverted index or LIKE queries | SQLite FTS5 `MATCH` + `bm25()` | Already in schema; handles tokenisation, stemming, ranking |
| ISO 8601 timestamps | Custom date formatting | `datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")` | Consistent with existing `reindex.py` pattern |
| SQLite schema migration check | Blind `ALTER TABLE` (raises if column exists) | `PRAGMA table_info(notes)` check first | SQLite has no `ALTER TABLE ADD COLUMN IF NOT EXISTS` |

**Key insight:** The entire Phase 2 surface is stdlib + python-frontmatter (already installed). Resist adding new dependencies.

---

## Common Pitfalls

### Pitfall 1: Cross-Device `os.replace()` Inside Docker

**What goes wrong:** `os.replace(tmp_path, target_path)` raises `OSError: [Errno 18] Invalid cross-device link`.

**Why it happens:** Docker mounts `/tmp` as `tmpfs` (separate filesystem). Default `tempfile.NamedTemporaryFile()` creates the temp in `/tmp`. `os.replace()` cannot cross filesystem boundaries.

**How to avoid:** Always pass `dir=target_path.parent` to `tempfile.mkstemp()`. This guarantees same filesystem.

**Warning signs:** `OSError` on rename step only, not on write step.

### Pitfall 2: FTS5 Index Out of Sync After `ON CONFLICT DO UPDATE`

**What goes wrong:** `reindex.py` uses `INSERT … ON CONFLICT(path) DO UPDATE SET …`. The UPDATE branch fires `notes_au` trigger correctly. But if capture also uses upsert, the trigger fires on UPDATE — this is correct. The risk is calling `os.replace()` *before* committing the DB transaction, leaving the FTS5 index and the note file in inconsistent states.

**How to avoid:** The order must be: (1) write temp file, (2) `conn.execute(INSERT)` + `log_audit()`, (3) `conn.commit()`, (4) `os.replace(tmp → target)`. Step 4 only executes after DB commit. If step 4 fails (extremely rare), there is a DB entry with no file — `/sb-reindex` will attempt to re-index it and fail gracefully (file not found error logged, not fatal).

**Warning signs:** File exists on disk but search returns no results; or DB row exists but file is absent.

### Pitfall 3: `audit_log` Not Populated for Read Operations

**What goes wrong:** GDPR-03 requires every *access* to be logged. It is easy to forget to insert into `audit_log` inside `search.py` when just reading notes.

**Why it happens:** Reads don't modify the `notes` table, so no trigger fires. The audit insert must be explicit.

**How to avoid:** `search.py` must call `log_audit(conn, "read", note_path)` for each returned result (or at minimum one "search" event with the query). For `/sb-capture --read` (future), the read audit log insert should be in the same function as the content retrieval.

**Warning signs:** `audit_log` has `create` rows but no `read` rows after multiple searches.

### Pitfall 4: `people` Column Missing Until Migration Runs

**What goes wrong:** Existing `brain.db` from Phase 1 has no `people` column. Phase 2 capture code that does `INSERT INTO notes (…, people, …)` fails with `table notes has no column named people`.

**Why it happens:** SQLite `CREATE TABLE IF NOT EXISTS` in `SCHEMA_SQL` does not add columns to an existing table.

**How to avoid:** Add `migrate_add_people_column()` and call it from `init_schema()`. Tests should verify it runs idempotently on a DB created by Phase 1 schema (without the `people` column).

**Warning signs:** `OperationalError: table notes has no column named people` on first capture.

### Pitfall 5: Secret Values in Error Output (GDPR-05)

**What goes wrong:** An exception handler logs the full note body or frontmatter dict, which may contain a value from `.env.host` if the user accidentally types one.

**How to avoid:** Exception messages log only: the file path, the exception class name, and the exception message. Never log `post.metadata`, `post.content`, or any user-provided string in full. Use structured error messages: `f"Failed to index {note_path}: {type(e).__name__}"`.

---

## Code Examples

### Verified: `frontmatter.dumps()` round-trip

```python
# Source: https://python-frontmatter.readthedocs.io/
import frontmatter

post = frontmatter.Post(
    "Body text",
    type="meeting",
    title="Q1 Planning",
    tags=["planning"],
    people=["people/alice.md"],
    content_sensitivity="public",
)
serialised = frontmatter.dumps(post)
# serialised starts with "---\n" and contains all metadata

reloaded = frontmatter.loads(serialised)
assert reloaded["type"] == "meeting"
assert reloaded.content == "Body text"
```

### Verified: FTS5 BM25 query (best-first)

```python
# Source: https://www.sqlite.org/fts5.html (Section 4 — Auxiliary Functions)
# BM25 returns negative scores; ORDER BY ASC = best match first

rows = conn.execute("""
    SELECT n.path, n.title, bm25(notes_fts) AS score
    FROM notes_fts
    JOIN notes n ON notes_fts.rowid = n.id
    WHERE notes_fts MATCH ?
    ORDER BY bm25(notes_fts)
    LIMIT 20
""", (query,)).fetchall()
```

### Verified: SQLite migration check for new column

```python
# Source: https://www.sqlite.org/pragma.html#pragma_table_info
# PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)

cols = {row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()}
if "people" not in cols:
    conn.execute("ALTER TABLE notes ADD COLUMN people TEXT NOT NULL DEFAULT '[]'")
    conn.commit()
```

### Verified: Atomic write with same-directory temp file

```python
# Source: https://docs.python.org/3/library/tempfile.html
# Source: https://docs.python.org/3/library/os.html#os.replace
import os, tempfile
from pathlib import Path

target = Path("/workspace/brain/meetings/2026-03-14-q1.md")
target.parent.mkdir(parents=True, exist_ok=True)

fd, tmp_str = tempfile.mkstemp(dir=str(target.parent), prefix=".sb-tmp-", suffix=".md")
tmp_path = Path(tmp_str)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
    # ... do DB work here ...
    os.replace(str(tmp_path), str(target))
    tmp_path = None
except Exception:
    if tmp_path and tmp_path.exists():
        tmp_path.unlink()
    raise
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `sqlite3` FTS3/FTS4 full-text search | FTS5 with built-in BM25 | SQLite 3.9.0 (2015); widely available by 2019 | BM25 replaces custom ranking; no extension needed |
| Manual YAML header string assembly | `python-frontmatter` `Post` + `dumps()` | Library available since ~2014 | Round-trip safe; handles edge cases |
| `os.rename()` for atomic writes | `os.replace()` | Python 3.3+ | `os.replace()` overwrites destination atomically; `os.rename()` raises on Windows if dest exists |
| Raw file writes + no rollback | Temp-file + `os.replace()` pattern | Best practice since POSIX; stdlib `tempfile` since Python 2 | Prevents partial files on crash |

**Deprecated/outdated:**
- FTS4 `matchinfo()` for ranking: Replaced by FTS5 `bm25()`. No reason to use FTS4 in new code.
- `os.rename()` for cross-platform atomic writes: Use `os.replace()` — handles Windows correctly without `FileExistsError`.

---

## Open Questions

1. **Capture CLI UX: argparse prompts vs. guided wizard**
   - What we know: `argparse` can provide all flags as optional arguments; if absent, print a usage error. Alternatively, the CLI can prompt interactively with `input()`.
   - What's unclear: Should `/sb-capture` be fully flag-driven (`sb-capture --type meeting --title "Q1 Planning"`) or wizard-style (prompts for each field)?
   - Recommendation: Implement flag-driven first (consistent with `sb-init`/`sb-reindex`). Wizard-style is a UX enhancement for Phase 3+ when typer is considered.

2. **`people` field values: free text vs. enforced path references**
   - What we know: CAP-02 says `people` contains "refs". The requirement says `brain/people/<name>.md`.
   - What's unclear: Should `/sb-capture` validate that referenced people files exist? Or accept free-text and validate later?
   - Recommendation: Accept free-text list at capture time (no validation). PEOPLE-04 (`/sb-check-links`) in Phase 4 handles orphan detection. Adding validation now would block captures when the people file doesn't exist yet.

3. **Template initialisation: who creates `.meta/templates/`?**
   - What we know: `TEMPLATES_DIR` is defined in `engine/paths.py`. `sb-init` creates `.meta/` but not the templates subdirectory.
   - Recommendation: Either extend `sb-init` (Phase 1 code) to create `templates/` and write bundled default templates, or have `capture.py` create them on first use. Extending `sb-init` is cleaner — add to `BRAIN_SUBDIRS` or as a separate step in `create_brain_structure()`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest 7.x (already in pyproject.toml dev deps) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (already exists) |
| Quick run command | `uv run --no-project --with pytest pytest tests/ -x -q` |
| Full suite command | `uv run --no-project --with pytest pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| CAP-01 | `sb-capture` creates markdown file with correct frontmatter fields | unit | `pytest tests/test_capture.py::test_capture_writes_note -x` | Wave 0 |
| CAP-02 | All 8 required frontmatter fields present and round-trip parseable | unit | `pytest tests/test_capture.py::test_frontmatter_fields_complete -x` | Wave 0 |
| CAP-03 | Index failure rolls back file write (file absent on disk after failure) | unit | `pytest tests/test_capture.py::test_rollback_on_index_failure -x` | Wave 0 |
| CAP-07 | Template file loaded and used for note body structure | unit | `pytest tests/test_capture.py::test_template_applied -x` | Wave 0 |
| SEARCH-01 | `/sb-search "phrase"` returns note containing that phrase, BM25-ordered | unit | `pytest tests/test_search.py::test_search_returns_match -x` | Wave 0 |
| SEARCH-01 | 1000-note index search completes within 2 seconds | perf | `pytest tests/test_search.py::test_search_1000_notes_perf -x` | Wave 0 |
| SEARCH-02 | `--type meeting` scopes results to meeting notes only | unit | `pytest tests/test_search.py::test_search_type_filter -x` | Wave 0 |
| GDPR-03 | Every capture produces `audit_log` row with correct event_type and timestamp | unit | `pytest tests/test_capture.py::test_audit_log_create_entry -x` | Wave 0 |
| GDPR-03 | Every search produces `audit_log` row with event_type `read` or `search` | unit | `pytest tests/test_search.py::test_audit_log_search_entry -x` | Wave 0 |
| GDPR-05 | No secret value in exception messages or log output | static | `pytest tests/test_capture.py::test_error_message_no_body_content -x` | Wave 0 |
| GDPR-06 | `detect-secrets` scan reports zero violations | CI | `detect-secrets scan --baseline .secrets.baseline` (not pytest — run in CI) | Existing |

### Sampling Rate

- **Per task commit:** `uv run --no-project --with pytest pytest tests/ -x -q`
- **Per wave merge:** `uv run --no-project --with pytest pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_capture.py` — covers CAP-01, CAP-02, CAP-03, CAP-07, GDPR-03, GDPR-05
- [ ] `tests/test_search.py` — covers SEARCH-01 (including perf), SEARCH-02, GDPR-03 (read audit)
- [ ] `conftest.py` already has `brain_root` and `db_conn` fixtures — extend with a `populated_db` fixture (1000 notes) for perf test

---

## Sources

### Primary (HIGH confidence)

- [SQLite FTS5 official docs](https://www.sqlite.org/fts5.html) — BM25 scoring, MATCH syntax, auxiliary functions, content= mode
- [Python tempfile stdlib](https://docs.python.org/3/library/tempfile.html) — `mkstemp(dir=...)` pattern
- [Python os.replace stdlib](https://docs.python.org/3/library/os.html#os.replace) — atomic rename semantics, cross-device behaviour
- [python-frontmatter docs](https://python-frontmatter.readthedocs.io/) — `Post`, `dumps()`, `loads()`, round-trip guarantee
- [SQLite PRAGMA table_info](https://www.sqlite.org/pragma.html#pragma_table_info) — column introspection for migration check

### Secondary (MEDIUM confidence)

- [python-frontmatter GitHub](https://github.com/eyeseast/python-frontmatter) — confirmed `dumps()` API and handler model
- [SQLite FTS5 in Practice — TheLinuxCode](https://thelinuxcode.com/sqlite-full-text-search-fts5-in-practice-fast-search-ranking-and-real-world-patterns/) — BM25 negative score ordering verified against official docs

### Tertiary (LOW confidence — flag for validation)

- [python-atomicwrites](https://python-atomicwrites.readthedocs.io/) — referenced only to confirm stdlib pattern is equivalent; library itself not used
- [typer prompt docs](https://typer.tiangolo.com/tutorial/prompt/) — reviewed to confirm argparse is sufficient for Phase 2; typer not adopted

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are stdlib or already in pyproject.toml; no new dependencies
- Architecture: HIGH — atomic write pattern is standard POSIX; FTS5 BM25 from official SQLite docs; migration pattern from SQLite PRAGMA docs
- Pitfalls: HIGH — cross-device link error is documented stdlib behaviour; FTS5 BM25 score sign from official SQLite docs; people column migration from existing schema analysis

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stdlib patterns are stable; python-frontmatter 1.x API is stable)
