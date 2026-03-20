# Phase 12: Micro-Code Fixes — Research

**Researched:** 2026-03-15
**Domain:** Python CLI entry points (pyproject.toml), SQLite schema initialisation, pathlib.Path resolution, SQLite INSERT/DO UPDATE column coverage
**Confidence:** HIGH

---

## Summary

Phase 12 is surgical: five isolated code defects identified in the v1.5 audit, each requiring ≤5 lines of change in a single file. No new modules, no new dependencies. The fixes are:

1. `sb-anonymize` and `sb-update-memory` are missing from `[project.scripts]` in `pyproject.toml` — both functions already have `main()` entry points (`engine/anonymize.py` and `engine/ai.py`), so this is a one-liner addition per entry.
2. `engine/export.py:main()` calls `get_connection()` then immediately queries `notes` without first calling `init_schema(conn)` — on a fresh install the table does not exist, producing an `OperationalError`.
3. `engine/reindex.py` stores `str(md_path)` (which may be relative) instead of `str(md_path.resolve())` — this breaks `sb-forget`'s DELETE-by-path because forget resolves paths before matching.
4. `engine/reindex.py`'s INSERT omits the `people` column from both the column list and the `DO UPDATE SET` clause — so reindex silently overwrites `people` with the column default (`'[]'`), destroying data written by `sb-capture`.

All five fixes are in existing, well-tested code. The Wave 0 regression tests must be written first to lock behaviour before touching production code.

**Primary recommendation:** Write failing regression tests first (Wave 0), then apply each fix in the minimal file it lives in. The three Wave 1 plans are independent and run in parallel.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GDPR-03 | Every note creation, access, and modification recorded in audit log | `sb-anonymize` entry point enables CLI-driven anonymization; audit_log INSERT already present in `anonymize_note()` |
| GDPR-01 | `sb-forget` deletes person file, meetings, FTS5 entries, audit log, backlinks | Reindex resolve fix ensures DELETE path matches the absolute path stored by `sb-capture`/`sb-forget` |
| GDPR-05 | `.env.host` secrets never logged, never in error messages | `export.py` init_schema fix prevents OperationalError stack traces that could expose connection state; `anonymize.py` already logs only `type(e).__name__` |
| CAP-02 | YAML frontmatter includes `people` field | Reindex INSERT/DO UPDATE must include `people` column so frontmatter values survive a reindex cycle |
| AI-06 | Other AI models addable via adapter pattern without changing core logic | `sb-update-memory` entry point exposes `update_memory()` (which already uses the adapter pattern) as a callable CLI tool |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `pathlib.Path` | stdlib | Path manipulation | Already used throughout engine (FOUND-12) |
| `sqlite3` | stdlib | DB connection + schema | Already in use; `init_schema()` exists in `engine/db.py` |
| `pyproject.toml [project.scripts]` | PEP 621 / hatchling | CLI entry point registration | All existing `sb-*` commands use this mechanism |

### No New Dependencies
Phase 12 requires zero new packages. Every fix uses code already present in the codebase.

**Installation:** None required.

---

## Architecture Patterns

### Pattern 1: pyproject.toml entry point registration

**What:** Add a line to `[project.scripts]` mapping `sb-<name>` to `module:function`.

**Current state of `[project.scripts]`:**
```toml
sb-init        = "engine.init_brain:main"
sb-reindex     = "engine.reindex:main"
sb-capture     = "engine.capture:main"
sb-search      = "engine.search:main"
sb-watch       = "engine.watcher:main"
sb-check-links = "engine.links:main_check_links"
sb-install     = "scripts.install_native:main"
sb-forget      = "engine.forget:main"
sb-read        = "engine.read:main"
sb-export      = "engine.export:main"
```

**Missing entries (both `main()` functions exist and are tested):**
```toml
sb-anonymize     = "engine.anonymize:main"
sb-update-memory = "engine.ai:update_memory"
```

Note: `engine/ai.py:update_memory()` is not a `main()` — it is a direct function call. The planner must decide whether to wrap it in a `main()` shim or point the entry point directly at `update_memory`. Given it takes `(note_type, summary, config_path)` arguments, a `main()` wrapper with argparse is the correct pattern (consistent with every other `sb-*` CLI). The `main()` in `engine/anonymize.py` already exists. `engine/ai.py` needs a `main()` added.

### Pattern 2: init_schema() before first query

**What:** In `engine/export.py:main()`, call `init_schema(conn)` immediately after `get_connection()`, before any SELECT.

**Current code (lines 80-82):**
```python
conn = get_connection()
try:
    count = export_brain(brain_root, conn, output_path)
```

**Required fix:**
```python
from engine.db import get_connection, init_schema   # init_schema already imported elsewhere
conn = get_connection()
init_schema(conn)
try:
    count = export_brain(brain_root, conn, output_path)
```

`init_schema()` is idempotent (`IF NOT EXISTS` throughout `SCHEMA_SQL`) — safe to call even when schema already exists.

### Pattern 3: Absolute path storage in reindex

**What:** Replace `str(md_path)` with `str(md_path.resolve())` in `engine/reindex.py`.

**Current code (line 41):**
```python
note_path = str(md_path)
```

**Required fix:**
```python
note_path = str(md_path.resolve())
```

`Path.resolve()` returns an absolute path with symlinks resolved, consistent with how `engine/capture.py` stores paths (Phase 7 fix) and how `engine/forget.py` resolves paths before DELETE.

### Pattern 4: Include `people` in reindex INSERT/DO UPDATE

**What:** Add `people` to the INSERT column list and to the `DO UPDATE SET` clause in `engine/reindex.py`.

**Current INSERT (lines 51-73):**
```python
conn.execute(
    """
    INSERT INTO notes (path, type, title, body, tags, created_at, updated_at, sensitivity)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(path) DO UPDATE SET
        type=excluded.type,
        title=excluded.title,
        body=excluded.body,
        tags=excluded.tags,
        updated_at=excluded.updated_at,
        sensitivity=excluded.sensitivity
    """,
    (
        note_path,
        meta.get("type", "note"),
        meta.get("title", md_path.stem),
        post.content,
        tags_json,
        meta.get("created_at", now),
        now,
        meta.get("content_sensitivity", "public"),
    ),
)
```

**Required additions:**
- Column list: add `people` after `sensitivity`
- VALUES tuple: add `json.dumps(meta.get("people", []))` (same pattern as `tags_json`)
- `DO UPDATE SET`: add `people=excluded.people`

The `people` column exists in the schema (added via `migrate_add_people_column()` called from `init_schema()`). The `tags` handling pattern (`json.dumps(...)`) is the correct model.

### Anti-Patterns to Avoid
- **Wrapping `init_schema()` call inside `export_brain()` function itself:** The library function `export_brain()` receives a `conn` argument and should not mutate schema — schema init belongs at the call site (`main()`). Tests pass a pre-initialized `db_conn` fixture; adding `init_schema()` inside `export_brain()` would not break tests but violates the single-responsibility pattern already established across the engine.
- **Using `str(md_path.absolute())` instead of `str(md_path.resolve())`:** `absolute()` does not resolve symlinks; `resolve()` is the correct call and matches what `capture.py` uses.
- **Adding `people` only to INSERT, not to `DO UPDATE SET`:** The upsert would fail to update the `people` field on subsequent reindexes, leaving stale data after a note's people field changes.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema idempotency | Custom table-existence check | `init_schema()` from `engine/db.py` | Already uses `IF NOT EXISTS` throughout; tested |
| Absolute path conversion | Custom `os.path.abspath()` logic | `pathlib.Path.resolve()` | Already used in `engine/anonymize.py` line 46; consistent |
| CLI argument parsing for `sb-update-memory` | Custom stdin parser | `argparse` | Every other `sb-*` command uses argparse; stay consistent |

---

## Common Pitfalls

### Pitfall 1: `sb-update-memory` entry point points at a non-`main()` function
**What goes wrong:** `engine/ai.py:update_memory(note_type, summary, config_path)` takes three required args — if pointed at directly as an entry point it cannot be called from the shell without wrapping.
**Why it happens:** The function was designed as a library call, not a CLI.
**How to avoid:** Add a `main()` function to `engine/ai.py` that uses argparse to accept `--note-type`, `--summary`, `--config-path` then calls `update_memory()`. The entry point then points at `engine.ai:main`.
**Warning signs:** `sb-update-memory --help` errors with `TypeError` rather than showing usage.

### Pitfall 2: `people` frontmatter value is not always a list
**What goes wrong:** If a note has `people: "Alice"` (string) instead of `people: ["Alice"]`, `json.dumps(meta.get("people", []))` will store `'"Alice"'` (a JSON string, not array).
**Why it happens:** YAML parses single values without brackets as strings, not lists.
**How to avoid:** Apply the same normalisation pattern used for `tags`:
```python
people = meta.get("people", [])
if isinstance(people, list):
    people_json = json.dumps(people)
else:
    people_json = json.dumps([str(people)])
```
**Warning signs:** `json.loads(people)` returns a string instead of list in downstream consumers.

### Pitfall 3: `init_schema` import missing in `export.py:main()`
**What goes wrong:** `engine/export.py` currently imports `get_connection` inside `main()` but not `init_schema`. Adding the call without updating the import raises `NameError`.
**Why it happens:** The import block at the top of `export.py` (`import sqlite3`, etc.) does not include engine internals — they are lazy-imported inside `main()`.
**How to avoid:** Add `init_schema` to the same lazy import line: `from engine.db import get_connection, init_schema`.

### Pitfall 4: Regression test for `people` column preservation must use `reindex_brain()`, not direct INSERT
**What goes wrong:** A test that inserts a row with `people` set, then calls `reindex_brain()`, will see `people` overwritten to `'[]'` because the current INSERT omits the column — this is exactly the bug being fixed. The test must assert `people != '[]'` AFTER the fix.
**Why it happens:** Writing the test after the fix masks whether the test would have caught the bug.
**How to avoid:** Write the test first (Wave 0), confirm it fails, then apply the fix and confirm it passes.

---

## Code Examples

### Regression test pattern for pyproject entry points
```python
# Source: existing test_install_native.py pattern + subprocess.run
import subprocess
import sys

def test_sb_anonymize_help():
    result = subprocess.run(
        [sys.executable, "-m", "engine.anonymize", "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0

# For entry-point tests (after uv tool install):
def test_sb_anonymize_entry_point_registered():
    import importlib.metadata
    eps = {ep.name: ep for ep in importlib.metadata.entry_points(group="console_scripts")}
    assert "sb-anonymize" in eps
    assert "sb-update-memory" in eps
```

### Regression test for export fresh-install (no pre-existing schema)
```python
# Source: engine/db.py init_schema() + engine/export.py
def test_export_main_fresh_install(tmp_path, monkeypatch):
    """sb-export must not raise OperationalError on a fresh DB."""
    import sqlite3
    from engine.export import main as export_main
    db_path = tmp_path / "brain.db"
    monkeypatch.setenv("BRAIN_DB_PATH", str(db_path))
    # Should not raise — init_schema() must be called before SELECT
    # Use in-memory conn to simulate fresh install
    conn = sqlite3.connect(":memory:")
    from engine.db import init_schema
    # Test that export_brain does NOT require caller to pre-init:
    # After fix, main() calls init_schema(conn) before export_brain()
    from engine.export import export_brain
    output = tmp_path / "out.json"
    count = export_brain(tmp_path, conn, output)  # schema init happens in main()
    assert count == 0  # empty DB is valid
```

### Regression test for reindex people column preservation
```python
# Source: test_reindex.py pattern
def test_reindex_preserves_people_column(brain_root, db_conn):
    """After reindex, people field from frontmatter must be stored."""
    from engine.db import init_schema
    from engine.reindex import reindex_brain
    init_schema(db_conn)
    note = brain_root / "alice.md"
    note.write_text("---\ntype: people\ntitle: Alice\npeople: [alice]\n---\nProfile")
    reindex_brain(brain_root, db_conn)
    row = db_conn.execute("SELECT people FROM notes WHERE path LIKE '%alice.md'").fetchone()
    assert row is not None
    import json
    people = json.loads(row[0])
    assert "alice" in people  # must not be [] (the default)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Entry points registered manually after coding | Entry points added to pyproject.toml in same plan as `main()` | Phase 1 standard | Phase 12 is paying tech debt from Phase 11 (anonymize) and Phase 3 (update_memory) |
| `str(md_path)` — may be relative | `str(md_path.resolve())` — always absolute | Phase 6 capture.py, Phase 7 reindex gap | Reindex was missed in Phase 6/7 fixes |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_reindex.py tests/test_export.py tests/test_ai.py tests/test_anonymize.py -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GDPR-03 | `sb-anonymize` entry point registered | unit | `uv run pytest tests/test_anonymize.py -q` | ✅ (needs new test) |
| AI-06 | `sb-update-memory` entry point registered | unit | `uv run pytest tests/test_ai.py -q` | ✅ (needs new test) |
| GDPR-05 | `sb-export` fresh-install no OperationalError | unit | `uv run pytest tests/test_export.py -q` | ✅ (needs new test) |
| GDPR-01 | After reindex+forget, DELETE matches >0 rows | unit | `uv run pytest tests/test_reindex.py tests/test_forget.py -q` | ✅ (needs new test) |
| CAP-02 | After reindex, `people` field preserved | unit | `uv run pytest tests/test_reindex.py -q` | ✅ (needs new test) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_reindex.py tests/test_export.py tests/test_ai.py tests/test_anonymize.py -q`
- **Per wave merge:** `uv run pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_reindex.py` — add `test_reindex_preserves_people_column` and `test_reindex_stores_resolved_absolute_paths` (confirm `.resolve()`)
- [ ] `tests/test_export.py` — add `test_export_main_initialises_schema_on_fresh_db`
- [ ] `tests/test_anonymize.py` — add `test_sb_anonymize_entry_point_registered`
- [ ] `tests/test_ai.py` — add `test_sb_update_memory_entry_point_registered` + `test_update_memory_main_argparse`

---

## Open Questions

1. **`engine/ai.py:update_memory()` needs a `main()` wrapper**
   - What we know: The function signature `update_memory(note_type, summary, config_path)` takes three required args; no `main()` exists in `engine/ai.py`.
   - What's unclear: Whether `config_path` should default to a standard location (e.g., `BRAIN_ROOT / ".meta/config.toml"`) so it can be omitted from CLI for normal use.
   - Recommendation: Default `config_path` to `None` in `main()` and resolve to `BRAIN_ROOT / ".meta/config.toml"` if not provided, matching the pattern in `engine/capture.py`.

2. **`test_sb_anonymize_entry_point_registered` — subprocess vs importlib.metadata**
   - What we know: `importlib.metadata.entry_points()` requires the package to be installed (editable or otherwise); in CI with `uv run pytest` this is satisfied.
   - What's unclear: Whether the test environment always has the package installed in editable mode.
   - Recommendation: Use `importlib.metadata` — it is the canonical approach and matches the project's `uv tool install --editable` native install pattern from Phase 4.1.

---

## Sources

### Primary (HIGH confidence)
- Direct source inspection: `engine/reindex.py`, `engine/export.py`, `engine/anonymize.py`, `engine/ai.py`, `engine/db.py` — line-level defect confirmation
- Direct source inspection: `pyproject.toml` — confirmed missing entry points
- Direct source inspection: `tests/conftest.py`, `tests/test_reindex.py`, `tests/test_export.py` — test patterns confirmed

### Secondary (MEDIUM confidence)
- PEP 621 / hatchling documentation: `[project.scripts]` entry point format
- Python docs: `pathlib.Path.resolve()` vs `absolute()` semantics

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all changes are in existing, read files
- Architecture: HIGH — exact line numbers and code verified from source
- Pitfalls: HIGH — derived from direct code inspection, not inference

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable — no external dependencies)
